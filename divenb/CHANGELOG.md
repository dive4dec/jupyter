# devenb Changelog

## 0.2.63 (2026-09-22)

### Changed
- **dsh shim: single startup orchestrator, no hardcoded provider (dedup +
  deployment-agnostic).** The shim's "sync providers + start/restart the daemon"
  logic existed in TWO places — the image's `before-notebook.d` boot hook (bash)
  AND every hub values file's mounted `jupyter_server_config` (a Python block).
  That duplication is how the course hubs (cs1302a/cs2310) drifted from edbt:
  they never got the 0.2.61 values-file copy and stayed on the 0.2.49 model.
  - (a) NEW `dsh-proxy ensure` subcommand (shim) is now the ONLY place the
      logic lives: it syncs the deployment's `DIVEAI_*`/`LITELLM_*` entries into
      `~/.dsh/proxy.conf`, then STARTS the daemon if down or RESTARTS it if the
      sync changed anything (unchanged + running → no-op). `dsh-proxy ensure`
      is what the boot hook calls now.
  - (b) The image's `40-dsh-proxy` hook's manual bash sync+start+status is gone —
      replaced by a single `dsh-proxy ensure` call.
  - (c) The duplicated Python sync block is REMOVED from the hub values files
      (edbt.yaml; the course files never had it). Their `jupyter_server_config`
      now carries only a pointer comment.

### Fixed
- **Removed the hardcoded `--default-provider litellm` from the image.** The
  image is deployment-agnostic and may be deployed to clusters whose default
  dsh provider is not litellm; baking one in was a fragile coupling. The
  first-run default is now DEPLOYMENT POLICY: the shim's `ensure`/`sync` read it
  from the `DSH_PROXY_DEFAULT_PROVIDER` pod env (unset → nothing forced, the
  student keeps/picks their own). Each hub values file now declares its own
  `DSH_PROXY_DEFAULT_PROVIDER` in `extraEnv` (edbt + cs1302a + cs2310 = `litellm`,
  preserving prior behavior). A unit test (`test_ensure_no_hardcoded_default`)
  locks in that the package forces no provider when the env is unset.
- **Removed the hardcoded dsh model name (`Socrates`) and `contextWindow`
  (262144) from the image.** The `40-dsh-proxy` boot hook used to bake a fixed
  `~/.dsh/settings.yaml` (model `Socrates`, `contextWindow: 262144`) into the
  first boot — the same fragile coupling as the provider, and both values are
  discoverable. Now the hook calls a new `dsh-proxy seed-settings` which, on
  first boot only, **discovers** the model name and its `contextWindow` from
  the deployment provider's `/v1/models` (exactly how hermes discovers them).
  The model is deployment policy — `DSH_DEFAULT_MODEL` in `extraEnv`
  (edbt + cs1302a + cs2310 = `Socrates`, preserving prior behavior); unset →
  the first model the endpoint advertises. The window is omitted rather than
  fabricated when it can't be discovered (the shim self-heals it from the first
  context-length 400). Seeded only when `settings.yaml` is absent, so a
  student's edits survive (tests: `test_seed_*`, incl. a regression asserting
  the package contains no baked model name or window).
- Fixed stale comments that referenced a nonexistent in-pod `dsh-proxy-config.py`
  ("mounted below, invoked from jupyter_server_config.py") and the outdated
  0.2.49 "default DiveAI, student-overridable" model — the real mechanism is the
  image boot hook + `dsh-proxy ensure` + `dsh-proxy seed-settings`.

### Notes
- Shim: `dsh-openai-shim` v0.2.0 → v0.2.1 (new `ensure` command + tests).
- Behavior for the three current hubs is unchanged (litellm still the first-run
  default) — it is now expressed in the values file instead of the image, so the
  same image can serve a cluster with a different default.

## 0.2.62 (2026-09-21)

