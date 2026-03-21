"""
AuthProvider - pluggable authentication strategies for the API client.

Supported types:
    none                        — no auth
    api_key                     — static header: value
    oauth2_client_credentials   — fetches a Bearer token via client-credentials flow,
                                  caches it and refreshes before expiry
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Protocol

import requests

from pytaf.utils.api.api_registry import ApiCfg, AuthCfg

logger = logging.getLogger(__name__)

_TOKEN_EXPIRY_BUFFER_SECONDS = 30
_DEFAULT_TTL_SECONDS = 300


class AuthProvider(Protocol):
    def apply(self, session: requests.Session) -> None: ...


class NoneAuth:
    def apply(self, session: requests.Session) -> None:
        pass


class ApiKeyAuth:
    def __init__(self, header: str, value: str) -> None:
        self._header = header
        self._value = value

    def apply(self, session: requests.Session) -> None:
        session.headers[self._header] = self._value


class OAuth2ClientCredentials:
    def __init__(self, token_url: str, client_id: str, client_secret: str, scope: str) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope or ""
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = threading.Lock()

    def apply(self, session: requests.Session) -> None:
        with self._lock:
            if self._token is None or time.time() >= self._expires_at - _TOKEN_EXPIRY_BUFFER_SECONDS:
                self._refresh()
        session.headers["Authorization"] = f"Bearer {self._token}"

    def _refresh(self) -> None:
        resp = requests.post(
            self._token_url,
            auth=(self._client_id, self._client_secret),
            data={"grant_type": "client_credentials", "scope": self._scope},
            verify=False,  # relaxed HTTPS validation on token endpoint
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"OAuth token request failed with HTTP {resp.status_code}")
        body = resp.json()
        token = body.get("access_token")
        if not token:
            raise RuntimeError("OAuth response did not contain an access_token")
        self._token = token
        ttl = body.get("expires_in", _DEFAULT_TTL_SECONDS)
        self._expires_at = time.time() + (ttl if ttl > 0 else _DEFAULT_TTL_SECONDS)
        logger.info("OAuth2 token refreshed, expires in %ds", ttl)


def from_cfg(cfg: ApiCfg) -> AuthProvider:
    """Factory — build the correct AuthProvider from an ApiCfg."""
    auth: AuthCfg = cfg.auth
    kind = (auth.type or "none").lower()

    if kind == "none":
        return NoneAuth()
    if kind == "api_key":
        return ApiKeyAuth(auth.header or "", auth.value or "")
    if kind == "oauth2_client_credentials":
        return OAuth2ClientCredentials(
            auth.token_url or "",
            auth.client_id or "",
            auth.client_secret or "",
            auth.scope or "",
        )
    raise ValueError(f"Unsupported auth type: {auth.type!r}")
