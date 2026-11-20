"""Main loop and scene management."""
from __future__ import annotations

import random
import sys
import time
import traceback
from typing import List, Optional

import pygame

from . import settings as S
from .discord_rpc import DiscordPresence
from .level import LevelPack
from .resources import resource_path, user_data_dir
from .savegame import SaveGame
from .sound import SoundManager
from .ui import Fonts, Sprites


class Scene:
    """Base class. Opaque scenes hide everything below them on the stack."""

    opaque = True

    def __init__(self, game: "Game"):
        self.game = game

    def on_enter(self):
        pass

    def handle_event(self, event: pygame.event.Event):
        pass

    def update(self, dt: float):
        pass

    def draw(self, surf: pygame.Surface):
        pass

    def presence(self) -> Optional[tuple]:
        """Discord status as (details, state[, start_timestamp]).

        None means: use whatever the scene below this one shows.
        """
        return None


class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption(f"{S.TITLE} - {S.ORGANISATION}")
        try:
            icon = pygame.image.load(resource_path("assets", "sprites", "logo.png"))
            pygame.display.set_icon(icon)
        except (pygame.error, FileNotFoundError):
            pass
        self.save = SaveGame()
        flags = pygame.SCALED
        self.screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H), flags)
        if self.save.settings.get("fullscreen"):
            self._toggle_fullscreen_raw()
        self.canvas = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()
        self.sprites = Sprites()
        self.levels = LevelPack()
        self.save.upgrade(self.levels.legacy_map())
        self.sound = SoundManager(self.save.settings)
        self.scenes: List[Scene] = []
        self.running = True
        self.time = 0.0
        self._shake_time = 0.0
        self._shake_power = 0
        self.started = int(time.time())
        self.discord = DiscordPresence(
            S.DISCORD_CLIENT_ID, enabled=lambda: self.save.settings.get("discord", True))

    # ------------------------------------------------------------- scenes
    def push(self, scene: Scene):
        self.scenes.append(scene)
        scene.on_enter()

    def pop(self) -> Optional[Scene]:
        scene = self.scenes.pop() if self.scenes else None
        if self.scenes:
            self.scenes[-1].on_enter()
        return scene

    def replace(self, scene: Scene):
        if self.scenes:
            self.scenes.pop()
        self.push(scene)

    def reset_to(self, scene: Scene):
        self.scenes.clear()
        self.push(scene)

    @property
    def top(self) -> Optional[Scene]:
        return self.scenes[-1] if self.scenes else None

    # ------------------------------------------------------------- effects
    def shake(self, power: int = 4, duration: float = 180):
        self._shake_power = power
        self._shake_time = duration

    def toggle_fullscreen(self):
        self._toggle_fullscreen_raw()
        self.save.settings["fullscreen"] = not self.save.settings["fullscreen"]
        self.save.save()

    def _toggle_fullscreen_raw(self):
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass

    def quit(self):
        self.save.save()
        self.running = False

    # ------------------------------------------------------------- discord
    def presence_activity(self) -> Optional[dict]:
        info = None
        for scene in reversed(self.scenes):
            info = scene.presence()
            if info:
                break
        if not info:
            return None
        details, state = info[0], info[1]
        start = info[2] if len(info) > 2 and info[2] else self.started
        assets = {"large_text": f"{S.TITLE} - {S.SUBTITLE}"}
        if S.DISCORD_LARGE_IMAGE:
            assets["large_image"] = S.DISCORD_LARGE_IMAGE
        return {
            "details": details[:128],
            "state": state[:128],
            "timestamps": {"start": int(start)},
            "assets": assets,
        }

    # ------------------------------------------------------------- loop
    def run(self):
        from .menu import LoadingScene
        self.push(LoadingScene(self))
        while self.running and self.scenes:
            dt = self.clock.tick(S.FPS)
            dt = min(dt, 50)
            self.time += dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                    break
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    continue
                if self.top:
                    self.top.handle_event(event)
            if not self.running or not self.scenes:
                break
            self.top.update(dt)
            self._draw(dt)
            self.discord.set(self.presence_activity())
        self.discord.close()
        pygame.quit()

    def _draw(self, dt):
        # draw from the last opaque scene upwards
        start = 0
        for i in range(len(self.scenes) - 1, -1, -1):
            if self.scenes[i].opaque:
                start = i
                break
        for scene in self.scenes[start:]:
            scene.draw(self.canvas)
        ox = oy = 0
        if self._shake_time > 0:
            self._shake_time -= dt
            ox = random.randint(-self._shake_power, self._shake_power)
            oy = random.randint(-self._shake_power, self._shake_power)
        self.screen.fill(S.BLACK)
        self.screen.blit(self.canvas, (ox, oy))
        pygame.display.flip()


def main():
    try:
        Game().run()
    except Exception:  # pragma: no cover - last resort error report
        log = traceback.format_exc()
        try:
            import os
            path = os.path.join(user_data_dir(), "foutrapport.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(log)
        except OSError:
            path = None
        print(log, file=sys.stderr)
        try:
            import ctypes
            msg = "Er is een onverwachte fout opgetreden.\n\nUw aanvraag kon niet worden verwerkt."
            if path:
                msg += f"\n\nFoutrapport: {path}"
            ctypes.windll.user32.MessageBoxW(None, msg, S.TITLE, 0x10)
        except Exception:
            pass
        sys.exit(1)
