"""
Unit tests for Batch Post helpers and RapidsParser.

These tests intentionally document historical bugs so regressions are obvious:
- bitwise OR used as a default for rapid min distance
- substring matching of M/G codes against multi-line settings
- effectiveDist using sum instead of max
- Process button disabled for rotated setups when machine config is optional
- Setup checkboxes greyed out when WCS origin/rotation did not match the reference
- SINGLE_FILE tail taken from the wrong setup
- UNC Path subscripting crash in SetOutputFolder
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

# Ensure package + Fusion stub are installed even if collected without conftest order quirks.
from tests.conftest import install_addin_package, install_adsk_stub, PACKAGE_NAME

install_adsk_stub()
install_addin_package()

from batch_post.commands.postProcessor.gcode_helpers import (  # noqa: E402
    coalesce_min_distance,
    code_in_list,
    parse_code_list,
)
from batch_post.commands.postProcessor.operations.operation.rapidsParser import RapidsParser  # noqa: E402
from batch_post.commands.postProcessor.validation_helpers import (  # noqa: E402
    are_process_inputs_valid,
    is_setup_row_selectable,
    select_single_file_tail_setup,
    should_warn_machine_lacks_a_axis,
    unc_output_folder_value,
)


# ---------------------------------------------------------------------------
# G-code setting helpers
# ---------------------------------------------------------------------------

class TestParseCodeList:
    def test_splits_newline_separated_codes(self):
        assert parse_code_list("M5\nM9\nM30") == {"M5", "M9", "M30"}

    def test_ignores_blank_lines_and_normalizes_case(self):
        assert parse_code_list(" m5 \n\nM30\n") == {"M5", "M30"}

    def test_empty_and_none(self):
        assert parse_code_list("") == set()
        assert parse_code_list(None) == set()


class TestCodeInListExactMatch:
    """
    Historical bug: ``\"M3\" in \"M5\\nM9\\nM30\"`` is True because M30
    contains the substring M3. Exact token matching must reject that.
    """

    def test_m3_is_not_matched_by_m30(self):
        end_codes = "M5\nM9\nM30"
        assert "M3" in end_codes  # documents the unsafe substring check
        assert not code_in_list("M3", end_codes)
        assert code_in_list("M30", end_codes)
        assert code_in_list("M5", end_codes)

    def test_g2_is_not_matched_by_g20(self):
        header_codes = "G20\nG21"
        assert "G2" in header_codes  # documents the unsafe substring check
        assert not code_in_list("G2", header_codes)
        assert code_in_list("G20", header_codes)
        assert code_in_list("g21", header_codes)


class TestCoalesceMinDistance:
    """
    Historical bug: ``value | 20`` is bitwise OR.
    ``15 | 20 == 31``, so a user setting of 15 became 31.
    """

    def test_preserves_user_value(self):
        assert coalesce_min_distance(15) == 15.0
        assert coalesce_min_distance(20) == 20.0

    def test_default_when_none_or_zero(self):
        assert coalesce_min_distance(None) == 20.0
        assert coalesce_min_distance(0) == 20.0

    def test_bitwise_or_would_corrupt_fifteen(self):
        # Guardrail: if someone reintroduces ``| 20``, this documents why not.
        assert (15 | 20) == 31
        assert coalesce_min_distance(15) != (15 | 20)


# ---------------------------------------------------------------------------
# RapidsParser
# ---------------------------------------------------------------------------

def _write_gcode(tmp_path: Path, lines: list[str]) -> Path:
    path = tmp_path / "sample.ngc"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class TestRapidsParserDetectsRetractTraversePlunge:
    def test_detects_simple_rapid_pattern(self, tmp_path: Path):
        path = _write_gcode(
            tmp_path,
            [
                "G21",
                "G0 X0 Y0 Z5",
                "G1 Z0 F100",
                "G1 X10 Y0 F200",
                "G1 Z5 F100",  # retract
                "G1 X20 Y0 F200",  # XY traverse
                "G1 Z0 F100",  # plunge
                "G1 X30 Y0 F200",
                "M30",
            ],
        )
        segments = RapidsParser.parseFile(path)
        assert len(segments) >= 1
        seg = segments[0]
        assert seg["startLine"] == 5
        assert seg["endLine"] == 7

    def test_rejects_arc_in_middle(self):
        # parseFile aborts G2 middles when requireG1=True; analyze() still
        # guards against arcs if a segment is produced another way.
        segment = {
            "dZUp": 10.0,
            "dZDown": 10.0,
            "totalXYDist": 50.0,
            "middle": ["G2 X10 Y0 I5 J0"],
            "end": "G1 Z0",
            "middleLines": [2],
            "startLine": 1,
            "endLine": 3,
        }
        RapidsParser.analyze([segment], minDist=1)
        assert segment["isValid"] is False
        assert "arc_in_middle" in segment["reasons"]


class TestRapidsEffectiveDistanceUsesMax:
    """
    Historical bug: docstring said max(totalXY, zDist) but code used sum.
    A 12 mm XY + 12 mm Z move should pass minDist=20 with max, fail with sum.
    """

    def test_analyze_uses_max_not_sum(self):
        segment = {
            "dZUp": 6.0,
            "dZDown": 6.0,
            "totalXYDist": 12.0,
            "middle": [],
            "end": "G1 Z0",
            "middleLines": [],
            "startLine": 1,
            "endLine": 3,
        }
        RapidsParser.analyze([segment], minDist=20.0)
        assert segment["zDist"] == pytest.approx(12.0)
        assert segment["effectiveDist"] == pytest.approx(12.0)  # max(12, 12)
        assert segment["isValid"] is False
        assert "too_short_effectiveDist" in segment["reasons"]

        # With a lower threshold, max-based distance should accept.
        segment2 = dict(segment)
        segment2["reasons"] = []
        RapidsParser.analyze([segment2], minDist=10.0)
        assert segment2["effectiveDist"] == pytest.approx(12.0)
        assert segment2["isValid"] is True


# ---------------------------------------------------------------------------
# Dialog / merge validation helpers
# ---------------------------------------------------------------------------

class TestProcessInputValidation:
    def test_allows_no_machine_when_rotation_not_requested(self):
        assert are_process_inputs_valid(
            has_program=True,
            can_process=True,
            has_selected_setups=True,
            selected_setups_ok=True,
            rotate_a_axis_enabled=False,
            machine_has_a_axis=False,
            a_axis_rotation_required=True,
        )

    def test_allows_rotation_without_machine_when_enabled(self):
        # Historical bug: Process was disabled unless a Fusion machine
        # reported an A-axis, which blocked multi-setup single-file posting.
        assert are_process_inputs_valid(
            has_program=True,
            can_process=True,
            has_selected_setups=True,
            selected_setups_ok=True,
            rotate_a_axis_enabled=True,
            machine_has_a_axis=False,
            a_axis_rotation_required=True,
        )

    def test_allows_rotation_with_machine(self):
        assert are_process_inputs_valid(
            has_program=True,
            can_process=True,
            has_selected_setups=True,
            selected_setups_ok=True,
            rotate_a_axis_enabled=True,
            machine_has_a_axis=True,
            a_axis_rotation_required=True,
        )

    def test_requires_post_processor(self):
        assert not are_process_inputs_valid(
            has_program=True,
            can_process=False,
            has_selected_setups=True,
            selected_setups_ok=True,
            rotate_a_axis_enabled=False,
            machine_has_a_axis=False,
            a_axis_rotation_required=False,
        )


class TestWarnMachineLacksAAxis:
    def test_no_machine_does_not_warn(self):
        # Historical bug: Process warned (and felt blocked) whenever
        # setups needed A rotation but the NC Program had no machine.
        assert not should_warn_machine_lacks_a_axis(
            has_machine=False,
            machine_has_a_axis=False,
            a_axis_rotation_required=True,
        )

    def test_warns_when_attached_machine_has_no_a_axis(self):
        assert should_warn_machine_lacks_a_axis(
            has_machine=True,
            machine_has_a_axis=False,
            a_axis_rotation_required=True,
        )

    def test_no_warn_when_machine_has_a_axis(self):
        assert not should_warn_machine_lacks_a_axis(
            has_machine=True,
            machine_has_a_axis=True,
            a_axis_rotation_required=True,
        )

    def test_no_warn_when_rotation_not_required(self):
        assert not should_warn_machine_lacks_a_axis(
            has_machine=True,
            machine_has_a_axis=False,
            a_axis_rotation_required=False,
        )


class TestSetupRowSelectable:
    def test_requires_valid_program(self):
        assert not is_setup_row_selectable(valid_program=False)

    def test_allows_any_setup_when_program_is_valid(self):
        # Historical bug: mismatched origin/rotation greyed out every
        # setup except the reference, so multi-setup single-file posting
        # was impossible without a Fusion machine A-axis.
        assert is_setup_row_selectable(valid_program=True)


class TestSingleFileTailSelection:
    def test_picks_last_setup_with_tail(self):
        setups = [
            types.SimpleNamespace(name="A", hasTail=True, hasHeader=True),
            types.SimpleNamespace(name="B", hasTail=False, hasHeader=False),
            types.SimpleNamespace(name="C", hasTail=True, hasHeader=False),
        ]
        chosen = select_single_file_tail_setup(setups)
        assert chosen.name == "C"

    def test_returns_none_when_no_tail(self):
        setups = [types.SimpleNamespace(hasTail=False), types.SimpleNamespace(hasTail=False)]
        assert select_single_file_tail_setup(setups) is None


class TestUncOutputFolder:
    def test_does_not_subscript_path_object(self):
        # Historical bug: ``folder[0:2]`` on a Path raises TypeError.
        folder = Path("/tmp/out")
        assert unc_output_folder_value(folder) is None

    def test_doubles_unc_prefix(self):
        value = unc_output_folder_value(r"\\server\share\nc")
        assert value is not None
        assert value.startswith(r"\\\\")
