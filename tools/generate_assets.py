"""Generate all pixel-art sprites, backgrounds and 8-bit sounds.

All artwork is original and drawn here as 16x16 pixel grids which are
scaled 2x to 32x32 tiles. Sounds and music are synthesised square/triangle
waves. Run once (results are committed to assets/):

    python tools/generate_assets.py
"""
from __future__ import annotations

import array
import math
import os
import random
import shutil
import struct
import sys
import wave

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITES = os.path.join(ROOT, "assets", "sprites")
SOUNDS = os.path.join(ROOT, "assets", "sounds")
BACKGROUNDS = os.path.join(ROOT, "assets", "backgrounds")
FONTS = os.path.join(ROOT, "assets", "fonts")

PALETTE = {
    "K": (20, 22, 38),      # outline
    "N": (24, 50, 112),     # rijksblauw (navy)
    "n": (14, 30, 72),      # deep navy
    "B": (48, 98, 178),     # blue
    "L": (130, 178, 232),   # light blue
    "W": (244, 244, 240),   # white
    "G": (196, 198, 206),   # light grey
    "g": (138, 142, 156),   # grey
    "d": (72, 74, 92),      # dark grey
    "S": (242, 194, 152),   # skin
    "s": (206, 146, 112),   # skin shadow
    "H": (92, 58, 34),      # hair
    "O": (206, 156, 86),    # cardboard
    "o": (156, 104, 52),    # cardboard shadow
    "Y": (244, 214, 104),   # manila folder
    "R": (204, 44, 44),     # red
    "E": (64, 168, 74),     # green
    "e": (32, 104, 44),     # dark green
    "C": (112, 70, 40),     # coffee
    "T": (178, 126, 74),    # wood
    "t": (122, 82, 46),     # dark wood
    "F": (98, 230, 120),    # screen green
}

# --------------------------------------------------------------------- art
HEAD_DOWN = [
    "................",
    ".....KKKKKK.....",
    "....KHHHHHHK....",
    "...KHHHHHHHHK...",
    "...KHSSSSSSHK...",
    "...KSKSSSSKSK...",
    "...KSSSSSSSSK...",
    "....KSSssSSK....",
    "...KKNWRRWNKK...",
    "..KNNNWRRWNNNK..",
    "..KNKNNRRNNKNK..",
    "..KSKNNNNNNKSK..",
    "...KKNNNNNNKK...",
]
HEAD_UP = [
    "................",
    ".....KKKKKK.....",
    "....KHHHHHHK....",
    "...KHHHHHHHHK...",
    "...KHHHHHHHHK...",
    "...KHHHHHHHHK...",
    "...KHHHHHHHHK...",
    "....KSSSSSSK....",
    "...KKNNNNNNKK...",
    "..KNNNNNNNNNNK..",
    "..KNKNNNNNNKNK..",
    "..KSKNNNNNNKSK..",
    "...KKNNNNNNKK...",
]
HEAD_LEFT = [
    "................",
    ".....KKKKKK.....",
    "....KHHHHHHK....",
    "...KHHHHHHHHK...",
    "...KSSSHHHHHK...",
    "...KSKSSHHHHK...",
    "...KSSSSSHHHK...",
    "....KSSSSSSK....",
    "....KKWNNNNK....",
    "....KWRNNNNK....",
    "....KNRNNNNK....",
    "....KNSNNNNK....",
    "....KKNNNNNK....",
]
LEGS_FRONT = [
    ["....KddKKddK....", "....KddKKddK....", "...KKKK..KKKK..."],
    ["....KddKKddK....", "....KddK.KKK....", "...KKKK........."],
    ["....KddKKddK....", "....KKK.KddK....", ".........KKKK..."],
]
LEGS_SIDE = [
    [".....KddddK.....", ".....KddddK.....", "....KKKKKK......"],
    ["....KddKKddK....", "...KddK..KddK...", "..KKKK...KKKK..."],
    [".....KddddK.....", "......KddK......", ".....KKKK......."],
]

