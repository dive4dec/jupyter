# devenb Changelog

## 0.2.39 (2026-08-25)

### Fixes
- **Fix all Hermes tools broken on Python 3.14** (`DaemonThreadPoolExecutor
  has no attribute '_initializer'`).
  hermes-agent v2026.8.19 (0.20.5) ships `tools/daemon_pool.py` with
  `DaemonThreadPoolExecutor._adjust_thread_count` hard-coded to the CPython
  3.8–3.13 `ThreadPoolExecutor` private API (`self._initializer` /
  `self._initargs` passed to `_worker`). CPython 3.14 removed those
  attributes (the initializer now lives in a `WorkerContext` created via
  `self._create_worker_context()`, and `_worker`'s signature changed to
  `_worker(exec_ref, ctx, work_queue)`). Because Hermes routes **every**
  tool call through a `DaemonThreadPoolExecutor` (`agent/tool_executor.py`),
  the first tool dispatch on 3.14 raised
  `AttributeError: 'DaemonThreadPoolExecutor' object has no attribute
  '_initializer'` and every tool — Jupyter MCP, terminal, `read_file`,
  `web_search`, `execute_code` — failed for the rest of the session.
  This image runs Python 3.14, so the `%%hermes` persona was fully broken
  (its "MCP is down" self-diagnosis was a red herring — the MCP server on
  `localhost:3001` was fine; the agent's own tool dispatcher was crashing).
  Fix: the Dockerfile now overwrites the installed
  `site-packages/tools/daemon_pool.py` with `hermes_daemon_pool_314.py`
  (byte-identical to upstream except a `sys.version_info >= (3, 14)`
  guard in `_adjust_thread_count`) and runs `hermes_daemon_pool_gate.py`
  in the build — a self-contained gate (no third-party deps) that
  exercises the installed module: submit/results, daemon flag,
  `_threads_queues` absence, initializer/initargs, and a wedged-worker
  exit check in a subprocess pinned to site-packages. The build fails if
  the fix regresses. Re-run/verify this step after any hermes-agent
  version bump.

## 0.2.38 (2026-08-22)

### Upgrades
- **code-server 4.131.0 → 4.133.0**
- **Obsidian 1.13.4 → 1.13.7** (1.13.8 shipped no Linux desktop build, only an APK)
- **emsdk 6.0.5 → 6.0.8**
- **TurboVNC 3.3 → 3.3.1**
- **micromamba 2.8.1-1 → 2.9.0-0** (re-resolves the conda env on build)
- **hermes-agent v2026.7.30 → v2026.8.19** (version 0.20.5)
  - `agent-client-protocol` is still pinned `==0.9.0` by the `[acp]` extra, so the
    Dockerfile's final ACP pin and the `jupyter-ai-hermes` workaround are unchanged.
  - The two `acp_adapter/server.py` cancel/stop-button sed patches still apply
    (code at the same logical location).
  - `HERMES_NIX_BUILD=1` and the `web_dist` build+copy steps are still required
    (`web_dist/` remains gitignored, not in package-data).
  - Hermes' Matrix extra now pins `mautrix 0.21.1` / `aiohttp-socks 0.11.0` /
    `asyncpg 0.31.0` / `aiosqlite 0.22.1` — identical to the versions the
    Dockerfile installs separately, so no dependency conflict.

### Fixes
- **Obsidian .desktop path**: since 1.13.7 the desktop file is
  `md.obsidian.Obsidian.desktop` (was `obsidian.desktop`). The wrapper
  `sed` now globs `*bsidian*.desktop` under `/usr/share/applications`, so the
  `Exec=` rewrite no longer fails with "No such file or directory".
- **Pin `evcxr_jupyter` to 0.21.1**: the Rust-kernel step previously ran an
  unpinned `cargo install evcxr_jupyter`, which re-resolves to the latest when
  the layer is rebuilt. 0.22.0 depends on rust-analyzer crates requiring
  rustc 1.95, but apt's rustc is 1.93 → build failure. Pinned to 0.21.1
  (the documented working version) to keep the build reproducible.

## 0.1.4 (2026-08-01)

### Fixes
- **ACP version conflict (Hermes chat)**: `hermes-agent[acp]` pins
  `agent-client-protocol==0.9.0` (needs `ModelInfo` in `acp.schema`), but
  `jupyter-ai-hermes` → `jupyter-ai-acp-client` pulls `>=0.11` (removed
  `ModelInfo`). Installing jupyter-ai-hermes AFTER the acp pin overrides it
  back to 0.11.1 → `hermes acp` subprocess fails → jupyter-ai chat broken.
  Fix: pin `agent-client-protocol==0.9.0` as the LAST install step, after
  jupyter-ai-hermes. `JaiAcpClient` works fine with 0.9.0 (adds its own
  `create_session` method; the `>=0.11` constraint is overly strict).
- **Hermes dashboard/proxy not starting**: `jupyter_hermes_proxy` launches
  `hermes dashboard --skip-build`, but `web_dist/` was missing from the
  installed package. Hermes' `pyproject.toml` `package-data` doesn't include
  `web_dist` (only `observability/schemas/*.json` and `gateway/assets/**/*`).
  Fix: `cp -r /tmp/hermes-agent/hermes_cli/web_dist` to site-packages after
  `pip install`, before source cleanup.
- **`%%hermes` magic cell not writing to notebook**: `jupyter-ai-tools`
  `_resolve_cell_id` misidentifies numeric cell IDs as array indices.
  JupyterLab 4+ YDoc cell IDs can be short numeric strings (e.g. "22334524").
  `_is_index_like()` returns True for any numeric string → cell ID treated as
  index 22334524 → "Invalid cell index" → `run_cell`/`select_cell` fail.
  Fix: patch `_resolve_cell_id` to only treat values < 10000 as indices.
  Patch must be applied AFTER all pip installs (jupyter-ai-hermes reinstalls
  jupyter-ai-tools, overwriting earlier patches).

### Changes
- Install `hermes-agent[acp]` (not bare `hermes-agent`) for ACP support.
- Remove `jupyter-collaboration` from Dockerfile (jupyter-ai pulls it transitively).
- Remove custom XFCE panel XML (hardcoded launcher IDs caused empty launchers).
- Remove noVNC viewer.js/index.css sed patches (corrupted minified CSS/JS).
- Remove font/terminal/Xft changes (none resolved spacing issue).
- Add `NoDisplay=true` to `xfce4-session-logout.desktop` (hide logout from menu).
- Patch `xstartup` with `ELECTRON_DISABLE_SANDBOX=1` (Obsidian/VSCode/Chrome).
- Patch `jupyter-server-documents` serverSideExecution to "false" (fix input()).
- Patch `acp_adapter/server.py` interrupt handling.

## 0.1.0 (2026-07-31)

Initial clone of cs1302nb:0.4.23. Identical Dockerfile and dependencies.
Streamlining will happen incrementally after first successful build.
