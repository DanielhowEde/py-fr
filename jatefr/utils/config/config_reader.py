"""
ConfigReader - reads config.properties from the project root or classpath.

Usage:
    from jatefr.utils.config.config_reader import ConfigReader

    base_url = ConfigReader.get("base.url")
    timeout  = ConfigReader.get_int("timeout", 10)
    headless = ConfigReader.get_bool("headless", False)
"""

import os
import threading
from pathlib import Path


class ConfigReader:
    _props: dict[str, str] = {}
    _lock = threading.Lock()
    _loaded = False

    @classmethod
    def _load(cls) -> None:
        with cls._lock:
            if cls._loaded:
                return
            # Search for config.properties: cwd, then parents up to 3 levels
            search_dirs = [Path.cwd()] + list(Path.cwd().parents)[:3]
            for base in search_dirs:
                candidate = base / "config.properties"
                if candidate.exists():
                    cls._parse(candidate)
                    break
            cls._loaded = True

    @classmethod
    def _parse(cls, path: Path) -> None:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("!"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    cls._props[key.strip()] = value.strip()

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        cls._load()
        # Environment variables take precedence
        return os.environ.get(key.upper().replace(".", "_"), cls._props.get(key, default))

    @classmethod
    def get_int(cls, key: str, default: int = 0) -> int:
        val = cls.get(key, str(default))
        try:
            return int(val)
        except ValueError:
            return default

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        val = cls.get(key, "").lower()
        if not val:
            return default
        return val in ("true", "1", "yes")
