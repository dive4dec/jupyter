# divenb Changelog

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
