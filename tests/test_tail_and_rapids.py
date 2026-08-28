from pathlib import Path

from commands.postProcessor.gcode_helpers import (
    find_posted_output,
    force_rapid_start_line,
    is_tail_gap_line,
    line_matches_end_codes,
    normalize_nc_extension,
    snapshot_files,
    strip_feed_words,
    update_trailing_end_sequence,
    wait_for_post_output,
)
from commands.postProcessor.operations.operation.rapidsParser import RapidsParser

REPO = Path(__file__).resolve().parents[1]
SAMPLE_NGC = REPO / "1001.ngc"
SETUP1_NGC = REPO / "Setup1.ngc"
END_CODES = "M5\nM9\nM30"


def _trailing_tail(lines: list[str], *, start_index: int = 0) -> int:
    tail = -1
    for i in range(start_index, len(lines)):
        line = lines[i]
        is_end = line_matches_end_codes(line, END_CODES)
        is_significant = (not is_end) and (not is_tail_gap_line(line))
        tail = update_trailing_end_sequence(
            tail,
            is_end_code=is_end,
            is_significant=is_significant,
            line_number=i,
        )
    return tail


def test_opening_m9_is_not_treated_as_tail():
    tail = -1
    tail = update_trailing_end_sequence(tail, is_end_code=True, is_significant=False, line_number=15)
    assert tail == 15
    tail = update_trailing_end_sequence(tail, is_end_code=False, is_significant=True, line_number=16)
    assert tail == -1
    tail = update_trailing_end_sequence(tail, is_end_code=False, is_significant=True, line_number=100)
    tail = update_trailing_end_sequence(tail, is_end_code=True, is_significant=False, line_number=228)
    assert tail == 228


def test_trailing_m5_m9_m30_keeps_first_of_run():
    tail = -1
    tail = update_trailing_end_sequence(tail, is_end_code=False, is_significant=True, line_number=200)
    tail = update_trailing_end_sequence(tail, is_end_code=True, is_significant=False, line_number=201)
    tail = update_trailing_end_sequence(tail, is_end_code=False, is_significant=False, line_number=202)
    tail = update_trailing_end_sequence(tail, is_end_code=True, is_significant=False, line_number=203)
    tail = update_trailing_end_sequence(tail, is_end_code=True, is_significant=False, line_number=204)
    assert tail == 201


def test_line_matches_end_codes_ignores_toolchange_m600():
    assert line_matches_end_codes("N25 M9\n", END_CODES)
    assert line_matches_end_codes("N1090 M30\n", END_CODES)
    assert not line_matches_end_codes("N30 T15 M600\n", END_CODES)
    assert not line_matches_end_codes("N35 S15000 M3\n", END_CODES)


def test_linuxcnc_sample_tail_is_m30_not_opening_m9():
    lines = SAMPLE_NGC.read_text(encoding="utf-8").splitlines(True)
    body_start = next(i for i, line in enumerate(lines) if "G53" in line and "G0" in line)
    m9 = next(i for i, line in enumerate(lines) if line_matches_end_codes(line, "M9"))
    m30 = next(i for i, line in enumerate(lines) if line_matches_end_codes(line, "M30"))
    assert m9 > body_start
    assert _trailing_tail(lines, start_index=body_start) == m30
    assert m9 != m30


def test_sample_retracts_are_inside_body_window():
    lines = SAMPLE_NGC.read_text(encoding="utf-8").splitlines(True)
    body_start = next(i for i, line in enumerate(lines) if "G53" in line and "G0" in line)
    tail = _trailing_tail(lines, start_index=body_start)
    segs = RapidsParser.analyze(RapidsParser.parseFile(SAMPLE_NGC), minDist=20)
    valid = [s for s in segs if s.get("isValid")]
    assert len(valid) == 4
    for seg in valid:
        start_row = seg["startLine"] - 1
        assert body_start <= start_row < tail