BOX = [
    "................",
    ".KKKKKKKKKKKKKK.",
    ".KYYWWWYYLLYYYK.",
    ".KOOOOOOOOOOOOK.",
    ".KooooooooooooK.",
    ".KOOOOOOOOOOOOK.",
    ".KOOKKKKKKKKOOK.",
    ".KOOKWWWWWWKOOK.",
    ".KOOKWddddWKOOK.",
    ".KOOKWWWWWWKOOK.",
    ".KOOKWddWWWKOOK.",
    ".KOOKKKKKKKKOOK.",
    ".KOOOOOOOOOOOOK.",
    ".KooooooooooooK.",
    ".KKKKKKKKKKKKKK.",
    "................",
]
BOX_DONE = [
    "................",
    ".KKKKKKKKKKKKKK.",
    ".KYYWWWYYLLYYYK.",
    ".KOOOOOOOOOOOOK.",
    ".KooooooooooooK.",
    ".KOOOOOOOOOOOOK.",
    ".KOOKKKKKKKKOOK.",
    ".KOOKWWWWWEKOOK.",
    ".KOOKWWWWEEKOOK.",
    ".KOOKEWWEEWKOOK.",
    ".KOOKWEEEWWKOOK.",
    ".KOOKKKKKKKKOOK.",
    ".KOOOOOOOOOOOOK.",
    ".KooooooooooooK.",
    ".KKKKKKKKKKKKKK.",
    "................",
]
DESK = [
    "................",
    "................",
    "...KKKK...KKK...",
    "..KWWWWK.KYYYK..",
    ".KKWddWKKKYYYKK.",
    ".KTTTTTTTTTTTTK.",
    ".KTTTTTTTTTTTTK.",
    ".KttttttttttttK.",
    ".KKKKKKKKKKKKKK.",
    ".KtK........KtK.",
    ".KtK.KKKKKK.KtK.",
    ".KtK.KTTTTK.KtK.",
    ".KtK.KttttK.KtK.",
    ".KtK.KKKKKK.KtK.",
    ".KKK........KKK.",
    "................",
]
COMPUTER = [
    "................",
    "...KKKKKKKKKK...",
    "...KGGGGGGGGK...",
    "...KGKKKKKKGK...",
    "...KGKFFFFKGK...",
    "...KGKFeFFKGK...",
    "...KGKFFFFKGK...",
    "...KGKKKKKKGK...",
    "...KGGGGGGgGK...",
    "...KKKKKKKKKK...",
    ".KKKKKKGGKKKKKK.",
    ".KTTTKKKKKKTTTK.",
    ".KTTKGgGgGgKTTK.",
    ".KTTKKKKKKKKTTK.",
    ".KttttttttttttK.",
    ".KKKKKKKKKKKKKK.",
]
PLANT = [
    "................",
    ".....K...K......",
    "....KEK.KEK.....",
    "...KEeEKEeEK.K..",
    "..KEEeEEeEEKKEK.",
    ".KEeEEEeEEeEEeK.",
    "..KEEeEEEeEEEK..",
    ".KEeEEeEEeEeEEK.",
    "..KKEEeEEEeEKK..",
    "....KKKEEKKK....",
    "....KOOOOOOK....",
    "....KOOOOOOK....",
    ".....KooooK.....",
    ".....KooooK.....",
    ".....KKKKKK.....",
    "................",
]
COFFEE = [
    "................",
    "..KKKKKKKKKKKK..",
    "..KddddddddddK..",
    "..KdRRRRRRRRdK..",
    "..KdRWWRWWRRdK..",
    "..KdRRRRRRRRdK..",
    "..KddddddddddK..",
    "..KdLdLdLdgddK..",
    "..KddddddddddK..",
    "..KdKKKKKKKKdK..",
    "..KdK..WW..KdK..",
    "..KdK..WC..KdK..",
    "..KdKKKKKKKKdK..",
    "..KddddddddddK..",
    "..KKKKKKKKKKKK..",
    "..KK........KK..",
]
PRINTER = [
    "................",
    "....KKKKKKKK....",
    "....KWWWWWWK....",
    "....KWddddWK....",
    "..KKKKKKKKKKKK..",
    ".KGGGGGGGGGGGGK.",
    ".KGGGGGGGGEGRGK.",
    ".KggggggggggggK.",
    ".KGKKKKKKKKKKGK.",
    ".KGKWWWWWWWWKGK.",
    ".KGKKKKKKKKKKGK.",
    ".KGGGGGGGGGGGGK.",
    ".KggggggggggggK.",
    ".KKKKKKKKKKKKKK.",
    "..Kd........dK..",
    "................",
]
CABINET = [
    ".KKKKKKKKKKKKKK.",
    ".KGGGGGGGGGGGGK.",
    ".KGKKKKKKKKKKGK.",
    ".KGKLLLLLLLLKGK.",
    ".KGKLLKWWKLLKGK.",
    ".KGKKKKKKKKKKGK.",
    ".KGGGGGGGGGGGGK.",
    ".KGKKKKKKKKKKGK.",
    ".KGKLLLLLLLLKGK.",
    ".KGKLLKWWKLLKGK.",
    ".KGKKKKKKKKKKGK.",
    ".KGGGGGGGGGGGGK.",
    ".KGKKKKKKKKKKGK.",
    ".KGKLLKWWKLLKGK.",
    ".KggggggggggggK.",
    ".KKKKKKKKKKKKKK.",
]
GOAL_ICON = [
    "KKKKKKKK",
    "KLLLLLLK",
    "KLKWWKLK",
    "KLLLLLLK",
    "KKKKKKKK",
    "KLLLLLLK",
    "KLKWWKLK",
    "KKKKKKKK",
]
ICON_INFO = [
    "................",
    ".....KKKKKK.....",
    "...KKBBBBBBKK...",
    "..KBBBBWWBBBBK..",
    "..KBBBBWWBBBBK..",
    ".KBBBBBBBBBBBBK.",
    ".KBBBBWWWBBBBBK.",
    ".KBBBBBWWBBBBBK.",
    ".KBBBBBWWBBBBBK.",
    ".KBBBBBWWBBBBBK.",
    "..KBBBBWWBBBBK..",
    "..KBBBWWWWBBBK..",
    "...KKBBBBBBKK...",
    ".....KKKKKK.....",
    "................",
    "................",
]
ICON_WARN = [
    "................",
    ".......KK.......",
    "......KYYK......",
    "......KYYK......",
    ".....KYYYYK.....",
    ".....KYKKYK.....",
    "....KYYKKYYK....",
    "....KYYKKYYK....",
    "...KYYYKKYYYK...",
    "...KYYYKKYYYK...",
    "..KYYYYYYYYYYK..",
    "..KYYYYKKYYYYK..",
    ".KYYYYYKKYYYYYK.",
    ".KYYYYYYYYYYYYK.",
    ".KKKKKKKKKKKKKK.",
    "................",
]
ICON_OK = [
    "................",
    ".....KKKKKK.....",
    "...KKEEEEEEKK...",
    "..KEEEEEEEEEEK..",
    "..KEEEEEEEEWEK..",
    ".KEEEEEEEEWWEEK.",
    ".KEEEEEEEWWWEEK.",
    ".KEEWEEEWWWEEEK.",
    ".KEEWWEWWWEEEEK.",
    ".KEEEWWWWEEEEEK.",
    "..KEEEWWEEEEEK..",
    "..KEEEEEEEEEEK..",
    "...KKEEEEEEKK...",
    ".....KKKKKK.....",
    "................",
    "................",
]
ICON_CLOCK = [
    "................",
    ".....KKKKKK.....",
    "...KKWWWWWWKK...",
    "..KWWWWKWWWWWK..",
    "..KWWWWKWWWWWK..",
    ".KWWWWWKWWWWWWK.",
    ".KWWWWWKWWWWWWK.",
    ".KWKWWWKKKKWKWK.",
    ".KWWWWWWWWWWWWK.",
    ".KWWWWWWWWWWWWK.",
    "..KWWWWWWWWWWK..",
    "..KWWWWWKWWWWK..",
    "...KKWWWWWWKK...",
    ".....KKKKKK.....",
    "................",
    "................",
]
# Fictional logo: Rijksdienst voor Dossierverplaatsing (a folder with an arrow)
LOGO = [
    "................",
    "..KKKKK.........",
    ".KYYYYYK........",
    ".KYYYYYKKKKKKKK.",
    ".KYYYYYYYYYYYYK.",
    ".KYYYYYYYYYYYYK.",
    ".KYYYYYNYYYYYYK.",
    ".KYYYYYNNYYYYYK.",
    ".KYNNNNNNNYYYYK.",
    ".KYNNNNNNNNYYYK.",
    ".KYNNNNNNNYYYYK.",
    ".KYYYYYNNYYYYYK.",
    ".KYYYYYNYYYYYYK.",
    ".KYYYYYYYYYYYYK.",
    ".KKKKKKKKKKKKKK.",
    "................",
]


