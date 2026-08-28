"""
A-axis injection when Fusion does not post G0 A0 (no machine definition).
"""
from __future__ import annotations

from io import StringIO
from pathlib import Path

from tests.conftest import install_addin_package, install_adsk_stub

install_adsk_stub()
install_addin_package()

from batch_post.commands.postProcessor.gcode_helpers import (  # noqa: E402
    format_a_axis_angle,
    format_a_axis_rotation_block,
    should_inject_synthetic_a_axis,
)
from batch_post.commands.postProcessor.operations.operation.body import OperationBody  # noqa: E402
from batch_post.commands.postProcessor.settings import settings as settings_mod  # noqa: E402
from batch_post.commands.postProcessor import runtime_options  # noqa: E402


def _reset_settings(**overrides):
    base = dict(settings_mod.Settings._defaultSettings)
    base.update(overrides)
    settings_mod.Settings._default = dict(base)
    settings_mod.Settings._items = dict(base)


class _BodyHarness(OperationBody):
    def __init__(self, path: Path, *, body_start: int = 0, tail_start: int = -1, rotation_line: int = -1, name: str = "Op"):
        self._tempFilePath = path
        self._bodyStartLine = body_start
        self._tailStartLine = tail_start
        self._rotationLine = rotation_line
        self._allowBlankLines = False
        self._lineNumber = 0
        self._rapidsAnalysis = {}
        self.name = name


def _write_source(tmp_path: Path, lines: list[str]) -> Path:
    path = tmp_path / "op.ngc"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class TestFormatAAxis:
    def test_strips_trailing_zeros(self):
        assert format_a_axis_angle(90.0) == "90"
        assert format_a_axis_angle(90.5) == "90.5"
        assert format_a_axis_angle(0) == "0"
        assert format_a_axis_angle(-45.25) == "-45.25"

    def test_retract_block_includes_a_word(self):
        lines = format_a_axis_rotation_block(90, retract_y=False)
        assert "(Rotating A-axis between setups)" in lines
        assert "G90 G53 G0 Z-3" in lines
        assert "G90 G54 G0 A90" in lines

    def test_y_retract_and_first_setup_home(self):
        with_y = format_a_axis_rotation_block(180, retract_y=True, y_coordinate=-100)
        assert "G90 G53 G0 Z-3 Y-100" in with_y
        home = format_a_axis_rotation_block(0, include_retract=False)
        assert home == ["G90 G54 G0 A0"]


class TestShouldInjectSynthetic:
    def test_injects_when_no_native_g0_a0(self):
        assert should_inject_synthetic_a_axis(has_native_rotation=False, rotation_angle=90)

    def test_zero_angle_is_still_injected(self):
        assert should_inject_synthetic_a_axis(has_native_rotation=False, rotation_angle=0)

    def test_skips_when_native_rotation_exists(self):
        assert not should_inject_synthetic_a_axis(has_native_rotation=True, rotation_angle=90)

    def test_skips_when_no_rotation_requested(self):
        assert not should_inject_synthetic_a_axis(has_native_rotation=False, rotation_angle=None)


class TestWriteBodyInjectsWithoutMachinePost:
    """
    Historical bug: A-axis injection only rewrote Fusion's G0 A0. Posts
    without a 4-axis machine definition never emit that line, so 4th-axis
    G-code was silently omitted.
    """

    def setup_method(self):
        _reset_settings(
            **{
                settings_mod.Settings.LINE_SEQUENCE: False,
                settings_mod.Settings.SAFE_Y_RETRACTION: False,
                settings_mod.Settings.Y_RETRACTION_COORDINATE: -100,
            }
        )
        runtime_options.restore_rapid_moves = False

    def test_injects_a_move_when_source_has_no_a_word(self, tmp_path: Path):
        source = _write_source(
            tmp_path,
            [
                "T1 M6",
                "G0 X0 Y0 Z5",
                "G1 Z0 F100",
                "M30",
            ],
        )
        out = StringIO()
        body = _BodyHarness(source, body_start=0, tail_start=3)
        body.WriteBody(out, rotationAngle=90.0, preserveRotation=False)
        text = out.getvalue()
        assert "(Op)" in text
        assert "(Rotating A-axis between setups)" in text
        assert "G90 G53 G0 Z-3" in text
        assert "G90 G54 G0 A90" in text
        assert "G0 X0 Y0 Z5" in text

    def test_first_setup_injects_a0_without_g53(self, tmp_path: Path):
        source = _write_source(tmp_path, ["T1 M6", "G0 X1 Y1 Z5", "M30"])
        out = StringIO()
        body = _BodyHarness(source, body_start=0, tail_start=2)
        body.WriteBody(out, rotationAngle=0.0, preserveRotation=True)
        text = out.getvalue()
        assert "G90 G54 G0 A0" in text
        assert "G53" not in text
        assert "(Rotating A-axis between setups)" not in text

    def test_does_not_inject_when_rotation_not_requested(self, tmp_path: Path):
        source = _write_source(tmp_path, ["T1 M6", "G0 X0 Y0 Z5", "M30"])
        out = StringIO()
        body = _BodyHarness(source, body_start=0, tail_start=2)
        body.WriteBody(out, rotationAngle=None, preserveRotation=True)
        text = out.getvalue()
        assert "A0" not in text
        assert "A90" not in text

    def test_rewrites_native_g0_a0_instead_of_double_injecting(self, tmp_path: Path):
        source = _write_source(
            tmp_path,
            [
                "G0 A0",
                "G0 X0 Y0 Z5",
                "M30",
            ],
        )
        out = StringIO()
        body = _BodyHarness(source, body_start=0, tail_start=2, rotation_line=0)
        body.WriteBody(out, rotationAngle=45.0, preserveRotation=False)
        text = out.getvalue()
        assert text.count("G90 G54 G0 A45") == 1
        assert "G0 A0" not in text
        assert "A45" in text
