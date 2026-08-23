"""Regression tests for LinuxCNC-safe merged G-code output."""

from commands.postProcessor.gcode_helpers import (
    filter_merged_source_line,
    force_rapid_start_line,
    format_comment,
    is_percent_line,
    sanitize_comment_text,
    strip_inline_comments,
)


def test_is_percent_line():
    assert is_percent_line("%\n")
    assert is_percent_line("  %%  \n")
    assert not is_percent_line("G1 X0\n")
    assert not is_percent_line("(percent % in comment)\n")


def test_filter_merged_source_line_drops_percent_delimiters():
    assert filter_merged_source_line("%\n") is None
    assert filter_merged_source_line("  %  \n") is None
    assert filter_merged_source_line("G1 X0\n") == "G1 X0\n"


def test_strip_inline_comments_removes_parenthetical_and_semicolon():
    assert strip_inline_comments("G1 Z5. (retract)") == "G1 Z5."
    assert strip_inline_comments("G1 X0 ; traverse") == "G1 X0"
    assert strip_inline_comments("N10 G0 X1 (a) Y2 (b)") == "N10 G0 X1 Y2"


def test_strip_inline_comments_handles_nested_parentheses():
  # LinuxCNC rejects nested comments; strip the whole parenthetical group.
    assert strip_inline_comments("G1 Z5 (outer (inner))") == "G1 Z5"


def test_force_rapid_start_strips_existing_inline_comments():
    assert force_rapid_start_line("G1 Z5. (retract)\n") == "G0 Z5. (Rapid movement start)\n"
    assert force_rapid_start_line("G1 Z5. (a) (b)\n") == "G0 Z5. (Rapid movement start)\n"


def test_sanitize_comment_text_escapes_parentheses():
    assert sanitize_comment_text("Op (variant)") == "Op [variant]"
    assert format_comment("Op (variant)") == "(Op [variant])"
