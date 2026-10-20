#!/usr/bin/env python3
"""dsh-web-openinapp-hidden — remove the dsh web UI "open in app" surface.

The `@deepseek-ai/dsh-client-ui-open-in-app` client plugin renders the
top-right "open in <app>" split button (conversation.session.header.utilities
slot) plus the document-preview / deliverables "open path in app" actions.
Every one of those controls SPAWNS a NATIVE desktop application (VS Code
`code`, Cursor, Zed, JetBrains, Finder/Explorer, …) via
`@deepseek-ai/dsh-host-open-in-app`. On Linux the `vscode` catalog entry
resolves to `spawn("code", [path])` — it requires a display manager.

In the divnedb singleuser image there is no display manager and no point in
the native-spawn path: the intended editor is code-server (the JupyterLab
"VS Code" launcher tile -> jupyter-vscode-proxy -> code-server, with the
Jager.dsh-vscode extension baked in). So the top-right icon is DEAD here:
clicking it fires a native `code` spawn that can't display.

This patch NO-OPS the client plugin's `apply(ctx)` — the single function that
mounts the header split button, the sidebar "open path" actions, and the
shortcut — so the whole surface never renders. We do NOT patch the hashed
CSS class names (`.OMoRSG_*`), which change on every dsh build; no-op-ing
apply() is stable across dsh version bumps. No native-spawn code path is
removed — only the UI entry points that reached it.

Applied at BUILD time (after the dsh stage install), baked into the image
layer like dsh-web-tokenless. DETERMINISTIC and LOUD: if the dsh source shape
changes, every replacement asserts and the build fails rather than silently
shipping an image that still shows a broken icon.

Re-run safety: if the file already carries the [dsh-web-openinapp-hidden]
marker we exit 0 without touching it.
"""
import glob
import os
import re
import sys
from typing import NoReturn

# The open-in-app CLIENT plugin lives next to the other @deepseek-ai/* client
# packages. Where npm places it depends on install style (staged/project vs
# global) exactly as in dsh-web-tokenless, so we resolve it layout-agnostic.
DSH_ROOT = os.environ.get(
    "DSH_ROOT", "/opt/conda/lib/dsh-stage/node_modules/@deepseek-ai/dsh"
)
CLIENT_INDEX = "dsh-client-ui-open-in-app/lib/client.js"
MARKER = "[dsh-web-openinapp-hidden]"


def fail(msg: str) -> NoReturn:
    sys.stderr.write("dsh-web-openinapp-hidden: FATAL: %s\n" % msg)
    sys.exit(1)


def find_target():
    """Locate dsh-client-ui-open-in-app/lib/client.js, layout-agnostic
    (same resolution strategy as dsh-web-tokenless)."""
    scope_dir = os.path.dirname(DSH_ROOT)  # .../node_modules/@deepseek-ai (hoisted scope)
    nested_top = os.path.join(DSH_ROOT, "node_modules/@deepseek-ai")
    candidates = [
        os.path.join(scope_dir, CLIENT_INDEX),
        os.path.join(nested_top, CLIENT_INDEX),
        os.path.join(nested_top, "dsh-web-app", "node_modules/@deepseek-ai", CLIENT_INDEX),
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    hits = glob.glob(os.path.join(DSH_ROOT, "node_modules", "**", CLIENT_INDEX), recursive=True)
    if hits:
        return sorted(hits)[0]
    hits = glob.glob(os.path.join(scope_dir, "**", CLIENT_INDEX), recursive=True)
    return sorted(hits)[0] if hits else None


def main() -> None:
    target = find_target()
    if target is None:
        fail("could not locate %s under %s (dsh layout changed?)" % (CLIENT_INDEX, DSH_ROOT))
    try:
        with open(target, "r", encoding="utf-8") as fh:
            src = fh.read()
    except OSError as exc:
        fail("cannot read %s: %s" % (target, exc))

    if MARKER in src:
        print("dsh-web-openinapp-hidden: already patched, nothing to do.")
        return

    # No-op the client plugin's apply(ctx): the single function that mounts the
    # top-right "open in <app>" split button (conversation.session.header.
    # utilities slot), the document-preview / deliverables "open path in app"
    # actions, and the Alt+Opt+O shortcut. All of these spawn NATIVE desktop
    # apps (no display manager in the headless singleuser image), so the whole
    # surface is dead here — the working editor is the JupyterLab "VS Code"
    # launcher tile (code-server). Early-returning apply() removes every UI
    # entry point while leaving the (unreachable, harmless) native-spawn code
    # in place. Anchored to the unique `function apply(ctx) {` + the first
    # statement it runs (the OpenInAppController construction), so it fails
    # loudly if the shape changes.
    a = re.compile(
        r"\t\tfunction apply\(ctx\) \{\n"
        r"\t\t\tconst controller = new OpenInAppController\(\);\n"
        r"\t\t\tcontroller\.load\(\);\n"
    )
    a_new = (
        "\t\tfunction apply(ctx) {\n"
        "\t\t\t/* [dsh-web-openinapp-hidden] divnedb: the open-in-app UI (top-right "
        "split button + sidebar 'open path in app' + shortcut) is REMOVED. It spawns "
        "native desktop apps (code/Cursor/Zed/JetBrains) via dsh-host-open-in-app, "
        "which need a display manager the headless singleuser pod lacks — the working "
        "editor is the JupyterLab 'VS Code' launcher tile (code-server). No-op the "
        "mount so the dead icon never renders. */\n"
        "\t\t\treturn;\n"
    )
    src, n = a.subn(a_new, src, count=1)
    if n != 1:
        fail("apply() no-op did not match — dsh open-in-app client changed shape; "
             "refuse to ship an image that still shows the broken icon.")

    with open(target, "w", encoding="utf-8") as fh:
        fh.write(src)

    print("dsh-web-openinapp-hidden: patched %s (apply() no-op)." % target)


if __name__ == "__main__":
    main()
