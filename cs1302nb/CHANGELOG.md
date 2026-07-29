# cs1302nb Changelog

## 0.4.21 (2026-07-29)

### Added
- **jupyter-ai-hermes-magics v0.4.0**: Persistent ACP connection (~25s → ~2.5s first prompt), multi-session support (`--label`, `--new`), `%hermes help` subcommand, transcript cell placement/rendering fixes, MCP server integration (notebook tools).

## 0.4.20 (2026-07-29)

### Fixed
- **jupyter-python-tutor "dancing" cell (root cause fix)**: The outer iframe polling script compared `frame.offsetHeight` (which includes border) against `widget.offsetHeight` (which is border-box). With `border:1px`, `offsetHeight` was always 2px larger, so the condition `frame.offsetHeight !== h` was **always true** — the script wrote `style.height` every 200ms forever, triggering continuous layout reflow. Fix: match cpp-tutor's approach exactly — `border:none`, read `body.scrollHeight + 20`, no condition check (idempotent). Browser-verified: 0 rewrites in 2s monitoring, 16 steps all identical 320px.

## 0.4.19 (2026-07-29)

### Fixed
- **jupyter-python-tutor "dancing" cell**: Widget height was dynamically recalculated on every step change via `autoResize()`, causing the iframe (and the entire cell) to resize continuously as the user navigated through execution steps. Rewrote renderer to match jupyter-cpp-tutor's approach: **fixed widget height** with **internal scrolling** in code/frames/heap sections. The cell height never changes — content scrolls within the fixed-height widget instead.
- **jupyter-python-tutor dead code removed**: Removed unused `render_trace_widget()` function, unused `widget_id` parameter, and the `autoResize()` function with all its call sites (~83 lines removed, 1036→953 lines).

## 0.4.18 (2026-07-29)

### Fixed
- **`%%hermes` transcript cell not created**: MCP session expired between cell execution and button click. Now re-initializes MCP session before `add_cell`. Also fixed `exec_count` off-by-one (`ip.execution_count` returns next count, not current).
- **`%%hermes` "New session" every time**: `tree.update_session_id()` was never called after Hermes completed. Now saves session ID back to tree, so subsequent runs show "↻ Resume" and Hermes remembers conversation history.
- **`%%hermes` no thinking/tool-call details**: Verbose mode now parsed for tool-call markers (`┊ 📖 read ...`). Tool calls rendered as collapsed `<details>` blocks in cell output (like jupyter-ai chat). DOMPurify preserves `<details>` (structural HTML).
- **`%%hermes` speed**: Added `-t file,terminal` flag to limit toolsets, reducing startup overhead. Full fix (persistent ACP subprocess) deferred.
- **MCP `notifications/initialized` rejected**: Notification was sent with `id` field (should be fire-and-forget without `id`). Fixed in `context.py`.
- **Hermes output parser**: Fixed to match actual verbose output format (`─ ⚕ Hermes ─` box markers, not `╭─`). ANSI escape codes stripped. Session ID extracted from stdout (`hermes --resume <id>` line).
- **jupyter-python-tutor 20px vertical spacing**: iframe missing `display:block;margin:0;` caused inline baseline gap. Fixed in `renderer.py`.

## 0.4.17 (2026-07-29)

### Fixed
- **`%%hermes` button click not working in JupyterLab 4**: JupyterLab 4 sanitizes all HTML output with DOMPurify, stripping `<script>` tags and `onclick` handlers. Switched from raw HTML/JS to `ipywidgets.Button` (uses `application/vnd.jupyter.widget-view+json` MIME type, bypasses HTML sanitizer). After completion (done/stopped/error), widget is replaced with static HTML — no widget state saved in notebook.
- **424 browser console warnings**: Caused by DOMPurify logging each stripped tag/attribute across all cells. Eliminated by removing all `<script>`/`onclick` from output.

## 0.4.16 (2026-07-28)

