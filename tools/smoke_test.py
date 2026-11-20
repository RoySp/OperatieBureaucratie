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
# Secret code opens every level and a second time locks them again
ls = g.top
start = ls.index
code = menu.SECRET_CODE
for k in code:
    key(g, k)
    frame(g, 2)
assert g.save.unlock_all and ls.index == start
assert all(g.levels.is_unlocked(lv, g.save) for lv in g.levels.levels)
frame(g, 40)
shot(g, "03_levelselect_unlocked")
for k in code[:5] + (pygame.K_UP,) + code:   # a wrong key in between restarts the code
    key(g, k)
frame(g, 2)
assert not g.save.unlock_all
assert [g.levels.is_unlocked(lv, g.save) for lv in g.levels.levels[:2]] == [True, False]
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

# Level select scrolls through all levels and keeps the selection visible
ls = menu.LevelSelectScene(g)
g.reset_to(ls)
assert ls.max_scroll > 0
key(g, pygame.K_HOME)
frame(g, 40)
assert ls.index == 0 and ls.scroll == 0
shot(g, "03_levelselect_top")
for _ in range(37):
    key(g, pygame.K_DOWN)
    frame(g, 3)
frame(g, 40)
assert ls.VIEW.contains(ls._row_rect(ls.level_y[ls.index])), "selectie buiten beeld"
shot(g, "03_levelselect_middle")
key(g, pygame.K_END)
frame(g, 40)
assert ls.index == len(g.levels.levels) - 1 and abs(ls.scroll - ls.max_scroll) < 1
assert ls.VIEW.contains(ls._row_rect(ls.level_y[ls.index]))
shot(g, "03_levelselect_bottom")
ls.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=5, flipped=False))
frame(g, 40)
assert ls.scroll < ls.max_scroll
key(g, pygame.K_PAGEUP)
assert ls.index == len(g.levels.levels) - 11

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

# Discord statuses reported by the real scenes
def status():
    act = g.presence_activity()
    return act["details"], act["state"]

g.reset_to(menu.TitleScene(g))
frame(g, 2)
assert status()[0] == "In het hoofdmenu", status()
g.push(menu.OptionsScene(g))
assert "INST-7" in status()[1], status()
g.pop()
lv = g.levels.by_id("3-4")
play.start_level(g, lv, show_intro=False)
scene = g.top
frame(g, 2)
assert status() == ("Dossier 3-4: " + lv.name, "Denkt na... (0/5 gearchiveerd)"), status()
seq = SOLUTIONS["3-4"]
scene.try_move(LETTER_DIRS[seq[0]])          # first move of 3-4 is a push
frame(g, 1)
assert status()[1].startswith("Duwt een dossier"), status()
frame(g, 200, dt=16)                         # ~3 s idle
assert status()[1].startswith("Denkt na"), status()
scene.try_move(LETTER_DIRS["l"])             # step back left (no push)
frame(g, 1)
assert status()[1].startswith("Loopt door de gang"), status()
key(g, pygame.K_ESCAPE)
assert status()[1].startswith("Koffiepauze"), status()
assert g.presence_activity()["timestamps"]["start"] == int(scene.started)
print("Discord statuses OK:", status())

g.reset_to(play.EndingScene(g))
frame(g, 200)
shot(g, "10_ending")

# saved progress reloads
from game.savegame import SaveGame  # noqa: E402
s2 = SaveGame()
assert len(s2.completed) == len(g.levels.levels), s2.completed
print("SMOKE TEST OK -", len(s2.completed), "levels completed via the real game scenes")
print("Screenshots in", OUT)
