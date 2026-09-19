#!/usr/bin/env python3
"""dsh-web-tokenless — remove the dsh web UI launch-token/cookie requirement.

The `dsh --profile web` server mints a random launch token at startup and
gates BOTH the index page (`/`) and every `/api` + WebSocket call behind the
token->signed-cookie exchange (see BrowserAuth in
`@deepseek-ai/dsh-client-connection`). There is no flag/env/config to turn
this off; it is by-design.

In the divnedb image the web server binds 127.0.0.1 only and is reachable
EXCLUSIVELY through the code-server port-forward, which itself sits behind
JupyterHub authentication (and implies full pod shell access). So the token
adds no real security — it is only friction. This patch disables the
token/cookie requirement while KEEPING the loopback host-fence
(`isTrustedApiRequest` -> 403) that is the actual network boundary.

Applied at BUILD time (after `npm install -g @deepseek-ai/dsh`) so it is
baked into the image layer — durable across pod respawns, like the
dsh-openai-shim. It is DETERMINISTIC and LOUD: if the dsh source ever changes
shape (a dsh version bump), every replacement asserts and the build fails
rather than silently shipping an unpatched/token-gated image.

Re-run safety: if the file already carries the [dsh-web-tokenless] marker we
exit 0 without touching it.
"""
import re
import sys

TARGET = (
    "/opt/conda/lib/node_modules/@deepseek-ai/dsh"
    "/node_modules/@deepseek-ai/dsh-client-connection/lib/index.js"
)
MARKER = "[dsh-web-tokenless]"


def fail(msg: str) -> None:
    sys.stderr.write("dsh-web-tokenless: FATAL: %s\n" % msg)
    sys.exit(1)


def main() -> None:
    try:
        with open(TARGET, "r", encoding="utf-8") as fh:
            src = fh.read()
    except OSError as exc:
        fail("cannot read %s: %s" % (TARGET, exc))

    if MARKER in src:
        print("dsh-web-tokenless: already patched, nothing to do.")
        return

    # ------------------------------------------------------------------ #
    # Patch A: neutralize BrowserAuth.isAuthenticated -> always authorized. #
    # This is the single decision point consulted by BOTH the index page    #
    # (authorizeIndex: `if (this.isAuthenticated(req)) return true;`) and  #
    # the /api + WebSocket gate (requestRejection:                         #
    #   `... ? void 0 : 401`). Returning true disables the token/cookie     #
    # requirement everywhere it is used.                                    #
    # ------------------------------------------------------------------ #
    a = re.compile(
        r"isAuthenticated\(request\)\s*\{\n"
        r"\t\tconst authority = requestAuthority\(request\.headers\);\n"
        r"\t\tconst rawCookie = header\(request\.headers, \"cookie\"\);\n"
        r"\t\tif \(authority === void 0 \|\| rawCookie === void 0\) return false;\n"
        r"\t\tconst value = cookieValue\(rawCookie, cookieName\(authority\)\);\n"
        r"\t\tif \(value === void 0\) return false;\n"
        r"\t\tconst payload = decodeCookie\(value, this\.secret\);\n"
        r"\t\tif \(payload === void 0 \|\| payload\.authority !== authority\) return false;\n"
        r"\t\tconst now = Date\.now\(\);\n"
        r"\t\treturn payload\.issuedAt <= now && payload\.expiresAt > now && "
        r"payload\.expiresAt > payload\.issuedAt && payload\.expiresAt - payload\.issuedAt "
        r"<= this\.maxAgeMilliseconds;\n"
        r"\t\}",
    )
    a_new = (
        "isAuthenticated(request) {\n"
        "\t\t/* [dsh-web-tokenless] divnedb: token/cookie auth DISABLED. The web server "
        "binds 127.0.0.1 only and is reachable exclusively via the code-server "
        "port-forward behind JupyterHub auth, so the launch-token/cookie added no "
        "security. The loopback host-fence (isTrustedApiRequest -> 403) is still "
        "enforced in requestRejection for /api and WebSocket. */\n"
        "\t\treturn true;\n"
        "\t}"
    )
    src, n = a.subn(a_new, src, count=1)
    if n != 1:
        fail("Patch A (isAuthenticated) did not match — dsh source changed shape; "
             "refuse to ship an unpatched token-gated image.")

    # ------------------------------------------------------------------ #
    # Patch B: make requestRejection explicit + self-documenting.          #
    # After Patch A this already resolves to `void 0` (pass) for loopback;  #
    # we state it directly so a future re-enable of isAuthenticated cannot #
    # silently re-gate /api. The 403 loopback fence is RETAINED.           #
    # ------------------------------------------------------------------ #
    b = re.compile(
        r"if \(!isTrustedApiRequest\(request, this\.trustedHosts\)\) return 403;\n"
        r"\t\treturn this\.browserAuth\.isAuthenticated\(request\) \? void 0 : 401;\n"
        r"\t\}",
    )
    b_new = (
        "if (!isTrustedApiRequest(request, this.trustedHosts)) return 403;\n"
        "\t\treturn void 0; /* [dsh-web-tokenless] loopback fence retained; token/cookie "
        "dropped */\n"
        "\t}"
    )
    src, n = b.subn(b_new, src, count=1)
    if n != 1:
        fail("Patch B (requestRejection) did not match — dsh source changed shape.")

    # ------------------------------------------------------------------ #
    # Patch C: keep the printed startup URL clean (no `?token=...`).       #
    # authenticatedUrl() otherwise appends the launch token to the URL.    #
    # ------------------------------------------------------------------ #
    c = re.compile(
        r"(\t\turl\.search = \"\";\n"
        r"\t\turl\.hash = \"\";\n)"
        r"\t\turl\.searchParams\.set\(TOKEN_QUERY, this\.launchToken\);\n"
        r"(\t\treturn url\.href;)"
    )
    c_new = (
        "\\1"
        "\t\t/* [dsh-web-tokenless] do not append ?token=... to the printed URL */\n"
        "\\2"
    )
    src, n = c.subn(c_new, src, count=1)
    if n != 1:
        fail("Patch C (authenticatedUrl) did not match — dsh source changed shape.")

    with open(TARGET, "w", encoding="utf-8") as fh:
        fh.write(src)

    print("dsh-web-tokenless: patched %s (isAuthenticated + requestRejection + authenticatedUrl)." % TARGET)


if __name__ == "__main__":
    main()
