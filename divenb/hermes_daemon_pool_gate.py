"""Build-time gate for the hermes-agent daemon_pool Python-3.14 patch.

Run inside the Docker image build (see Dockerfile) as:

    python hermes_daemon_pool_gate.py <site-packages-root>

where ``<site-packages-root>`` is the directory that contains the
``tools/`` package (hermes-agent is installed flat into site-packages,
not under a ``hermes_agent/`` namespace).

The script imports the *installed* module exactly the way Hermes does
(``from tools.daemon_pool import DaemonThreadPoolExecutor``) and asserts the
behaviours that were broken before the fix. Any failure exits non-zero,
failing the image build. No third-party deps.

Before the patch, on Python 3.14, check (1) raised:
    AttributeError: 'DaemonThreadPoolExecutor' object has no attribute
    '_initializer'
"""

import subprocess
import sys
import threading

if len(sys.argv) < 2:
    print("usage: hermes_daemon_pool_gate.py <site-packages-root>", file=sys.stderr)
    sys.exit(2)
SITE_PACKAGES = sys.argv[1]
sys.path.insert(0, SITE_PACKAGES)

from concurrent.futures.thread import _threads_queues

from tools.daemon_pool import DaemonThreadPoolExecutor


def fail(msg):
    print(f"GATE FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


# (1) The exact call that raised AttributeError before the fix: submit() must
#     spawn a worker and execute on Python 3.14.
pool = DaemonThreadPoolExecutor(max_workers=2)
try:
    is_daemon, worker = pool.submit(
        lambda: (threading.current_thread().daemon, threading.current_thread())
    ).result(timeout=10)
    # (2) results are correct
    assert pool.submit(lambda: 41 + 1).result(timeout=10) == 42
finally:
    pool.shutdown(wait=True)
print("ok: submit() executes on Python 3.14 + results correct")

# (3) worker is a daemon thread
if is_daemon is not True:
    fail("worker thread must be a daemon")
print("ok: worker thread is a daemon")

# (4) worker is NOT registered in _threads_queues (the class's raison d'etre:
#     abandoned workers must never block interpreter exit via _python_exit)
if worker in _threads_queues:
    fail("worker must not be registered in _threads_queues")
print("ok: worker not in _threads_queues (exit-blocking guard holds)")

# (5) initializer/initargs still run through the 3.14 WorkerContext path
seen = []
pool2 = DaemonThreadPoolExecutor(max_workers=1, initializer=seen.append, initargs=("t",))
try:
    assert pool2.submit(lambda: 7).result(timeout=10) == 7
finally:
    pool2.shutdown(wait=True)
if seen != ["t"]:
    fail(f"initializer must run exactly once with initargs, got {seen!r}")
print("ok: initializer/initargs work (3.14 WorkerContext path)")

# (6) A wedged worker in a SEPARATE process must not block interpreter exit,
#     and that subprocess must import the INSTALLED (patched) module. We pin
#     PYTHONPATH to site-packages and drop the repo from the path so this
#     exercises the installed file, not any source clone.
script = (
    "from tools.daemon_pool import DaemonThreadPoolExecutor\n"
    "import time\n"
    "pool = DaemonThreadPoolExecutor(max_workers=1)\n"
    "pool.submit(time.sleep, 120)\n"
    "time.sleep(0.3)\n"
    "pool.shutdown(wait=False)\n"
    "print('main-done', flush=True)\n"
)
import os
import time as _time
env = dict(os.environ, PYTHONPATH=SITE_PACKAGES)
t0 = _time.time()
proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                      timeout=30, env=env, cwd="/")
dt = _time.time() - t0
if proc.returncode != 0:
    fail(f"wedged-worker subprocess exited {proc.returncode}: {proc.stderr[-300:]}")
if "main-done" not in proc.stdout:
    fail(f"wedged-worker subprocess did not finish: {proc.stdout[-300:]}")
if dt >= 10:
    fail(f"exit blocked by wedged worker ({dt:.1f}s)")
print(f"ok: wedged worker does not block exit ({dt:.1f}s) — installed module")

print("daemon_pool 3.14 patch GATE PASSED")
