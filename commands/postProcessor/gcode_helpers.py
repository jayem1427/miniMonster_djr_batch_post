"""
Shared G-code helpers used by parsing and tests.

Kept free of Fusion imports so unit tests can exercise matching logic
without Autodesk Fusion installed.
"""
from __future__ import annotations
import re
import time
from pathlib import Path


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


def is_percent_line(line: str) -> bool:
    """True when the line is only a LinuxCNC percent delimiter (``%`` / ``%%``)."""
    stripped = line.strip()
    return stripped in ("%", "%%")


def is_tail_gap_line(line: str) -> bool:
    """
    True for blanks, ``%`` / ``%%``, and full-line comments.

    These may appear inside an ending sequence (or after ``M30``) and must
    not cancel a trailing end-code run.
    """
    stripped = line.strip()
    if not stripped or is_percent_line(line):
        return True
    return stripped.startswith("(") and stripped.endswith(")")


def sanitize_comment_text(text: str) -> str:
    """
    Make arbitrary text safe inside a LinuxCNC ``(...)`` comment.

    Parentheses cannot be nested in RS-274 comments; replace them so operation
    names and other injected text cannot break parsing.
    """
    return str(text).replace("(", "[").replace(")", "]")


def format_comment(text: str) -> str:
    """Format sanitized text as a full-line LinuxCNC comment."""
    return f"({sanitize_comment_text(text)})"


def strip_inline_comments(line: str) -> str:
    """
    Remove parenthetical and semicolon comments from a G-code line.

    LinuxCNC does not support nested ``(...)`` comments. Stripping before
    appending our own markers avoids invalid multi-comment lines such as
    ``G1 Z5. (retract) (Rapid movement start)``.
    """
    result: list[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "(":
            depth = 1
            i += 1
            while i < len(line) and depth > 0:
                if line[i] == "(":
                    depth += 1
                elif line[i] == ")":
                    depth -= 1
                i += 1
            continue
        if ch == ";":
            break
        result.append(ch)
        i += 1
    return re.sub(r"[ \t]+", " ", "".join(result)).rstrip()


def filter_merged_source_line(line: str) -> str | None:
    """
    Return ``None`` to drop a line when stitching posted operation files.

    Percent delimiters are stripped from merged output. LinuxCNC only allows
    ``%`` as the first and last non-blank lines of a file; Batch Post injects
    its own header comments before the post-processor header, which would leave
    a stray ``%`` in the body. ``M30`` / ``M2`` make percent wrapping optional.
    """
    if is_percent_line(line):
        return None
    return line


def line_matches_end_codes(line: str, end_codes: str | None) -> bool:
    """
    True if the first G/M word on the line is an exact ``END_CODES`` entry.

    Leading ``N`` words and ``(...)`` comments are ignored. ``T15 M600`` does
    not match because the first word is ``T``, not an end code.
    """
    clean = strip_inline_comments(line)
    clean = re.sub(r"^\s*N\d+\s*", "", clean, flags=re.IGNORECASE)
    match = re.match(r"\s*([GM])0*(\d+)", clean, flags=re.IGNORECASE)
    if not match:
        return False
    token = f"{match.group(1).upper()}{int(match.group(2))}"
    return code_in_list(token, end_codes)


def update_trailing_end_sequence(
    current_tail: int,
    *,
    is_end_code: bool,
    is_significant: bool,
    line_number: int,
) -> int:
    """
    Track the start of a trailing M5/M9/M30 (or custom) ending sequence.

    Fusion LinuxCNC posts ``M9`` at the *start* of an operation (coolant off
    before the tool change) as well as using ``M30`` at the end. The first
    matching end code is therefore not the program tail.

    Rules:
    - An end-code line starts a candidate if none is open, otherwise keeps it.
    - A significant body line (motion, tool change, etc.) clears the candidate.
    - Gap lines (blank / comment / ``%``) leave the candidate unchanged.
    """
    if is_end_code:
        return current_tail if current_tail != -1 else line_number
    if is_significant:
        return -1
    return current_tail


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


def wait_for_post_output(
    path: Path,
    *,
    delay: float = 0.2,
    max_loops: int = 10,
    stable_reads: int = 3,
    min_bytes: int = 32,
    require_end_marker: str = "M30",
) -> bool:
    """
    Wait until Fusion finishes writing a post-processor output file.

    ``Path.exists()`` alone is not enough: Fusion often creates an empty
    (or partial) file first, then streams the rest. Rapid analysis that
    runs against that partial file finds nothing, while the later body
    parse sees the completed file — so restore-rapids appears "on" but
    never rewrites any moves.

    When ``require_end_marker`` is set, the file must also contain that
    token (default ``M30``) so a stable mid-write header is not treated
    as complete.
    """
    loops = 0
    last_size = -1
    stable = 0
    marker = (require_end_marker or "").strip().upper()

    while loops < max_loops:
        loops += 1
        if not path.exists() or not path.is_file():
            last_size = -1
            stable = 0
            time.sleep(delay * loops)
            continue

        try:
            size = path.stat().st_size
        except OSError:
            last_size = -1
            stable = 0
            time.sleep(delay * loops)
            continue

        if size < min_bytes:
            last_size = size
            stable = 0
            time.sleep(delay * loops)
            continue

        has_marker = True
        if marker:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                last_size = -1
                stable = 0
                time.sleep(delay * loops)
                continue
            has_marker = marker in text.upper()

        if size == last_size and has_marker:
            stable += 1
            if stable >= stable_reads:
                return True
        else:
            last_size = size
            stable = 1 if has_marker else 0

        time.sleep(delay)

    if not (path.exists() and path.is_file()):
        return False
    try:
        if path.stat().st_size < min_bytes:
            return False
        if marker:
            return marker in path.read_text(encoding="utf-8", errors="replace").upper()
        return True
    except OSError:
        return False


_FEED_WORD_RE = re.compile(r"\s*F[+-]?(?:\d+(?:\.\d*)?|\.\d+)", re.IGNORECASE)
_LEADING_MOTION_G_RE = re.compile(r"^(\s*(?:N\d+\s*)?)G0*[01](?:\.\d*)?\b", re.IGNORECASE)


def strip_feed_words(line: str) -> str:
    """Remove F-words so restored rapids are not capped at feed rate."""
    return _FEED_WORD_RE.sub("", line)


def force_rapid_start_line(line: str) -> str:
    """
    Rewrite a retract/traverse line as ``G0`` and mark it as a restored rapid.

    Handles modal lines such as `` Z5.`` (leading spaces, no G-word) that the
    older G-code regex matched as an empty string.
    """
    working = strip_feed_words(strip_inline_comments(line.rstrip("\r\n")))
    if _LEADING_MOTION_G_RE.match(working):
        working = _LEADING_MOTION_G_RE.sub(r"\1G0", working, count=1)
    else:
        # Modal axis words (" Z5." / "X10 Y20") need an explicit G0.
        working = working.lstrip()
        if working.upper().startswith("N") and working[1:2].isdigit():
            # Rare: N-word without G — keep N, insert G0 after it.
            parts = working.split(None, 1)
            working = parts[0] + " G0" + ((" " + parts[1]) if len(parts) > 1 else "")
        else:
            working = "G0 " + working
    working = re.sub(r"[ \t]+", " ", working).strip()
    return f"{working} (Rapid movement start)\n"
