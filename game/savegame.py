"""Progress and settings, stored as JSON in the user's AppData folder."""
from __future__ import annotations

import json
import os
import tempfile
from typing import Dict, Optional

from .resources import user_data_dir

SAVE_VERSION = 1

DEFAULT_SETTINGS = {
    "sound": True,
    "sfx_volume": 0.7,
    "music": True,
    "music_volume": 0.45,
    "fullscreen": False,
}


class SaveGame:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(user_data_dir(), "savegame.json")
        self.completed: Dict[str, dict] = {}
        self.last_level: Optional[str] = None
        self.settings = dict(DEFAULT_SETTINGS)
        self.load_error: Optional[str] = None
        self.load()

    # ----------------------------------------------------------- persistence
    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("savegame is geen object")
            completed = data.get("completed", {})
            if isinstance(completed, dict):
                self.completed = {
                    str(k): v for k, v in completed.items() if isinstance(v, dict)
                }
            last = data.get("last_level")
            self.last_level = str(last) if last else None
            settings = data.get("settings", {})
            if isinstance(settings, dict):
                for key, default in DEFAULT_SETTINGS.items():
                    value = settings.get(key, default)
                    if isinstance(default, bool):
                        self.settings[key] = bool(value)
                    elif isinstance(default, float):
                        try:
                            self.settings[key] = min(1.0, max(0.0, float(value)))
                        except (TypeError, ValueError):
                            pass
        except (OSError, ValueError) as exc:
            # Corrupt save: keep a backup and continue with a fresh one.
            self.load_error = str(exc)
            try:
                os.replace(self.path, self.path + ".beschadigd")
            except OSError:
                pass

    def save(self) -> bool:
        data = {
            "version": SAVE_VERSION,
            "completed": self.completed,
            "last_level": self.last_level,
            "settings": self.settings,
        }
        try:
            folder = os.path.dirname(self.path)
            os.makedirs(folder, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False

    # ---------------------------------------------------------------- queries
    def is_completed(self, level_id: str) -> bool:
        return level_id in self.completed

    def best(self, level_id: str) -> Optional[dict]:
        return self.completed.get(level_id)

    def record(self, level_id: str, moves: int, pushes: int) -> bool:
        """Store a result. Returns True when it is a new best."""
        prev = self.completed.get(level_id)
        new_best = prev is None or (moves, pushes) < (
            prev.get("moves", 10**9), prev.get("pushes", 10**9))
        if new_best:
            self.completed[level_id] = {"moves": moves, "pushes": pushes}
        self.save()
        return new_best

    def reset_progress(self) -> None:
        self.completed = {}
        self.last_level = None
        self.save()
