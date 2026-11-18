"""Headless smoke test: drives every scene and saves screenshots.

    python tools/smoke_test.py [output_dir]

Uses a temporary APPDATA so the real savegame is untouched.
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["APPDATA"] = tempfile.mkdtemp()
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame  # noqa: E402

from game import menu, play  # noqa: E402
from game.board import LETTER_DIRS  # noqa: E402
from game.engine import Game  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "screenshots")
os.makedirs(OUT, exist_ok=True)
SOLUTIONS = json.load(open(os.path.join(ROOT, "tools", "solutions.json")))


def frame(g, n=1, dt=16):
    for _ in range(n):
        g.time += dt
        g.top.update(dt)
        g._draw(dt)


def shot(g, name):
    pygame.image.save(g.canvas, os.path.join(OUT, name + ".png"))


def key(g, k):
    g.top.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))
    g.top.handle_event(pygame.event.Event(pygame.KEYUP, key=k, mod=0, unicode=""))


g = Game()
g.push(menu.LoadingScene(g))
frame(g, 60)
shot(g, "01_loading")
frame(g, 120)
assert isinstance(g.top, menu.TitleScene), g.top
frame(g, 5)
shot(g, "02_title")
key(g, pygame.K_DOWN)    # 'Verder spelen' is disabled without progress
key(g, pygame.K_RETURN)  # level select
frame(g, 3)
assert isinstance(g.top, menu.LevelSelectScene)
shot(g, "03_levelselect")
key(g, pygame.K_ESCAPE)
key(g, pygame.K_DOWN)
key(g, pygame.K_RETURN)  # options
frame(g, 3)
assert isinstance(g.top, menu.OptionsScene)
shot(g, "04_options")
key(g, pygame.K_ESCAPE)
key(g, pygame.K_DOWN)
key(g, pygame.K_RETURN)  # credits
frame(g, 200)
shot(g, "05_credits")
key(g, pygame.K_ESCAPE)

# Play every level by feeding the stored solution through the real scene.
for idx, lv in enumerate(g.levels.levels):
    play.start_level(g, lv)
    if isinstance(g.top, menu.DepartmentIntroScene):
        frame(g, 40)
        if idx in (0, 8):
            shot(g, f"06_intro_{lv.id}")
        key(g, pygame.K_RETURN)
    scene = g.top
    assert isinstance(scene, play.PlayScene), g.top
    frame(g, 2)
    if lv.id in ("1-1", "2-3", "3-4", "4-1", "5-3"):
        shot(g, f"07_play_{lv.id}")
    # bump a wall / undo / restart sanity
    for ch in SOLUTIONS[lv.id]:
        scene.try_move(LETTER_DIRS[ch])
        frame(g, 1, dt=200)
    assert scene.board.is_solved, lv.id
    frame(g, 30)
    assert isinstance(g.top, play.VictoryScene), (lv.id, g.top)
    if lv.id == "1-1":
        frame(g, 60)
        shot(g, "08_victory")
    frame(g, 60)
    assert g.save.is_completed(lv.id)

# Pause menu on a level
play.start_level(g, g.levels.levels[3], show_intro=False)
scene = g.top
scene.try_move(LETTER_DIRS["l"])
frame(g, 20)
key(g, pygame.K_z)
frame(g, 20)
assert scene.board.moves == 0
scene.try_move(LETTER_DIRS["l"])
frame(g, 20)
key(g, pygame.K_r)       # restart shows the AFGEWEZEN stamp
frame(g, 8)
shot(g, "09_restart")
frame(g, 60)
assert scene.board.moves == 0 and scene.board.boxes == scene.board.start_boxes
key(g, pygame.K_ESCAPE)
frame(g, 3)
assert isinstance(g.top, play.PauseScene)
shot(g, "09_pause")
key(g, pygame.K_ESCAPE)

g.reset_to(play.EndingScene(g))
frame(g, 200)
shot(g, "10_ending")

# saved progress reloads
from game.savegame import SaveGame  # noqa: E402
s2 = SaveGame()
assert len(s2.completed) == len(g.levels.levels), s2.completed
print("SMOKE TEST OK -", len(s2.completed), "levels completed via the real game scenes")
print("Screenshots in", OUT)
