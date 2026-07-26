# cs1302nb Changelog

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
