#!/usr/bin/env python3
"""Idempotent, assertion-guarded patch for the ACP stuck-turn watchdog.

Applied to the *installed* hermes-agent (cloned from v2026.8.31 at build).
Fixes the `%%hermes` "Redirected the active turn with your correction." failure:
a turn that wedges (hung LLM stream / stuck approval) never clears
state.is_running, so every later prompt is swallowed into a redirect and
answered with nothing. We add a server-side watchdog that hard-interrupts a
session idle past HERMES_ACP_TURN_STALL_TIMEOUT seconds, reusing the existing
cancel() interrupt path (cancel_event + request_hard_interrupt).

Usage: patch_acp_adapter.py <site-packages-dir>
Files patched: <sp>/acp_adapter/session.py, <sp>/acp_adapter/server.py
Each file is backed up to <file>.orig-hermes-wd on first patch (idempotent).
Exits non-zero (build fails) if any anchor is missing — i.e. the upstream
file drifted and the patch must be re-reviewed.
"""
import ast
import os
import sys

SP = sys.argv[1]
SESSION = os.path.join(SP, "acp_adapter", "session.py")
SERVER = os.path.join(SP, "acp_adapter", "server.py")


def patch_once(path, replacements, marker_note):
    """Apply (old, new) replacements; each old must occur exactly once."""
    with open(path, "r", encoding="utf-8") as f:
        src = orig = f.read()

    # Idempotent: if already patched (sentinel present), skip.
    if "WATCHDOG_MARKER_HERMES_WD" in src:
        print(f"  {os.path.basename(path)}: already patched (sentinel present) — skip")
        return

    for i, (old, new) in enumerate(replacements):
        count = src.count(old)
        if count != 1:
            raise SystemExit(
                f"PATCH FAIL {path} [{marker_note}] #{i}: anchor found {count}x (need 1):\n---\n{old[:200]}\n---"
            )
        src = src.replace(old, new, 1)

    # Sanity: result must still parse.
    ast.parse(src)

    backup = path + ".orig-hermes-wd"
    if not os.path.exists(backup):
        with open(backup, "w", encoding="utf-8") as f:
            f.write(orig)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"  {os.path.basename(path)}: patched ({len(replacements)} hunks), backup at {os.path.basename(backup)}")


# ─────────────────────────── session.py ───────────────────────────
# Add activity-tracking fields to SessionState + SessionManager.all_states().
sess_repl = [
    (
        """    is_running: bool = False
    queued_prompts: List[str] = field(default_factory=list)
    runtime_lock: Any = field(default_factory=Lock)
    current_prompt_text: str = ""
    interrupted_prompt_text: str = ""
""",
        """    is_running: bool = False
    queued_prompts: List[str] = field(default_factory=list)
    runtime_lock: Any = field(default_factory=Lock)
    current_prompt_text: str = ""
    interrupted_prompt_text: str = ""
    # WATCHDOG_MARKER_HERMES_WD — turn-stall watchdog bookkeeping.
    # last_activity: monotonic-ish wall clock (time.time) of the most recent
    #   client-visible activity (streamed text, reasoning, tool start/progress,
    #   step, permission prompt). Refreshed by thin wrappers around the existing
    #   callbacks in server.py. turn_started: when the current turn began.
    # Both default to 0.0 = "no activity yet"; the watchdog only acts while
    # is_running is True, so a fresh session is never interrupted.
    last_activity: float = 0.0
    turn_started: float = 0.0
""",
    ),
    (
        """    def get_session(self, session_id: str) -> Optional[SessionState]:""",
        """    def all_states(self) -> List[SessionState]:
        \"\"\"Snapshot of all in-memory session states (for the turn-stall watchdog).

        Returns a shallow copy of the value list; each SessionState is the live
        object, so callers must treat is_running/last_activity as a momentary
        read. The watchdog holds no lock while inspecting them — is_running is
        set/cleared under each state's runtime_lock, and a stale read here can
        only cause at most one extra (no-op) interrupt attempt.
        \"\"\"
        with self._lock:
            return list(self._sessions.values())

    def get_session(self, session_id: str) -> Optional[SessionState]:""",
    ),
]