### Changed
- **`%%hermes` magics v0.3.0 → v0.3.0 (button redesign)**:
  - Two-phase button design: Shift+Enter shows ▶ button (no auto-send), click ▶ to start Hermes
  - Stop button (⏹) during streaming — kills subprocess, no transcript cell created if stopped
  - **No ipywidgets** — uses IPython comms (built into IPython) for button callbacks, avoiding widget-state-saving issues
  - **Dynamic transcript cell type**: code cell for pure code responses, markdown for explanations
  - **Always create new cell** (never edit_cell) — simpler, no fragile update logic
  - Magic cell identified by `execution_count` (not cell selection) — transcript always targets correct cell
  - Live timer during streaming (updates every 1s)
  - State consistency: ▶ only when idle/done/stopped, ⏹ only during streaming
  - On kernel restart, button becomes static snapshot (no comm registered)

## 0.4.15 (2026-07-28)

### Added
- **jupyter-python-tutor** v0.3.0 (`%%pytutor`) — Python Tutor-style step-by-step
  code visualization, installed via build context, auto-loaded in `ipython_config.py`
- **jupyter-cpp-tutor** v0.2.2 (`%%cpptutor`) — C++ step-by-step code visualization
  via GDB tracing, installed via build context, auto-loaded in `ipython_config.py`

### Fixed (jupyter-ai-hermes-magics v0.3.0)
- **Bug #1 — transcript cell was code not markdown**: `jupyter-mcp-cli` subprocess
  hung due to asyncio event-loop cleanup bug in `streamablehttp_client`.
  Replaced all `jupyter-mcp-cli` subprocess calls with **direct synchronous HTTP**
  to the MCP server (`urllib.request` — no asyncio, no subprocess).
- **Bug #2 — Hermes explained ALL cells, not just "code above"**: Context now
  only includes cells **up to and including** the `%%hermes` cell. Cells below
  are excluded so "the code above" unambiguously refers to prior cells.
- **Bug #3 — no streaming, reply appears only when done**: The `-Q` (quiet) flag
  buffers the entire response. Added a live **animated progress indicator**
  ("⏳ Hermes is thinking... ⠋ (Ns)") while the subprocess runs.
- **Bug #4 — re-execution creates duplicate cells**: Now checks for an existing
  cell below the magic cell and uses `edit_cell` to update it instead of
  always calling `add_cell`.

## 0.4.14 (2026-07-28)

### Fixed
- **`%%hermes` Bug #1**: `gather_context()` was async but called without awaiting in a Jupyter
  kernel event loop → `RuntimeWarning: coroutine 'gather_context' was never awaited`. Rewrote
  context gathering to be fully synchronous (subprocess calls to `jupyter-mcp-cli`).
- **`%%hermes` Bug #2**: Response appeared in BOTH the output cell AND the transcript cell.
  Transcript cell was created as code instead of markdown. Now: output is cleared after
  streaming, response lives only in a markdown transcript cell (via `jupyter-mcp-cli add_cell`
  with `cell_type=markdown`).
- **`%%hermes` Bug #3**: Context only provided the active cell (the `%%hermes` cell itself),
  not the cells above it. Hermes saw the MCP tool documentation as the main content and
  explained that instead of the user's code. Now: context reads ALL notebook cells, the active
  cell is clearly marked, and the user's question is placed first in the prompt (before context
  and tool docs).

### Changed
- `jupyter-ai-hermes-magics` bumped to v0.2.0
- `MCP_TOOLS_DOC` reduced from ~500 chars of verbose explanation to brief tool reference
- Prompt restructured: user question → notebook context → brief tool docs → focus instruction

## 0.4.13 (2026-07-28)

