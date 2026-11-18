"""Sokoban solver and reverse-search level generator (development tool).

Forward solver: breadth-first search over push states (optimal in pushes),
returns a full LURD move string that can be replayed on game.board.Board.

Reverse generator: starting from the solved position it "pulls" boxes away
from the goals with a BFS. The deepest state found is the hardest starting
position for that room layout (measured in pushes) and is guaranteed solvable.
"""
from __future__ import annotations

import os
import sys
from collections import deque
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.board import Board  # noqa: E402

DIRS = [(0, -1, "u"), (0, 1, "d"), (-1, 0, "l"), (1, 0, "r")]


class Grid:
    """Integer-indexed view of a board for fast searching."""

    def __init__(self, board: Board):
        self.w = board.width
        self.h = board.height
        self.floor = sorted(board.interior())
        self.index = {p: i for i, p in enumerate(self.floor)}
        self.pos = self.floor
        n = len(self.floor)
        # neighbour[i][d] = index or -1
        self.nb: List[List[int]] = []
        for (x, y) in self.floor:
            row = []
            for dx, dy, _ in DIRS:
                row.append(self.index.get((x + dx, y + dy), -1))
            self.nb.append(row)
        self.goals = frozenset(self.index[g] for g in board.goals)
        self.n = n
        self.dead = self._dead_squares()

    def _dead_squares(self) -> List[bool]:
        """Squares from which a box can never reach any goal (pull analysis)."""
        alive = [False] * self.n
        q = deque(self.goals)
        for g in self.goals:
            alive[g] = True
        while q:
            c = q.popleft()
            for d in range(4):
                b = self.nb[c][d]            # box moves c -> b via pull
                if b < 0:
                    continue
                p2 = self.nb[b][d]          # player must stand beyond
                if p2 < 0:
                    continue
                if not alive[b]:
                    alive[b] = True
                    q.append(b)
        return [not a for a in alive]

    def reach(self, start: int, boxes) -> List[bool]:
        seen = [False] * self.n
        seen[start] = True
        stack = [start]
        nb = self.nb
        while stack:
            c = stack.pop()
            for n in nb[c]:
                if n >= 0 and not seen[n] and n not in boxes:
                    seen[n] = True
                    stack.append(n)
        return seen

    def norm(self, start: int, boxes) -> int:
        seen = self.reach(start, boxes)
        return seen.index(True)

    def path(self, start: int, goal: int, boxes) -> Optional[str]:
        if start == goal:
            return ""
        prev = {start: None}
        q = deque([start])
        while q:
            c = q.popleft()
            for d, (_, _, ch) in enumerate(DIRS):
                n = self.nb[c][d]
                if n < 0 or n in prev or n in boxes:
                    continue
                prev[n] = (c, ch)
                if n == goal:
                    out = []
                    while prev[n] is not None:
                        n, ch2 = prev[n]
                        out.append(ch2)
                    return "".join(reversed(out))
                q.append(n)
        return None


def solve(board: Board, max_states: int = 3_000_000) -> Optional[str]:
    """Return an optimal-push LURD solution, or None if unsolvable/too big."""
    g = Grid(board)
    boxes0 = frozenset(g.index[b] for b in board.boxes)
    p0 = g.index[board.player]
    start = (boxes0, g.norm(p0, boxes0))
    parent: Dict[tuple, Optional[tuple]] = {start: None}
    q = deque([start])
    found = None
    if boxes0 == g.goals:
        return ""
    while q and found is None:
        state = q.popleft()
        boxes, pn = state
        seen = g.reach(pn, boxes)
        for b in boxes:
            for d in range(4):
                stand = g.nb[b][d ^ 1]  # opposite side (u<->d, l<->r)
                dest = g.nb[b][d]
                if stand < 0 or dest < 0 or not seen[stand]:
                    continue
                if dest in boxes or g.dead[dest]:
                    continue
                nboxes = (boxes - {b}) | {dest}
                ns = (nboxes, g.norm(b, nboxes))
                if ns in parent:
                    continue
                parent[ns] = (state, stand, d, b)
                if nboxes == g.goals:
                    found = ns
                    break
                q.append(ns)
                if len(parent) > max_states:
                    return None
            if found:
                break
    if found is None:
        return None
    # Reconstruct push sequence
    pushes = []
    s = found
    while parent[s] is not None:
        prev, stand, d, b = parent[s]
        pushes.append((prev[0], stand, d, b))
        s = prev
    pushes.reverse()
    moves = []
    player = p0
    for boxes, stand, d, b in pushes:
        walk = g.path(player, stand, boxes)
        assert walk is not None
        moves.append(walk)
        moves.append(DIRS[d][2])
        player = b
    return "".join(moves)


