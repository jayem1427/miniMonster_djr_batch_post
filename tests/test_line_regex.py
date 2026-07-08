"""
Tests for line-number-aware G-code parsing used by rapid restore / A-axis.
"""
from __future__ import annotations

from tests.conftest import install_addin_package, install_adsk_stub

install_adsk_stub()
install_addin_package()

from batch_post.commands.postProcessor.line import Line


def test_parse_line_matches_g1_with_line_number_prefix():
    match = Line._PARSE_LINE_RE.match("N100 G1 Z10.0 F300\n")
    assert match is not None
    assert match.group("G") is not None
    assert int(float(match.group("G"))) == 1
    assert match.group("Z") is not None


def test_parse_line_matches_plain_g1():
    match = Line._PARSE_LINE_RE.match("G1 X10 Y20 F200\n")
    assert match is not None
    assert int(float(match.group("G"))) == 1