### Added
- **`%%hermes` cell magic** (`jupyter-ai-hermes-magics` v0.1.0): Talk to Hermes Agent
  directly inside notebook cells. Features:
  - Dot-notation session tree (`main.debug.fix`) with fork semantics — child
    sessions inherit parent's conversation history
  - Auto-resume: consecutive `%%hermes` cells continue the same session
  - Streaming output by default (stdout streams line-by-line)
  - Transcript cell group: response goes into linked cells below the magic cell;
    re-execution updates instead of duplicating
  - Notebook context awareness via MCP tools (JupyterLab) or kernel
    introspection (any IPython, including VS Code notebooks)
  - No litellm dependency — Hermes handles model routing itself
  - Auto-loaded via `ipython_config.py` (`c.InteractiveShellApp.extensions`)
- **Build context for `jupyter-ai-hermes-magics`** in Makefile and Dockerfile,
  same pattern as `jupyter-ai-hermes`, `cppmanlite`, `jupyterlab-pwa`

### Fixed
- **ACP stop button bugs** (baked into image via Dockerfile sed patch):
  - Bug 1: `None.startswith()` crash when `final_response` is `None` after
    interruption — now uses `result.get("final_response") or ""`
  - Bug 2: Junk output after cancel — partial LLM text was re-delivered as a
    complete message; now suppresses ALL interrupt responses

## 0.4.11 (2026-07-26)

### Changed
- **Reverted all PWA splash page code**: The splash page experiments (0.4.6–0.4.10)
  all failed in MagicOS desktop projection mode. MagicOS does not paint any web
  content during PWA cold launch — no splash page, redirect, or JS approach can
  fix this from the web side. Reverted jupyterlab-pwa to its original simple
  state: `start_url: /lab`, minimal empty-handler service worker, no splash page.
- **Added `mobile-web-app-capable` meta tag**: The one useful finding from the
  investigation — code-server (which works in MagicOS) has this meta tag. Added
  it alongside the existing `apple-mobile-web-app-capable`. This is a harmless
  one-line addition that standardizes PWA behavior on Android.
- **Accepted "open twice" workaround**: On MagicOS desktop projection, the first
  PWA launch shows a stuck OS splash. Opening the app a second time works. This
  is an OS-level limitation, not something we can fix from the web side.

### Fixed
- **PWA splash screen stuck on MagicOS desktop projection (cold launch)**:
  The "first open fails, second open works" pattern revealed the true root
  cause: on cold launch, DNS + TLS + HTTP round-trip takes too long before
  the WebView produces first paint, so the OS splash never dismisses. On
  second open, everything is cached and it works.
  - **Service Worker now caches the splash page** (`/pwa/splash`) with a
    cache-first strategy (stale-while-revalidate). The SW installs on first
    PWA launch, caches the ~600-byte splash page, and serves it instantly
    (0ms network) on every subsequent launch — cold or warm.
  - This matches how code-server works in MagicOS: its SW is already
    registered and its page loads from cache on every launch.
  - Only `/pwa/splash` is cached. All other requests (`/lab`, JS assets,
    etc.) fall through to the network unchanged.
  - SW also pre-caches `./splash` at install time for immediate availability.

### Fixed
- **PWA splash screen stuck on MagicOS desktop projection**: The `<meta
  http-equiv="refresh" content="0">` in the 0.4.8 splash page was the
  culprit — when a browser sees an imminent navigation (content="0"), it
  defers painting the current page entirely, so neither the splash page
  nor the eventual /lab page ever produced first-contentful-paint in
  MagicOS WebView.
  - Replaced meta refresh with **double-RAF** (`requestAnimationFrame`
    nested twice) + `window.location.href`. This forces the browser to
    commit at least one paint of the splash page (dismissing the OS
    splash) before navigating to /lab.
  - Removed `<meta http-equiv="refresh">` tag entirely.

