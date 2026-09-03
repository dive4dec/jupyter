"""Python 3.14-compatible replacement for hermes-agent's tools/daemon_pool.py.

Upstream hermes-agent v2026.8.31 (version 0.21.0) shipped
``tools/daemon_pool.py`` with ``DaemonThreadPoolExecutor._adjust_thread_count``
hard-coded to the CPython **3.8-3.13** private ``ThreadPoolExecutor`` API:
it passes ``self._initializer`` and ``self._initargs`` to
``concurrent.futures.thread._worker``.

CPython **3.14** removed those two private instance attributes. The
initializer is now carried by a ``WorkerContext`` object created through
the bound ``self._create_worker_context()`` (assigned in
``ThreadPoolExecutor.__init__`` via ``prepare_context()``), and
``_worker``'s signature changed to ``_worker(executor_reference, ctx,
work_queue)``.

Consequence on Python 3.14: the *first* ``submit()`` on any
``DaemonThreadPoolExecutor`` raises

    AttributeError: 'DaemonThreadPoolExecutor' object has no
    attribute '_initializer'

and because the Hermes agent routes **every** tool call through such a
pool (``agent/tool_executor.py``: ``DaemonThreadPoolExecutor(...)``),
all tools — MCP, terminal, read_file, web_search, execute_code — fail
for the lifetime of the session. Notably this hits the Jupyter
%%hermes persona, whose container runs Python 3.14, while CLI/gateway
hosts on Python <=3.13 stay unaffected.

This module is byte-identical to upstream except for a version guard in
``_adjust_thread_count``: on >=3.14 it builds the worker args from
``self._create_worker_context()``; on <3.14 it keeps the original
initializer/initargs form. All other behaviour (daemon workers, no
``_threads_queues`` registration, idle-thread reuse) is unchanged, and
Hermes' own ``tests/tools/test_daemon_pool.py`` passes unmodified on
both 3.14 and 3.11.

The Dockerfile overwrites the installed
``site-packages/tools/daemon_pool.py`` with this file and then runs the
full Hermes daemon-pool test suite inside the image as a build-time
gate (the build fails if the fix ever regresses or the upstream file
layout changes incompatibly).
"""

from __future__ import annotations

import sys
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures.thread import _worker

__all__ = ["DaemonThreadPoolExecutor"]


class DaemonThreadPoolExecutor(ThreadPoolExecutor):
    """ThreadPoolExecutor variant whose workers do not block process exit."""

    def _adjust_thread_count(self) -> None:
        # Mirrors CPython's implementation with two changes:
        # daemon=True and no _threads_queues registration.
        if self._idle_semaphore.acquire(timeout=0):
            return

        def weakref_cb(_, q=self._work_queue):
            q.put(None)

        num_threads = len(self._threads)
        if num_threads < self._max_workers:
            thread_name = "%s_%d" % (self._thread_name_prefix or self, num_threads)
            if sys.version_info >= (3, 14):
                # Python 3.14+: _worker(exec_ref, worker_context, work_queue);
                # _initializer/_initargs were removed from ThreadPoolExecutor.
                worker_args = (
                    weakref.ref(self, weakref_cb),
                    self._create_worker_context(),
                    self._work_queue,
                )
            else:
                # Python 3.8-3.13: _worker(exec_ref, work_queue,
                # initializer, initargs).
                worker_args = (
                    weakref.ref(self, weakref_cb),
                    self._work_queue,
                    self._initializer,
                    self._initargs,
                )
            t = threading.Thread(
                name=thread_name,
                target=_worker,
                args=worker_args,
                daemon=True,
            )
            t.start()
            self._threads.add(t)
