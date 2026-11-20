"""Loading the level collection from levels/levels.json."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

from .board import Board, LevelFormatError
from .resources import resource_path


@dataclass
class Level:
    id: str
    name: str
    note: str
    rows: List[str]
    department: "Department"
    index: int  # global index 0..n-1
    legacy_id: Optional[str] = None  # id in the 16-levels-per-department build

    def make_board(self) -> Board:
        return Board.from_rows(self.rows)

    @property
    def title(self) -> str:
        return f"Dossier {self.id}: {self.name}"


@dataclass
class Department:
    id: int
    name: str
    motto: str
    levels: List[Level]


class LevelPack:
    def __init__(self, path: Optional[str] = None):
        self.path = path or resource_path("levels", "levels.json")
        self.departments: List[Department] = []
        self.levels: List[Level] = []
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            raise LevelFormatError(f"Kan levelbestand niet lezen: {exc}") from exc
        for d in data.get("departments", []):
            dept = Department(int(d["id"]), d["name"], d.get("motto", ""), [])
            for lv in d.get("levels", []):
                level = Level(str(lv["id"]), lv["name"], lv.get("note", ""),
                              list(lv["map"]), dept, len(self.levels), lv.get("legacy_id"))
                level.make_board()  # validate early
                dept.levels.append(level)
                self.levels.append(level)
            self.departments.append(dept)
        if not self.levels:
            raise LevelFormatError("Geen levels gevonden")

    def legacy_map(self) -> dict:
        """Old level id -> current level id, for upgrading older save games."""
        return {lv.legacy_id: lv.id for lv in self.levels if lv.legacy_id}

    def by_id(self, level_id: Optional[str]) -> Optional[Level]:
        for lv in self.levels:
            if lv.id == level_id:
                return lv
        return None

    def next_level(self, level: Level) -> Optional[Level]:
        if level.index + 1 < len(self.levels):
            return self.levels[level.index + 1]
        return None

    def is_unlocked(self, level: Level, save) -> bool:
        """A level is open when it is completed, when the secret 'unlock all'
        mode is on, or when every level before it has been completed."""
        if save.is_completed(level.id) or getattr(save, "unlock_all", False):
            return True
        return all(save.is_completed(lv.id) for lv in self.levels[:level.index])

    def continue_level(self, save) -> Level:
        """First unfinished unlocked level, or the last one played."""
        for lv in self.levels:
            if not save.is_completed(lv.id) and self.is_unlocked(lv, save):
                return lv
        last = self.by_id(save.last_level)
        return last or self.levels[-1]
