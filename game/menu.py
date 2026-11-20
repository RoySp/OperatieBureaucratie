"""Menus: loading screen, title, options, credits, level select and dialogs."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, List, Optional

import pygame

from . import settings as S
from . import ui
from .engine import Scene

UP_KEYS = (pygame.K_UP, pygame.K_w)
DOWN_KEYS = (pygame.K_DOWN, pygame.K_s)
LEFT_KEYS = (pygame.K_LEFT, pygame.K_a)
RIGHT_KEYS = (pygame.K_RIGHT, pygame.K_d)
OK_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
# Secret code in the level select: up up down down left right left right B A
SECRET_CODE = (pygame.K_UP, pygame.K_UP, pygame.K_DOWN, pygame.K_DOWN, pygame.K_LEFT,
               pygame.K_RIGHT, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_b, pygame.K_a)


@dataclass
class MenuItem:
    label: str
    action: Optional[Callable[[], None]] = None
    kind: str = "button"            # button | toggle | slider
    get: Optional[Callable[[], object]] = None
    set: Optional[Callable[[object], None]] = None
    enabled: bool = True
    hint: str = ""


class MenuList:
    """Keyboard and mouse driven vertical menu in DOS style."""

    def __init__(self, game, items: List[MenuItem], rect, item_h=34, font="large"):
        self.game = game
        self.items = items
        self.rect = pygame.Rect(rect)
        self.item_h = item_h
        self.font = font
        self.index = next((i for i, it in enumerate(items) if it.enabled), 0)

    def item_rect(self, i):
        return pygame.Rect(self.rect.x, self.rect.y + i * self.item_h, self.rect.w, self.item_h - 4)

    def _move(self, step):
        n = len(self.items)
        for _ in range(n):
            self.index = (self.index + step) % n
            if self.items[self.index].enabled:
                break
        self.game.sound.play("menu_move")

    def _adjust(self, item: MenuItem, step: int):
        if item.kind == "toggle":
            item.set(not item.get())
            self.game.sound.play("menu_move")
        elif item.kind == "slider":
            value = round(min(1.0, max(0.0, item.get() + 0.1 * step)), 2)
            item.set(value)
            self.game.sound.play("menu_move")

    def _activate(self, item: MenuItem):
        if not item.enabled:
            self.game.sound.play("error")
            return
        if item.kind == "toggle":
            self._adjust(item, 1)
        elif item.kind == "slider":
            self._adjust(item, 1 if item.get() < 1.0 else -10)
        elif item.action:
            self.game.sound.play("menu_select")
            item.action()

    def handle_event(self, e) -> bool:
        if e.type == pygame.KEYDOWN:
            if e.key in UP_KEYS:
                self._move(-1)
            elif e.key in DOWN_KEYS:
                self._move(1)
            elif e.key in LEFT_KEYS:
                self._adjust(self.items[self.index], -1)
            elif e.key in RIGHT_KEYS:
                self._adjust(self.items[self.index], 1)
            elif e.key in OK_KEYS:
                self._activate(self.items[self.index])
            else:
                return False
            return True
        if e.type == pygame.MOUSEMOTION:
            for i, it in enumerate(self.items):
                if it.enabled and self.item_rect(i).collidepoint(e.pos) and i != self.index:
                    self.index = i
                    self.game.sound.play("menu_move")
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, it in enumerate(self.items):
                r = self.item_rect(i)
                if r.collidepoint(e.pos):
                    self.index = i
                    if it.kind == "slider":
                        self._adjust(it, -1 if e.pos[0] < r.right - 90 else 1)
                    else:
                        self._activate(it)
                    return True
        return False

    def draw(self, surf):
        fonts = self.game.fonts
        blink = (self.game.time // 400) % 2 == 0
        for i, it in enumerate(self.items):
            r = self.item_rect(i)
            selected = i == self.index
            if selected:
                pygame.draw.rect(surf, S.LIGHT_BLUE, r)
                color, shadow = S.NAVY, None
                if blink:
                    cy = r.centery
                    pygame.draw.polygon(surf, S.NAVY, [(r.x + 8, cy - 7), (r.x + 8, cy + 7), (r.x + 16, cy)])
            else:
                color, shadow = (S.WHITE if it.enabled else S.MID_GREY), S.BLACK
            th = fonts.size(it.label, self.font)[1]
            ui.text(surf, fonts, it.label, (r.x + 26, r.centery - th // 2), self.font, color, shadow=shadow)
            if it.kind == "toggle":
                val = "AAN" if it.get() else "UIT"
                ui.text(surf, fonts, f"[{val}]", (r.right - 12, r.centery - th // 2), self.font,
                        color, align="right", shadow=shadow)
            elif it.kind == "slider":
                v = it.get()
                for b in range(10):
                    bx = r.right - 132 + b * 12
                    rect = (bx, r.centery - 7, 9, 14)
                    if b < round(v * 10):
                        pygame.draw.rect(surf, S.YELLOW if not selected else S.NAVY, rect)
                    else:
                        pygame.draw.rect(surf, color, rect, 1)


# ===================================================================== scenes
class LoadingScene(Scene):
    def presence(self):
        return ("In het hoofdmenu", "Start het systeem op...")

    """'Een moment geduld alstublieft...' - the obligatory waiting room."""

    DURATION = 2300

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.line = 0

    def handle_event(self, e):
        if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.finish()

    def finish(self):
        self.game.reset_to(TitleScene(self.game))

    def update(self, dt):
        self.t += dt
        self.line = int(self.t // 450) % len(S.LOADING_LINES)
        if self.t >= self.DURATION:
            self.finish()

    def draw(self, surf):
        surf.fill(S.BLACK)
        f = self.game.fonts
        logo = self.game.sprites["logo_big"]
        surf.blit(logo, logo.get_rect(center=(S.SCREEN_W // 2, 190)))
        ui.text(surf, f, S.ORGANISATION.upper(), (400, 250), "normal", S.LIGHT_BLUE, "center")
        ui.text(surf, f, "presenteert", (400, 276), "small", S.MID_GREY, "center")
        frac = self.t / self.DURATION
        if 0.55 < frac < 0.75:   # bureaucratic hiccup
            frac = 0.55 - (frac - 0.55) * 0.5
            ui.text(surf, f, "Formulier 12B ontbreekt... wordt opgevraagd.", (400, 388),
                    "small", S.RED, "center")
        elif frac >= 0.75:
            frac = 0.45 + (frac - 0.75) * 2.2
        ui.progress_bar(surf, (220, 350, 360, 28), frac)
        ui.text(surf, f, S.LOADING_LINES[self.line], (400, 320), "normal", S.WHITE, "center")
        if (self.game.time // 500) % 2 == 0:
            ui.text(surf, f, "_", (590, 320), "normal", S.WHITE)
        ui.text(surf, f, "Druk op een toets om de wachtrij over te slaan", (400, 560),
                "small", S.DARK_GREY, "center", shadow=None)


class TitleScene(Scene):
    def presence(self):
        return ("In het hoofdmenu", "Bladert door het menu")

    def __init__(self, game):
        super().__init__(game)
        self.menu: Optional[MenuList] = None
        self.ticker = 0.0

    def on_enter(self):
        g = self.game
        g.sound.play_music("music_menu")
        has_progress = bool(g.save.completed) or bool(g.save.last_level)
        items = [
            MenuItem("Nieuw spel", self.new_game),
            MenuItem("Verder spelen", self.continue_game, enabled=has_progress),
            MenuItem("Level selecteren", lambda: g.push(LevelSelectScene(g))),
            MenuItem("Opties", lambda: g.push(OptionsScene(g))),
            MenuItem("Credits", lambda: g.push(CreditsScene(g))),
            MenuItem("Afsluiten", self.ask_quit),
        ]
        old_index = self.menu.index if self.menu else (1 if has_progress else 0)
        self.menu = MenuList(g, items, (270, 278, 260, 0), item_h=36)
        self.menu.index = old_index

    def new_game(self):
        g = self.game
        from .play import start_level
        if g.save.completed:
            def yes():
                g.save.reset_progress()
                start_level(g, g.levels.levels[0])
            g.push(ConfirmScene(g, "NIEUW SPEL",
                                ["Een nieuw spel wist al uw voortgang.",
                                 "Alle goedgekeurde dossiers worden versnipperd.",
                                 "Weet u het zeker?"], yes))
        else:
            start_level(g, g.levels.levels[0])

    def continue_game(self):
        from .play import start_level
        start_level(self.game, self.game.levels.continue_level(self.game.save))

    def ask_quit(self):
        g = self.game
        g.push(ConfirmScene(g, "AFSLUITEN",
                            ["Weet u zeker dat u wilt afsluiten?",
                             "Hiervoor is formulier U-1 vereist.",
                             "(Dat hebben wij alvast voor u ingevuld.)"], g.quit))

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.ask_quit()
            return
        self.menu.handle_event(e)

    def update(self, dt):
        self.ticker += dt

    def draw(self, surf):
        g = self.game
        f = g.fonts
        surf.blit(g.sprites.title_bg, (0, 0))
        ui.dither_overlay(surf, (0, 0, 20), 80)
        # header
        logo = g.sprites["logo"]
        surf.blit(logo, (190, 40))
        surf.blit(pygame.transform.flip(logo, True, False), (578, 40))
        wobble = int(math.sin(g.time / 600) * 2)
        ui.text(surf, f, "OPERATIE", (400, 36 + wobble), "large", S.LIGHT_BLUE, "center", scale=2)
        ui.text(surf, f, "BUREAUCRATIE", (400, 92 + wobble), "large", S.YELLOW, "center",
                shadow=S.RED, scale=2)
        pygame.draw.line(surf, S.LIGHT_BLUE, (150, 152), (650, 152), 2)
        ui.text(surf, f, f'"{S.SUBTITLE}"', (400, 164), "normal", S.WHITE, "center")
        ui.text(surf, f, "De weg naar het juiste loket.", (400, 188), "small", S.LIGHT_BLUE, "center")
        # menu window
        ui.dos_window(surf, f, (240, 236, 320, 278), "HOOFDMENU")
        self.menu.draw(surf)
        # footer
        band = pygame.Surface((S.SCREEN_W, 80), pygame.SRCALPHA)
        band.fill((6, 10, 26, 215))
        surf.blit(band, (0, 520))
        pygame.draw.line(surf, S.RIJKSBLAUW, (0, 520), (S.SCREEN_W, 520), 2)
        done = len(g.save.completed)
        total = len(g.levels.levels)
        ui.text(surf, f, f"Gearchiveerd: {done}/{total} dossiers", (400, 528), "small", S.YELLOW, "center")
        ui.text(surf, f, f"(c) 1993 {S.ORGANISATION}  -  Formulier OB-93  -  Versie {S.VERSION}",
                (400, 574), "small", S.MID_GREY, "center")
        hint = "Pijltjes/WASD: kiezen   ENTER: bevestigen   F11: volledig scherm"
        ui.text(surf, f, hint, (400, 552), "small", S.LIGHT_BLUE, "center")


class ConfirmScene(Scene):
    opaque = False

    def __init__(self, game, title, lines, on_yes, on_no=None):
        super().__init__(game)
        self.title, self.lines = title, lines
        self.on_yes, self.on_no = on_yes, on_no
        w = 470
        h = 110 + 22 * len(lines)
        self.rect = pygame.Rect((S.SCREEN_W - w) // 2, (S.SCREEN_H - h) // 2, w, h)
        self.menu = MenuList(game, [MenuItem("Ja", self.yes), MenuItem("Nee", self.no)],
                             (self.rect.centerx - 60, self.rect.bottom - 82, 120, 0),
                             item_h=34)
        self.menu.index = 1

    def yes(self):
        self.game.pop()
        self.on_yes()

    def no(self):
        self.game.pop()
        if self.on_no:
            self.on_no()

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE or e.key == pygame.K_n:
                self.game.sound.play("menu_move")
                self.no()
                return
            if e.key in (pygame.K_j, pygame.K_y):
                self.game.sound.play("menu_select")
                self.yes()
                return
        self.menu.handle_event(e)

    def draw(self, surf):
        f = self.game.fonts
        ui.dither_overlay(surf, (0, 0, 0), 110)
        ui.dos_window(surf, f, self.rect, self.title, face=S.NAVY, border=S.YELLOW,
                      title_bg=S.YELLOW)
        surf.blit(self.game.sprites["icon_warn"], (self.rect.x + 22, self.rect.y + 26))
        for i, line in enumerate(self.lines):
            ui.text(surf, f, line, (self.rect.x + 66, self.rect.y + 26 + i * 22), "normal", S.WHITE)
        self.menu.draw(surf)


class OptionsScene(Scene):
    def presence(self):
        return ("In het hoofdmenu", "Vult formulier INST-7 in (opties)")

    opaque = False

    def __init__(self, game):
        super().__init__(game)
        st = game.save.settings
        snd = game.sound

        def setter(key):
            def _set(v):
                st[key] = v
                snd.apply_volume()
                if key == "music" and v and snd.current_music:
                    name = snd.current_music
                    snd.current_music = None
                    snd.play_music(name)
            return _set

        items = [
            MenuItem("Geluidseffecten", kind="toggle", get=lambda: st["sound"], set=setter("sound")),
            MenuItem("Effectvolume", kind="slider", get=lambda: st["sfx_volume"], set=setter("sfx_volume")),
            MenuItem("Wachtmuziek", kind="toggle", get=lambda: st["music"], set=setter("music")),
            MenuItem("Muziekvolume", kind="slider", get=lambda: st["music_volume"], set=setter("music_volume")),
            MenuItem("Volledig scherm", kind="toggle", get=lambda: st["fullscreen"],
                     set=lambda v: game.toggle_fullscreen()),
        ]
        if game.discord.active:
            items.append(MenuItem("Discord-status", kind="toggle", get=lambda: st["discord"],
                                  set=setter("discord")))
        items.append(MenuItem("Terug", self.close))
        height = 320 + 38 * (len(items) - 6)
        self.rect = pygame.Rect(170, (600 - height) // 2, 460, height)
        self.menu = MenuList(game, items, (self.rect.x + 24, self.rect.y + 40, self.rect.w - 48, 0),
                             item_h=38, font="normal")

    def close(self):
        self.game.save.save()
        self.game.pop()

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.game.sound.play("menu_move")
            self.close()
            return
        self.menu.handle_event(e)

    def draw(self, surf):
        f = self.game.fonts
        ui.dither_overlay(surf, (0, 0, 0), 110)
        ui.dos_window(surf, f, self.rect, "OPTIES - FORMULIER INST-7")
        self.menu.draw(surf)
        ui.text(surf, f, "Links/rechts: wijzigen   ESC: terug", (self.rect.centerx, self.rect.bottom - 34),
                "small", S.LIGHT_BLUE, "center")


class CreditsScene(Scene):
    def presence(self):
        return ("In het hoofdmenu", "Leest de credits")

    LINES = [
        ("OPERATIE BUREAUCRATIE", "title"),
        ("De weg naar het juiste loket", "sub"),
        ("", ""),
        ("Een uitgave van de", "sub"),
        (S.ORGANISATION, "head"),
        ("(een volledig verzonnen overheidsdienst)", "sub"),
        ("", ""),
        ("SPELONTWERP", "head"),
        ("Afdeling Spelzaken, kamer 4.071", "txt"),
        ("", ""),
        ("PROGRAMMERING", "head"),
        ("Python 3 en Pygame", "txt"),
        ("", ""),
        ("PIXELKUNST", "head"),
        ("Bureau Beeldvorming (16 kleuren, geen budget)", "txt"),
        ("", ""),
        ("GELUID EN WACHTMUZIEK", "head"),
        ("Het Rijksblokgolforkest", "txt"),
        ("", ""),
        ("PUZZELCONTROLE", "head"),
        ("De Commissie Oplosbaarheid", "txt"),
        ("(alle dossiers zijn aantoonbaar archiveerbaar)", "sub"),
        ("", ""),
        ("KOFFIE", "head"),
        ("De automaat op de derde verdieping", "txt"),
        ("(tijdelijk buiten gebruik)", "sub"),
        ("", ""),
        ("LETTERTYPE", "head"),
        ("FreeSans Bold (GNU FreeFont, meegeleverd met Pygame)", "txt"),
        ("", ""),
        ("MET DANK AAN", "head"),
        ("Iedereen die ooit een nummertje heeft getrokken", "txt"),
        ("", ""),
        ("Dit spel is een parodie. Elke gelijkenis met", "sub"),
        ("bestaande loketten berust op toeval.", "sub"),
        ("", ""),
        ("Uw aanvraag is in behandeling.", "head"),
    ]

    def __init__(self, game):
        super().__init__(game)
        self.offset = 0.0

    def handle_event(self, e):
        if (e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE,) + OK_KEYS) or \
                (e.type == pygame.MOUSEBUTTONDOWN):
            self.game.sound.play("menu_move")
            self.game.pop()

    def update(self, dt):
        self.offset += dt * 0.035
        if self.offset > len(self.LINES) * 28 + 520:
            self.offset = 0

    def draw(self, surf):
        g = self.game
        f = g.fonts
        surf.blit(g.sprites.title_bg, (0, 0))
        ui.dither_overlay(surf, (0, 0, 20), 150)
        clip = pygame.Rect(0, 40, S.SCREEN_W, 500)
        surf.set_clip(clip)
        y = 540 - self.offset
        for txt, kind in self.LINES:
            if kind == "title":
                ui.text(surf, f, txt, (400, y), "large", S.YELLOW, "center", scale=2)
                y += 52
                continue
            font, color = {"head": ("large", S.YELLOW), "sub": ("small", S.LIGHT_BLUE),
                           "txt": ("normal", S.WHITE)}.get(kind, ("normal", S.WHITE))
            if txt:
                ui.text(surf, f, txt, (400, y), font, color, "center")
            y += 28
        surf.set_clip(None)
        ui.text(surf, f, "CREDITS", (400, 10), "large", S.LIGHT_BLUE, "center")
        ui.text(surf, f, "ESC: terug naar het hoofdmenu", (400, 570), "small", S.MID_GREY, "center")


class LevelSelectScene(Scene):
    def presence(self):
        done = len([lv for lv in self.game.levels.levels if self.game.save.is_completed(lv.id)])
        return ("In het hoofdmenu", f"Kiest een dossier ({done}/{len(self.game.levels.levels)} goedgekeurd)")

    ROW_H = 18
    DEPT_H = 21
    VIEW = pygame.Rect(32, 44, 410, 500)       # visible part of the list
    BAR = pygame.Rect(446, 44, 8, 500)         # scrollbar track

    def __init__(self, game, from_pause=False):
        super().__init__(game)
        self.from_pause = from_pause
        levels = game.levels.levels
        last = game.levels.by_id(game.save.last_level) or game.levels.continue_level(game.save)
        self.index = last.index
        self.rows = []  # (kind, obj, y) with y relative to the top of the list
        y = 4
        for dept in game.levels.departments:
            self.rows.append(("dept", dept, y))
            y += self.DEPT_H
            for lv in dept.levels:
                self.rows.append(("level", lv, y))
                y += self.ROW_H
            y += 3
        self.content_h = y
        self.level_y = {obj.index: y for kind, obj, y in self.rows if kind == "level"}
        self.levels = levels
        self.preview_cache = {}
        self.message = ""
        self.message_t = 0.0
        self.message_ok = False
        self.dragging = False
        self.code = []  # (key, selection before that key) for the secret code
        self.scroll = self.target = 0.0
        self.follow_selection(center=True)
        self.scroll = self.target

    # ------------------------------------------------------------ scrolling
    @property
    def max_scroll(self) -> float:
        return max(0, self.content_h - self.VIEW.h)

    def scroll_to(self, value: float):
        self.target = min(self.max_scroll, max(0.0, value))

    def follow_selection(self, center=False):
        """Scroll just enough to keep the selected level (and its heading) visible."""
        y = self.level_y[self.index]
        if center:
            self.scroll_to(y - self.VIEW.h // 2)
            return
        lv = self.levels[self.index]
        top = y - (self.DEPT_H + 4 if lv.department.levels[0] is lv else 2 * self.ROW_H)
        bottom = y + 3 * self.ROW_H
        if top < self.target:
            self.scroll_to(top)
        elif bottom > self.target + self.VIEW.h:
            self.scroll_to(bottom - self.VIEW.h)

    def select(self, index: int):
        index = max(0, min(len(self.levels) - 1, index))
        if index != self.index:
            self.game.sound.play("menu_move")
        self.index = index
        self.follow_selection()

    def thumb_rect(self) -> pygame.Rect:
        if self.max_scroll <= 0:
            return self.BAR.copy()
        h = max(24, int(self.BAR.h * self.VIEW.h / self.content_h))
        y = self.BAR.y + int((self.BAR.h - h) * self.scroll / self.max_scroll)
        return pygame.Rect(self.BAR.x, y, self.BAR.w, h)

    def _drag_to(self, mouse_y):
        thumb = self.thumb_rect()
        free = self.BAR.h - thumb.h
        if free > 0:
            frac = (mouse_y - self.BAR.y - thumb.h / 2) / free
            self.scroll_to(frac * self.max_scroll)
            self.scroll = self.target

    def _row_rect(self, y):
        return pygame.Rect(self.VIEW.x + 4, self.VIEW.y + y - int(self.scroll), 402, self.ROW_H - 1)

    def level_at(self, pos):
        if not self.VIEW.collidepoint(pos):
            return None
        for kind, obj, y in self.rows:
            if kind == "level" and self._row_rect(y).collidepoint(pos):
                return obj
        return None

    def check_code(self, key) -> bool:
        """Track the secret code. Returns True when it was just completed."""
        self.code.append((key, self.index))
        # keep the longest tail that is still a valid start of the code
        while self.code and tuple(k for k, _ in self.code) != SECRET_CODE[:len(self.code)]:
            self.code.pop(0)
        if len(self.code) < len(SECRET_CODE):
            return False
        g = self.game
        start = self.code[0][1]
        self.code = []
        on = g.save.toggle_unlock_all()
        g.sound.play("stamp" if on else "undo")
        self.select(start)  # undo the cursor moves made while typing the code
        self.message = ("GEHEIME MACHTIGING: alle dossiers zijn vrijgegeven." if on else
                        "Machtiging ingetrokken: niet-afgeronde dossiers zijn weer in behandeling.")
        self.message_t = 3500
        self.message_ok = True
        return True

    def play_selected(self):
        g = self.game
        lv = self.levels[self.index]
        if not g.levels.is_unlocked(lv, g.save):
            g.sound.play("error")
            self.message = "Uw aanvraag is nog in behandeling. Voltooi eerst het vorige dossier."
            self.message_t = 2500
            self.message_ok = False
            return
        g.sound.play("menu_select")
        from .play import start_level
        start_level(g, lv)

    def handle_event(self, e):
        g = self.game
        n = len(self.levels)
        if e.type == pygame.KEYDOWN:
            if self.check_code(e.key):
                return
            if e.key == pygame.K_ESCAPE:
                g.sound.play("menu_move")
                g.pop()
            elif e.key in UP_KEYS:
                self.select((self.index - 1) % n)
            elif e.key in DOWN_KEYS:
                self.select((self.index + 1) % n)
            elif e.key in LEFT_KEYS:
                dept = self.levels[self.index].department
                prev = max(0, g.levels.departments.index(dept) - 1)
                self.select(g.levels.departments[prev].levels[0].index)
            elif e.key in RIGHT_KEYS:
                dept = self.levels[self.index].department
                nxt = min(len(g.levels.departments) - 1, g.levels.departments.index(dept) + 1)
                self.select(g.levels.departments[nxt].levels[0].index)
            elif e.key == pygame.K_PAGEUP:
                self.select(self.index - 10)
            elif e.key == pygame.K_PAGEDOWN:
                self.select(self.index + 10)
            elif e.key == pygame.K_HOME:
                self.select(0)
            elif e.key == pygame.K_END:
                self.select(n - 1)
            elif e.key in OK_KEYS:
                self.play_selected()
        elif e.type == pygame.MOUSEWHEEL:
            self.scroll_to(self.target - e.y * self.ROW_H * 3)
        elif e.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._drag_to(e.pos[1])
                return
            lv = self.level_at(e.pos)
            if lv is not None and lv.index != self.index:
                self.index = lv.index
                g.sound.play("menu_move")
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.BAR.inflate(10, 0).collidepoint(e.pos) and self.max_scroll > 0:
                self.dragging = True
                self._drag_to(e.pos[1])
                return
            lv = self.level_at(e.pos)
            if lv is not None:
                self.index = lv.index
                self.play_selected()
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.dragging = False

    def update(self, dt):
        if self.message_t > 0:
            self.message_t -= dt
        diff = self.target - self.scroll
        if abs(diff) < 0.5:
            self.scroll = self.target
        else:
            self.scroll += diff * min(1.0, dt / 70)

    def preview(self, lv):
        if lv.id in self.preview_cache:
            return self.preview_cache[lv.id]
        from .play import render_board_background, tile_sprite
        board = lv.make_board()
        t = next((t for t in (16, 12, 10, 8) if board.width * t <= 296 and board.height * t <= 156), 6)
        bg = render_board_background(self.game, board, t)
        for b in board.boxes:
            name = "box_done" if b in board.goals else "box"
            bg.blit(tile_sprite(self.game, name, t), (b[0] * t, b[1] * t))
        bg.blit(tile_sprite(self.game, "player_down_0", t), (board.player[0] * t, board.player[1] * t))
        self.preview_cache[lv.id] = (bg, len(board.boxes))
        return self.preview_cache[lv.id]

    def draw(self, surf):
        g = self.game
        f = g.fonts
        surf.blit(g.sprites.title_bg, (0, 0))
        ui.dither_overlay(surf, (0, 0, 20), 120)
        ui.dos_window(surf, f, (16, 16, 768, 568), "LEVEL SELECTEREN - DOSSIEROVERZICHT")
        save = g.save
        surf.set_clip(self.VIEW)
        top = int(self.scroll)
        for kind, obj, y in self.rows:
            if y - top > self.VIEW.h or y - top < -self.DEPT_H:
                continue
            if kind == "dept":
                ui.text(surf, f, f"AFDELING {obj.id}: {obj.name.upper()}",
                        (self.VIEW.x + 4, self.VIEW.y + y - top + 2), "normal", S.YELLOW)
                continue
            lv = obj
            r = self._row_rect(y)
            selected = lv.index == self.index
            unlocked = g.levels.is_unlocked(lv, save)
            done = save.best(lv.id)
            if selected:
                pygame.draw.rect(surf, S.LIGHT_BLUE, r)
            col = S.NAVY if selected else (S.WHITE if unlocked else S.MID_GREY)
            sh = None if selected else S.BLACK
            ui.text(surf, f, f"{lv.id}", (r.x + 8, r.y + 1), "small", col, shadow=sh)
            ui.text(surf, f, lv.name if unlocked else "? ? ? ? ?", (r.x + 46, r.y + 1), "small", col, shadow=sh)
            if done:
                status, scol = "GOEDGEKEURD", (S.GREEN if not selected else (20, 110, 30))
            elif unlocked:
                status, scol = "OPEN", (S.YELLOW if not selected else S.NAVY)
            else:
                status, scol = "IN BEHANDELING", (S.MID_GREY if not selected else S.DARK_GREY)
            ui.text(surf, f, status, (r.right - 8, r.y + 1), "small", scol, "right", shadow=sh)
        surf.set_clip(None)
        # thin line at an edge where more of the list is hidden
        if self.scroll > 1:
            pygame.draw.line(surf, S.LIGHT_BLUE, (self.VIEW.x + 4, self.VIEW.y), (self.VIEW.right - 4, self.VIEW.y))
        if self.scroll < self.max_scroll - 1:
            pygame.draw.line(surf, S.LIGHT_BLUE, (self.VIEW.x + 4, self.VIEW.bottom - 1),
                             (self.VIEW.right - 4, self.VIEW.bottom - 1))
        # scrollbar
        pygame.draw.rect(surf, S.NAVY, self.BAR)
        pygame.draw.rect(surf, S.MID_GREY, self.BAR, 1)
        thumb = self.thumb_rect()
        pygame.draw.rect(surf, S.YELLOW if self.dragging else S.LIGHT_BLUE, thumb)
        pygame.draw.rect(surf, S.WHITE, thumb, 1)
        # right panel
        lv = self.levels[self.index]
        px = 456
        pygame.draw.rect(surf, S.NAVY, (px, 56, 312, 470))
        pygame.draw.rect(surf, S.LIGHT_BLUE, (px, 56, 312, 470), 1)
        unlocked = g.levels.is_unlocked(lv, save)
        ui.text(surf, f, f"DOSSIER {lv.id}", (px + 156, 66), "normal", S.YELLOW, "center")
        ui.text(surf, f, lv.name if unlocked else "Vertrouwelijk", (px + 156, 88), "normal", S.WHITE, "center")
        ui.text(surf, f, f"Afdeling {lv.department.name}", (px + 156, 110), "small", S.LIGHT_BLUE, "center")
        if unlocked:
            img, nboxes = self.preview(lv)
            frame = img.get_rect(center=(px + 156, 210))
            surf.blit(img, frame)
            pygame.draw.rect(surf, S.LIGHT_BLUE, frame.inflate(6, 6), 1)
            yy = 300
            for line in f.wrap(lv.note, 280, "small"):
                ui.text(surf, f, line, (px + 156, yy), "small", S.WHITE, "center")
                yy += 18
            yy += 8
            ui.text(surf, f, f"Dossiers: {nboxes}", (px + 156, yy), "small", S.GREY, "center")
            best = save.best(lv.id)
            yy += 26
            if best:
                surf.blit(g.sprites["icon_ok"], (px + 30, yy - 4))
                ui.text(surf, f, f"Beste: {best['moves']} zetten, {best['pushes']} duwen",
                        (px + 70, yy + 4), "small", S.GREEN)
            else:
                surf.blit(g.sprites["icon_clock"], (px + 30, yy - 4))
                ui.text(surf, f, "Nog niet behandeld", (px + 70, yy + 4), "small", S.YELLOW)
        else:
            surf.blit(g.sprites["icon_warn"], g.sprites["icon_warn"].get_rect(center=(px + 156, 220)))
            for i, line in enumerate(["Dit dossier is nog niet vrijgegeven.",
                                      "Voltooi eerst het vorige dossier."]):
                ui.text(surf, f, line, (px + 156, 260 + i * 20), "small", S.GREY, "center")
        if save.unlock_all:
            ui.text(surf, f, "GEHEIME MACHTIGING ACTIEF", (px + 156, 426), "small", S.YELLOW, "center")
        done = len(save.completed)
        total = len(self.levels)
        ui.text(surf, f, f"Voltooid: {done} van {total}", (px + 156, 450), "normal", S.YELLOW, "center")
        ui.progress_bar(surf, (px + 26, 474, 260, 22), done / total, fg=S.GREEN)
        foot = self.message if self.message_t > 0 else \
            "Op/neer: dossier  Links/rechts: afdeling  PgUp/PgDn: 10  Wiel: scrollen  ENTER: openen"
        col = (S.YELLOW if self.message_ok else S.RED) if self.message_t > 0 else S.LIGHT_BLUE
        ui.text(surf, f, foot, (400, 556), "small", col, "center")


class DepartmentIntroScene(Scene):
    def presence(self):
        d = self.level.department
        return (f"Afdeling {d.id}: {d.name}", "Meldt zich bij de balie")

    """Title card shown when entering a new afdeling."""

    def __init__(self, game, level, then: Callable[[], None]):
        super().__init__(game)
        self.level = level
        self.then = then
        self.t = 0.0
        self.done = False

    def handle_event(self, e):
        if self.t > 400 and e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.finish()

    def finish(self):
        if not self.done:
            self.done = True
            self.game.sound.play("menu_select")
            self.then()

    def update(self, dt):
        self.t += dt
        if self.t > 3800:
            self.finish()

    def draw(self, surf):
        g = self.game
        f = g.fonts
        dept = self.level.department
        surf.fill(S.NAVY)
        for y in range(0, S.SCREEN_H, 4):
            pygame.draw.line(surf, S.RIJKSBLAUW, (0, y), (S.SCREEN_W, y))
        reveal = min(1.0, self.t / 500)
        w = int(560 * reveal)
        r = pygame.Rect(0, 0, max(8, w), 230)
        r.center = (400, 290)
        ui.dos_window(surf, f, r, "")
        if reveal >= 1.0:
            ui.text(surf, f, f"AFDELING {dept.id}", (400, 200), "large", S.LIGHT_BLUE, "center")
            ui.text(surf, f, dept.name.upper(), (400, 232), "large", S.YELLOW, "center",
                    shadow=S.BLACK, scale=1 if len(dept.name) > 18 else 2)
            ui.text(surf, f, f'"{dept.motto}"', (400, 300), "small", S.WHITE, "center")
            ui.text(surf, f, f"{len(dept.levels)} dossiers liggen klaar voor behandeling.",
                    (400, 330), "small", S.LIGHT_BLUE, "center")
            if (g.time // 450) % 2 == 0:
                ui.text(surf, f, "Druk op een toets om plaats te nemen", (400, 362),
                        "small", S.GREY, "center")
