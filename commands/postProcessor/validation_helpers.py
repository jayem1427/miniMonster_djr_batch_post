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
    rotate_a_axis_enabled: bool = False,
    machine_has_a_axis: bool = False,
    a_axis_rotation_required: bool = False,
) -> bool:
    """
    Decide whether the Process / OK button should be enabled.

    Machine configuration is optional. A-axis injection is done by this
    add-in from setup WCS orientation, so a missing machine A-axis must
    not disable Process.
    """
    # Kept in the signature because the dialog still reports these.
    _ = (rotate_a_axis_enabled, machine_has_a_axis, a_axis_rotation_required)
    return bool(has_program and can_process and has_selected_setups and selected_setups_ok)


def should_warn_machine_lacks_a_axis(
    *,
    has_machine: bool,
    machine_has_a_axis: bool,
    a_axis_rotation_required: bool,
) -> bool:
    """
    Warn only when an attached Fusion machine cannot rotate A.

    No machine is fine: indexed A moves are written by this add-in, not
    by Fusion kinematics. Skip the Process-time scare dialog in that case.
    """
    return bool(has_machine and not machine_has_a_axis and a_axis_rotation_required)


def is_setup_row_selectable(*, valid_program: bool) -> bool:
    """
    Any non-error setup can be included in a multi-setup / single-file post.

    WCS origin, X-axis alignment, and A-axis rotation are shown in the
    table and warned at Process time. They must not grey out checkboxes:
    that made it impossible to select more than the reference setup
    unless a Fusion machine reported an A-axis *and* origins matched
    exactly.
    """
    return bool(valid_program)


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
