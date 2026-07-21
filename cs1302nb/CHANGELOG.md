# cs1302nb Changelog

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
