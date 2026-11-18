"""Locating bundled resources and the per-user data folder.

When the game runs from a PyInstaller --onefile EXE, bundled files are
unpacked to a temporary folder exposed as ``sys._MEIPASS``.
"""
from __future__ import annotations

import os
import sys

APP_NAME = "OperatieBureaucratie"


def base_path() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts: str) -> str:
    return os.path.join(base_path(), *parts)


def user_data_dir() -> str:
    """%APPDATA%\\OperatieBureaucratie on Windows, ~/.operatiebureaucratie elsewhere."""
    root = os.environ.get("APPDATA")
    if root:
        path = os.path.join(root, APP_NAME)
    else:
        path = os.path.join(os.path.expanduser("~"), "." + APP_NAME.lower())
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path
