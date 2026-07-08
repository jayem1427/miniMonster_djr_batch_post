"""
Shared G-code helpers used by parsing and tests.

Kept free of Fusion imports so unit tests can exercise matching logic
without Autodesk Fusion installed.
"""
from __future__ import annotations


def parse_code_list(raw: str | None) -> set[str]:
    """
    Split a newline-separated G/M code setting into exact tokens.

    Settings are stored as multi-line strings such as ``\"M5\\nM9\\nM30\"``.
    Matching with ``\"M3\" in raw`` is unsafe because ``M30`` contains ``M3``.
    """
    if not raw:
        return set()
    return {line.strip().upper() for line in str(raw).splitlines() if line.strip()}


def code_in_list(code: str, raw: str | None) -> bool:
    """Return True if ``code`` (e.g. ``M3`` or ``G21``) is an exact entry in ``raw``."""
    return code.strip().upper() in parse_code_list(raw)


def coalesce_min_distance(value, default: float = 20.0) -> float:
    """
    Resolve the rapid-move minimum distance setting.

    Uses a truthy fallback (``or``), not bitwise OR. Bitwise ``|`` turns
    user values such as ``15`` into ``31`` (``15 | 20``).
    """
    if value is None:
        return float(default)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float(default)
    return numeric if numeric != 0 else float(default)
