#!/usr/bin/env python3
"""Idempotent, assertion-guarded patch for the ACP stuck-turn watchdog.

Applied to the *installed* hermes-agent (cloned from v2026.9.14 at build).
Fixes the `%%hermes` "Redirected the active turn with your correction." failure:
a turn that wedges (hung LLM stream / stuck approval) never clears
state.is_running, so every later prompt is absorbed into the active turn (or
queued behind it) and answered with nothing. We add a server-side watchdog that
hard-interrupts a session idle past HERMES_ACP_TURN_STALL_TIMEOUT seconds,
reusing the existing cancel() interrupt path (cancel_event +
request_hard_interrupt).

Re-ported for the v2026.9.14 (0.21.3) acp_adapter refactor: the streaming
callbacks now live on a per-turn `_TurnCallbacks` dataclass (cbs.*) instead of
local vars, the streaming callback is `stream_delta_cb`, and the turn-start /
turn-finished / except blocks were restructured. Anchors below match the 0.21.3
source exactly; patch_once fails the build if any anchor stops matching exactly
once, i.e. on the next hermes bump this must be re-reviewed.

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
        """    interrupted_prompt_text: str = ""
    # Per-session allocator for ACP assistant messageIds (lazily created by
    # the server so streamed chunks group into distinct assistant replies).
    message_ids: Any = None
""",
        """    interrupted_prompt_text: str = ""
    # Per-session allocator for ACP assistant messageIds (lazily created by
    # the server so streamed chunks group into distinct assistant replies).
    message_ids: Any = None
    # WATCHDOG_MARKER_HERMES_WD — turn-stall watchdog bookkeeping.
    # last_activity: wall clock (time.time) of the most recent
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
        read. The watchdog holds no lock while inspecting them - is_running is
        set/cleared under each state's runtime_lock, and a stale read here can
        only cause at most one extra (no-op) interrupt attempt.
        \"\"\"
        with self._lock:
            return list(self._sessions.values())

    def get_session(self, session_id: str) -> Optional[SessionState]:""",
    ),
]

# ─────────────────────────── server.py ───────────────────────────
# (1) imports  (2) __init__  (3) on_connect + watchdog methods
# (4) turn-start activity in _claim_turn_or_queue
# (5) callback wrappers (on the _TurnCallbacks dataclass)
# (6) cancel-clear activity in prompt()
# (7) turn-finished in _finish_turn  (8) exception path in prompt()
srv_repl = [
    (
        """import os
import threading
from collections import defaultdict, deque
""",
        """import os
import threading
import time
from collections import defaultdict, deque
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
        """                state.is_running = True
                state.current_prompt_text = user_text or "[Image attachment]"
                return None
""",
        """                state.is_running = True
                state.current_prompt_text = user_text or "[Image attachment]"
                # WATCHDOG_MARKER_HERMES_WD — start the stall clock for this turn.
                state.turn_started = time.time()
                state.last_activity = time.time()
                return None
""",
    ),
    (
        """        agent = state.agent
        agent.tool_progress_callback = cbs.tool_progress_cb
""",
        """        # WATCHDOG_MARKER_HERMES_WD — thin wrappers that refresh the
        # session's last_activity, so any client-visible activity resets the
        # stall timer. The original callbacks still run; we only timestamp
        # around them. No-ops when a callback is None (never invoked then).
        def _act() -> None:
            state.last_activity = time.time()

        for _attr in ("tool_progress_cb", "reasoning_cb", "step_cb",
                      "stream_delta_cb", "approval_cb"):
            _raw = getattr(cbs, _attr, None)
            if _raw is None:
                continue

            def _make_wrapper(_raw=_raw):
                def _wrapped(*a, **k):
                    _act()
                    return _raw(*a, **k)
                return _wrapped

            setattr(cbs, _attr, _make_wrapper())

        agent = state.agent
        agent.tool_progress_callback = cbs.tool_progress_cb
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
""",
        """        with state.runtime_lock:
            state.is_running = False
            state.current_prompt_text = ""
            # WATCHDOG_MARKER_HERMES_WD — turn finished; stop the stall clock.
            state.turn_started = 0.0
        while True:
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