### Fixed
- **dsh-openai-shim: context-window-aware `max_tokens` (fixes the sglang/vLLM
  "context length" 400).** 0.2.61's per-provider `token_cap` clamped the
  *output* limit, but sglang/vLLM report `max_model_len` as the *total* context
  window (input + output), so a large prompt + large `max_tokens` still overflowed
  and 400'd. The shim (now `dsh-openai-shim` 0.2.0) stores both `token_cap` and
  `context_window`, clamps `max_tokens = min(cap, window − est_input − 128)`,
  and self-heals a remaining context-window 400 by retrying once with the
  server-reported input count and persisting the window.
- **Build gate** updated for the 4-tuple `resolve_upstream` (now also returns the
  context window).

### Changed
- Bumped `divenb` version to `0.2.62`.

## 0.2.61 (2026-09-21)

### Added
- **dsh-openai-shim: per-provider completion-token cap, auto-discovered.**
  `dsh-proxy use --base` probes `/v1/models` to learn the upstream's output limit
  and stores it as the provider's `token_cap`; the shim clamps `max_tokens` to it
  and self-heals a completion-cap 400 (parses the server-reported cap, retries,
  persists). `dsh-proxy use` now restarts the shim after changing providers
  (was stop-only, leaving a dead endpoint).

### Changed
- **Deployment-agnostic build gate wired into the Dockerfile**
  (`dsh_shim_deployment_agnostic_gate.py`): fails the build if a deployment host
  or the old hardcoded provider catalog reappears in the package, and
  functionally verifies file-based (env-inert) resolution + the
  sync-never-clobbers contract. Re-run after any dsh-openai-shim refactor.
- **`before-notebook.d/40-dsh-proxy` runs `dsh-proxy sync` before daemon start.**
  Upserts the deployment's `diveai`/`litellm` entries from the pod
  `DIVEAI_*`/`LITELLM_*` env into `~/.dsh/proxy.conf` on every start (key
  rotation + endpoint moves propagate without a rebuild; student-added providers
  untouched; first-run default `litellm`). Best-effort — a sync failure never
  blocks notebook boot.

## 0.2.60 (2026-09-21)

### Changed
- **dsh providers now live in `~/.dsh/proxy.conf` (hermes-style sync).**
  proxy.conf is the SINGLE source of truth for ALL providers — the
  deployment's (`diveai` / `litellm`) and any number of student-added custom
  ones. The 0.2.59 `DSH_PROXY_<NAME>_BASE/_KEY` pod env vars are gone; the
  shim resolves providers purely from the file (verified env-inert by the
  build-time gate).
  - **Sync on every notebook start** (before-notebook.d hook + jupyter
    server config): `dsh-proxy sync` upserts the `diveai` / `litellm` entries
    from the spawner's `DIVEAI_*` / `LITELLM_*` env — key rotation and
    endpoint moves propagate without a rebuild, student-added entries are
    never touched, and the first-run default (`litellm`) is set once. The
    shim restarts only when something actually changed (or is down).
  - The hub `pre_spawn_hook` no longer maps `DIVEAI_*/LITELLM_*` onto
    `DSH_PROXY_*`; the values file (`DIVEAI_API_BASE/_KEY`,
    `LITELLM_API_BASE`) stays the single endpoint/key source for both hermes
    and dsh.
- **`dsh-proxy use` accepts ANY provider name.**
  `dsh-proxy use myprovider --base https://host/v1 --key sk-...` adds a
  custom provider of any name (multiple allowed) and switches to it; a bare
  `dsh-proxy use <name>` switches to an existing one; omitting `--key`
  forwards the caller's Authorization as-is. New `dsh-proxy list` shows all
  configured providers with the current one flagged.
- **Build-time gate rewritten** for the file-based contract: no deployment
  hosts in the package, resolution is env-inert, and `sync_deployment`
  must upsert + set first-run default without clobbering student entries.

## 0.2.59 (2026-09-21)

### Changed
- **dsh-openai-shim made deployment-agnostic (superseded by 0.2.60's
  file-based sync, kept for history).** No hardcoded provider endpoints /
  URLs in the package; a named provider resolved from
  `DSH_PROXY_<NAME>_BASE/_KEY` pod env; the hub `pre_spawn_hook` mapped
  `DIVEAI_*/LITELLM_*` onto `DSH_PROXY_*`; `dsh-proxy use <name>` accepted
  any deployment-defined name and failed fast with the exact env var to
  define; build-time gate added.

