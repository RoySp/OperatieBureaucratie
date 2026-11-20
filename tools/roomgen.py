"""Random office floor plans for the procedural levels (development tool).

A room is assembled from 3x3 blocks (random templates, rotated/mirrored),
cleaned up (one connected floor, no dead-end squares, no large open halls),
then archive spots are placed. ``candidate`` runs the reverse search on such a
room and returns the hardest solvable start position found.
"""
from __future__ import annotations

import os
import random
import sys
from collections import deque
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.board import Board  # noqa: E402
from tools.solver import board_to_rows, hardest_start  # noqa: E402

# 3x3 blocks: '#' wall, ' ' floor. Each is used with random rotation/mirror.
BLOCKS = [
    ["   ", "   ", "   "],
    ["#  ", "   ", "   "],
    ["## ", "   ", "   "],
    ["###", "   ", "   "],
    ["#  ", "#  ", "   "],
    ["#  ", "#  ", "#  "],
    ["   ", " # ", "   "],
    ["## ", "#  ", "   "],
    ["#  ", "   ", "  #"],
    [" # ", "   ", " # "],
    ["#  ", "#  ", "## "],
    ["# #", "   ", "   "],
    [" # ", " # ", "   "],
    ["## ", "## ", "   "],
    ["   ", " # ", " # "],
]

FURNITURE = "bcpkra"


def _variants(block):
    out = []
    g = [list(r) for r in block]
    for _ in range(4):
        g = [list(r) for r in zip(*g[::-1])]
        out.append(["".join(r) for r in g])
        out.append(["".join(r[::-1]) for r in g])
    return out


VARIANTS = [v for b in BLOCKS for v in _variants(b)]
# tight rooms favour blocks with more wall in them
TIGHT_WEIGHTS = [1 + sum(r.count("#") for r in v) for v in VARIANTS]


def make_room(rng: random.Random, bw: int, bh: int, max_open: int = 3,
              tight: bool = False) -> Optional[List[List[str]]]:
    """bw x bh blocks of 3x3 -> grid with walls around. None if unusable."""
    W, H = bw * 3 + 2, bh * 3 + 2
    g = [["#"] * W for _ in range(H)]
    for by in range(bh):
        for bx in range(bw):
            blk = rng.choices(VARIANTS, TIGHT_WEIGHTS)[0] if tight else rng.choice(VARIANTS)
            for y in range(3):
                for x in range(3):
                    g[1 + by * 3 + y][1 + bx * 3 + x] = blk[y][x]
    floor = [(x, y) for y in range(H) for x in range(W) if g[y][x] == " "]
    if not floor:
        return None
    # remove dead ends (floor squares with 3+ walls around) repeatedly
    changed = True
    while changed:
        changed = False
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                if g[y][x] == " ":
                    walls = sum(g[y + dy][x + dx] == "#" for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                    if walls >= 3:
                        g[y][x] = "#"
                        changed = True
    floor = [(x, y) for y in range(H) for x in range(W) if g[y][x] == " "]
    if not floor:
        return None
    # keep the largest connected area
    seen = set()
    best = []
    for start in floor:
        if start in seen:
            continue
        comp = []
        q = deque([start])
        seen.add(start)
        while q:
            x, y = q.popleft()
            comp.append((x, y))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if n not in seen and g[n[1]][n[0]] == " ":
                    seen.add(n)
                    q.append(n)
        if len(comp) > len(best):
            best = comp
    keep = set(best)
    for (x, y) in floor:
        if (x, y) not in keep:
            g[y][x] = "#"
    # reject big open halls (they make levels easy and searches explode)
    for y in range(1, H - max_open):
        for x in range(1, W - max_open):
            if all(g[y + j][x + i] == " " for j in range(max_open + 1) for i in range(max_open + 1)):
                return None
    if len(keep) < (bw * bh * 9) * 0.45:
        return None
    return g


def place_goals(rng: random.Random, g, k: int, clustered: bool):
    floor = [(x, y) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] == " "]
    if len(floor) < k * 4:
        return None
    if not clustered:
        return rng.sample(floor, k)
    start = rng.choice(floor)
    chosen = [start]
    frontier = [start]
    fs = set(floor)
    while len(chosen) < k and frontier:
        x, y = rng.choice(frontier)
        opts = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if (x + dx, y + dy) in fs and (x + dx, y + dy) not in chosen]
        if not opts:
            frontier.remove((x, y))
            continue
        n = rng.choice(opts)
        chosen.append(n)
        frontier.append(n)
    return chosen if len(chosen) == k else None


