"""
Pytest configuration: install Fusion API stub and expose the add-in root
as package ``batch_post`` so relative imports (``from ...config``) resolve.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

from tests.adsk_stub import install_adsk_stub

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "batch_post"


def install_addin_package() -> None:
    if PACKAGE_NAME in sys.modules and getattr(sys.modules[PACKAGE_NAME], "__path__", None):
        return
    pkg = types.ModuleType(PACKAGE_NAME)
    pkg.__file__ = str(ROOT / "__init__.py")
    pkg.__path__ = [str(ROOT)]  # type: ignore[attr-defined]
    sys.modules[PACKAGE_NAME] = pkg


install_adsk_stub()
install_addin_package()