def grid_surface(rows, scale=2, palette=PALETTE):
    width = max(len(r) for r in rows)
    surf = pygame.Surface((width, len(rows)), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    for y, row in enumerate(rows):
        if len(row) > width:
            raise ValueError(f"row too long: {row!r}")
        for x, ch in enumerate(row):
            if ch != ".":
                surf.set_at((x, y), palette[ch])
    if scale != 1:
        surf = pygame.transform.scale(surf, (width * scale, len(rows) * scale))
    return surf


def save(surf, name, folder=SPRITES):
    pygame.image.save(surf, os.path.join(folder, name))


def mirror(rows):
    return [r[::-1] for r in rows]


def make_player():
    for facing, head, legs in (
        ("down", HEAD_DOWN, LEGS_FRONT),
        ("up", HEAD_UP, LEGS_FRONT),
        ("left", HEAD_LEFT, LEGS_SIDE),
    ):
        for i, leg in enumerate(legs):
            rows = list(head) + list(leg)
            save(grid_surface(rows), f"player_{facing}_{i}.png")
            if facing == "left":
                save(grid_surface(mirror(rows)), f"player_right_{i}.png")


def make_floor():
    for name, base, alt in (("floor_a", (206, 210, 220), (192, 197, 210)),
                            ("floor_b", (196, 201, 213), (184, 189, 203))):
        s = pygame.Surface((16, 16))
        s.fill(base)
        for y in range(16):
            for x in range(16):
                if (x + y * 3) % 7 == 0:
                    s.set_at((x, y), alt)
        pygame.draw.line(s, (170, 176, 192), (0, 15), (15, 15))
        pygame.draw.line(s, (170, 176, 192), (15, 0), (15, 15))
        pygame.draw.line(s, (222, 226, 234), (0, 0), (14, 0))
        save(pygame.transform.scale(s, (32, 32)), name + ".png")


def make_walls():
    # top of a wall (seen from above): dark navy with subtle bricks
    s = pygame.Surface((16, 16))
    s.fill(PALETTE["n"])
    for y in range(0, 16, 4):
        pygame.draw.line(s, (20, 40, 92), (0, y), (15, y))
        off = 0 if (y // 4) % 2 == 0 else 4
        for x in range(off, 16, 8):
            pygame.draw.line(s, (20, 40, 92), (x, y), (x, y + 3))
    save(pygame.transform.scale(s, (32, 32)), "wall_top.png")
    # front face of a wall: navy cap, light wall panel, white skirting board
    s = pygame.Surface((16, 16))
    s.fill(PALETTE["n"])
    pygame.draw.rect(s, PALETTE["B"], (0, 4, 16, 9))
    pygame.draw.line(s, PALETTE["L"], (0, 4), (15, 4))
    for x in (3, 11):
        pygame.draw.rect(s, (40, 84, 160), (x, 6, 3, 5))
    pygame.draw.rect(s, PALETTE["W"], (0, 13, 16, 2))
    pygame.draw.line(s, PALETTE["K"], (0, 15), (15, 15))
    save(pygame.transform.scale(s, (32, 32)), "wall_front.png")
    # void outside the office
    s = pygame.Surface((16, 16))
    s.fill((10, 14, 30))
    s.set_at((3, 5), (24, 32, 60))
    s.set_at((11, 12), (24, 32, 60))
    save(pygame.transform.scale(s, (32, 32)), "void.png")


def make_goal():
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    yellow = PALETTE["Y"]
    for i in range(1, 15):
        if (i // 2) % 2 == 0:
            for p in ((i, 1), (i, 14), (1, i), (14, i)):
                s.set_at(p, yellow)
    s.blit(grid_surface(GOAL_ICON, scale=1), (4, 4))
    save(pygame.transform.scale(s, (32, 32)), "goal.png")


def make_objects():
    for name, art in (("box", BOX), ("box_done", BOX_DONE), ("bureau", DESK),
                      ("computer", COMPUTER), ("plant", PLANT), ("koffie", COFFEE),
                      ("printer", PRINTER), ("kast", CABINET), ("icon_info", ICON_INFO),
                      ("icon_warn", ICON_WARN), ("icon_ok", ICON_OK),
                      ("icon_clock", ICON_CLOCK), ("logo", LOGO)):
        save(grid_surface(art), name + ".png")
    save(grid_surface(LOGO, scale=4), "logo_big.png")
    # shadow under objects
    sh = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 30, 70), (4, 22, 24, 9))
    save(sh, "shadow.png")


def make_stamps(font_path):
    font = pygame.font.Font(font_path, 22)
    for name, text, colour in (("stamp_ok", "GOEDGEKEURD", (40, 150, 60)),
                               ("stamp_no", "AFGEWEZEN", (200, 40, 40))):
        label = font.render(text, False, colour)
        w, h = label.get_width() + 20, label.get_height() + 14
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, colour, (0, 0, w, h), 3)
        pygame.draw.rect(s, colour, (5, 5, w - 10, h - 10), 1)
        s.blit(label, (10, 7))
        # worn ink: knock out random pixels
        rnd = random.Random(42)
        for _ in range(w * h // 9):
            x, y = rnd.randrange(w), rnd.randrange(h)
            s.set_at((x, y), (0, 0, 0, 0))
        small = pygame.transform.scale(s, (w // 2, h // 2))
        big = pygame.transform.scale(small, (w, h))
        save(pygame.transform.scale(big, (w * 2, h * 2)), name + ".png")


def make_title_background():
    w, h = 800, 600
    s = pygame.Surface((w, h))
    # dithered navy gradient
    for y in range(0, h, 4):
        t = y / h
        c1 = (int(10 + 20 * t), int(18 + 40 * t), int(48 + 80 * t))
        c2 = (int(14 + 20 * t), int(24 + 40 * t), int(58 + 80 * t))
        for x in range(0, w, 4):
            s.fill(c1 if (x // 4 + y // 4) % 2 else c2, (x, y, 4, 4))
    rnd = random.Random(7)
    for _ in range(70):
        x, y = rnd.randrange(w), rnd.randrange(260)
        s.fill((180, 200, 255), (x - x % 4, y - y % 4, 4, 4))
    # skyline of government office blocks
    x = 0
    while x < w:
        bw = rnd.choice((64, 80, 96, 112, 128))
        bh = rnd.choice((120, 160, 200, 240, 280))
        top = h - bh
        pygame.draw.rect(s, (16, 26, 60), (x, top, bw - 8, bh))
        pygame.draw.rect(s, (30, 46, 96), (x, top, bw - 8, 4))
        for wy in range(top + 16, h - 20, 20):
            for wx in range(x + 8, x + bw - 20, 16):
                lit = rnd.random() < 0.45
                col = (250, 220, 120) if lit else (36, 52, 104)
                s.fill(col, (wx, wy, 8, 8))
        x += bw
    pygame.draw.rect(s, (8, 12, 28), (0, h - 24, w, 24))
    save(s, "title.png", BACKGROUNDS)


def write_ico(png_path, ico_path):
    """Write a .ico that embeds a 256px PNG (supported since Windows Vista)."""
    img = pygame.image.load(png_path)
    big = pygame.transform.scale(img, (256, 256))
    tmp = ico_path + ".png"
    pygame.image.save(big, tmp)
    with open(tmp, "rb") as f:
        data = f.read()
    os.remove(tmp)
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(data), 6 + 16)
    with open(ico_path, "wb") as f:
        f.write(header + entry + data)


# ------------------------------------------------------------------ sounds
RATE = 22050


def _write_wav(name, samples):
    data = array.array("h", (max(-32767, min(32767, int(v * 32767))) for v in samples))
    with wave.open(os.path.join(SOUNDS, name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


def _osc(kind, phase):
    phase %= 1.0
    if kind == "square":
        return 1.0 if phase < 0.5 else -1.0
    if kind == "pulse":
        return 1.0 if phase < 0.25 else -1.0
    if kind == "triangle":
        return 4 * abs(phase - 0.5) - 1
    if kind == "saw":
        return 2 * phase - 1
    return math.sin(2 * math.pi * phase)


def tone(segments, kind="square", vol=0.35, attack=0.004, release=0.03):
    """segments: list of (freq_start, freq_end, seconds)."""
    out = []
    for f0, f1, dur in segments:
        n = int(dur * RATE)
        phase = 0.0
        for i in range(n):
            t = i / max(1, n - 1)
            f = f0 + (f1 - f0) * t
            phase += f / RATE
            env = 1.0
            if i < attack * RATE:
                env = i / (attack * RATE)
            if n - i < release * RATE:
                env *= (n - i) / (release * RATE)
            out.append(_osc(kind, phase) * vol * env if f > 0 else 0.0)
    return out


def noise(dur, vol=0.3, decay=8.0, step=1, seed=1):
    rnd = random.Random(seed)
    n = int(dur * RATE)
    out, v = [], 0.0
    for i in range(n):
        if i % step == 0:
            v = rnd.uniform(-1, 1)
        out.append(v * vol * math.exp(-decay * i / RATE))
    return out


def mix(*tracks):
    n = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(n)]


def note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def make_sounds():
    _write_wav("step.wav", tone([(180, 120, 0.035)], "square", 0.16, release=0.02))
    _write_wav("step2.wav", tone([(150, 100, 0.035)], "square", 0.16, release=0.02))
    _write_wav("push.wav", mix(noise(0.12, 0.25, 14, step=6, seed=3),
                               tone([(90, 70, 0.12)], "triangle", 0.3)))
    _write_wav("goal.wav", tone([(note(76), note(76), 0.06), (note(83), note(83), 0.1)],
                                "pulse", 0.25))
    _write_wav("error.wav", tone([(110, 100, 0.09), (0, 0, 0.03), (110, 90, 0.12)],
                                 "square", 0.25))
    _write_wav("menu_move.wav", tone([(note(84), note(84), 0.03)], "pulse", 0.18))
    _write_wav("menu_select.wav", tone([(note(79), note(79), 0.04),
                                        (note(91), note(91), 0.07)], "square", 0.22))
    _write_wav("undo.wav", tone([(note(72), note(64), 0.08)], "triangle", 0.35))
    _write_wav("restart.wav", tone([(note(72), note(48), 0.25)], "square", 0.2))
    _write_wav("stamp.wav", mix(noise(0.25, 0.6, 22, step=2, seed=9),
                                tone([(80, 40, 0.2)], "sine", 0.6)))
    fanfare = []
    for m, d in ((72, 0.1), (76, 0.1), (79, 0.1), (84, 0.22), (79, 0.1), (84, 0.4)):
        fanfare += tone([(note(m), note(m), d)], "square", 0.22, release=0.04)
    bass = []
    for m, d in ((48, 0.3), (55, 0.3), (48, 0.42)):
        bass += tone([(note(m), note(m), d)], "triangle", 0.3)
    _write_wav("complete.wav", mix(fanfare, bass))


def render_song(melody, chords, bpm, name, lead="pulse", lead_vol=0.13):
    """melody: list of (midi|None, eighths); chords: list of root midi per bar."""
    eighth = 60.0 / bpm / 2
    lead_track = []
    for m, length in melody:
        dur = eighth * length
        if m is None:
            lead_track += [0.0] * int(dur * RATE)
        else:
            body = tone([(note(m), note(m), dur * 0.85)], lead, lead_vol, release=0.03)
            lead_track += body + [0.0] * (int(dur * RATE) - len(body))
    bass_track, arp_track = [], []
    for root in chords:
        for beat in range(4):
            m = root if beat % 2 == 0 else root + 7
            body = tone([(note(m), note(m), eighth * 1.6)], "triangle", 0.22)
            bass_track += body + [0.0] * (int(eighth * 2 * RATE) - len(body))
        third = 4 if root % 12 in (0, 5, 7) else 3
        for i in range(8):
            m = root + 24 + (0, third, 7, 12)[i % 4]
            body = tone([(note(m), note(m), eighth * 0.4)], "square", 0.035)
            arp_track += body + [0.0] * (int(eighth * RATE) - len(body))
    _write_wav(name, mix(lead_track, bass_track, arp_track))


def make_music():
    # "Wachtmuziek" - original hold-music style tune for the menus.
    mel = [
        (76, 2), (79, 1), (81, 1), (79, 2), (76, 2),
        (74, 2), (76, 1), (74, 1), (72, 4),
        (72, 2), (74, 1), (76, 1), (77, 2), (76, 1), (74, 1),
        (74, 6), (None, 2),
        (76, 2), (79, 1), (81, 1), (84, 2), (83, 1), (81, 1),
        (79, 2), (77, 1), (76, 1), (74, 4),
        (72, 2), (76, 1), (79, 1), (77, 2), (74, 2),
        (72, 6), (None, 2),
    ]
    chords = [48, 45, 41, 43, 48, 45, 41, 43]
    render_song(mel, chords, 112, "music_menu.wav")
    # Calm office tune for in-game.
    mel2 = [
        (69, 3), (72, 1), (71, 2), (69, 2),
        (67, 3), (69, 1), (64, 4),
        (65, 3), (69, 1), (67, 2), (65, 2),
        (64, 6), (None, 2),
        (69, 3), (72, 1), (76, 2), (74, 2),
        (72, 3), (71, 1), (69, 4),
        (65, 2), (67, 2), (69, 2), (71, 2),
        (69, 6), (None, 2),
    ]
    chords2 = [45, 43, 41, 40, 45, 43, 41, 40]
    render_song(mel2, chords2, 96, "music_game.wav", lead="triangle", lead_vol=0.2)


def main():
    pygame.init()
    for d in (SPRITES, SOUNDS, BACKGROUNDS, FONTS):
        os.makedirs(d, exist_ok=True)
    font_src = os.path.join(os.path.dirname(pygame.__file__), "freesansbold.ttf")
    font_dst = os.path.join(FONTS, "freesansbold.ttf")
    shutil.copyfile(font_src, font_dst)
    make_player()
    make_floor()
    make_walls()
    make_goal()
    make_objects()
    make_stamps(font_dst)
    make_title_background()
    write_ico(os.path.join(SPRITES, "logo.png"), os.path.join(ROOT, "assets", "icon.ico"))
    make_sounds()
    make_music()
    print("Assets gegenereerd.")


if __name__ == "__main__":
    sys.exit(main())
