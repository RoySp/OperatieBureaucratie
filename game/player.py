"""Animated sprite state for the ambtenaar and the boxes (presentation only)."""
from __future__ import annotations

from typing import Dict, Tuple

from .board import DOWN, LEFT, RIGHT, UP
from .settings import MOVE_TIME

FACING_NAMES = {UP: "up", DOWN: "down", LEFT: "left", RIGHT: "right"}


def _ease(t: float) -> float:
    return t * t * (3 - 2 * t)


class Tween:
    """Linear movement between two tile positions."""

    def __init__(self, pos: Tuple[int, int]):
        self.start = pos
        self.end = pos
        self.elapsed = MOVE_TIME

    def go(self, start, end):
        self.start, self.end, self.elapsed = start, end, 0.0

    def snap(self, pos):
        self.start = self.end = pos
        self.elapsed = MOVE_TIME

    def update(self, dt: float):
        self.elapsed = min(MOVE_TIME, self.elapsed + dt)

    @property
    def done(self) -> bool:
        return self.elapsed >= MOVE_TIME

    @property
    def progress(self) -> float:
        return self.elapsed / MOVE_TIME

    @property
    def pos(self) -> Tuple[float, float]:
        t = _ease(self.progress)
        return (self.start[0] + (self.end[0] - self.start[0]) * t,
                self.start[1] + (self.end[1] - self.start[1]) * t)


class PlayerSprite:
    def __init__(self, pos):
        self.tween = Tween(pos)
        self.facing = "down"
        self.steps = 0

    def move(self, start, end, direction):
        self.facing = FACING_NAMES[direction]
        self.steps += 1
        self.tween.go(start, end)

    def turn(self, direction):
        self.facing = FACING_NAMES[direction]

    def snap(self, pos, direction=DOWN):
        self.facing = FACING_NAMES[direction]
        self.tween.snap(pos)

    def update(self, dt):
        self.tween.update(dt)

    @property
    def frame(self) -> str:
        if self.tween.done:
            idx = 0
        else:
            idx = 1 if self.steps % 2 else 2
        return f"player_{self.facing}_{idx}"

    @property
    def bob(self) -> int:
        """Vertical offset in source pixels while walking."""
        if self.tween.done:
            return 0
        return -1 if 0.25 < self.tween.progress < 0.75 else 0


class BoxSprites:
    """Keeps a tween for each box so pushes animate smoothly."""

    def __init__(self, boxes):
        self.tweens: Dict[Tuple[int, int], Tween] = {b: Tween(b) for b in boxes}

    def reset(self, boxes):
        self.tweens = {b: Tween(b) for b in boxes}

    def move(self, start, end):
        tw = self.tweens.pop(start, None) or Tween(start)
        tw.go(start, end)
        self.tweens[end] = tw

    def update(self, dt):
        for tw in self.tweens.values():
            tw.update(dt)

    def items(self):
        return self.tweens.items()
