"""
Per-run options captured from the dialog at Process time.

Fusion add-ins can end up with duplicated Settings module state depending on
import path; reading the checkbox once into this module keeps restore-rapids
tied to what the user actually clicked for this run.
"""
from __future__ import annotations

restore_rapid_moves: bool = False
rapid_moves_minimum_distance: float = 20.0


def sync_from_command_inputs(inputs) -> None:
    global restore_rapid_moves, rapid_moves_minimum_distance
    from .dialog.dialog_constants import PostDialogConstants
    from .settings.settings import Settings

    restore = inputs.itemById(PostDialogConstants._RESTORE_RAPID_MOVES_ID)
    if restore is not None:
        restore_rapid_moves = bool(restore.value)
        Settings(Settings.RESTORE_RAPID_MOVES, restore_rapid_moves)
    else:
        restore_rapid_moves = bool(Settings(Settings.RESTORE_RAPID_MOVES))

    min_dist = inputs.itemById(PostDialogConstants._RAPID_MOVES_MINIMUM_DISTANCE_ID)
    if min_dist is not None:
        rapid_moves_minimum_distance = float(min_dist.value)
        Settings(Settings.RAPID_MOVES_MINIMUM_DISTANCE, int(min_dist.value))
    else:
        value = Settings(Settings.RAPID_MOVES_MINIMUM_DISTANCE)
        rapid_moves_minimum_distance = float(value) if value is not None else 20.0
