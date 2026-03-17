"""
TemplateLoader - load and render JSON templates with variable substitution.

Placeholder syntax (mirrors Java version):
    ${var}              — replace with value from vars dict (raises if missing)
    ${var:default}      — replace with default if var absent
    ${{var}}            — raw insert (no JSON-quoting); inserts null if missing
    {date(...),fmt}     — date expression (handled by DateFunctionTemplater)
    {#if ...}{#/if}     — conditional block (handled by ConditionalTemplater)

Usage:
    raw = TemplateLoader.load("src/test/resources/api/Payments/v1/templates/create-payment.json")
    filled = TemplateLoader.render(raw, vars, validate_json=True)
"""

import json
import re
from pathlib import Path
from typing import Any

from jatefr.utils.api import conditional_templater, date_function_templater

_VAR = re.compile(r"\$\{([a-zA-Z0-9_.:-]+)\}")
_RAW_VAR = re.compile(r"\$\{\{([a-zA-Z0-9_.:-]+)\}\}")


def load(resource_path: str) -> str:
    """Load template from a file path or resource path."""
    p = Path(resource_path)
    if p.exists():
        return p.read_text(encoding="utf-8")
    # Strip leading slash and retry relative to cwd
    stripped = resource_path.lstrip("/\\")
    p2 = Path(stripped)
    if p2.exists():
        return p2.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Template not found: {resource_path}")


def render(template: str, vars: dict[str, Any], validate_json: bool = False) -> str:
    """Run conditional → date → variable substitution, then optionally validate JSON."""
    with_conds = conditional_templater.render(template, vars)
    with_dates = date_function_templater.render(with_conds, vars)
    filled = _apply(with_dates, vars)
    if validate_json:
        _assert_valid_json(filled)
    return filled


def apply(template: str, vars: dict[str, Any]) -> str:
    """Apply only variable substitution (no date/conditional pass)."""
    return _apply(template, vars)


def assert_valid_json(json_str: str) -> None:
    _assert_valid_json(json_str)


# ------------------------------------------------------------------
# Internal
# ------------------------------------------------------------------

def _apply(template: str, vars: dict[str, Any]) -> str:
    # Raw insert first (${{var}})
    def raw_replace(m: re.Match) -> str:
        key = m.group(1)
        val = vars.get(key)
        return "null" if val is None else str(val)

    t = _RAW_VAR.sub(raw_replace, template)

    # Normal ${var[:default]}
    def var_replace(m: re.Match) -> str:
        key = m.group(1)
        name, _, default = key.partition(":")
        val = vars.get(name) if vars else None
        if val is None and default:
            val = default
        if val is None:
            raise ValueError(f"Missing template variable: {name!r}")
        return str(val)

    return _VAR.sub(var_replace, t)


def _assert_valid_json(text: str) -> None:
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Filled template is not valid JSON: {exc}\n---\n{text}") from exc
