#!/bin/bash
# Passthrough wrapper for containers without CAP_SYS_ADMIN.
# Ubuntu 26.04 glycin (GTK image loader) uses bwrap to sandbox image decoders.
# bwrap needs mount namespaces (CAP_SYS_ADMIN), unavailable in K8s pods.
# Without this, XFCE panel crashes on icon load: "bwrap: Failed to make / slave".
# The wrapper strips sandbox flags and execs the target binary directly,
# which is safe because the container itself provides isolation.
args=("$@")
target=""
target_idx=0
for i in "${!args[@]}"; do
    arg="${args[$i]}"
    [[ "$arg" == --* ]] && continue
    [[ -d "$arg" ]] && continue
    [[ "$arg" == /dev/* ]] && continue
    if [[ -x "$arg" ]] && [[ -f "$arg" ]]; then
        target="$arg"
        target_idx=$((i + 1))
        break
    fi
done
if [[ -n "$target" ]]; then
    exec "$target" "${args[@]:$target_idx}"
fi
echo "bwrap-wrapper: no executable target found in: $*" >&2
exit 1
