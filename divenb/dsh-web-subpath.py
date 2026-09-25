#!/usr/bin/env python3
"""dsh-web-subpath — make the dsh web UI work under an arbitrary URL subpath.

The `dsh --profile web` SPA is built to be served at the origin root (`/`).
Under the JupyterHub + code-server proxy path (…/vscode/proxy/3080/), the
browser resolves assets/API/WS against the site root instead of the proxy
prefix → all 404 → blank page.

code-server's transparent proxy STRIPS the /vscode/proxy/<port> prefix before
forwarding to 127.0.0.1:3080, so the server always sees root and is fine. The
break is purely client-side URL resolution. The fix makes every client-side
URL base-aware (use the page's <base> instead of location.origin) and strips
the leading slash so the proxy prefix is included:

  1. dsh-host-frontend-static/lib/index.js
     a) <base href="/"> -> <base href="./">
     b) served HTML: /plugins/ -> ./plugins/   (plugin module scripts)
  2. dsh-client-connection/lib/client.js
     a) resolveBase(): location.origin -> document.baseURI
     b) new URL(`${channel}/${endpoint}`, base): strip leading /
  3. dsh-api-gateway/lib/client.js
     a) remoteStreamUrl(): location.origin -> document.baseURI
     b) new URL(REMOTE_STREAM_MUX_PATH, base): strip leading /
  4. dsh-client-ui-chat/lib/client.js
     a) media caller: window.location.origin -> document.baseURI
     b) localPathMediaUrl: strip trailing / from base (avoids //api)
  5. dsh-session-log-export/lib/client.js
     a) hostBase(): location.origin -> document.baseURI
     b) new URL("/api/session.export", base): strip leading /

The RPC `path`/`channel` ARGUMENTS (e.g. file-upload FILE_UPLOAD_PATH, the
`channel !== "/api"` guards) are sent to the server over the connection carrier
and resolved server-side — they are NOT browser URLs and are deliberately
untouched.

Works at origin root too: with no proxy prefix, <base href="./"> resolves to
"/" and document.baseURI = origin+"/", so new URL("api/x", base) is unchanged.

Deterministic: each replacement asserts its target appears exactly once; a dsh
version bump that changes the source shape fails the build loudly. Idempotent
via the end-of-file marker comment.
"""
import glob
import os, sys

# The 5 @deepseek-ai/* packages below are a transitive dep tree of
# @deepseek-ai/dsh. npm places them either HOISTED at
# ${DSH}/node_modules/@deepseek-ai (the 0.2.64-era layout) or NESTED under
# ${DSH}/node_modules/@deepseek-ai/dsh-web-app/node_modules/@deepseek-ai (the
# layout the 0.1.5-rc.3 family resolves to after 0.2.64 was first built). We
# do NOT hardcode the layout: resolve the base dir where ALL five target files
# actually exist, so the patch is layout-agnostic and survives dsh bumps.
DSH = "/opt/conda/lib/node_modules/@deepseek-ai/dsh"
MARKER = "[dsh-web-subpath]"
_PKG_FILES = [
    "dsh-client-connection/lib/client.js",
    "dsh-host-frontend-static/lib/index.js",
    "dsh-api-gateway/lib/client.js",
    "dsh-client-ui-chat/lib/client.js",
    "dsh-session-log-export/lib/client.js",
]
_BASE_CANDIDATES = [
    DSH + "/node_modules/@deepseek-ai",
    DSH + "/node_modules/@deepseek-ai/dsh-web-app/node_modules/@deepseek-ai",
]


def fail(msg):
    sys.stderr.write("FATAL: %s\n" % msg)
    sys.exit(1)


def _resolve_base():
    for base in _BASE_CANDIDATES:
        if all(os.path.isfile(os.path.join(base, f)) for f in _PKG_FILES):
            return base
    # Last resort: locate each file anywhere under the dsh tree; require all 5.
    found = {}
    for f in _PKG_FILES:
        hits = glob.glob(DSH + "/node_modules/**/@deepseek-ai/" + f, recursive=True)
        if not hits:
            fail("dsh-web-subpath: cannot find %s under %s (dsh layout changed?)"
                 % (f, DSH))
        found[f] = sorted(hits)[0]
    # If all are found in one directory, use it; else fail (mixed layout is
    # not expected).
    dirs = {os.path.dirname(os.path.dirname(found[f])) for f in _PKG_FILES}
    if len(dirs) == 1:
        return dirs.pop()
    fail("dsh-web-subpath: target files span multiple dirs %s — layout changed"
         % sorted(dirs))


