"""
Tests for OperationParser G/M code boundary detection.

Documents the historical substring bug where ``M3`` matched ``M30``
and ``G2`` matched ``G20`` when settings were searched with ``in``.
"""
from __future__ import annotations

from tests.conftest import install_addin_package, install_adsk_stub

install_adsk_stub()
install_addin_package()

from batch_post.commands.postProcessor.gcode_helpers import code_in_list
from batch_post.commands.postProcessor.settings import settings as settings_mod


def _reset_settings(**overrides):
    base = dict(settings_mod.Settings._defaultSettings)
    base.update(overrides)
    settings_mod.Settings._default = dict(base)
    settings_mod.Settings._items = dict(base)


class _ParserHarness:
    """Minimal stand-in that reuses OperationParser matching helpers."""

    def __init__(self):
        from batch_post.commands.postProcessor.operations.operation.parser import OperationParser

        self._parser_cls = OperationParser
        self._headerEndLine = -1
        self._bodyStartLine = -1
        self._tailStartLine = -1
        self._rotationLine = -1
        self._toolCommentLine = -1
        self.name = "TestOp"

    def parse_header_line(self, line: str, line_number: int, in_header: bool):
        return self._parser_cls._parseHeaderLine(self, line, line_number, in_header)

    def parse_body_line(self, line: str, line_number: int):
        return self._parser_cls._parseBodyLine(self, line, line_number)


def test_m3_does_not_start_tail_when_end_codes_include_m30():
    _reset_settings(**{settings_mod.Settings.END_CODES: "M5\nM9\nM30"})
    harness = _ParserHarness()
    assert harness.parse_body_line("M3\n", 10) is False
    assert harness._tailStartLine == -1
    assert harness.parse_body_line("M30\n", 11) is True
    assert harness._tailStartLine == 11


def test_g2_does_not_end_header_when_header_codes_are_g20_g21():
    _reset_settings(**{settings_mod.Settings.HEADER_END_CODES: "G20\nG21"})
    harness = _ParserHarness()
    harness.parse_header_line("G2 X10 Y0 I5 J0\n", 5, False)
    assert code_in_list("G2", "G20\nG21") is False
    assert harness._headerEndLine == -1

    harness.parse_header_line("G21\n", 6, False)
    assert harness._headerEndLine == 6
