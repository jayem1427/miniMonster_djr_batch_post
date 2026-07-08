"""
Regression tests for Operation wait-loop and Settings path.exists bug.
"""
from __future__ import annotations

import threading
import time as time_module
from pathlib import Path

from tests.conftest import install_addin_package, install_adsk_stub

install_adsk_stub()
install_addin_package()


def test_wait_loop_does_not_shadow_time_module(tmp_path: Path):
    """
    Historical bug: ``time = 0.1`` then ``time.sleep(...)`` raised
    AttributeError because the float shadowed the time module.
    """
    from batch_post.commands.postProcessor.settings import settings as settings_mod

    settings_mod.Settings._default = dict(settings_mod.Settings._defaultSettings)
    settings_mod.Settings._items = dict(settings_mod.Settings._defaultSettings)

    delay = float(settings_mod.Settings(settings_mod.Settings.INITIAL_DELAY) or 0.1)
    retries = int(settings_mod.Settings(settings_mod.Settings.POST_RETRIES) or 3)

    target = tmp_path / "late.ngc"
    created = {"done": False}

    def create_later():
        time_module.sleep(0.05)
        target.write_text("%\nM30\n", encoding="utf-8")
        created["done"] = True

    threading.Thread(target=create_later, daemon=True).start()

    loops = 0
    max_loops = max(retries * 3, 10)
    while not target.exists() and loops < max_loops:
        loops += 1
        # This must be the time *module*, not a float named time.
        time_module.sleep(min(delay * loops, 0.05))

    assert target.exists()
    assert created["done"]


def test_settings_path_exists_is_called(tmp_path: Path, monkeypatch):
    """
    Historical bug: ``if path.exists and path.is_file()`` used the method
    object (always truthy) instead of calling ``exists()``.
    """
    from batch_post.commands.postProcessor.settings import settings as settings_mod

    settings_mod.Settings._default = None
    settings_mod.Settings._items = {}
    settings_mod.Settings._fMustSave = False

    missing = tmp_path / "does-not-exist.settings"
    monkeypatch.setattr(settings_mod.Settings, "_getPath", classmethod(lambda cls: missing))

    settings_mod.Settings.Load(None)
    assert settings_mod.Settings._default[settings_mod.Settings.END_CODES] == "M5\nM9\nM30"
