"""
CredentialStore — secure credential management for pytaf.

Credentials are resolved in priority order:
    1. Encrypted file  (credentials.enc, decrypted with PYTAF_CREDENTIAL_KEY)
    2. Environment variables  ({ALIAS}_USERNAME / {ALIAS}_PASSWORD)

The encrypted file is a Fernet-encrypted JSON object:
    {
        "admin":   {"username": "alice",   "password": "s3cr3t"},
        "qa-user": {"username": "bob",     "password": "hunter2"}
    }

Aliases are matched case-insensitively.

Config keys (config.properties):
    credential.file   Path to the encrypted credentials file (default: credentials.enc)
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # no-op if already loaded; ensures .env is available when used outside Behave

logger = logging.getLogger(__name__)


class CredentialStore:
    _cache: dict | None = None
    _lock = threading.Lock()

    @classmethod
    def get(cls, alias: str) -> tuple[str, str]:
        """Return (username, password) for the given alias."""
        creds = cls._from_file(alias)
        if creds:
            return creds
        return cls._from_env(alias)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the in-memory decrypted cache. Call between test suites if needed."""
        with cls._lock:
            cls._cache = None

    # ------------------------------------------------------------------
    # Encrypted file provider
    # ------------------------------------------------------------------

    @classmethod
    def _from_file(cls, alias: str) -> tuple[str, str] | None:
        key_str = os.environ.get("PYTAF_CREDENTIAL_KEY", "")
        if not key_str:
            return None

        if cls._cache is None:
            cls._load_file(key_str)

        if not cls._cache:
            return None

        # Case-insensitive alias lookup
        normalised = alias.lower().replace("-", "_").replace(" ", "_")
        for stored_alias, entry in cls._cache.items():
            if stored_alias.lower().replace("-", "_").replace(" ", "_") == normalised:
                return entry["username"], entry["password"]

        return None

    @classmethod
    def _load_file(cls, key_str: str) -> None:
        from cryptography.fernet import Fernet, InvalidToken
        from pytaf.utils.config.config_reader import ConfigReader

        cred_file = ConfigReader.get("credential.file", "credentials.enc")
        path = Path(cred_file)

        with cls._lock:
            if cls._cache is not None:
                return
            if not path.exists():
                logger.warning("Credential file not found: %s", path.resolve())
                cls._cache = {}
                return
            try:
                f = Fernet(key_str.encode())
                decrypted = f.decrypt(path.read_bytes())
                cls._cache = json.loads(decrypted)
                logger.info("Loaded %d credential(s) from %s", len(cls._cache), path)
            except InvalidToken as exc:
                raise RuntimeError(
                    "PYTAF_CREDENTIAL_KEY is set but could not decrypt credentials.enc — "
                    "wrong key or corrupted file."
                ) from exc
            except Exception as exc:
                raise RuntimeError(f"Failed to load credential file: {exc}") from exc

    # ------------------------------------------------------------------
    # Environment variable provider
    # ------------------------------------------------------------------

    @classmethod
    def _from_env(cls, alias: str) -> tuple[str, str]:
        env_key = alias.upper().replace("-", "_").replace(" ", "_")
        username = os.environ.get(f"{env_key}_USERNAME", "")
        password = os.environ.get(f"{env_key}_PASSWORD", "")
        if not username or not password:
            raise RuntimeError(
                f"No credentials found for alias '{alias}'. "
                f"Options:\n"
                f"  1. Set {env_key}_USERNAME and {env_key}_PASSWORD environment variables.\n"
                f"  2. Add the alias to credentials.enc and set PYTAF_CREDENTIAL_KEY."
            )
        return username, password
