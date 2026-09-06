#!/usr/bin/env python3
"""Functional verification of the ACP turn-stall watchdog + redirect recovery.

Runs INSIDE a container with hermes-agent installed. Imports the REAL
acp_adapter.server/session (patched) and drives HermesACPAgent.prompt() with a
fake agent to prove, with no LLM:

  Case S (stall rescue):
    - turn1 blocks with NO activity  -> watchdog hard-interrupts it
    - a prompt sent while turn1 runs -> returns the redirect ack (symptom)
    - is_running clears after interrupt
    - a retry prompt -> runs normally, NOT redirected  (recovery)

  Case H (healthy, must NOT be interrupted):
    - a turn that streams activity every ~0.5s for ~3s
    - watchdog (2s threshold) never fires
    - turn completes normally

Verdict PASS only if both cases behave exactly as above.
"""
import os
import sys
import time
import asyncio
import logging
import threading

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

# Low timeout so the test runs in a few seconds.
os.environ["HERMES_ACP_TURN_STALL_TIMEOUT"] = "2"

from acp_adapter.server import HermesACPAgent  # noqa: E402
from acp_adapter.session import SessionManager  # noqa: E402
from acp.schema import TextContentBlock  # noqa: E402

REDIRECT_STR = "Redirected the active turn with your correction."


def T(text):
    return [TextContentBlock(text=text, type="text")]


class FakeAgent:
    """Stand-in for AIAgent. mode='block' wedges turn1; mode='healthy' streams."""

    def __init__(self, mode):
        self.mode = mode
        self.session_id = "fake-internal"
        self.model = "fake-model"
        self.provider = ""
        self.base_url = ""
        self.api_mode = ""
        self.history = []
        self._supports_active_turn_redirect = True
        self._interrupted = False
        self._wake = threading.Event()
        # callbacks assigned by prompt()
        self.tool_progress_callback = None
        self.reasoning_callback = None
        self.step_callback = None
        self.stream_delta_callback = None
        self.thinking_callback = None
        self._on_session_title = None
        self.redirect_calls = []

    def redirect(self, content):
        self.redirect_calls.append(content)
        return True

    def hard_interrupt(self, message=None, *, tool_reason=None):
        self._interrupted = True
        self._wake.set()

    def run_conversation(self, user_message=None, conversation_history=None,
                         task_id=None, persist_user_message=None, **kw):
        hist = list(conversation_history or [])
        if self.mode == "block":
            # No activity at all -> wedge until the watchdog interrupts.
            self._wake.wait(timeout=30)
            return {"final_response": "", "messages": hist, "interrupted": True}
        # healthy: emit activity every ~0.5s for ~3s
        end = time.time() + 3.0
        while time.time() < end:
            if self._interrupted:
                break
            if self.stream_delta_callback is not None:
                try:
                    self.stream_delta_callback("tok ")
                except Exception:
                    pass
            self._wake.wait(timeout=0.5)
        return {"final_response": "ok-healthy", "messages": hist,
                "interrupted": self._interrupted}


class FakeConn:
    def __init__(self):
        self.updates = []

    async def session_update(self, sid, update, **k):
        txt = ""
        c = getattr(update, "content", None)
        if c is not None:
            txt = getattr(c, "text", None) or ""
        self.updates.append(txt)

    async def request_permission(self, *a, **k):
        return None

    async def cancel(self, sid, **k):
        pass


def had_redirect(conn):
    return any(REDIRECT_STR in u for u in conn.updates)


async def case_s():
    print("\n=== Case S: stalled turn rescued by watchdog ===")
    mgr = SessionManager(agent_factory=lambda: FakeAgent("block"))
    agent = HermesACPAgent(session_manager=mgr)
    conn = FakeConn()
    agent._conn = conn
    agent._start_turn_watchdog()
    state = mgr.create_session(cwd="/tmp")
    sid = state.session_id

    # turn1 starts and wedges (blocks, no activity)
    t1 = asyncio.create_task(agent.prompt(T("question 1"), sid))
    await asyncio.sleep(1.0)  # let turn1 go is_running=True

    # turn2 while turn1 running -> should get the redirect ack (the symptom)
    conn.updates.clear()
    t2 = await agent.prompt(T("question 2 (correction)"), sid)
    s2_redirect = had_redirect(conn)
    s2_reason = t2.stop_reason

    # await turn1: watchdog should hard-interrupt it (~2s threshold)
    t1_done = await asyncio.wait_for(t1, timeout=15)
    is_running_after = state.is_running
    t1_reason = t1_done.stop_reason

    # turn3 retry -> must run, NOT be redirected
    conn.updates.clear()
    t3 = await agent.prompt(T("question 3 retry"), sid)
    t3_redirect = had_redirect(conn)
    t3_reason = t3.stop_reason
    is_running_final = state.is_running

    print(f"[S] turn2 redirect_ack={s2_redirect} stop={s2_reason}")
    print(f"[S] turn1 stop={t1_reason} is_running_after={is_running_after}")
    print(f"[S] turn3 redirect={t3_redirect} stop={t3_reason} is_running_final={is_running_final}")
    ok = (s2_redirect and s2_reason == "end_turn"
          and (not is_running_after)
          and (not t3_redirect) and t3_reason == "end_turn"
          and (not is_running_final))
    print(f"[S] PASS={ok}")
    return ok


async def case_h():
    print("\n=== Case H: healthy streaming turn must NOT be interrupted ===")
    mgr = SessionManager(agent_factory=lambda: FakeAgent("healthy"))
    agent = HermesACPAgent(session_manager=mgr)
    conn = FakeConn()
    agent._conn = conn
    agent._start_turn_watchdog()
    state = mgr.create_session(cwd="/tmp")
    sid = state.session_id

    t0 = time.time()
    resp = await agent.prompt(T("question H"), sid)
    elapsed = time.time() - t0
    fa = mgr.get_session(sid).agent
    interrupted = fa._interrupted
    is_running = state.is_running
    print(f"[H] stop={resp.stop_reason} elapsed={elapsed:.1f}s interrupted={interrupted} is_running={is_running}")
    ok = (not interrupted) and (is_running is False) and (resp.stop_reason in ("end_turn", "cancelled"))
    print(f"[H] PASS={ok}")
    return ok


async def main():
    s = await case_s()
    h = await case_h()
    verdict = "PASS" if (s and h) else "FAIL"
    print(f"\nVERDICT: {verdict} (stall_rescue={s}, healthy_untouched={h})")
    return 0 if (s and h) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