def hardest_start(board: Board, preferred_player, max_states: int = 400_000,
                  max_depth: int = 10_000):
    """Reverse BFS from the solved position.

    Returns dict(depth, boxes, player, solution, states) for the deepest state
    (at most max_depth pushes), preferring states with fewer boxes on goals.
    The solution is a LURD string from that start to the solved position.
    """
    g = Grid(board)
    goals = g.goals
    starts = []
    regions_done = set()
    for c in range(g.n):
        if c in goals:
            continue
        key = g.norm(c, goals)
        if key not in regions_done:
            regions_done.add(key)
            starts.append((goals, key))
    # parent[state] = (depth, parent_state, box_before_pull, box_after_pull, player_after)
    info = {s: (0, None, None, None, None) for s in starts}
    q = deque(starts)
    best = None
    best_key = None
    while q:
        state = q.popleft()
        boxes, pn = state
        dcur = info[state][0]
        on_goal = len(boxes & goals)
        key = (dcur, -on_goal)
        if dcur > 0 and (best_key is None or key > best_key):
            best_key, best = key, state
        if dcur >= max_depth:
            continue
        seen = g.reach(pn, boxes)
        for b in boxes:
            for d in range(4):
                p = g.nb[b][d]          # player stands next to box
                if p < 0 or not seen[p]:
                    continue
                p2 = g.nb[p][d]         # player steps back
                if p2 < 0 or p2 in boxes:
                    continue
                nboxes = (boxes - {b}) | {p}
                ns = (nboxes, g.norm(p2, nboxes))
                if ns in info:
                    continue
                info[ns] = (dcur + 1, state, b, p, p2)
                if len(info) < max_states:
                    q.append(ns)
    if best is None:
        return None
    boxes, pn = best
    seen = g.reach(pn, boxes)
    pref = g.index.get(preferred_player, -1)
    if pref >= 0 and seen[pref] and pref not in boxes:
        player = pref
    else:
        # nearest reachable square to the preferred position
        px, py = preferred_player
        cands = [i for i in range(g.n) if seen[i] and i not in boxes]
        player = min(cands, key=lambda i: abs(g.pos[i][0] - px) + abs(g.pos[i][1] - py))
    # Build forward solution by undoing pulls.
    moves = []
    cur = best
    cur_player = player
    while info[cur][1] is not None:
        _, parent, box_before, box_after, player_after = info[cur]
        # Forward push: player at player_after pushes box at box_after -> box_before
        walk = g.path(cur_player, player_after, cur[0])
        assert walk is not None, "walk failed"
        moves.append(walk)
        bx, by = g.pos[box_before]
        ax, ay = g.pos[box_after]
        dx, dy = bx - ax, by - ay
        moves.append({(0, -1): "u", (0, 1): "d", (-1, 0): "l", (1, 0): "r"}[(dx, dy)])
        cur_player = box_after
        cur = parent
    return {
        "depth": best_key[0],
        "boxes": [g.pos[b] for b in boxes],
        "player": g.pos[player],
        "solution": "".join(moves),
        "states": len(info),
    }


def board_to_rows(board: Board, boxes, player) -> List[str]:
    rows = []
    rev = {v: k for k, v in {
        "b": "bureau", "c": "computer", "p": "plant",
        "k": "koffie", "r": "printer", "a": "kast"}.items()}
    boxes = set(boxes)
    for y in range(board.height):
        row = []
        for x in range(board.width):
            p = (x, y)
            if p in board.walls:
                ch = "#"
            elif p in board.furniture:
                ch = rev[board.furniture[p]]
            elif p in boxes:
                ch = "*" if p in board.goals else "$"
            elif p == player:
                ch = "+" if p in board.goals else "@"
            elif p in board.goals:
                ch = "."
            else:
                ch = " "
            row.append(ch)
        rows.append("".join(row).rstrip())
    return rows
