"""Bąbelkowo – gra o sortowaniu bąbelkowym.

Uruchomienie:  python main.py      (wymaga: pip install pygame-ce)
"""
import gc
import os
import sys
from collections import deque

# pozwala uruchamiać z dowolnego folderu i z aplikacji zbudowanej PyInstallerem
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame

from core import W, H, FPS, TITLE, INK, PEARL, Save, Audio, text, panel
from world import World, bubble_icon


class App:
    def __init__(self):
        pygame.init()
        self.save = Save()
        pygame.display.set_caption(TITLE)
        pygame.display.set_icon(bubble_icon(64))
        self.vsync = True
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED, vsync=1)
        except pygame.error:
            self.vsync = False
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED)
        if self.save.data["fullscreen"]:
            pygame.display.toggle_fullscreen()
        self.audio = Audio(self.save)
        from quests import Quests
        self.quests = Quests(self)
        self.quests.ensure_daily()
        self._worlds = {}
        from world import WORLD_ORDER, PREVIEW_WORLD
        for key in WORLD_ORDER + [PREVIEW_WORLD]:   # wczytanie z góry: brak przycięć przy zmianie świata
            self.world(key).draw(self.screen)
        self.clock = pygame.time.Clock()
        self.mouse = pygame.mouse.get_pos()
        self.mouse_moved = False
        self.running = True
        self.fade = 1.0
        self.next = None
        self.toasts = []
        from scenes_menu import MenuScene
        self.scene = MenuScene(self)
        # krok czasu: uśredniony z kilku klatek, żeby ruch był równy mimo drobnych wahań zegara
        self.dt_hist = deque([1 / FPS] * 6, maxlen=6)
        self.cap = 0 if self.vsync else FPS
        self.fast_frames = 0
        gc.collect()
        gc.freeze()                      # obiekty z ładowania nie są już przeglądane przez sprzątanie pamięci
        gc.set_threshold(50000, 50, 100)  # rzadsze, krótsze sprzątanie w trakcie gry

    def world(self, key):
        if key not in self._worlds:
            self._worlds[key] = World(key)
        return self._worlds[key]

    def go(self, scene):
        if self.next is None:
            self.next = scene
            if self.save.dirty:
                self.save.write()

    def quit(self):
        self.running = False

    def toggle_fullscreen(self):
        pygame.display.toggle_fullscreen()
        self.save.data["fullscreen"] = not self.save.data["fullscreen"]
        self.save.write()

    def toast(self, msg):
        if not any(t[0] == msg for t in self.toasts):
            self.toasts.append([msg, 2.8])

    def frame(self, dt, events):
        self.mouse_moved = False
        for e in events:
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.MOUSEMOTION:
                self.mouse = e.pos
                self.mouse_moved = True
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.toggle_fullscreen()
                continue
            if self.next is None and self.fade <= 0.5:
                self.scene.event(e)
        if self.next is not None:
            self.fade += dt * 4
            if self.fade >= 1:
                self.fade = 1
                self.scene = self.next
                self.next = None
        elif self.fade > 0:
            self.fade = max(0.0, self.fade - dt * 3)
        self.scene.update(dt)
        self.scene.draw(self.screen)
        # powiadomienia: u góry ekranu, jedno pod drugim, wjeżdżają i znikają płynnie
        for k, t in enumerate(self.toasts[:3]):
            t[1] -= dt
            slide = min(1.0, (2.8 - t[1]) * 5, t[1] * 4)
            r = pygame.Rect(0, 0, 600, 50)
            r.midtop = (W / 2, 82 + k * 58 - (1 - slide) * 30)
            panel(self.screen, r, 240, edge=PEARL)
            text(self.screen, t[0], 20, INK, r.center, bold=True, shadow=False, max_w=r.w - 30)
        self.toasts = [t for t in self.toasts if t[1] > 0]
        if self.fade > 0:
            if not hasattr(self, "_fade_surf"):
                self._fade_surf = pygame.Surface((W, H)).convert()
                self._fade_surf.fill((2, 12, 20))
            f = min(1.0, self.fade)
            self._fade_surf.set_alpha(int(255 * f * f * (3 - 2 * f)))  # łagodne wejście i wyjście
            self.screen.blit(self._fade_surf, (0, 0))

    def run(self):
        while self.running:
            raw = self.clock.tick(self.cap) / 1000
            # zabezpieczenie: jeśli synchronizacja z ekranem nie działa, ogranicz do 120 klatek
            if self.cap == 0:
                self.fast_frames = self.fast_frames + 1 if raw < 0.004 else 0
                if self.fast_frames > 30:
                    self.cap = 120
            raw = min(raw, 0.1)
            if raw > 0.05:                       # pojedyncza długa klatka (np. ładowanie): nie przeskakuj animacji
                raw = 1 / FPS
            self.dt_hist.append(raw)
            dt = sum(self.dt_hist) / len(self.dt_hist)
            self.frame(dt, pygame.event.get())
            pygame.display.flip()
        self.save.write()
        pygame.quit()


if __name__ == "__main__":
    App().run()
