"""Gameplay: board rendering, input handling, pause, victory and ending."""
from __future__ import annotations

import random
import time
from typing import Dict, List, Optional

import pygame

from . import settings as S
from . import ui
from .board import DOWN, LEFT, RIGHT, UP, Board
from .engine import Scene
from .level import Level
from .menu import (OK_KEYS, DepartmentIntroScene, LevelSelectScene, MenuItem, MenuList,
                   OptionsScene, TitleScene)
from .player import BoxSprites, PlayerSprite

KEY_DIRS = {
    pygame.K_UP: UP, pygame.K_w: UP,
    pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
    pygame.K_LEFT: LEFT, pygame.K_a: LEFT,
    pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT,
}

_TILE_CACHE: Dict[tuple, pygame.Surface] = {}


def tile_sprite(game, name: str, size: int) -> pygame.Surface:
    """Pixel-perfect sprite at 16, 32, 48 or 64 px (art is 16px native)."""
    key = (name, size)
    surf = _TILE_CACHE.get(key)
    if surf is None:
        src = game.sprites[name]
        if src.get_width() == size:
            surf = src
        else:
            native = pygame.transform.scale(src, (16, 16))
            surf = pygame.transform.scale(native, (size, size))
        _TILE_CACHE[key] = surf
    return surf