## 0.2.58 (2026-09-20)

### Changed
- **code-server 4.133.0 → 4.138.0.**
- **Continue.continue extension removed** from the image (no longer installed).
- **hermes-agent v2026.8.31 (0.21.0) → v2026.9.14 (0.21.3).** Upstream
  refactored `acp_adapter`, so the three Dockerfile patches were re-validated
  and re-ported against the 0.21.3 source (each is assertion/gate-guarded and
  fails the build if an anchor drifts on a future bump):
  - `tools/daemon_pool.py` 3.14 override regenerated from the 0.21.3 base — it
    now preserves the new contextvar-propagating `submit()` (the
    `UnscopedSecretError` fix under the multiplexed gateway) plus the 3.14
    `_create_worker_context()` guard.
  - ACP cancel sed reduced to the one still-relevant fix (the
    `final_response=None` → `None.startswith()` crash); the "junk output after
    cancel" bug was refactored upstream (block now uses a local `suppress` var,
    import still in use).
  - Turn-stall watchdog re-ported to the new structure: `SessionState`
    activity fields, `SessionManager.all_states()`, and the streaming-callback
    wrappers now target the per-turn `_TurnCallbacks` dataclass (`cbs.*`,
    `stream_delta_cb`) instead of the old local callback vars.
- **acp-client stays at 0.2.0** — already the latest published version on the
  marketplace.

## 0.2.51 (2026-09-18)

### Added
- **In-editor dsh chat via the `Jager.dsh-vscode` code-server extension.**
  Baked into the code-server system extensions dir (NFS-proof, the same dir as
  the other ~15 built-in extensions). Students get the `@dsh` chat participant
  in the native Chat panel, a secondary sidebar / standalone chat window,
  `@file`/`@session`/`@agent` mentions, image attachments, model/preset/permission
  controls, and turn-level Git rollback — no marketplace install step.
- The extension is a **client to the `dsh web` server** (it auto-starts
  `dsh web` on code-server startup via `dsh.autoStart`). Verified in-pod:
  `engines.vscode ^1.90.0` is satisfied by code-server 4.133.0 (Code 1.133.0).

### Changed
- **dsh runtime: PyPI `deepseek-harness-sdk==0.1.5rc1` → npm
  `@deepseek-ai/dsh@0.1.5-rc.2`.** The PyPI build was the *SDK-focused*
  distribution whose baked Node SEA snapshot omitted the web-app frontend
  (`dsh web` crashed with `Cannot find package
  '@deepseek-ai/dsh-session-title-llm'`). The npm distro is the *complete*
  package (CLI + `dsh web` + ACP + the web-app frontend packages).
- **No provider config required for the web chat.** The npm `dsh`'s deepseek
  provider reads `DEEPSEEK_BASE_URL`/`DEEPSEEK_API_KEY` from the environment
  (source-confirmed: "DEEPSEEK_BASE_URL wins when set"), and the spawner already
  injects `DEEPSEEK_BASE_URL=http://127.0.0.1:8090/v1` + a per-user key — so the
  in-editor chat auto-routes through the same in-pod `dsh-openai-shim` →
  Socrates that the terminal dsh CLI uses. One config drives both.
- The `dsh-openai-shim` boot hook (`before-notebook.d/40-dsh-proxy`) is
  unchanged — it still starts the `:8090` proxy at pod spawn.

### Notes
- The extension is shipped as a version-pinned VSIX in the repo
  (`extensions/dsh-vscode-0.13.17.vsix`). To bump it: download the new VSIX
  (gunzip the marketplace vspackage), replace the file, update the `COPY` +
  `--install-extension` line in the Dockerfile.

## 0.2.50 (2026-09-17)

