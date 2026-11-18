"""Pure Sokoban rules for Operatie Bureaucratie.

This module deliberately has no dependency on pygame so that the rules can be
unit-tested and used by the level tools.

Map legend (standard Sokoban notation plus office furniture):

    #  muur (wall)                  .  archiefplek (goal)
    $  dossierdoos (box)            *  doos op archiefplek
    @  ambtenaar (player)           +  ambtenaar op archiefplek
       vloer (floor)
    b  bureau      c  computer      p  plant
    k  koffieautomaat               r  printer      a  archiefkast

Furniture behaves exactly like a wall; it only looks different.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

Pos = Tuple[int, int]

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRECTIONS = {"up": UP, "down": DOWN, "left": LEFT, "right": RIGHT}
DIR_LETTERS = {UP: "u", DOWN: "d", LEFT: "l", RIGHT: "r"}
LETTER_DIRS = {v: k for k, v in DIR_LETTERS.items()}

FURNITURE = {
    "b": "bureau",
    "c": "computer",
    "p": "plant",
    "k": "koffie",
    "r": "printer",
    "a": "kast",
}
VALID_CHARS = set("#.$*@+ -_") | set(FURNITURE)


class LevelFormatError(ValueError):
    """Raised when a level map is malformed."""


@dataclass(frozen=True)
class MoveResult:
    moved: bool
    pushed: bool = False
    box_from: Optional[Pos] = None
    box_to: Optional[Pos] = None
    box_on_goal: bool = False
    blocked_by: Optional[str] = None  # "wall", "furniture", "box"
    solved: bool = False


@dataclass
class _HistoryEntry:
    player: Pos
    box_from: Optional[Pos]
    box_to: Optional[Pos]
    facing: Pos


@dataclass
class Board:
    width: int
    height: int
    walls: Set[Pos]
    furniture: Dict[Pos, str]
    goals: Set[Pos]
    start_boxes: Set[Pos]
    start_player: Pos
    boxes: Set[Pos] = field(default_factory=set)
    player: Pos = (0, 0)
    facing: Pos = DOWN
    moves: int = 0
    pushes: int = 0
    history: List[_HistoryEntry] = field(default_factory=list)

    # ------------------------------------------------------------------ setup
    @classmethod
    def from_rows(cls, rows: Iterable[str]) -> "Board":
        rows = [r.rstrip("\n") for r in rows]
        if not rows:
            raise LevelFormatError("Level is leeg")
        width = max(len(r) for r in rows)
        height = len(rows)
        walls: Set[Pos] = set()
        furniture: Dict[Pos, str] = {}
        goals: Set[Pos] = set()
        boxes: Set[Pos] = set()
        player: Optional[Pos] = None
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch not in VALID_CHARS:
                    raise LevelFormatError(f"Onbekend teken {ch!r} op ({x},{y})")
                p = (x, y)
                if ch == "#":
                    walls.add(p)
                elif ch in FURNITURE:
                    furniture[p] = FURNITURE[ch]
                if ch in ".*+":
                    goals.add(p)
                if ch in "$*":
                    boxes.add(p)
                if ch in "@+":
                    if player is not None:
                        raise LevelFormatError("Meer dan één ambtenaar in level")
                    player = p
        if player is None:
            raise LevelFormatError("Geen ambtenaar (@) in level")
        if not boxes:
            raise LevelFormatError("Geen dossiers ($) in level")
        if len(boxes) != len(goals):
            raise LevelFormatError(
                f"Aantal dossiers ({len(boxes)}) wijkt af van archiefplekken ({len(goals)})"
            )
        board = cls(width, height, walls, furniture, goals, set(boxes), player)
        board.reset()
        return board

    def reset(self) -> None:
        self.boxes = set(self.start_boxes)
        self.player = self.start_player
        self.facing = DOWN
        self.moves = 0
        self.pushes = 0
        self.history.clear()

    # ---------------------------------------------------------------- queries
    def is_blocked(self, p: Pos) -> bool:
        """True when p is a wall, furniture or outside the map."""
        x, y = p
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return True
        return p in self.walls or p in self.furniture

    def blocker_kind(self, p: Pos) -> Optional[str]:
        if p in self.furniture:
            return "furniture"
        if self.is_blocked(p):
            return "wall"
        if p in self.boxes:
            return "box"
        return None

    @property
    def is_solved(self) -> bool:
        return self.boxes == self.goals

    @property
    def boxes_on_goals(self) -> int:
        return len(self.boxes & self.goals)

    def interior(self) -> Set[Pos]:
        """Cells reachable from the player ignoring boxes (the office floor)."""
        seen = {self.start_player}
        stack = [self.start_player]
        while stack:
            x, y = stack.pop()
            for dx, dy in (UP, DOWN, LEFT, RIGHT):
                n = (x + dx, y + dy)
                if n not in seen and not self.is_blocked(n):
                    seen.add(n)
                    stack.append(n)
        return seen

    def is_dead_box(self, p: Pos) -> bool:
        """Simple corner deadlock check: box not on a goal stuck in a corner."""
        if p in self.goals:
            return False
        x, y = p
        up = self.is_blocked((x, y - 1))
        down = self.is_blocked((x, y + 1))
        left = self.is_blocked((x - 1, y))
        right = self.is_blocked((x + 1, y))
        return (up or down) and (left or right)

    # ---------------------------------------------------------------- actions
    def move(self, direction: Pos) -> MoveResult:
        dx, dy = direction
        self.facing = direction
        px, py = self.player
        target = (px + dx, py + dy)
        if self.is_blocked(target):
            kind = "furniture" if target in self.furniture else "wall"
            return MoveResult(moved=False, blocked_by=kind)

        if target in self.boxes:
            beyond = (target[0] + dx, target[1] + dy)
            if self.is_blocked(beyond) or beyond in self.boxes:
                return MoveResult(moved=False, blocked_by="box")
            self.history.append(_HistoryEntry(self.player, target, beyond, direction))
            self.boxes.remove(target)
            self.boxes.add(beyond)
            self.player = target
            self.moves += 1
            self.pushes += 1
            return MoveResult(
                moved=True,
                pushed=True,
                box_from=target,
                box_to=beyond,
                box_on_goal=beyond in self.goals,
                solved=self.is_solved,
            )

        self.history.append(_HistoryEntry(self.player, None, None, direction))
        self.player = target
        self.moves += 1
        return MoveResult(moved=True, solved=self.is_solved)

    def undo(self) -> Optional[_HistoryEntry]:
        """Undo the last move. Returns the undone entry or None."""
        if not self.history:
            return None
        entry = self.history.pop()
        if entry.box_from is not None:
            self.boxes.remove(entry.box_to)
            self.boxes.add(entry.box_from)
            self.pushes -= 1
        self.player = entry.player
        self.facing = entry.facing
        self.moves -= 1
        return entry

    def apply_solution(self, solution: str) -> bool:
        """Play a LURD string (case-insensitive). Returns True when solved."""
        for ch in solution.lower():
            if ch not in LETTER_DIRS:
                continue
            if not self.move(LETTER_DIRS[ch]).moved:
                return False
        return self.is_solved
