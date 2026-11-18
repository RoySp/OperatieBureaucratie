"""Retro UI helpers: fonts, sprites and DOS / Windows 3.1 style panels."""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import pygame

from . import settings as S
from .resources import resource_path

Color = Tuple[int, int, int]


class Fonts:
    """Non-antialiased fonts give crisp pixel text; 'title' is upscaled 2x."""

    def __init__(self):
        path = resource_path("assets", "fonts", "freesansbold.ttf")
        if not os.path.exists(path):
            path = None  # pygame default font as fallback
        self.small = pygame.font.Font(path, 13)
        self.normal = pygame.font.Font(path, 16)
        self.large = pygame.font.Font(path, 22)
        self.huge_src = pygame.font.Font(path, 22)
        self._cache: Dict[tuple, pygame.Surface] = {}

    def render(self, text: str, font: str = "normal", color: Color = S.WHITE,
               scale: int = 1) -> pygame.Surface:
        key = (text, font, color, scale)
        surf = self._cache.get(key)
        if surf is None:
            f = getattr(self, font)
            surf = f.render(text, False, color)
            if scale != 1:
                surf = pygame.transform.scale(
                    surf, (surf.get_width() * scale, surf.get_height() * scale))
            if len(self._cache) > 600:
                self._cache.clear()
            self._cache[key] = surf
        return surf

    def size(self, text: str, font: str = "normal") -> Tuple[int, int]:
        return getattr(self, font).size(text)

    def wrap(self, text: str, width: int, font: str = "normal") -> List[str]:
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if self.size(test, font)[0] <= width or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines


class Sprites:
    NAMES = ["box", "box_done", "bureau", "computer", "plant", "koffie", "printer",
             "kast", "floor_a", "floor_b", "goal", "wall_top", "wall_front", "void",
             "shadow", "icon_info", "icon_warn", "icon_ok", "icon_clock", "logo",
             "logo_big", "stamp_ok", "stamp_no"]

    def __init__(self):
        self.images: Dict[str, pygame.Surface] = {}
        for name in self.NAMES:
            self.images[name] = self._load(name)
        for facing in ("down", "up", "left", "right"):
            for i in range(3):
                n = f"player_{facing}_{i}"
                self.images[n] = self._load(n)
        bg_path = resource_path("assets", "backgrounds", "title.png")
        try:
            self.title_bg = pygame.image.load(bg_path).convert()
        except (pygame.error, FileNotFoundError):
            self.title_bg = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
            self.title_bg.fill(S.NAVY)

    @staticmethod
    def _load(name: str) -> pygame.Surface:
        path = resource_path("assets", "sprites", name + ".png")
        try:
            return pygame.image.load(path).convert_alpha()
        except (pygame.error, FileNotFoundError):
            # Missing asset: magenta placeholder so the game still runs.
            s = pygame.Surface((S.TILE, S.TILE))
            s.fill((255, 0, 255))
            return s

    def __getitem__(self, name: str) -> pygame.Surface:
        return self.images[name]


# ---------------------------------------------------------------- drawing
def text(surf, fonts: Fonts, txt: str, pos, font="normal", color=S.WHITE,
         align="left", shadow: Optional[Color] = S.BLACK, scale=1):
    img = fonts.render(txt, font, color, scale)
    x, y = pos
    if align == "center":
        x -= img.get_width() // 2
    elif align == "right":
        x -= img.get_width()
    if shadow:
        surf.blit(fonts.render(txt, font, shadow, scale), (x + scale, y + scale))
    surf.blit(img, (x, y))
    return img.get_rect(topleft=(x, y))


def bevel_box(surf, rect, face=S.GREY, light=S.WHITE, dark=S.DARK_GREY, depth=2):
    """Windows 3.1 style raised box."""
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, face, r)
    for i in range(depth):
        pygame.draw.line(surf, light, (r.x + i, r.y + i), (r.right - 1 - i, r.y + i))
        pygame.draw.line(surf, light, (r.x + i, r.y + i), (r.x + i, r.bottom - 1 - i))
        pygame.draw.line(surf, dark, (r.x + i, r.bottom - 1 - i), (r.right - 1 - i, r.bottom - 1 - i))
        pygame.draw.line(surf, dark, (r.right - 1 - i, r.y + i), (r.right - 1 - i, r.bottom - 1 - i))


def dos_window(surf, fonts: Fonts, rect, title: str = "", face=S.RIJKSBLAUW,
               border=S.LIGHT_BLUE, title_bg=S.LIGHT_BLUE, title_fg=S.NAVY):
    """A DOS-style window: drop shadow, double line border, title bar."""
    r = pygame.Rect(rect)
    shadow = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    shadow.fill((0, 0, 0, 140))
    surf.blit(shadow, (r.x + 8, r.y + 8))
    pygame.draw.rect(surf, face, r)
    pygame.draw.rect(surf, border, r.inflate(-6, -6), 2)
    pygame.draw.rect(surf, border, r.inflate(-12, -12), 1)
    if title:
        img = fonts.render(f" {title} ", "normal", title_fg)
        bar = img.get_rect(midtop=(r.centerx, r.y + 1))
        pygame.draw.rect(surf, title_bg, bar.inflate(8, 2))
        surf.blit(img, bar)
    return r


def dither_overlay(surf, color=(0, 0, 0), alpha=150):
    over = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    over.fill((*color, alpha))
    surf.blit(over, (0, 0))


def progress_bar(surf, rect, frac, fg=S.YELLOW, bg=S.NAVY):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, bg, r)
    pygame.draw.rect(surf, S.LIGHT_BLUE, r, 2)
    inner = r.inflate(-6, -6)
    blocks = max(1, inner.w // 10)
    filled = int(blocks * max(0.0, min(1.0, frac)))
    for i in range(filled):
        pygame.draw.rect(surf, fg, (inner.x + i * 10, inner.y, 8, inner.h))