### Fixed (three boot-breaking bugs found by throwaway-pod verification)
- **The `before-notebook.d` hook was `40-dsh-proxy.sh`; `start.sh`'s
  `run-hooks()` *sources* `*.sh` files, so the hook's `exit 0` would have
  terminated `start.sh` itself and the Jupyter server would never start.**
  Renamed to `40-dsh-proxy` (no extension) — `run-hooks()` *executes* other
  executable files as child processes, where `exit` is safe.
- **The hook's "already running?" guard (`grep -q running`) matched the
  substring in "not running", so the daemon was never started on a fresh pod.**
  `dsh-proxy status` now returns a real exit code (0=running, 1=not) and the
  hook branches on it.
- **`dsh-proxy serve` (the daemon) never wrote its pidfile, so
  `dsh-proxy use <provider>` couldn't stop the running shim to pick up the new
  provider.** `serve` now writes/removes its own PID.

### Changed
- **Default provider is now LiteLLM** (the per-user key, verified
  end-to-end). DiveAI is deliberately not the default:
  `dive.cs.cityu.edu.hk/ai/v1` 404s on `/chat/completions` and is therefore not
  an OpenAI-chat endpoint dsh can speak to. It remains available via
  `dsh-proxy use diveai` should it gain such a path.

### Notes
- 0.2.50 is a **clean re-tag of the fixed build**. The 0.2.49 tag already in
  the registry is the pre-fix build (the three bugs above). Because the spawner
  uses `imagePullPolicy: IfNotPresent` and a verification pod already pulled the
  broken 0.2.49 to a node, reusing the tag risked serving the stale cached
  image — 0.2.50 avoids that.

## 0.2.49 (2026-09-17)

### Removed
- **The `jupyter-ai-dsh` ACP persona** (added in 0.2.48, same-day). dsh is now
  driven through the **`dsh-openai-shim` proxy** — the intended, dsh-native way —
  instead of a Jupyter AI persona. The persona fought dsh's design (it had to
  invent a per-session working dir dsh never asked for; a home-wide `glob`
  overflowed the model context and deadlocked the ACP turn). The persona package
  and its `--build-context` are removed from the image.

### Added
- **dsh proxy as a first-class in-pod service** (`before-notebook.d` boot hook,
  `divenb/before-notebook.d/40-dsh-proxy.sh`): starts the `dsh-openai-shim`
  daemon as the notebook user on `127.0.0.1:8090`, reading the provider from
  `~/.dsh/proxy.conf`. This is the (a3) model — dsh is used from the terminal /
  code-server (VS Code) already in the image, with the loopback proxy as the
  shared OpenAI-compatible endpoint. Multi-session / multi-folder is free: the
  proxy is stateless; each dsh workspace carries its own working dir.
- **`dsh-proxy` CLI** (in `dsh-openai-shim`): `show` / `use diveai|litellm|custom`
  / `status` / `init` / `serve`. Default provider is **LiteLLM** (the per-user
  key, verified end-to-end). **DiveAI is deliberately not the default** —
  `dive.cs.cityu.edu.hk/ai/v1` 404s on `/chat/completions`, so it is not an
  OpenAI-chat endpoint dsh can speak to (it is kept as an option via
  `dsh-proxy use diveai`). The choice is persisted to `~/.dsh/proxy.conf`
  (NFS home) and **never clobbered** on restart (mirrors the jupyter-ai-hermes
  default-provider pattern).
- **`DEEPSEEK_BASE_URL` / `DEEPSEEK_API_KEY`** in the spawner `extraEnv` point
  dsh at the loopback proxy, so any dsh invocation (terminal, code-server, VS
  Code) works with no extra setup. The per-user `LITELLM_API_KEY` already in the
  pod env is picked up by the proxy at serve time.

### Notes
- 0.2.49 is **not** a superset of 0.2.48 — the persona that 0.2.48 added is
  gone. If you deployed 0.2.48 expecting a dsh entry in Jupyter AI, it is no
  longer there by design; use the proxy instead.

## 0.2.48 (2026-09-17)

