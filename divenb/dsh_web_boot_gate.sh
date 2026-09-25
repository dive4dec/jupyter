#!/bin/bash
# dsh web boot gate — the END-TO-END guard that catches what the per-file
# patch gates cannot.
#
# The patch gates (dsh-web-tokenless, dsh-web-subpath) only prove their regex
# matched a file. They cannot prove `dsh web` actually STARTS. That was exactly
# the 0.2.67 failure: the patches applied and their gates passed, but `dsh web`
# crashed at boot with
#   "plugin(s) failed to load: @deepseek-ai/dsh-sandbox-local"
# because the npm layout nested that dev-dep where dsh's plugin loader
# (createRequire(...).resolve) could not find it. A build-time patch gate
# would still pass; only actually launching `dsh web` would catch it.
#
# This gate boots `dsh web` on a throwaway DSH_HOME + port, and requires the
# tokenless-patched server to answer the index page with HTTP 200 (the patch
# removes the launch token, so a live server returns 200, not 401). If dsh web
# crashes (plugin-tree / module-resolution failure) it never answers -> the
# gate fails the build rather than shipping an image whose launcher page hangs.
set -u
PORT=3187
GATE_HOME=/tmp/dsh-boot-gate-home
LOG=/tmp/dsh-boot-gate.log
rm -rf "$GATE_HOME"; mkdir -p "$GATE_HOME"
export DSH_HOME="$GATE_HOME"

dsh web --no-open --port "$PORT" >"$LOG" 2>&1 &
DW=$!
ok=0
for _ in $(seq 1 45); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/" 2>/dev/null || echo 000)
  case "$code" in 200|301|302) ok=1; break ;; esac
  sleep 1
done
final=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/" 2>/dev/null || echo 000)
kill "$DW" 2>/dev/null || true
wait "$DW" 2>/dev/null || true

if [ "$ok" = 1 ]; then
  echo "dsh web boot gate: OK — served HTTP $final on :$PORT (no plugin crash)"
  rm -rf "$GATE_HOME" "$LOG"
  exit 0
fi
{
  echo "dsh web boot gate: FAILED — dsh web did not serve HTTP 2xx/3xx (last=$final)"
  echo "--- $LOG (tail) ---"
  tail -50 "$LOG"
} >&2
exit 1