def test_force_rapid_start_handles_indented_modal_z():
    assert force_rapid_start_line(" Z5.\n") == "G0 Z5. (Rapid movement start)\n"
    assert force_rapid_start_line("N65 G1 Z5. F1200.\n") == "N65 G0 Z5. (Rapid movement start)\n"
    assert force_rapid_start_line("G1 Z5. (retract)\n") == "G0 Z5. (Rapid movement start)\n"
    assert "F" not in force_rapid_start_line("G1 Z5. F2286.\n")


def test_strip_feed_words():
    assert strip_feed_words("X10 Y20 F1200.\n").strip() == "X10 Y20"


def test_setup1_has_valid_rapid_candidates():
    segs = RapidsParser.analyze(RapidsParser.parseFile(SETUP1_NGC), minDist=20)
    valid = [s for s in segs if s.get("isValid")]
    assert len(valid) == 4


def test_feed_on_xy_middle_is_still_valid(tmp_path: Path):
    sample = tmp_path / "feed_middle.ngc"
    sample.write_text(
        "%\n"
        "G90 G94\n"
        "G1 Z0. F100.\n"
        "G1 Z5. F1200.\n"
        "X10 Y10 F1200.\n"
        "Z2. F1200.\n"
        "G1 X0 Y0 F100.\n"
        "M30\n"
        "%\n",
        encoding="utf-8",
    )
    segs = RapidsParser.analyze(RapidsParser.parseFile(sample), minDist=5)
    valid = [s for s in segs if s.get("isValid")]
    assert len(valid) >= 1


def test_wait_for_post_output_stable(tmp_path: Path):
    path = tmp_path / "out.ngc"
    path.write_text("%\n" + ("G1 X0\n" * 20) + "M30\n%\n", encoding="utf-8")
    assert wait_for_post_output(path, delay=0.01, max_loops=5, stable_reads=2, min_bytes=16)


def test_wait_for_post_output_accepts_millenniumos_end(tmp_path: Path):
    """
    Historical bug: wait required an M30 substring. MillenniumOS ends with
    M5.9 / M0, so Adaptive3 was posted then reported as 'file was not created'.
    """
    path = tmp_path / "adaptive3.gcode"
    body = (
        "(Begin Operation: Adaptive3)\n"
        "G0 X0 Y0\n"
        "G0 Z15\n"
        "G1 F400 Z-0.75\n"
        "G1 X10 Y0\n"
        "(Park)\n"
        "G27\n"
        "(Double-check spindle is stopped!)\n"
        "M5.9\n"
    )
    path.write_text(body, encoding="utf-8")
    assert wait_for_post_output(path, delay=0.01, max_loops=5, stable_reads=2, min_bytes=16)


def test_wait_for_post_output_accepts_m0_without_m30(tmp_path: Path):
    path = tmp_path / "job.nc"
    path.write_text("(End Job)\n" + ("G1 X1\n" * 10) + "M0\n", encoding="utf-8")
    assert wait_for_post_output(path, delay=0.01, max_loops=5, stable_reads=2, min_bytes=16)


def test_normalize_nc_extension_adds_dot():
    assert normalize_nc_extension("gcode") == ".gcode"
    assert normalize_nc_extension(".nc") == ".nc"
    assert normalize_nc_extension(None) == ".nc"
    assert normalize_nc_extension("") == ".nc"


def test_find_posted_output_uses_actual_extension(tmp_path: Path):
    expected = tmp_path / "abc123.nc"
    actual = tmp_path / "abc123.gcode"
    actual.write_text("G0 X0\nM0\n", encoding="utf-8")
    found = find_posted_output(expected, before=set())
    assert found == actual


def test_find_posted_output_picks_new_file(tmp_path: Path):
    before = snapshot_files(tmp_path)
    expected = tmp_path / "missing.nc"
    written = tmp_path / "NCProgram2.gcode"
    written.write_text("G0 X0\nM5.9\n", encoding="utf-8")
    found = find_posted_output(expected, before=before)
    assert found == written
