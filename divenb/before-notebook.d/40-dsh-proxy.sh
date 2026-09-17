#!/bin/bash
# dsh-openai-shim boot hook — start the dsh OpenAI proxy daemon (a3: in-pod).
#
# Installed to /usr/local/bin/before-notebook.d/40-dsh-proxy.sh and run by
# start.sh's run-hooks() immediately before the notebook is exec'd, as the
# notebook user (jovyan) in edbt (PID 1 = tini runs as jovyan; no root->sudo
# drop), so $HOME is the NFS home. It must not block or fail the notebook
# start, so everything is defensive and the daemon is detached.
#
# The proxy is the intended way to drive dsh (terminal / code-server / VS Code
# point dsh at this loopback endpoint). Provider selection (diveai | litellm |
# custom) comes from ~/.dsh/proxy.conf — written on first run with the default
# (DiveAI) and never clobbered when a student has chosen another.
#
# Layering (mirrors the dsh runtime): the shim process runs from the conda env
# (ephemeral image layer) and logs to /tmp (ephemeral). It never writes to the
# user home; the only file it touches there is the student-owned proxy.conf,
# created by `dsh-proxy init` (ensure_default), which is idempotent.

# Best-effort: never let this break the notebook boot.
set +e

# Make DSH_HOME explicit so dsh-proxy / the shim and the dsh runtime agree on
# where profiles + proxy.conf live (defaults to ~/.dsh when unset, but being
# explicit avoids any ambiguity between the two).
export DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
export DSH_SHIM_PORT="${DSH_SHIM_PORT:-8090}"

if ! command -v dsh-proxy >/dev/null 2>&1; then
    echo "[dsh-proxy] dsh-proxy not on PATH; skipping shim start" >&2
    exit 0
fi

# Already up? Do nothing (e.g. RESTARTABLE re-runs the hook).
if dsh-proxy status 2>/dev/null | grep -q "running"; then
    echo "[dsh-proxy] shim already running on ${DSH_SHIM_PORT}; leaving it"
    exit 0
fi

# Detach the daemon (setsid + nohup) so it survives the hook's parent being
# exec'd into the notebook server; log to /tmp (ephemeral, never the home).
nohup setsid dsh-proxy serve >/tmp/dsh-shim.log 2>&1 &
echo "[dsh-proxy] starting shim on ${DSH_SHIM_PORT} (see /tmp/dsh-shim.log)"
exit 0
