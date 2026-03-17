"""
ApiRegistry - loads apis.yaml and provides API configuration by (env, api_name).

apis.yaml structure:
    envs:
      dev:
        Payments:
          baseUrl: https://dev.payments.example.com
          auth:
            type: oauth2_client_credentials
            tokenUrl: https://...
            clientId: ${PAY_CLIENT_ID}
            clientSecret: ${PAY_CLIENT_SECRET}
            scope: payments.write
          defaultHeaders:
            Accept: application/json

${ENV_VAR} placeholders in any string value are expanded from the process environment.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

_ENV_VAR = re.compile(r"\$\{([A-Z0-9_]+)\}")


@dataclass
class AuthCfg:
    type: str = "none"          # none | api_key | oauth2_client_credentials
    token_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scope: Optional[str] = None
    header: Optional[str] = None
    value: Optional[str] = None


@dataclass
class ApiCfg:
    base_url: str = ""
    auth: AuthCfg = field(default_factory=AuthCfg)
    default_headers: dict[str, str] = field(default_factory=dict)


class ApiRegistry:
    _envs: dict[str, dict[str, ApiCfg]] = {}
    _loaded = False

    @classmethod
    def _load(cls) -> None:
        if cls._loaded:
            return
        # Look for apis.yaml in cwd and parents
        candidates = [
            Path("src/test/resources/api/apis.yaml"),
            Path("api/apis.yaml"),
        ]
        for base in [Path.cwd()] + list(Path.cwd().parents)[:3]:
            for rel in candidates:
                p = base / rel
                if p.exists():
                    cls._parse(p)
                    cls._loaded = True
                    return
        raise FileNotFoundError("apis.yaml not found — checked src/test/resources/api/ and api/")

    @classmethod
    def _parse(cls, path: Path) -> None:
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        for env_name, api_map in (raw.get("envs") or {}).items():
            cls._envs[env_name] = {}
            for api_name, api_raw in (api_map or {}).items():
                cls._envs[env_name][api_name] = cls._build_cfg(api_raw or {})

    @classmethod
    def _build_cfg(cls, raw: dict) -> ApiCfg:
        auth_raw = raw.get("auth") or {}
        auth = AuthCfg(
            type=auth_raw.get("type", "none"),
            token_url=_exp(auth_raw.get("tokenUrl")),
            client_id=_exp(auth_raw.get("clientId")),
            client_secret=_exp(auth_raw.get("clientSecret")),
            scope=_exp(auth_raw.get("scope")),
            header=_exp(auth_raw.get("header")),
            value=_exp(auth_raw.get("value")),
        )
        headers = {k: _exp(v) for k, v in (raw.get("defaultHeaders") or {}).items()}
        return ApiCfg(
            base_url=_exp(raw.get("baseUrl", "")),
            auth=auth,
            default_headers=headers,
        )

    @classmethod
    def get(cls, env: str, api_name: str) -> ApiCfg:
        cls._load()
        env_map = cls._envs.get(env)
        if env_map is None:
            raise ValueError(f"Unknown environment: {env!r}")
        cfg = env_map.get(api_name)
        if cfg is None:
            raise ValueError(f"Unknown API {api_name!r} in environment {env!r}")
        return cfg


def _exp(s: str | None) -> str:
    if s is None:
        return ""
    return _ENV_VAR.sub(lambda m: os.environ.get(m.group(1), ""), str(s))
