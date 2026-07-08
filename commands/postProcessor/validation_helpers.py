"""
Pure helpers for dialog validation and output-path handling.
"""
from __future__ import annotations

from pathlib import Path


def are_process_inputs_valid(
    *,
    has_program: bool,
    can_process: bool,
    has_selected_setups: bool,
    selected_setups_ok: bool,
    rotate_a_axis_enabled: bool,
    machine_has_a_axis: bool,
    a_axis_rotation_required: bool,
) -> bool:
    """
    Decide whether the Process / OK button should be enabled.

    Machine configuration is optional. A-axis presence is only required
    when the user enabled Rotate A-Axis *and* selected setups need rotation.
    """
    if not (has_program and can_process and has_selected_setups and selected_setups_ok):
        return False
    if rotate_a_axis_enabled and a_axis_rotation_required and not machine_has_a_axis:
        return False
    return True


def select_single_file_tail_setup(setups):
    """
    For SINGLE_FILE output, return the last selected setup that has a tail.

    Earlier code used the first setup with a header, which can skip the
    program-end block or write the wrong one.
    """
    for setup in reversed(list(setups)):
        if getattr(setup, "hasTail", False):
            return setup
    return None


def unc_output_folder_value(folder: Path | str) -> str | None:
    """
    If ``folder`` is a UNC path, return a doubled-leading-backslash form
    suitable for Fusion parameter storage. Otherwise return None.
    """
    text = folder.as_posix() if isinstance(folder, Path) else str(folder)
    # Path.as_posix() turns \\server\share into //server/share on some platforms;
    # also accept native backslash UNC strings.
    raw = str(folder)
    if raw.startswith("\\\\") or text.startswith("//"):
        # Fusion historically needed an extra leading backslash for UNC.
        if raw.startswith("\\\\"):
            return "\\\\" + raw
        return "\\\\" + text.replace("/", "\\")
    return None
