"""
JsonPathExtractor - extract values from JSON responses using JSONPath expressions.

Expression syntax:
    id                  — simple key (top-level or dot-path)
    items[0].id         — nested path
    expr|first          — take first element of a list
    expr|last           — take last element of a list
    expr|size           — count elements
    expr|join(,)        — join list elements with separator

JSONPath is evaluated via the jsonpath-ng library.
"""

from __future__ import annotations

from typing import Any

from jsonpath_ng import parse as jp_parse

from pytaf.utils.api.multi_api_client import ApiResponse


def extract(response: ApiResponse, expr: str) -> Any:
    path, *mods = [p.strip() for p in expr.split("|")]

    try:
        body = response.json()
    except Exception:
        return None

    # Normalise: bare keys like "id" become "$.id"
    jp_expr = path if path.startswith("$") else f"$.{path}"
    try:
        matches = [m.value for m in jp_parse(jp_expr).find(body)]
    except Exception:
        return None

    val: Any = matches if len(matches) != 1 else matches[0]

    for mod in mods:
        if val is None:
            break
        if mod == "first":
            val = val[0] if isinstance(val, list) and val else None
        elif mod == "last":
            val = val[-1] if isinstance(val, list) and val else None
        elif mod == "size":
            if isinstance(val, (list, dict)):
                val = len(val)
            else:
                val = 0 if val is None else 1
        elif mod.startswith("join(") and mod.endswith(")"):
            sep = mod[5:-1]
            if isinstance(val, list):
                val = sep.join(str(v) for v in val)

    return val
