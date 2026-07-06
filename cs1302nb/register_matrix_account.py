#!/usr/bin/env python3
"""
Register a Matrix account on the CS1302 server using the shared secret.

Usage:
    python3 register_matrix_account.py

This script registers your Matrix account with a password so you can:
- Sign in to Element Web with password (in addition to SSO)
- Sign in to Element X mobile app
- Change your password later in Element's settings

The account is created with your JupyterHub username. After registering,
you can also link your JupyterHub SSO by signing in via SSO once —
it will map to the same account.
"""

import hmac
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error

SERVER = "https://socratic.cs.cityu.edu.hk/matrix"
# The shared secret is embedded in the image — it allows account creation
# without open registration, but only from within JupyterHub.
SHARED_SECRET = "3rBQDnFvyx2KpR8sWmT6qJh1aE0zU7cN4oYbL3iV2eC6gH5sD9mP1tQ8rX4aZ0w"


def main():
    print("=" * 60)
    print("  Matrix Account Registration for CS1302")
    print("=" * 60)
    print()

    # Get username
    default_user = os.environ.get("JUPYTERHUB_USER", "")
    if default_user:
        username = input(f"Matrix username [{default_user}]: ").strip()
        if not username:
            username = default_user
    else:
        username = input("Matrix username: ").strip()

    if not username:
        print("Error: username is required")
        sys.exit(1)

    # Get password
    import getpass
    password = getpass.getpass("Choose a password: ")
    if len(password) < 8:
        print("Error: password must be at least 8 characters")
        sys.exit(1)
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("Error: passwords do not match")
        sys.exit(1)

    print()
    print(f"Registering @{username}:socratic.cs.cityu.edu.hk ...")

    # Step 1: Get nonce
    try:
        with urllib.request.urlopen(f"{SERVER}/_synapse/admin/v1/register") as resp:
            nonce_data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Error getting nonce: {e}")
        sys.exit(1)

    nonce = nonce_data["nonce"]

    # Step 2: Compute MAC
    mac = hmac.new(
        key=SHARED_SECRET.encode(),
        digestmod=hashlib.sha1,
    )
    mac.update(nonce.encode())
    mac.update(b"\x00")
    mac.update(username.encode())
    mac.update(b"\x00")
    mac.update(password.encode())
    mac.update(b"\x00")
    mac.update(b"notadmin")
    mac_hex = mac.hexdigest()

    # Step 3: Register
    body = json.dumps({
        "nonce": nonce,
        "username": username,
        "password": password,
        "admin": False,
        "mac": mac_hex,
    }).encode()

    req = urllib.request.Request(
        f"{SERVER}/_synapse/admin/v1/register",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Registration failed: {error_body}")
        if "M_USER_IN_USE" in error_body:
            print()
            print("This username is already registered.")
            print("If you forgot your password, contact your instructor to reset it.")
        sys.exit(1)

    print()
    print(f"✓ Account created: {result['user_id']}")
    print()
    print("You can now sign in to Element:")
    print(f"  Web:  https://socratic.cs.cityu.edu.hk/element/")
    print(f"  Username: {username}")
    print(f"  Password: (the one you just chose)")
    print()
    print("To also enable SSO (JupyterHub) login on the same account:")
    print("  1. Sign in to Element Web with your password")
    print("  2. Go to Settings → Account & Privacy")
    print("  3. Look for 'Identity Providers' or 'SSO' and link JupyterHub")


if __name__ == "__main__":
    main()
