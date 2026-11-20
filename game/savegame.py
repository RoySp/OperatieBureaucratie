"""Progress and settings, stored as JSON in the user's AppData folder."""
from __future__ import annotations

import json
import os
import tempfile
from typing import Dict, Optional

from .resources import user_data_dir

# 1: original release and the short-lived 16-levels-per-department build
# 2: levels 6-1 and up regrouped into departments of 4 (see LevelPack.legacy_map)
SAVE_VERSION = 2

DEFAULT_SETTINGS = {
    "sound": True,
    "sfx_volume": 0.7,
    "music": True,
    "music_volume": 0.45,
    "fullscreen": False,
    "discord": True,
}


class SaveGame:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(user_data_dir(), "savegame.json")
        self.completed: Dict[str, dict] = {}
        self.last_level: Optional[str] = None
        self.unlock_all = False  # secret code: every level open (progress untouched)
        self.settings = dict(DEFAULT_SETTINGS)
        self.load_error: Optional[str] = None
        self.loaded_version: Optional[int] = None  # None: no save file yet
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
            try:
                self.loaded_version = int(data.get("version", 1))
            except (TypeError, ValueError):
                self.loaded_version = 1
            completed = data.get("completed", {})
            if isinstance(completed, dict):
                self.completed = {
                    str(k): v for k, v in completed.items() if isinstance(v, dict)
                }
            last = data.get("last_level")
            self.last_level = str(last) if last else None
            self.unlock_all = data.get("unlock_all") is True
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
            "unlock_all": self.unlock_all,
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

    def upgrade(self, legacy_map: Dict[str, str]) -> bool:
        """Rename level ids of a version-1 save to the current ids.

        Only version-1 saves can contain old ids; newer saves already use the
        current ones (an old "7-1" and a new "7-1" are different levels).
        Returns True when something changed.
        """
        if self.loaded_version is None or self.loaded_version >= SAVE_VERSION:
            return False
        renamed = {}
        for old_id, result in self.completed.items():
            new_id = legacy_map.get(old_id, old_id)
            prev = renamed.get(new_id)
            if prev is None or (result.get("moves", 10**9), result.get("pushes", 10**9)) < (
                    prev.get("moves", 10**9), prev.get("pushes", 10**9)):
                renamed[new_id] = result
        changed = renamed != self.completed
        self.completed = renamed
        if self.last_level in legacy_map:
            self.last_level = legacy_map[self.last_level]
            changed = True
        self.loaded_version = SAVE_VERSION
        self.save()
        return changed

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

    def toggle_unlock_all(self) -> bool:
        """Switch the secret 'all levels open' mode. Completed levels are never
        touched, so switching it off again restores the normal locks."""
        self.unlock_all = not self.unlock_all
        self.save()
        return self.unlock_all

    def reset_progress(self) -> None:
        self.completed = {}
        self.last_level = None
        self.unlock_all = False
        self.save()
