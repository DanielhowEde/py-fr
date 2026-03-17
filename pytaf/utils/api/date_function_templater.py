"""
DateFunctionTemplater - resolves {date(...)} expressions inside JSON templates.

Supported forms:
    {date(now),yyyy-MM-dd}                     — current date, formatted
    {date(now+7d),yyyy-MM-dd}                  — current date + offset
    {date(myVar|in=dd/MM/yyyy|out=yyyy-MM-dd)} — parse a var then reformat
    {date(now-1M),yyyy-MM-dd'T'HH:mm:ss}       — offsets: y M d h m

Offset units: y=years, M=months, d=days, h=hours, m=minutes
"""

import os
import re
from datetime import datetime, timedelta
from dateutil import relativedelta
from dateutil.tz import gettz
from typing import Any


_BASIC = re.compile(r"\{date\(([^)}]+)\),\s*([^}]+)}")
_EXTENDED = re.compile(r"\{date\(([^)]+)\)}")

_DEFAULT_INPUT_PATTERNS = [
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d%m%Y%H%M%S",
    "%d%m%Y",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y%m%d%H%M%S",
    "%Y%m%d",
]


def _zone():
    tz_name = os.environ.get("API_TIMEZONE", "Europe/London")
    tz = gettz(tz_name)
    return tz or gettz("Europe/London")


def render(template: str, vars: dict[str, Any]) -> str:
    if not template or "{" not in template:
        return template
    out = _replace_basic(template, vars)
    out = _replace_extended(out, vars)
    return out


# ------------------------------------------------------------------
# Basic form: {date(arg),format}
# ------------------------------------------------------------------

def _replace_basic(s: str, vars: dict[str, Any]) -> str:
    def replace(m: re.Match) -> str:
        arg = m.group(1).strip()
        out_pattern = m.group(2).strip()
        dt = _resolve_base(arg, vars, None)
        return _format(dt, out_pattern)

    return _BASIC.sub(replace, s)


# ------------------------------------------------------------------
# Extended form: {date(base|in=...|out=...)}
# ------------------------------------------------------------------

def _replace_extended(s: str, vars: dict[str, Any]) -> str:
    def replace(m: re.Match) -> str:
        arg = m.group(1).strip()
        opts = _parse_opts(arg)
        base = opts.get("base", "now")
        in_pat = opts.get("in")
        out_pat = opts.get("out", "%Y-%m-%dT%H:%M:%S")
        dt = _resolve_base(base, vars, in_pat)
        return _format(dt, out_pat)

    return _EXTENDED.sub(replace, s)


def _parse_opts(arg: str) -> dict[str, str]:
    parts = arg.split("|")
    result: dict[str, str] = {"base": parts[0].strip()}
    for part in parts[1:]:
        if "=" in part:
            k, _, v = part.partition("=")
            result[k.strip()] = v.strip()
    return result


# ------------------------------------------------------------------
# Resolution helpers
# ------------------------------------------------------------------

def _resolve_base(base: str, vars: dict[str, Any], explicit_in_pattern: str | None) -> datetime:
    tz = _zone()
    if base.startswith("now"):
        dt = datetime.now(tz=tz)
        offset_str = base[3:]
        return _apply_offset(dt, offset_str)

    # Variable reference, with optional trailing offset
    name = base
    offset_str = ""
    pm_idx = _index_of_plus_minus(base)
    if pm_idx > 0:
        name = base[:pm_idx]
        offset_str = base[pm_idx:]

    val = vars.get(name) if vars else None
    if val is None:
        raise ValueError(f"Missing date source for variable: {name}")

    dt = _parse_date(str(val).strip(), explicit_in_pattern, tz)
    return _apply_offset(dt, offset_str)


def _apply_offset(dt: datetime, offset: str) -> datetime:
    if not offset:
        return dt
    for m in re.finditer(r"([+-])(\d+)([yMdhm])", offset):
        sign = 1 if m.group(1) == "+" else -1
        amt = int(m.group(2)) * sign
        unit = m.group(3)
        if unit == "y":
            dt = dt + relativedelta.relativedelta(years=amt)
        elif unit == "M":
            dt = dt + relativedelta.relativedelta(months=amt)
        elif unit == "d":
            dt += timedelta(days=amt)
        elif unit == "h":
            dt += timedelta(hours=amt)
        elif unit == "m":
            dt += timedelta(minutes=amt)
    return dt


def _index_of_plus_minus(s: str) -> int:
    depth = 0
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch in ("+", "-") and depth == 0:
            return i
    return -1


def _parse_date(text: str, explicit_pattern: str | None, tz) -> datetime:
    patterns = [explicit_pattern] if explicit_pattern else _DEFAULT_INPUT_PATTERNS
    for pat in patterns:
        if pat is None:
            continue
        # Convert Java-style patterns to Python strftime
        py_pat = _java_to_python_fmt(pat)
        try:
            dt = datetime.strptime(text, py_pat)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            return dt
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date format: {text!r}")


def _format(dt: datetime, pattern: str) -> str:
    return dt.strftime(_java_to_python_fmt(pattern))


def _java_to_python_fmt(pattern: str) -> str:
    """Best-effort Java SimpleDateFormat → Python strftime conversion."""
    mapping = [
        ("yyyy", "%Y"),
        ("yy", "%y"),
        ("MM", "%m"),
        ("dd", "%d"),
        ("HH", "%H"),
        ("mm", "%M"),
        ("ss", "%S"),
        ("SSS", "%f"),
        ("'T'", "T"),
    ]
    result = pattern
    for java, py in mapping:
        result = result.replace(java, py)
    return result