def decorate(rows: List[str], used, rng: random.Random, chance: float = 0.25) -> List[str]:
    """Turn floor squares the solution never touches, next to a wall, into furniture."""
    g = [list(r) for r in rows]
    for y in range(len(g)):
        for x in range(len(g[y])):
            if g[y][x] != " " or (x, y) in used:
                continue
            near_wall = any(0 <= y + dy < len(g) and 0 <= x + dx < len(g[y + dy]) and g[y + dy][x + dx] == "#"
                            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if near_wall and rng.random() < chance:
                g[y][x] = rng.choice(FURNITURE)
    return ["".join(r).rstrip() for r in g]


def seal(rows: List[str]) -> List[str]:
    """Turn floor the player can never reach (cut off by furniture) into wall."""
    g = [list(r) for r in rows]
    start = next((x, y) for y, r in enumerate(g) for x, ch in enumerate(r) if ch in "@+")
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) not in seen and 0 <= ny < len(g) and 0 <= nx < len(g[ny]) \
                    and g[ny][nx] in " .$*@+":
                seen.add((nx, ny))
                stack.append((nx, ny))
    for y, r in enumerate(g):
        for x, ch in enumerate(r):
            if ch == " " and (x, y) not in seen:
                g[y][x] = "#"
    return ["".join(r).rstrip() for r in g]


def solution_footprint(rows: List[str], solution: str):
    """All squares the player or a box occupies while playing the solution."""
    from game.board import LETTER_DIRS
    b = Board.from_rows(rows)
    used = {b.player} | set(b.boxes)
    for ch in solution:
        b.move(LETTER_DIRS[ch])
        used.add(b.player)
        used |= b.boxes
    return used, b.is_solved


def candidate(args):
    """(seed, bw, bh, k, max_states) -> dict or None. Runs in a worker process."""
    seed, bw, bh, k, max_states, tight = args
    rng = random.Random(seed)
    for _ in range(200):
        g = make_room(rng, bw, bh, max_open=2 if tight else 3, tight=tight)
        if g is None:
            continue
        goals = place_goals(rng, g, k, clustered=rng.random() < 0.6)
        if goals is None:
            continue
        floor = [(x, y) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] == " " and (x, y) not in goals]
        player = rng.choice(floor)
        rows = []
        for y, r in enumerate(g):
            line = []
            for x, ch in enumerate(r):
                if (x, y) in goals:
                    line.append("*")
                elif (x, y) == player:
                    line.append("@")
                else:
                    line.append(ch)
            rows.append("".join(line))
        board = Board.from_rows(rows)
        res = hardest_start(board, player, max_states=max_states)
        if res is None:
            continue
        start_rows = board_to_rows(board, res["boxes"], res["player"])
        on_goal = sum(1 for b in res["boxes"] if tuple(b) in board.goals)
        used, ok = solution_footprint(start_rows, res["solution"])
        if not ok:
            continue
        final = decorate(start_rows, used, rng)
        check = Board.from_rows(final)
        if not check.apply_solution(res["solution"]):
            continue
        return {
            "seed": seed, "rows": final, "solution": res["solution"], "depth": res["depth"],
            "boxes": k, "on_goal": on_goal, "states": res["states"],
            "size": (max(len(r) for r in final), len(final)), "complete": res["states"] < max_states,
        }
    return None