> **Superseded:** the `jupyter-ai-dsh` persona added here was **removed in
> 0.2.49** in favor of the in-pod proxy. Do not target 0.2.48 for the persona.

### Added
- **`jupyter-ai-dsh` — a dsh ACP persona for Jupyter AI** (new repo,
  `~/dive-deploy/jupyter-ai-dsh`). It drives `dsh --profile acp` as the agent
  backend, mirroring `jupyter-ai-hermes`. Before every message it:
  1. lazily starts the `dsh-openai-shim` sidecar (`ensure_shim()`, in a worker
     thread so it never blocks the server's event loop);
  2. writes a `--patch` overlay that overrides the `acp` profile's LLM
     provider + model (the only supported way to select a model — there is no
     `--model` flag); the correct overlay id is `acp` (verified via
     `--dump-config`; `dsh-acp` is a silent no-op);
  3. points `DEEPSEEK_BASE_URL` / `DEEPSEEK_API_KEY` at the shim (dummy key —
     the shim injects the real `DSH_SHIM_UPSTREAM_KEY` upstream);
  4. injects live notebook context (active notebook + current cell) and the
     `jupyter-mcp-cli` tool docs, reusing `jupyter_ai_hermes.jupyter_context`
     and `MCP_TOOLS_DOC` so the two personas stay in lockstep.

- **Install:** added to the `divenb` build as a new `--build-context
  jupyter-ai-dsh=...` and installed with `uv pip install --system --no-deps`
  after `jupyter-ai-hermes` and `dsh-openai-shim` (its two runtime deps are
  local build-context packages already present in the image — a plain install
  would try to fetch them from PyPI and fail). A build-time sanity check
  imports `jupyter_ai_dsh.dsh` to prove the chain resolves.

### Notes
- The persona is **inert until `DSH_SHIM_UPSTREAM` is set** in the spawner env;
  without it, `before_agent_subprocess` raises `PersonaRequirementsUnmet` and
  Jupyter AI marks the persona unavailable instead of failing every message.
- Model / provider / profile are overridable via `DSH_ACP_MODEL` /
  `DSH_ACP_PROVIDER` / `DSH_ACP_PROFILE` (defaults `Socrates` /
  `deepseek-official` / `acp`). The model overlay file defaults to
  `/tmp/dsh-acp-model.yml` (ephemeral) so it stays off the NFS home.
- 5 unit tests cover the model-patch writer, the executable argv, the
  `before_agent_subprocess` env plumbing, and the no-upstream guard.

## 0.2.47 (2026-09-17)

### Added
- **DeepSeek Harness (`dsh`) + `dsh-openai-shim`.** The image now ships the
  dsh agent runtime and a small OpenAI-compatible shim that adapts dsh's
  `deepseek-official` route to any OpenAI-compatible endpoint (Socrates /
  LiteLLM / sglang / vLLM). The shim remaps `reasoning_effort` (dsh hard-injects
  `high`, which Socrates rejects) and clamps `max_tokens` to the model's context
  window — the two param mismatches that otherwise 400.

- **Layering:** the dsh runtime (~262MB, self-contained Node binary, "exe mode"
  — no system `node` needed at runtime) and the shim install into the **conda
  env** (`/opt/conda`) via `uv pip install --system` — the ephemeral image layer,
  exactly like every other package in this image (never `--user` / `~/.local`).
  Only `DSH_HOME` (`$HOME/.dsh`) is written, and dsh writes it **itself** at
  runtime (profiles / sessions / user plugins) into the **NFS-mounted home**.
  A fresh home is fine — dsh auto-initializes its profile skeleton on first use.

- **`pnpm`** installed into conda — needed only for `dsh plugin add` (installing
  user plugins into `DSH_HOME`); running dsh needs no pnpm.

- **`dsh-openai-shim` package** (new repo, `~/dive-deploy/dsh-openai-shim`):
  zero-dependency stdlib-only proxy. `python -m dsh_openai_shim.cli serve` /
  `dsh-openai-shim serve`, plus a library API
  (`apply_rewrites`, `make_handler`, `ensure_shim`, `stop_shim`) and an
  `ensure_shim()` lazy-spawn helper so a persona/magic can start the sidecar as
  the current user with no init-system hook (mirrors how `%%hermes` lazily
  spawns `hermes acp`). 14 tests, incl. an end-to-end run against a local fake
  OpenAI upstream.

### Notes
- dsh is a **developer preview** with breaking changes — pinned to
  `deepseek-harness-sdk==0.1.5rc1` deliberately.
- The shim is **opt-in per hub**: it reads `DSH_SHIM_UPSTREAM` /
  `DSH_SHIM_UPSTREAM_KEY` from the spawner environment. With no env set it does
  nothing — the image change is inert until a hub wires it up. The real endpoint
  key lives only in the shim; dsh connects with a dummy key.

## 0.2.46 (2026-09-07)

### Upgrades
- **Thonny 4.1.7 → 5.0.0.** The IDE for students is now Thonny 5, the
  Tkinter-based rewrite. Thonny 5 drops the Qt/PyQt5 backend (4.x was Qt),
  so it is installed from PyPI into the conda env (`uv pip install
  thonny==5.0.*`) instead of the Ubuntu apt package, which is stuck at
  4.1.7. The apt `thonny` package (and its PyQt5 deps) is removed from the
  base image; the conda env already ships tkinter 8.6. The `.desktop`
  launcher and icon are regenerated from the PyPI wheel (which ships
  neither). New conda deps pulled automatically: mypy, pyserial, wheel.

## 0.2.45 (2026-09-07)

### Upgrades
- **jupyter-ai-hermes-magics 0.5.1 → 0.5.2.**

### Fixed
- **Dark-theme readability of the `%%hermes` streaming output.** The live
  "thinking" response box and the "Tool calls (N)" rows were now theme-aware
  (JupyterLab `--jp-*` tokens) instead of a fixed light background, so the
  thinking text is legible under the dark theme (see magics 0.5.2).

## 0.2.44 (2026-09-07)

### Upgrades
- **jupyter-ai-hermes-magics 0.5.0 → 0.5.1.**

### Fixed
- **ACP turn-stall watchdog (server-side).** A `%%hermes` turn that wedged
  (hung LLM stream / stuck approval) left `state.is_running` stuck `True`, so
  every later prompt was folded in as a "correction" and the cell returned
  *"Redirected the active turn with your correction."* with no answer. The
  Dockerfile now applies an assertion-guarded `patch_acp_adapter.py` that adds
  a background turn-stall watchdog to the installed `acp_adapter/server.py`:
  after `HERMES_ACP_TURN_STALL_TIMEOUT` seconds (default 300) of no activity,
  a running session is hard-interrupted via the existing `cancel()` /
  `request_hard_interrupt(tool_reason="turn_stall")` path. A new in-build
  functional gate (`hermes_acp_watchdog_gate.py`, no LLM) drives the real
  patched `prompt()` with a fake agent and asserts a wedged turn is rescued
  while a healthy turn is left alone — the build fails if the patch
  regresses or its anchors drift.
- **`%%hermes` redirect-ack recovery + stderr drain (client side).** Shipped in
  magics 0.5.1: the magic detects the redirect ack, cancels the stuck server
  turn (`cancel_server_turn()`), retries once, and surfaces a clear
  "session still wedged — run `%hermes reset`" error instead of a bogus
  transcript; the ACP subprocess stderr is now drained so the pipe buffer can
  no longer fill and wedge the channel; a 300 s prompt timeout now raises a
  meaningful message.

## 0.2.40 (2026-08-26)

### Upgrades
- **jupyterlab-pwa 0.1.1 → 0.2.0** — PWA name is now configurable via
  environment variables (`JUPYTERLAB_PWA_NAME`, `JUPYTERLAB_PWA_SHORT_NAME`,
  `JUPYTERLAB_PWA_DESCRIPTION`), read at server startup. The image stays
  neutral (default `Jupyter`); per-hub display names are set via
  `singleuser.extraEnv` in values/hub (edbt → `EDB JHub`).

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
