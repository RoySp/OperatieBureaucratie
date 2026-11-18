"""Sound effects and music with graceful fallback when no audio device exists."""
from __future__ import annotations

import os
import random
from typing import Dict, Optional

import pygame

from .resources import resource_path

EFFECTS = ["step", "step2", "push", "goal", "error", "menu_move", "menu_select",
           "undo", "restart", "stamp", "complete"]


class SoundManager:
    def __init__(self, settings: dict):
        self.settings = settings
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.available = False
        self.current_music: Optional[str] = None
        self._step_toggle = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.available = True
        except pygame.error:
            self.available = False
            return
        for name in EFFECTS:
            path = resource_path("assets", "sounds", name + ".wav")
            try:
                self.sounds[name] = pygame.mixer.Sound(path)
            except (pygame.error, FileNotFoundError):
                pass
        self.apply_volume()

    def apply_volume(self) -> None:
        if not self.available:
            return
        vol = self.settings["sfx_volume"] if self.settings["sound"] else 0.0
        for snd in self.sounds.values():
            snd.set_volume(vol)
        mvol = self.settings["music_volume"] if self.settings["music"] else 0.0
        try:
            pygame.mixer.music.set_volume(mvol)
        except pygame.error:
            pass
        if self.settings["music"] and self.current_music and not pygame.mixer.music.get_busy():
            name, self.current_music = self.current_music, None
            self.play_music(name)

    def play(self, name: str) -> None:
        if not self.available or not self.settings["sound"]:
            return
        if name == "step":
            self._step_toggle = not self._step_toggle
            name = "step2" if self._step_toggle else "step"
        snd = self.sounds.get(name)
        if snd:
            snd.play()

    def play_music(self, name: str) -> None:
        if not self.available:
            return
        if self.current_music == name and pygame.mixer.music.get_busy():
            return
        self.current_music = name
        if not self.settings["music"]:
            pygame.mixer.music.stop()
            return
        path = resource_path("assets", "sounds", name + ".wav")
        if not os.path.exists(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.settings["music_volume"])
            pygame.mixer.music.play(-1, fade_ms=600)
        except pygame.error:
            pass

    def stop_music(self) -> None:
        if self.available:
            pygame.mixer.music.fadeout(300)
        self.current_music = None

    @staticmethod
    def pick(lines):
        return random.choice(lines)
