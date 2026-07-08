"""
Lightweight Fusion API stub so unit tests can import add-in modules
outside Autodesk Fusion.
"""
from __future__ import annotations

import sys
import types
from typing import Any


def _make_enum(name: str, **members: Any) -> type:
    return type(name, (), members)


def install_adsk_stub() -> None:
    if "adsk" in sys.modules and hasattr(sys.modules["adsk"], "_batch_post_stub"):
        # Ensure newer stub attributes exist even if an older stub was cached.
        core = sys.modules.get("adsk.core")
        if core is not None and not hasattr(core, "Event"):
            core.Event = object
            core.EventHandler = object
        return

    adsk = types.ModuleType("adsk")
    adsk._batch_post_stub = True  # type: ignore[attr-defined]

    core = types.ModuleType("adsk.core")
    cam = types.ModuleType("adsk.cam")

    class Application:
        @staticmethod
        def get():
            return Application()

        @property
        def userInterface(self):
            return types.SimpleNamespace(
                messageBox=lambda *a, **k: None,
            )

        def log(self, *args, **kwargs):
            return None

    core.Application = Application
    core.LogLevels = _make_enum(
        "LogLevels",
        InfoLogLevel=0,
        WarningLogLevel=1,
        ErrorLogLevel=2,
    )
    core.LogTypes = _make_enum(
        "LogTypes",
        FileLogType=0,
        ConsoleLogType=1,
    )
    core.MessageBoxButtonTypes = _make_enum(
        "MessageBoxButtonTypes",
        OKButtonType=0,
        OKCancelButtonType=1,
    )
    core.MessageBoxIconTypes = _make_enum(
        "MessageBoxIconTypes",
        InformationIconType=0,
        WarningIconType=1,
        CriticalIconType=2,
    )
    core.DialogResults = _make_enum(
        "DialogResults",
        DialogOK=0,
        DialogCancel=1,
    )
    core.DropDownStyles = _make_enum(
        "DropDownStyles",
        TextListDropDownStyle=0,
    )
    for name in (
        "ValidateInputsEventArgs",
        "CommandEventArgs",
        "CommandInputs",
        "CommandInput",
        "BoolValueCommandInput",
        "DropDownCommandInput",
        "TextBoxCommandInput",
        "Attributes",
        "Point3D",
        "Vector3D",
        "Event",
        "EventHandler",
        "ApplicationCommandEventArgs",
        "InputChangedEventArgs",
        "SelectionEventArgs",
        "CommandCreatedEventArgs",
        "CommandDefinition",
        "CommandDefinitions",
        "Workspace",
        "ToolbarPanel",
        "ToolbarControls",
        "ObjectCollection",
        "ValueInput",
        "StringValueCommandInput",
        "IntegerSpinnerCommandInput",
        "FloatSpinnerCommandInput",
        "TableCommandInput",
        "GroupCommandInput",
        "TabCommandInput",
        "BrowserCommandInput",
        "ButtonDefinition",
        "ListItems",
        "ListItem",
    ):
        setattr(core, name, object)

    cam.CAM = object
    cam.NCProgram = object
    cam.NCProgramPostProcessOptions = types.SimpleNamespace(create=staticmethod(lambda: object()))
    cam.Setup = object
    cam.Setups = object
    cam.Operation = object
    cam.Tool = object

    adsk.core = core
    adsk.cam = cam

    sys.modules["adsk"] = adsk
    sys.modules["adsk.core"] = core
    sys.modules["adsk.cam"] = cam