def render_board_background(game, board: Board, t: int) -> pygame.Surface:
    """Static layer: void, floor, walls, archive spots and furniture."""
    surf = pygame.Surface((board.width * t, board.height * t), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    interior = board.interior()
    floor_cells = set(interior) | set(board.furniture)
    for y in range(board.height):
        for x in range(board.width):
            p = (x, y)
            pos = (x * t, y * t)
            if p in board.walls:
                near = any((x + dx, y + dy) in floor_cells
                           for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                if not near:
                    continue
                below = (x, y + 1)
                name = "wall_front" if below in floor_cells else "wall_top"
                surf.blit(tile_sprite(game, name, t), pos)
            elif p in floor_cells:
                surf.blit(tile_sprite(game, "floor_a" if (x + y) % 2 == 0 else "floor_b", t), pos)
                if p in board.goals:
                    surf.blit(tile_sprite(game, "goal", t), pos)
                if p in board.furniture:
                    surf.blit(tile_sprite(game, "shadow", t), pos)
                    surf.blit(tile_sprite(game, board.furniture[p], t), pos)
    return surf


def start_level(game, level: Level, show_intro: Optional[bool] = None):
    """Open a level, showing the department title card when appropriate."""
    previous = game.levels.by_id(game.save.last_level)
    game.save.last_level = level.id
    game.save.save()
    if show_intro is None:
        first_of_dept = level.department.levels[0] is level
        show_intro = first_of_dept or previous is None or previous.department is not level.department

    def go():
        game.reset_to(PlayScene(game, level))

    if show_intro:
        game.sound.play_music("music_menu")
        game.reset_to(DepartmentIntroScene(game, level, go))
    else:
        go()


class FloatText:
    def __init__(self, text, x, y, color):
        self.text, self.x, self.y, self.color = text, x, y, color
        self.t = 0.0


class PlayScene(Scene):
    def __init__(self, game, level: Level):
        super().__init__(game)
        self.level = level
        self.board = level.make_board()
        free_w, free_h = S.SCREEN_W - 20, S.PLAY_RECT[3] - 16
        self.tile = 32
        for size in (64, 48):
            if self.board.width * size <= free_w and self.board.height * size <= free_h:
                self.tile = size
                break
        self.background = render_board_background(game, self.board, self.tile)
        bw, bh = self.background.get_size()
        self.origin = ((S.SCREEN_W - bw) // 2, S.HUD_H + (S.PLAY_RECT[3] - bh) // 2)
        self.player = PlayerSprite(self.board.player)
        self.boxes = BoxSprites(self.board.boxes)
        self.held: List[tuple] = []
        self.buffer: Optional[tuple] = None
        self.repeat_timer = 0.0
        self.error_cooldown = 0.0
        self.floats: List[FloatText] = []
        self.message = level.note
        self.message_icon = "icon_info"
        self.message_age = 0.0
        self.win_timer: Optional[float] = None
        self.flash = 0.0
        self.rejected = 0.0   # AFGEWEZEN stamp after a restart
        self.void_tile = tile_sprite(game, "void", 32)
        self.started = time.time()       # Discord "elapsed" timer for this level
        self.last_step = -1e9            # game.time of the last walk step
        self.last_push = -1e9            # game.time of the last push

    def on_enter(self):
        self.game.sound.play_music("music_game")
        self.held.clear()
        self.buffer = None

    # ------------------------------------------------------------ messages
    def say(self, text, icon="icon_info"):
        self.message = text
        self.message_icon = icon
        self.message_age = 0.0

    def float_text(self, text, cell, color=S.GREEN):
        x = self.origin[0] + cell[0] * self.tile + self.tile // 2
        y = self.origin[1] + cell[1] * self.tile
        self.floats.append(FloatText(text, x, y, color))

    # ------------------------------------------------------------- actions
    @property
    def locked(self) -> bool:
        return self.win_timer is not None

    def try_move(self, direction):
        if self.locked:
            return
        g = self.game
        old = self.board.player
        res = self.board.move(direction)
        if not res.moved:
            self.player.turn(direction)
            if self.error_cooldown <= 0:
                g.sound.play("error")
                self.error_cooldown = 350
                if res.blocked_by == "box":
                    self.say(random.choice(S.MSG_BLOCKED_BOX), "icon_warn")
                elif res.blocked_by == "furniture":
                    self.say(random.choice(S.MSG_FURNITURE), "icon_warn")
                else:
                    self.say(random.choice(S.MSG_WALL), "icon_warn")
            return
        self.player.move(old, self.board.player, direction)
        self.last_step = g.time
        if res.pushed:
            self.last_push = g.time
            self.boxes.move(res.box_from, res.box_to)
            g.sound.play("push")
            if res.box_on_goal:
                g.sound.play("goal")
                self.float_text("GEARCHIVEERD", res.box_to)
                if not res.solved:
                    self.say(random.choice(S.MSG_GOAL), "icon_ok")
            elif self.board.is_dead_box(res.box_to):
                self.say(random.choice(S.MSG_DEADLOCK), "icon_warn")
                self.float_text("KLEM!", res.box_to, S.RED)
        else:
            g.sound.play("step")
        if res.solved:
            self.win_timer = 420
            self.say(random.choice(S.WIN_LINES), "icon_ok")

    def undo(self):
        if self.locked:
            return
        entry = self.board.undo()
        if entry is None:
            self.game.sound.play("error")
            self.say("Er valt niets te herroepen.", "icon_warn")
            return
        current = self.player.tween.end
        self.player.move(current, self.board.player, entry.facing)
        if entry.box_from is not None:
            self.boxes.move(entry.box_to, entry.box_from)
        self.game.sound.play("undo")
        self.say(random.choice(S.MSG_UNDO), "icon_clock")

    def restart(self):
        if self.locked:
            return
        if self.board.moves == 0:
            return
        self.board.reset()
        self.player.snap(self.board.player)
        self.boxes.reset(self.board.boxes)
        self.game.sound.play("restart")
        self.game.sound.play("stamp")
        self.flash = 220
        self.rejected = 900
        self.say(random.choice(S.MSG_RESTART), "icon_clock")

    # ------------------------------------------------------------- discord
    @property
    def presence_details(self) -> str:
        return f"Dossier {self.level.id}: {self.level.name}"

    def presence_progress(self) -> str:
        b = self.board
        return f"{len(b.boxes & b.goals)}/{len(b.goals)} gearchiveerd"

    def activity(self) -> str:
        """'pushing', 'walking' or 'thinking', based on the last few seconds."""
        now = self.game.time
        if now - self.last_push < S.DISCORD_PUSH_WINDOW:
            return "pushing"
        if now - self.last_step < S.DISCORD_WALK_WINDOW:
            return "walking"
        return "thinking"

    def presence(self):
        state = {
            "pushing": "Duwt een dossier",
            "walking": "Loopt door de gang",
            "thinking": "Denkt na...",
        }[self.activity()]
        return (self.presence_details, f"{state} ({self.presence_progress()})", self.started)

    # -------------------------------------------------------------- events
    def handle_event(self, e):
        g = self.game
        if e.type == pygame.KEYDOWN:
            if e.key in KEY_DIRS:
                d = KEY_DIRS[e.key]
                if d in self.held:
                    self.held.remove(d)
                self.held.append(d)
                self.buffer = d
                self.repeat_timer = S.KEY_REPEAT_DELAY
            elif e.key in (pygame.K_z, pygame.K_BACKSPACE, pygame.K_u):
                self.undo()
            elif e.key == pygame.K_r:
                self.restart()
            elif e.key in (pygame.K_ESCAPE, pygame.K_p):
                if not self.locked:
                    g.sound.play("menu_select")
                    g.push(PauseScene(g, self))
            elif e.key == pygame.K_m:
                st = g.save.settings
                st["music"] = not st["music"]
                if st["music"]:
                    g.sound.current_music = None
                    g.sound.play_music("music_game")
                g.sound.apply_volume()
                g.save.save()
                self.say("Wachtmuziek " + ("aan." if st["music"] else "uit. Heerlijk stil."))
        elif e.type == pygame.KEYUP and e.key in KEY_DIRS:
            d = KEY_DIRS[e.key]
            # another key may map to the same direction (arrow + WASD)
            still = any(pygame.key.get_pressed()[k] for k, v in KEY_DIRS.items() if v == d)
            if d in self.held and not still:
                self.held.remove(d)

    def update(self, dt):
        self.player.update(dt)
        self.boxes.update(dt)
        self.error_cooldown -= dt
        self.message_age += dt
        if self.flash > 0:
            self.flash -= dt
        if self.rejected > 0:
            self.rejected -= dt
        for ft in self.floats:
            ft.t += dt
        self.floats = [ft for ft in self.floats if ft.t < 1100]
        if self.message_age > 14000:
            self.say(random.choice(S.MSG_IDLE), "icon_clock")

        if self.win_timer is not None:
            self.win_timer -= dt
            if self.win_timer <= 0 and self.player.tween.done:
                self.win_timer = 0
                self.finish_level()
            return

        if self.player.tween.done:
            if self.buffer is not None:
                d, self.buffer = self.buffer, None
                self.try_move(d)
            elif self.held:
                self.repeat_timer -= dt
                if self.repeat_timer <= 0:
                    self.repeat_timer = S.KEY_REPEAT_RATE
                    self.try_move(self.held[-1])
        else:
            self.repeat_timer -= dt

    def finish_level(self):
        g = self.game
        prev = g.save.best(self.level.id)
        new_best = g.save.record(self.level.id, self.board.moves, self.board.pushes)
        g.push(VictoryScene(g, self, prev, new_best))
        self.win_timer = None
        self.held.clear()

    # ---------------------------------------------------------------- draw
    def draw(self, surf):
        g = self.game
        f = g.fonts
        # background tiles
        for y in range(S.HUD_H, S.SCREEN_H - S.STATUS_H, 32):
            for x in range(0, S.SCREEN_W, 32):
                surf.blit(self.void_tile, (x, y))
        ox, oy = self.origin
        t = self.tile
        surf.blit(self.background, (ox, oy))
        # boxes
        for cell, tw in sorted(self.boxes.items(), key=lambda kv: kv[1].pos[1]):
            bx, by = tw.pos
            done = tw.done and cell in self.board.goals
            surf.blit(tile_sprite(g, "shadow", t), (ox + bx * t, oy + by * t))
            surf.blit(tile_sprite(g, "box_done" if done else "box", t), (ox + bx * t, oy + by * t))
        # player
        px, py = self.player.tween.pos
        bob = self.player.bob * (t // 16)
        surf.blit(tile_sprite(g, "shadow", t), (ox + px * t, oy + py * t))
        surf.blit(tile_sprite(g, self.player.frame, t), (ox + px * t, oy + py * t + bob))
        # floating texts
        for ft in self.floats:
            k = ft.t / 1100
            ui.text(surf, f, ft.text, (ft.x, ft.y - 6 - int(k * 34)), "small", ft.color, "center")
        if self.flash > 0:
            ui.dither_overlay(surf, (255, 255, 255), int(140 * self.flash / 220))
        if self.rejected > 0:
            k = min(1.0, (900 - self.rejected) / 120)
            img = pygame.transform.rotozoom(g.sprites["stamp_no"], -9, 2.2 - 1.2 * k)
            img.set_alpha(int(255 * min(1.0, self.rejected / 300)))
            surf.blit(img, img.get_rect(center=(S.SCREEN_W // 2, S.HUD_H + S.PLAY_RECT[3] // 2)))
        self.draw_hud(surf)

    def draw_hud(self, surf):
        g = self.game
        f = g.fonts
        b = self.board
        # top bar
        pygame.draw.rect(surf, S.NAVY, (0, 0, S.SCREEN_W, S.HUD_H))
        pygame.draw.line(surf, S.LIGHT_BLUE, (0, S.HUD_H - 2), (S.SCREEN_W, S.HUD_H - 2), 2)
        surf.blit(g.sprites["logo"], (6, 4))
        ui.text(surf, f, S.ORG_SHORT, (44, 4), "normal", S.YELLOW)
        ui.text(surf, f, f"Afd. {self.level.department.name}", (44, 22), "small", S.LIGHT_BLUE)
        ui.text(surf, f, f"DOSSIER {self.level.id}", (400, 3), "small", S.LIGHT_BLUE, "center")
        ui.text(surf, f, self.level.name, (400, 18), "normal", S.WHITE, "center")
        ui.text(surf, f, f"ZETTEN {b.moves:04d}", (790, 4), "small", S.YELLOW, "right")
        ui.text(surf, f, f"DUWEN {b.pushes:04d}", (790, 21), "small", S.YELLOW, "right")
        arch = f"{b.boxes_on_goals}/{len(b.goals)}"
        surf.blit(g.sprites["icon_ok"] if b.is_solved else g.sprites["box"], (612, 4))
        ui.text(surf, f, arch, (648, 12), "normal", S.WHITE)
        # status bar
        y0 = S.SCREEN_H - S.STATUS_H
        pygame.draw.rect(surf, S.GREY, (0, y0, S.SCREEN_W, S.STATUS_H))
        pygame.draw.line(surf, S.WHITE, (0, y0), (S.SCREEN_W, y0))
        icon = pygame.transform.scale(g.sprites[self.message_icon], (24, 24))
        surf.blit(icon, (4, y0 + 2))
        shown = self.message
        if self.message_age < 600:  # typewriter effect
            shown = self.message[: int(len(self.message) * self.message_age / 600)]
        ui.text(surf, f, shown, (34, y0 + 6), "small", S.NAVY, shadow=None)
        ui.text(surf, f, "Z: terug  R: opnieuw  ESC: pauze", (794, y0 + 6), "small",
                S.DARK_GREY, "right", shadow=None)


class PauseScene(Scene):
    def presence(self):
        return (self.play.presence_details, f"Koffiepauze ({self.play.presence_progress()})",
                self.play.started)

    opaque = False

    def __init__(self, game, play: PlayScene):
        super().__init__(game)
        self.play = play
        g = game
        items = [
            MenuItem("Hervatten", self.resume),
            MenuItem("Opnieuw beginnen", self.restart),
            MenuItem("Opties", lambda: g.push(OptionsScene(g))),
            MenuItem("Level selecteren", lambda: g.push(LevelSelectScene(g, from_pause=True))),
            MenuItem("Hoofdmenu", lambda: g.reset_to(TitleScene(g))),
        ]
        self.rect = pygame.Rect(230, 150, 340, 290)
        self.menu = MenuList(game, items, (self.rect.x + 30, self.rect.y + 70, self.rect.w - 60, 0),
                             item_h=38)

    def resume(self):
        self.game.pop()

    def restart(self):
        self.game.pop()
        self.play.restart()

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_p):
            self.game.sound.play("menu_move")
            self.resume()
            return
        self.menu.handle_event(e)

    def draw(self, surf):
        f = self.game.fonts
        ui.dither_overlay(surf, (0, 0, 20), 150)
        ui.dos_window(surf, f, self.rect, "PAUZE")
        ui.text(surf, f, "Uw aanvraag ligt even stil.", (self.rect.centerx, self.rect.y + 30),
                "normal", S.YELLOW, "center")
        self.menu.draw(surf)


class VictoryScene(Scene):
    def presence(self):
        return (self.play.presence_details, "Dossier goedgekeurd!", self.play.started)

    """An official 'beschikking' with a big GOEDGEKEURD stamp."""

    opaque = False
    STAMP_AT = 650

    def __init__(self, game, play: PlayScene, prev_best, new_best):
        super().__init__(game)
        self.play = play
        self.level = play.level
        self.moves = play.board.moves
        self.pushes = play.board.pushes
        self.prev_best = prev_best
        self.new_best = new_best and prev_best is not None
        self.first_time = prev_best is None
        self.t = 0.0
        self.stamped = False
        self.line = random.choice(S.WIN_LINES)
        self.next_level = game.levels.next_level(self.level)
        self.rect = pygame.Rect(150, 70, 500, 440)
        self.angle = random.choice((-12, -9, 8, 11))

    def on_enter(self):
        self.game.sound.stop_music()
        self.game.sound.play("complete")

    def handle_event(self, e):
        g = self.game
        if self.t < self.STAMP_AT + 200:
            return
        if e.type == pygame.KEYDOWN:
            if e.key in OK_KEYS or e.key == pygame.K_n:
                self.advance()
            elif e.key == pygame.K_r:
                g.sound.play("menu_select")
                g.reset_to(PlayScene(g, self.level))
            elif e.key == pygame.K_l:
                g.sound.play("menu_select")
                g.reset_to(TitleScene(g))
                g.push(LevelSelectScene(g))
            elif e.key == pygame.K_ESCAPE:
                g.sound.play("menu_move")
                g.reset_to(TitleScene(g))
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.advance()

    def advance(self):
        g = self.game
        g.sound.play("menu_select")
        if self.next_level is None:
            g.reset_to(EndingScene(g))
        else:
            start_level(g, self.next_level)

    def update(self, dt):
        self.t += dt
        if not self.stamped and self.t >= self.STAMP_AT + 140:
            self.stamped = True
            self.game.sound.play("stamp")
            self.game.shake(5, 200)

    def draw(self, surf):
        g = self.game
        f = g.fonts
        ui.dither_overlay(surf, (0, 0, 20), 140)
        r = self.rect
        slide = max(0.0, 1 - self.t / 300)
        r = r.move(0, int(slide * 420))
        shadow = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 120))
        surf.blit(shadow, (r.x + 10, r.y + 10))
        pygame.draw.rect(surf, (250, 250, 244), r)
        pygame.draw.rect(surf, S.RIJKSBLAUW, (r.x, r.y, r.w, 54))
        surf.blit(g.sprites["logo"], (r.x + 12, r.y + 10))
        ui.text(surf, f, S.ORGANISATION, (r.x + 52, r.y + 8), "normal", S.WHITE, shadow=None)
        ui.text(surf, f, "Directie Dossierverplaatsing - Afdeling " + self.level.department.name,
                (r.x + 52, r.y + 30), "small", S.LIGHT_BLUE, shadow=None)
        ink = (30, 34, 60)
        y = r.y + 72
        ui.text(surf, f, "BESCHIKKING", (r.x + 30, y), "large", S.RIJKSBLAUW, shadow=None)
        ui.text(surf, f, f"Kenmerk: OB/{self.level.id}/{1993 + self.level.index}", (r.right - 30, y + 6),
                "small", S.MID_GREY, "right", shadow=None)
        y += 40
        ui.text(surf, f, f"Betreft: dossier {self.level.id}, \"{self.level.name}\"", (r.x + 30, y),
                "small", ink, shadow=None)
        y += 30
        for line in f.wrap(self.line + " Hierbij delen wij u mede dat uw werkzaamheden "
                           "naar behoren zijn uitgevoerd.", r.w - 60, "small"):
            ui.text(surf, f, line, (r.x + 30, y), "small", ink, shadow=None)
            y += 18
        y += 14
        ui.text(surf, f, f"Aantal zetten:  {self.moves}", (r.x + 30, y), "normal", ink, shadow=None)
        ui.text(surf, f, f"Aantal duwen:  {self.pushes}", (r.x + 260, y), "normal", ink, shadow=None)
        y += 26
        if self.first_time:
            ui.text(surf, f, "Eerste goedkeuring voor dit dossier!", (r.x + 30, y), "small",
                    (20, 120, 40), shadow=None)
        elif self.new_best:
            ui.text(surf, f, f"NIEUW RECORD! Vorig record: {self.prev_best['moves']} zetten.",
                    (r.x + 30, y), "small", S.RED, shadow=None)
        else:
            best = g.save.best(self.level.id)
            ui.text(surf, f, f"Uw record blijft: {best['moves']} zetten, {best['pushes']} duwen.",
                    (r.x + 30, y), "small", S.MID_GREY, shadow=None)
        y += 34
        ui.text(surf, f, "Hoogachtend,", (r.x + 30, y), "small", ink, shadow=None)
        ui.text(surf, f, "De Directeur-Generaal (i.o.)", (r.x + 30, y + 40), "small", ink, shadow=None)
        pygame.draw.line(surf, ink, (r.x + 30, y + 36), (r.x + 200, y + 30), 1)
        # options
        if self.t > self.STAMP_AT + 200:
            yb = r.bottom - 36
            pygame.draw.line(surf, S.GREY, (r.x + 20, yb - 8), (r.right - 20, yb - 8))
            nxt = "ENTER: volgend dossier" if self.next_level else "ENTER: afronden"
            ui.text(surf, f, f"{nxt}    R: opnieuw    L: levels    ESC: menu", (r.centerx, yb),
                    "small", S.RIJKSBLAUW, "center", shadow=None)
        # stamp
        if self.t >= self.STAMP_AT:
            k = min(1.0, (self.t - self.STAMP_AT) / 140)
            scale = 2.6 - 1.6 * k
            stamp = g.sprites["stamp_ok"]
            img = pygame.transform.rotozoom(stamp, self.angle, scale * 0.9)
            if k < 1:
                img.set_alpha(int(255 * k))
            surf.blit(img, img.get_rect(center=(r.right - 150, r.y + 300)))


class EndingScene(Scene):
    def presence(self):
        return ("Alle dossiers gearchiveerd", "Gepromoveerd!")

    LINES = [
        "De procedure is succesvol afgerond.",
        "",
        "Alle dossiers zijn gearchiveerd. Alle loketten zijn gesloten.",
        "Het Archief is vol. Er wordt een nieuw archief aangevraagd.",
        "",
        "Wegens uitzonderlijke prestaties bent u bevorderd tot",
        "SENIOR BELEIDSMEDEWERKER DOSSIERVERPLAATSING",
        "(schaal 11, trede 3, met terugwerkende kracht)",
        "",
        "Uw bevordering wordt binnen 8 weken verwerkt.",
        "Bezwaar kan worden ingediend tot en met gisteren.",
    ]

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0

    def on_enter(self):
        self.game.sound.play_music("music_menu")

    def handle_event(self, e):
        if self.t > 1500 and (e.type == pygame.KEYDOWN or e.type == pygame.MOUSEBUTTONDOWN):
            self.game.sound.play("menu_select")
            self.game.reset_to(TitleScene(self.game))

    def update(self, dt):
        prev = self.t
        self.t += dt
        if prev < 900 <= self.t:
            self.game.sound.play("stamp")
            self.game.shake(6, 260)

    def draw(self, surf):
        g = self.game
        f = g.fonts
        surf.blit(g.sprites.title_bg, (0, 0))
        ui.dither_overlay(surf, (0, 0, 20), 120)
        ui.dos_window(surf, f, (60, 40, 680, 520), "EINDBESCHIKKING")
        ui.text(surf, f, "GEFELICITEERD!", (400, 76), "large", S.YELLOW, "center", scale=2)
        shown = int(self.t / 160)
        for i, line in enumerate(self.LINES[:shown]):
            color = S.YELLOW if line.isupper() else S.WHITE
            ui.text(surf, f, line, (400, 150 + i * 24), "normal", color, "center")
        total_moves = sum(v.get("moves", 0) for v in g.save.completed.values())
        total_pushes = sum(v.get("pushes", 0) for v in g.save.completed.values())
        ui.text(surf, f, f"Totaal beste zetten: {total_moves}   Totaal beste duwen: {total_pushes}",
                (400, 416), "small", S.LIGHT_BLUE, "center")
        if self.t > 900:
            k = min(1.0, (self.t - 900) / 140)
            img = pygame.transform.rotozoom(g.sprites["stamp_ok"], 8, 2.4 - 1.4 * k)
            surf.blit(img, img.get_rect(center=(400, 486)))
        if self.t > 1500 and (g.time // 500) % 2 == 0:
            ui.text(surf, f, "Druk op een toets om terug te keren naar het hoofdmenu", (400, 532),
                    "small", S.GREY, "center")