# ─────────────────────────── server.py ───────────────────────────
# (1) imports  (2) __init__  (3) on_connect  (4) watchdog methods
# (5) turn-start activity  (6) callback wrappers  (7) clear activity on end
srv_repl = [
    (
        """import asyncio
from datetime import datetime, timezone
import base64
import contextvars
import json
import logging
import os
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
""",
        """import asyncio
from datetime import datetime, timezone
import base64
import contextvars
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
""",
    ),
    (
        """        self.session_manager = session_manager or SessionManager()
        self._conn: Optional[acp.Client] = None
""",
        """        self.session_manager = session_manager or SessionManager()
        self._conn: Optional[acp.Client] = None
        # WATCHDOG_MARKER_HERMES_WD — turn-stall watchdog (see _turn_watchdog_loop).
        # A turn with no client-visible activity for HERMES_ACP_TURN_STALL_TIMEOUT
        # seconds is hard-interrupted via the existing cancel() path. Default 300s;
        # set to <=0 to disable.
        try:
            self._turn_stall_timeout = float(os.environ.get("HERMES_ACP_TURN_STALL_TIMEOUT", "300"))
        except (TypeError, ValueError):
            self._turn_stall_timeout = 300.0
        self._watchdog_thread: Optional[threading.Thread] = None
""",
    ),
    (
        """    def on_connect(self, conn: acp.Client) -> None:
        \"\"\"Store the client connection for sending session updates.\"\"\"
        self._conn = conn
        logger.info("ACP client connected")
""",
        """    def on_connect(self, conn: acp.Client) -> None:
        \"\"\"Store the client connection for sending session updates.\"\"\"
        self._conn = conn
        logger.info("ACP client connected")
        self._start_turn_watchdog()

    def _start_turn_watchdog(self) -> None:
        \"\"\"Start the per-process turn-stall watchdog (idempotent).

        Mirrors the chat gateway's HERMES_TURN_LEASE_TIMEOUT protection at the
        ACP-server level: polls each running session and, if one has had no
        client-visible activity past the stall threshold, hard-interrupts it
        using the same mechanism the manual Stop button uses (cancel_event +
        request_hard_interrupt). Activity-based, so long healthy turns that
        stream every few seconds are never touched.
        \"\"\"
        if self._turn_stall_timeout <= 0:
            return  # disabled
        if self._watchdog_thread is not None and self._watchdog_thread.is_alive():
            return
        timeout = self._turn_stall_timeout
        # Poll fast enough to react, never so fast it burns CPU: 2-10 s.
        poll = max(2.0, min(10.0, timeout / 3.0))
        t = threading.Thread(target=self._turn_watchdog_loop, args=(poll,),
                             daemon=True, name="acp-turn-watchdog")
        self._watchdog_thread = t
        t.start()
        logger.info("ACP turn-stall watchdog started (timeout=%.0fs, poll=%.1fs)", timeout, poll)

    def _turn_watchdog_loop(self, poll_interval: float) -> None:
        while True:
            time.sleep(poll_interval)
            try:
                self._turn_watchdog_tick()
            except Exception:
                logger.debug("ACP turn-stall watchdog tick failed", exc_info=True)

    def _turn_watchdog_tick(self) -> None:
        now = time.time()
        for state in self.session_manager.all_states():
            try:
                if not getattr(state, "is_running", False):
                    continue
                idle = now - getattr(state, "last_activity", 0.0)
                started = getattr(state, "turn_started", 0.0) or now
                # Only act when the turn has been running, has had a chance to
                # produce activity, and has been idle past the threshold. The
                # elapsed-since-start guard avoids interrupting a turn in its
                # first moment before any callback has fired yet.
                if idle >= self._turn_stall_timeout and (now - started) >= self._turn_stall_timeout:
                    logger.warning(
                        "ACP watchdog: session %s idle %.0fs with no activity -> hard-interrupting",
                        state.session_id, idle,
                    )
                    if state.cancel_event:
                        with state.runtime_lock:
                            state.cancel_event.set()
                    try:
                        request_hard_interrupt(
                            state.agent,
                            tool_reason="turn_stall",
                        )
                    except Exception:
                        logger.debug("ACP watchdog: interrupt failed for %s",
                                     state.session_id, exc_info=True)
            except Exception:
                logger.debug("ACP watchdog: error handling session %s",
                             getattr(state, "session_id", "?"), exc_info=True)
""",
    ),
    (
        """            else:
                state.is_running = True
                state.current_prompt_text = user_text or "[Image attachment]"
""",
        """            else:
                state.is_running = True
                state.current_prompt_text = user_text or "[Image attachment]"
                # WATCHDOG_MARKER_HERMES_WD — start the stall clock for this turn.
                state.turn_started = time.time()
                state.last_activity = time.time()
""",
    ),
    (
        """            approval_cb = make_approval_callback(conn.request_permission, loop, session_id)
""",
        """            approval_cb = make_approval_callback(conn.request_permission, loop, session_id)

            # WATCHDOG_MARKER_HERMES_WD — thin wrappers that refresh the
            # session's last_activity, so any client-visible activity resets the
            # stall timer. The original callbacks still run; we only timestamp
            # around them. (No-ops if the session somehow isn't tracked.)
            def _act() -> None:
                state.last_activity = time.time()

            _raw_tool_progress_cb = tool_progress_cb
            _raw_reasoning_cb = reasoning_cb
            _raw_step_cb = step_cb
            _raw_message_cb = message_cb
            _raw_approval_cb = approval_cb

            def _wrapped_tool_progress_cb(*a, **k):
                _act(); return _raw_tool_progress_cb(*a, **k)
            def _wrapped_reasoning_cb(*a, **k):
                _act(); return _raw_reasoning_cb(*a, **k)
            def _wrapped_step_cb(*a, **k):
                _act(); return _raw_step_cb(*a, **k)
            def _wrapped_message_cb(*a, **k):
                _act(); return _raw_message_cb(*a, **k)
            def _wrapped_approval_cb(*a, **k):
                _act(); return _raw_approval_cb(*a, **k)

            tool_progress_cb = _wrapped_tool_progress_cb
            reasoning_cb = _wrapped_reasoning_cb
            step_cb = _wrapped_step_cb
            message_cb = _wrapped_message_cb
            approval_cb = _wrapped_approval_cb
""",
    ),
    (
        """        if state.cancel_event:
            state.cancel_event.clear()
""",
        """        if state.cancel_event:
            state.cancel_event.clear()
        # WATCHDOG_MARKER_HERMES_WD — refresh activity at turn start (covers the
        # window before the first streamed callback fires).
        state.last_activity = time.time()
        state.turn_started = time.time()
""",
    ),
    (
        """        with state.runtime_lock:
            state.is_running = False
            state.current_prompt_text = ""

        while True:
            with state.runtime_lock:
                if not state.queued_prompts:
                    break
""",
        """        with state.runtime_lock:
            state.is_running = False
            state.current_prompt_text = ""
            # WATCHDOG_MARKER_HERMES_WD — turn finished; stop the stall clock.
            state.turn_started = 0.0

        while True:
            with state.runtime_lock:
                if not state.queued_prompts:
                    break
""",
    ),
    (
        """        except Exception:
            logger.exception("Executor error for session %s", session_id)
            with state.runtime_lock:
                state.is_running = False
                state.current_prompt_text = ""
            return PromptResponse(stop_reason="end_turn")
""",
        """        except Exception:
            logger.exception("Executor error for session %s", session_id)
            with state.runtime_lock:
                state.is_running = False
                state.current_prompt_text = ""
                # WATCHDOG_MARKER_HERMES_WD — exception path: stop the stall clock.
                state.turn_started = 0.0
            return PromptResponse(stop_reason="end_turn")
""",
    ),
]

patch_once(SESSION, sess_repl, "session")
patch_once(SERVER, srv_repl, "server")
print("acp_adapter patch applied OK")
