"""
manage_credentials.py — manage the pytaf encrypted credential store.

Commands:
    generate-key                        Print a new Fernet key to stdout
    add --alias <alias> --file <file>   Add or update a credential (prompts for username/password)
    list --file <file>                  List all stored aliases
    remove --alias <alias> --file <file> Remove a credential

The encryption key is always read from the PYTAF_CREDENTIAL_KEY environment variable.

Examples:
    # 1. Generate a key (store this somewhere safe — treat it like a password)
    python scripts/manage_credentials.py generate-key

    # 2. Export the key
    export PYTAF_CREDENTIAL_KEY=<key from step 1>

    # 3. Add credentials
    python scripts/manage_credentials.py add --alias admin --file credentials.enc
    python scripts/manage_credentials.py add --alias qa-user --file credentials.enc

    # 4. List aliases
    python scripts/manage_credentials.py list --file credentials.enc
"""

import argparse
import getpass
import json
import os
import sys
from pathlib import Path


def _fernet(key_str: str):
    try:
        from cryptography.fernet import Fernet
        return Fernet(key_str.encode())
    except ImportError:
        sys.exit("ERROR: cryptography package not installed. Run: pip install cryptography")


def _load(path: Path, f) -> dict:
    if not path.exists():
        return {}
    try:
        from cryptography.fernet import InvalidToken
        return json.loads(f.decrypt(path.read_bytes()))
    except Exception as exc:
        sys.exit(f"ERROR: Could not decrypt {path}: {exc}")


def _save(path: Path, f, data: dict) -> None:
    path.write_bytes(f.encrypt(json.dumps(data, indent=2).encode()))


def cmd_generate_key(_args) -> None:
    from cryptography.fernet import Fernet
    print(Fernet.generate_key().decode())


def cmd_add(args) -> None:
    key_str = _require_key()
    f = _fernet(key_str)
    path = Path(args.file)
    data = _load(path, f)

    print(f"Adding credentials for alias: {args.alias}")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    data[args.alias] = {"username": username, "password": password}
    _save(path, f, data)
    print(f"Saved. {path} now contains {len(data)} alias(es).")


def cmd_list(args) -> None:
    key_str = _require_key()
    f = _fernet(key_str)
    data = _load(Path(args.file), f)
    if not data:
        print("No credentials stored.")
        return
    print(f"Aliases in {args.file}:")
    for alias, entry in data.items():
        print(f"  {alias}  (username: {entry['username']})")


def cmd_remove(args) -> None:
    key_str = _require_key()
    f = _fernet(key_str)
    path = Path(args.file)
    data = _load(path, f)
    if args.alias not in data:
        sys.exit(f"ERROR: Alias '{args.alias}' not found.")
    del data[args.alias]
    _save(path, f, data)
    print(f"Removed '{args.alias}'. {path} now contains {len(data)} alias(es).")


def _require_key() -> str:
    key = os.environ.get("PYTAF_CREDENTIAL_KEY", "")
    if not key:
        sys.exit("ERROR: PYTAF_CREDENTIAL_KEY environment variable is not set.")
    return key


def main() -> None:
    parser = argparse.ArgumentParser(description="pytaf credential store manager")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("generate-key", help="Print a new encryption key")

    p_add = sub.add_parser("add", help="Add or update a credential")
    p_add.add_argument("--alias", required=True, help="Alias name (e.g. admin, qa-user)")
    p_add.add_argument("--file", default="credentials.enc", help="Credential file path")

    p_list = sub.add_parser("list", help="List stored aliases")
    p_list.add_argument("--file", default="credentials.enc", help="Credential file path")

    p_rm = sub.add_parser("remove", help="Remove a credential")
    p_rm.add_argument("--alias", required=True, help="Alias to remove")
    p_rm.add_argument("--file", default="credentials.enc", help="Credential file path")

    args = parser.parse_args()
    {"generate-key": cmd_generate_key, "add": cmd_add, "list": cmd_list, "remove": cmd_remove}[
        args.command
    ](args)


if __name__ == "__main__":
    main()
