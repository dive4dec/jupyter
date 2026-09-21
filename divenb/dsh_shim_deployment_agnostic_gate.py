#!/usr/bin/env python3
"""Build-time gate: dsh-openai-shim must stay DEPLOYMENT-AGNOSTIC.

The shim is installed into many different environments, so the package must
hold NO provider catalog and NO endpoint URLs. The single source of truth for
every provider is the student's ``~/.dsh/proxy.conf``; the deployment pushes
its own entries in via ``dsh-proxy sync`` (which reads DIVEAI_* / LITELLM_*
from the pod env and upserts the diveai / litellm entries — hermes style).
This gate fails the image build if that contract is ever violated:

  1. no site-packages source of dsh_openai_shim may mention a deployment
     host (cityu.edu.hk / svc.cluster.local) — i.e. no hardcoded endpoints;
  2. the old hardcoded-catalog constants must not reappear;
  3. functional: ``resolve_upstream`` must resolve PURELY from proxy.conf
     (a file-based providers dict) — stripping the trailing /v1 — and must be
     UNAFFECTED by the environment (setting DIVEAI_API_BASE etc. to a hostile
     value must not change what a file provider resolves to);
  4. functional: ``sync_deployment`` must upsert deployment entries, set the
     first-run default, and never clobber a student-added provider.

Exits non-zero (=> build fails) on any violation.
"""
import importlib
import os
import re
import sys

# Deployment hosts (endpoints) that must never leak into the package source.
_BANNED_HOSTS = ("cityu.edu.hk", "svc.cluster.local")
# Constants that encoded the old hardcoded catalog / env-var names.
_BANNED_CONSTS = ("_PROVIDER_BASE", "_PROVIDER_KEY_ENV", "_PROVIDERS")


def find_package_files():
    """Locate the installed dsh_openai_shim package files."""
    try:
        import dsh_openai_shim as pkg
    except ImportError as e:
        print(f"GATE FAIL: cannot import dsh_openai_shim: {e}")
        sys.exit(1)
    root = os.path.dirname(os.path.abspath(pkg.__file__))
    files = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".py"):
                files.append(os.path.join(dirpath, fn))
    return root, files


def main():
    root, files = find_package_files()
    print(f"dsh-shim gate: package at {root} ({len(files)} .py files)")

    violations = []
    for path in files:
        try:
            src = open(path, encoding="utf-8").read()
        except OSError:
            continue
        rel = os.path.relpath(path, root)
        for host in _BANNED_HOSTS:
            if host in src:
                violations.append(f"{rel}: hardcoded host {host!r}")
        for const in _BANNED_CONSTS:
            if re.search(rf"\b{const}\b", src):
                violations.append(f"{rel}: removed constant {const} reappeared")

    # Functional checks against the REAL installed module (fresh import so the
    # check is not defeated by test-patch artifacts).
    cfg = importlib.import_module("dsh_openai_shim.config")
    func_failures = []

    # --- resolution is FILE-based, strips /v1, returns the file key ---------
    fake = {"base_url": "http://fake.upstream.test:8000/v1", "api_key": "fake-key"}
    try:
        base, key, _cap, _win = cfg.resolve_upstream(
            cfg.ProxyConfig(provider="faketest", providers={"faketest": dict(fake)}))
    except ValueError as e:
        func_failures.append(f"resolve_upstream raised for a configured provider: {e}")
    else:
        if base != "http://fake.upstream.test:8000":
            func_failures.append(f"base not file-based / /v1 not stripped: {base!r}")
        if key != "fake-key":
            func_failures.append(f"key not from proxy.conf: {key!r}")

    # --- resolution must be UNAFFECTED by the environment -------------------
    os.environ["DIVEAI_API_BASE"] = "http://evil.host.test:9999/v1"
    os.environ["LITELLM_API_KEY"] = "evil-key"
    try:
        base2, key2, _cap2, _win2 = cfg.resolve_upstream(
            cfg.ProxyConfig(provider="faketest", providers={"faketest": dict(fake)}))
    finally:
        os.environ.pop("DIVEAI_API_BASE", None)
        os.environ.pop("LITELLM_API_KEY", None)
    if (base2, key2) != ("http://fake.upstream.test:8000", "fake-key"):
        func_failures.append(
            f"environment influenced resolution (got {base2!r}, {key2!r}); "
            "resolve_upstream must read ONLY proxy.conf")

    # --- unknown provider -> clear, actionable error ------------------------
    try:
        cfg.resolve_upstream(cfg.ProxyConfig(provider="nosuch",
                                             providers={"real": dict(fake)}))
    except ValueError as e:
        if "nosuch" not in str(e) or "real" not in str(e):
            func_failures.append(
                f"missing-provider error must name the bad name + available: {e}")
    else:
        func_failures.append("unknown provider did not raise ValueError")

    # --- sync_deployment: upsert + first-run default + never clobber --------
    c = cfg.ProxyConfig()
    entries = {"diveai": {"base_url": "http://dive.test/v1", "api_key": "dk"},
               "litellm": {"base_url": "http://lit.test/v1", "api_key": "lk"}}
    if not cfg.sync_deployment(c, entries, default_provider="litellm"):
        func_failures.append("sync_deployment reported no change on first run")
    if c.provider != "litellm":
        func_failures.append(f"first-run default not applied: {c.provider!r}")
    if c.providers.get("diveai", {}).get("api_key") != "dk":
        func_failures.append("sync_deployment did not upsert the diveai entry")
    # student-added provider must survive a later sync untouched
    c.providers["myprov"] = {"base_url": "http://mine.test/v1", "api_key": "mk"}
    c.provider = "myprov"
    cfg.sync_deployment(c, entries, default_provider="litellm")
    if c.provider != "myprov":
        func_failures.append("sync_deployment clobbered the student's provider choice")
    if c.providers.get("myprov") != {"base_url": "http://mine.test/v1", "api_key": "mk"}:
        func_failures.append("sync_deployment modified a student-added provider")

    if violations or func_failures:
        print("dsh-shim gate: FAIL — deployment-agnostic contract violated:")
        for v in violations + func_failures:
            print(f"  - {v}")
        sys.exit(1)
    print("dsh-shim gate: PASS (no hardcoded endpoints; file-based resolution, "
          "env-inert, sync never clobbers — verified)")


if __name__ == "__main__":
    main()