BASE = _resolve_base()

def patch_file(path, patches):
    if not os.path.exists(path):
        fail("file not found: %s" % path)
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    if MARKER in src:
        print("  %s: already patched, skipping" % os.path.basename(path))
        return
    for i, (old, new, desc) in enumerate(patches, 1):
        count = src.count(old)
        if count != 1:
            fail("%s patch %d (%s): expected 1 occurrence, found %d"
                 % (os.path.basename(path), i, desc, count))
        src = src.replace(old, new, 1)
    src += "\n/* %s: subpath-aware (base-aware) dsh web UI */\n" % MARKER
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("  %s: %d patches applied" % (os.path.basename(path), len(patches)))

# ── 1. dsh-host-frontend-static: base tag + /plugins/ rewrite ──
# Original (tail of the renderIndex return):
#   .replace(/<head(?:\s[^>]*)?>/i, (open) => `${open}<base href="/">`);
# New: also rewrite absolute /plugins/ to relative ./plugins/ in the served HTML.
p1_old = '.replace(/<head(?:\\s[^>]*)?>/i, (open) => `${open}<base href="/">`);'
p1_new = ('.replace(/<head(?:\\s[^>]*)?>/i, (open) => `${open}<base href="./">`)'
          '.replace(/\\/plugins\\//g, "./plugins/")')

patch_file(f"{BASE}/dsh-host-frontend-static/lib/index.js", [
    (p1_old, p1_new, "base tag + /plugins/ rewrite"),
])

# ── 2. dsh-client-connection: resolveBase + RPC URL ──
p2a_old = 'return location?.origin !== void 0 && location.origin !== "null" ? location.origin : INTERNAL_BASE;'
p2a_new = ('return document?.baseURI !== void 0 && document.baseURI !== "null" ? document.baseURI '
           ': (location?.origin !== void 0 && location.origin !== "null" ? location.origin : INTERNAL_BASE);')

p2b_old = 'new URL(`${channel}/${endpoint}`, resolveBase())'
p2b_new = 'new URL(`${channel}/${endpoint}`.replace(/^\\//, ""), resolveBase())'

patch_file(f"{BASE}/dsh-client-connection/lib/client.js", [
    (p2a_old, p2a_new, "resolveBase: baseURI"),
    (p2b_old, p2b_new, "RPC URL: strip leading /"),
])

# ── 3. dsh-api-gateway: WebSocket base + path ──
p3a_old = 'const base = location?.origin !== void 0 && location.origin !== "null" ? location.origin : INTERNAL_BASE;'
p3a_new = ('const base = document?.baseURI !== void 0 && document.baseURI !== "null" ? document.baseURI '
           ': (location?.origin !== void 0 && location.origin !== "null" ? location.origin : INTERNAL_BASE);')

p3b_old = 'const url = new URL(REMOTE_STREAM_MUX_PATH, base);'
p3b_new = 'const url = new URL(REMOTE_STREAM_MUX_PATH.replace(/^\\//, ""), base);'

patch_file(f"{BASE}/dsh-api-gateway/lib/client.js", [
    (p3a_old, p3a_new, "WS base: baseURI"),
    (p3b_old, p3b_new, "WS URL: strip leading /"),
])

# ── 4. dsh-client-ui-chat: local-path media URL ──
p4a_old = 'const { protocol, origin } = window.location;'
p4a_new = 'const protocol = window.location.protocol, origin = document.baseURI;'

p4b_old = 'return `${origin}/api/file?path=${encodeURIComponent(value)}`;'
p4b_new = 'return `${origin.replace(/\\/$/, "")}/api/file?path=${encodeURIComponent(value)}`;'

patch_file(f"{BASE}/dsh-client-ui-chat/lib/client.js", [
    (p4a_old, p4a_new, "media caller: baseURI"),
    (p4b_old, p4b_new, "media URL: strip trailing /"),
])

# ── 5. dsh-session-log-export: hostBase + export URL ──
p5a_old = 'const origin = globalThis.location?.origin;'
p5a_new = 'const origin = globalThis.document?.baseURI ?? globalThis.location?.origin;'

p5b_old = 'const url = new URL("/api/session.export", hostBase());'
p5b_new = 'const url = new URL("api/session.export", hostBase());'

patch_file(f"{BASE}/dsh-session-log-export/lib/client.js", [
    (p5a_old, p5a_new, "export hostBase: baseURI"),
    (p5b_old, p5b_new, "export URL: strip leading /"),
])

print("dsh-web-subpath: all patches applied")
