"""
ScenarioContext - thread-safe key/value store for sharing data between Cucumber steps.

Usage (inside step definitions):
    context.scenario_ctx.set("userId", "abc-123")
    user_id = context.scenario_ctx.get("userId")
"""

import threading
from typing import Any


class ScenarioContext:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def get(self, key: str) -> Any:
        with self._lock:
            return self._data.get(key)

    def contains(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def get_or_default(self, key: str, default: Any) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def all_keys(self) -> set[str]:
        with self._lock:
            return set(self._data.keys())

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
