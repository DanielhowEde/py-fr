"""
EvidenceWriter - saves request/response artifacts to disk for audit/debugging.

Written to: <report_dir>/api/<scenario_name>/<timestamp>/
    request.json
    request.headers.txt
    request.curl.txt
    response.status.txt
    response.headers.txt
    response.json

Sensitive headers (Authorization, X-API-Key, etc.) are redacted in evidence files.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jatefr.utils.api.multi_api_client import ApiResponse

logger = logging.getLogger(__name__)

_SENSITIVE_HEADERS = {"authorization", "x-api-key", "x-auth-token", "cookie"}

# Module-level report directory — set by environment.py before tests run
_report_dir: str = "test-reports"


def set_report_dir(path: str) -> None:
    global _report_dir
    _report_dir = path


def get_report_dir() -> str:
    return _report_dir


def save_request(
    scenario_name: str,
    method: str,
    url: str,
    body: str,
    headers: dict[str, str] | None,
) -> str:
    dir_path = _ensure_dir("api", _safe(scenario_name), _now())
    _write(dir_path / "request.json", _pretty_json(body))
    _write(dir_path / "request.headers.txt", _headers_to_str(headers))
    _write(dir_path / "request.curl.txt", _to_curl(method, url, headers, body))
    return str(dir_path)


def save_response(evidence_dir: str, response: "ApiResponse") -> str:
    p = Path(evidence_dir)
    _write(p / "response.status.txt", str(response.status_code))
    _write(p / "response.headers.txt", _resp_headers_to_str(response))
    _write(p / "response.json", _pretty_json(response.as_string()))
    return evidence_dir


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _ensure_dir(*parts: str) -> Path:
    p = Path(_report_dir, *parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:18]


def _safe(name: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", name)[:80]


def _write(path: Path, data: str) -> None:
    try:
        path.write_text(data or "", encoding="utf-8")
    except Exception as exc:
        logger.error("Failed writing evidence file %s: %s", path, exc)


def _pretty_json(raw: str | None) -> str:
    if not raw or not raw.strip():
        return ""
    try:
        return json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
    except Exception:
        return raw


def _redact(key: str, value: str) -> str:
    return "[REDACTED]" if key.lower() in _SENSITIVE_HEADERS else value


def _headers_to_str(headers: dict[str, str] | None) -> str:
    if not headers:
        return ""
    return "\n".join(f"{k}: {_redact(k, v)}" for k, v in headers.items())


def _resp_headers_to_str(response: "ApiResponse") -> str:
    return "\n".join(f"{k}: {v}" for k, v in response.headers().items())


def _to_curl(method: str, url: str, headers: dict[str, str] | None, body: str) -> str:
    parts = [f"curl -i -X {method} {_q(url)}"]
    if headers:
        for k, v in headers.items():
            parts.append(f"-H {_q(k + ': ' + _redact(k, v))}")
    if body and body.strip():
        parts.append(f"--data {_q(body)}")
    return " ".join(parts)


def _q(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"
