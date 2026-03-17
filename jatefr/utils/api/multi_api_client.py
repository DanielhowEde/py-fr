"""
MultiApiClient - thin HTTP client backed by requests, mirroring MultiApiClient.java.

Each instance is bound to a single API's base URL and auth provider.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
import urllib3

from jatefr.utils.config.config_reader import ConfigReader
from jatefr.utils.api.auth_provider import AuthProvider

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ApiResponse:
    """Thin wrapper around requests.Response to provide a stable interface."""

    def __init__(self, resp: requests.Response) -> None:
        self._resp = resp

    @property
    def status_code(self) -> int:
        return self._resp.status_code

    def json(self) -> Any:
        return self._resp.json()

    def text(self) -> str:
        return self._resp.text

    def headers(self) -> dict[str, str]:
        return dict(self._resp.headers)

    def as_string(self) -> str:
        return self._resp.text

    def __repr__(self) -> str:
        return f"<ApiResponse {self.status_code}>"


class MultiApiClient:
    def __init__(
        self,
        base_url: str,
        auth: AuthProvider,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = auth
        self._default_headers = default_headers or {}
        self._relax_https = ConfigReader.get_bool("api.relaxed.https", False)

    def _session(self, extra_headers: dict[str, str] | None = None) -> requests.Session:
        s = requests.Session()
        s.verify = not self._relax_https
        s.headers.update(self._default_headers)
        if extra_headers:
            s.headers.update(extra_headers)
        self._auth.apply(s)
        return s

    def get(
        self,
        path: str,
        params: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        url = self._base_url + path
        with self._session(headers) as s:
            resp = s.get(url, params=params)
        logger.debug("GET %s -> %d", url, resp.status_code)
        return ApiResponse(resp)

    def post_json(
        self,
        path: str,
        json_body: str,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        return self._send_with_body("POST", path, json_body, headers)

    def put_json(
        self,
        path: str,
        json_body: str,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        return self._send_with_body("PUT", path, json_body, headers)

    def delete(
        self,
        path: str,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        url = self._base_url + path
        with self._session(headers) as s:
            resp = s.delete(url)
        logger.debug("DELETE %s -> %d", url, resp.status_code)
        return ApiResponse(resp)

    def _send_with_body(
        self,
        method: str,
        path: str,
        json_body: str,
        headers: dict[str, str] | None,
    ) -> ApiResponse:
        url = self._base_url + path
        extra = {"Content-Type": "application/json"}
        if headers:
            extra.update(headers)
        with self._session(extra) as s:
            resp = s.request(method, url, data=json_body.encode("utf-8"))
        logger.debug("%s %s -> %d", method, url, resp.status_code)
        return ApiResponse(resp)