### Fixed
- **PWA splash screen stuck on desktop projection (MagicOS)**: Neither inline
  `<style>` nor external `<link rel="stylesheet">` triggered
  first-contentful-paint in Honor MagicOS desktop projection WebView when
  loading JupyterLab's /lab page (which has 17 MB of deferred JS and empty
  body).
  - **New approach**: PWA `start_url` now points to a dedicated splash page
    (`pwa/splash`) — a tiny HTML page with inline CSS (white bg + orange
    spinner) and `<meta http-equiv="refresh" content="0;url=.../lab">`. This
    page paints instantly (no JS, no deferred scripts, no config data),
    dismissing the OS splash screen. The meta refresh then navigates to /lab
    where JupyterLab loads normally.
  - New `PWASplashPageHandler` serves the splash page.
  - Manifest `start_url` changed from `base_url + "lab"` to `base_url + "pwa/splash"`.
  - LabHandler injection simplified back to PWA tags only (no splash CSS/spinner
    needed in /lab since the splash page handles OS splash dismissal).

## 0.4.6 (2026-07-23)

### Fixed
- **PWA splash screen stuck on desktop projection (MagicOS)**: When launching
  the JupyterLab PWA on a phone connected to an external screen (Honor Magic V3
  desktop mode), the system splash screen (app icon) stayed stuck because
  JupyterLab's HTML has no CSS in `<head>` and an empty `<body>` — the browser
  cannot produce a first paint until ~17 MB of JS loads, so the OS splash screen
  is never dismissed.
  - jupyterlab-pwa now injects an inline `<style>` (white background + CSS-only
    spinner) and a `<div id="jp-pwa-spinner">` into the rendered HTML via the
    LabHandler wrapper. This triggers an immediate first paint, dismissing the
    OS splash screen.
  - A `MutationObserver` removes the spinner and splash CSS once JupyterLab
    renders real content (any `[class*=jp-]:not(body)` element) — stable across
    JupyterLab 4.x/5.x, no dependency on specific component class names.
- **PWA manifest `display_override`**: Added `["window-controls-overlay",
  "standalone"]` to match code-server's manifest, improving desktop-mode PWA
  behavior.

### Changed
- jupyterlab-pwa `handlers.py`: Added `_build_splash_css()` and
  `_build_splash_body()` functions; `patched_get()` now injects both
  before `</head>` and `</body>` respectively.

## 0.4.5 (2026-07-21)

### Fixed
- **Desktop/VNC crash (bwrap)**: Ubuntu 26.04's glycin (GTK image loader) uses
  `bwrap` to sandbox image decoders. `bwrap` requires mount namespaces
  (`CAP_SYS_ADMIN`), which are unavailable in Kubernetes pods. This caused XFCE
  panel/desktop crashes: `bwrap: Failed to make / slave: Permission denied` →
  GTK abort → VNC lost → websockify `WebSocketClosedError`.
  - Added `bwrap-wrapper.sh` — a passthrough wrapper that strips sandbox flags
    and execs the target binary directly. This is safe because the container
    itself provides isolation.
  - Real `bwrap` backed up to `/usr/bin/bwrap.real`.
  - Installed via `COPY` + separate `RUN` (not inline `printf`) to reliably bust
    the Docker layer cache. Previous `printf` approach was cached in 0.4.3/0.4.4
    builds and the wrapper never made it into the image.
  - `chmod 755` on the wrapper to ensure it is readable/executable by all users
    (not just root).

### Changed
- **bwrap-wrapper.sh**: New file. 27-line shell script that parses bwrap args,
  strips all sandbox-related flags (`--unshare-*`, `--ro-bind`, `--dev`,
  `--proc`, `--tmpfs`, `--bind`, `--symlink`, `--setenv`, `--seccomp`,
  `--dbus-fd`, `--die-with-parent`, `--chdir`), finds the last executable
  argument, and execs it directly with any trailing arguments.

### Notes
- This is a bugfix release over 0.4.4. No feature changes.
- The in-pod runtime fix (`~/.local/bin/bwrap` + `~/.vnc/xstartup` on NFS PVC)
  installed during 0.4.4 debugging is no longer needed — the fix is now baked
  into the image. Those files can be removed manually if desired.
