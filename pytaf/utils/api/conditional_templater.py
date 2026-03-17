"""
ConditionalTemplater - renders {#if var}...{#else}...{#/if} blocks inside JSON templates.

Supports:
    {#if var}           — truthy check
    {#if eq var "val"}  — equality
    {#if ne var "val"}  — inequality
    {#if contains var "val"} — substring / collection contains
    {#else}             — optional else branch
    {#/if}              — end tag

Trailing commas before } or ] are cleaned up automatically.
"""

import re
from typing import Any


_IF_BLOCK = re.compile(
    r"\{#if\s+([^}]+)}(.*?)(?:\{#else}(.*?))?\{#/if}",
    re.DOTALL,
)


def render(template: str, vars: dict[str, Any]) -> str:
    out = template
    while True:
        m = _IF_BLOCK.search(out)
        if not m:
            break
        expr = m.group(1).strip()
        then_part = m.group(2)
        else_part = m.group(3)

        ok = _eval(expr, vars)
        replacement = then_part if ok else (else_part or "")
        out = out[: m.start()] + replacement + out[m.end() :]

    # Clean trailing commas before } or ]
    out = re.sub(r",\s*([}\]])", r"\1", out)
    return out


def _eval(expr: str, vars: dict[str, Any]) -> bool:
    parts = _split_expr(expr)
    if len(parts) == 1:
        return _truthy(vars.get(parts[0]))

    op, key = parts[0], parts[1]
    rhs = _unquote(parts[2]) if len(parts) > 2 else None
    val = vars.get(key)

    if op == "eq":
        return val is not None and str(val) == rhs
    if op == "ne":
        return val is None or str(val) != rhs
    if op == "contains":
        if isinstance(val, (list, set)):
            return any(str(x) == rhs for x in val)
        return rhs in str(val) if val is not None else False
    return False


def _split_expr(expr: str) -> list[str]:
    tokens: list[str] = []
    in_quote = False
    cur: list[str] = []
    for ch in expr:
        if ch == '"':
            in_quote = not in_quote
            cur.append(ch)
        elif ch.isspace() and not in_quote:
            if cur:
                tokens.append("".join(cur))
                cur = []
        else:
            cur.append(ch)
    if cur:
        tokens.append("".join(cur))
    return tokens


def _unquote(s: str | None) -> str | None:
    if s and len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


def _truthy(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v).strip()
    return bool(s) and s.lower() not in ("false", "0")
