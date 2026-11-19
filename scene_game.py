"""Rozgrywka: tryb Decyzje (Zamień / Zostaw, pytanie o koniec) i tryb Układanka (własne zamiany)."""
import math
import random

import pygame

from core import (row, dim, cached, W, H, INK, MUTED, AQUA, CORAL, PEARL, KELP, ALARM, NAVY, SHADOW, Button, ButtonList, font, text, draw_swap_icon,
                  text_block, panel, draw_star, draw_heart, mix)
from levels import LEVELS, make_values, inversions
from scenes_menu import Scene, LevelSelectScene, MenuScene, EndingScene
from world import WORLDS, Bubble, Mascot, Particles

CODE = [
    "dla p = 1 … n−1:",
    "   zamieniono ← fałsz",
    "   dla i = 0 … n−1−p:",
    "      jeśli t[i] > t[i+1]:",
    "         zamień t[i], t[i+1]",
    "         zamieniono ← prawda",
    "   jeśli nie zamieniono: koniec",
]
_mono = {}


def mono(size):
    if size not in _mono:
        _mono[size] = pygame.font.SysFont("menlo,consolas,couriernew,dejavusansmono", size)
    return _mono[size]


AREA_L, AREA_R = 40, 880
FLOOR_Y = 556
SURFACE_Y = 168
SIDE = pygame.Rect(904, 86, 352, 620)
# ramki okienek; przyciski są układane wewnątrz nich
INTRO_R = pygame.Rect(0, 0, 760, 560)
INTRO_R.center = (W // 2, 366)
RESULT_R = pygame.Rect(0, 0, 780, 520)
RESULT_R.center = (W // 2, 370)
PAUSE_R = pygame.Rect(0, 0, 460, 430)
PAUSE_R.center = (W // 2, 390)


class GameScene(Scene):
    def __init__(self, app, lid):
        super().__init__(app)
        self.lid = lid
        self.L = LEVELS[lid - 1]
        self.puzzle = self.L["mode"] == "puzzle"
        self.world = app.world(self.L["world"])
        self.values = make_values(self.L["n"], self.L["layout"], dupes=self.L.get("dupes", False))
        self.hidden_mode = self.L.get("hidden", False)
        self.n = len(self.values)
        self.slot = (AREA_R - AREA_L) / self.n
        self.max_r = min(self.slot * 0.42, 60)
        self.fixed = set()
        self.bubbles = []
        for i, v in enumerate(self.values):
            r = self.rad(v)
            self.bubbles.append(Bubble(v, self.sx(i), FLOOR_Y - r, r))
        # obrazki bąbelków: styl podstawowy od razu, pozostałe po jednym na klatkę
        for b in self.bubbles:
            b.hidden = self.hidden_mode
            b.warm(("normal",))
            b.hidden = False
        later = ("cmp", "fixed", "select") if self.L["mode"] == "puzzle" else ("cmp", "fixed")
        self.warm_queue = [(b, st) for st in later for b in self.bubbles]
        self.state = "intro"
        self.t = 0.0
        self.lives = 3
        self.score = 0
        self.combo = 0
        self.best_combo = 0
        self.mistakes = 0
        self.cmp = 0
        self.swaps = 0
        self.pass_no = 0
        self.line = None
        self.msg, self.msg_col = "", INK
        self.mascot = Mascot(AREA_L + 120, 300)
        self.particles = Particles()
        self.popups = []
        self.shake = 0.0
        self.gen = None
        self.wait = 0.0
        self.pending = None
        self.timer_max = self.L.get("timer", 0)
        self.timer = 0.0
        self.cmp_pair = None
        self.end_delay = None
        self.lose_reason = ""
        self.play_time = 0.0       # czas gry bez karty poziomu i pauzy (do rankingu najszybszych przejść)
        self.res_t = 0.0
        self.stars = 0
        self.stars_played = 0
        # układanka
        self.cursor = 0
        self.moves = 0
        self.min_moves = inversions(self.values)
        self.limit = self.min_moves + self.L.get("slack", 0)
        self.solved = False
        # przyciski
        self.intro_menu = ButtonList([
            Button("Start", (0, 0), (300, 64), "pearl", key="Enter", font_size=32, action="start"),
            Button("Mapa poziomów", (0, 0), (280, 64), "ghost", font_size=24, action="map"),
        ], vertical=False)
        row(self.intro_menu.buttons, INTRO_R.centerx, INTRO_R.bottom - 54, max_w=INTRO_R.w - 80)
        self.left_btn = Button("Zamień", (260, 664), (300, 70), "coral", key="Z", font_size=30)
        self.right_btn = Button("Zostaw", (640, 664), (300, 70), "ghost", key="X", font_size=30)
        self.pause_btn = Button("II", (W - 42, 37), (54, 48), "ghost", font_size=22)
        self.pause_menu = ButtonList([
            Button("Wznów", (W / 2, 300), (340, 62), "pearl", key="Esc", action="resume"),
            Button("Od nowa", (W / 2, 378), (340, 58), "primary", action="restart"),
            Button("Mapa poziomów", (W / 2, 452), (340, 58), "primary", action="map"),
            Button("Menu główne", (W / 2, 526), (340, 58), "ghost", action="menu"),
        ])
        self.result_menu = None
        if self.puzzle:
            self.say("Wybierz parę strzałkami i zamień ją spacją albo kliknij przycisk zamiany.")
        else:
            self.say("Do dzieła! Patrz na dwa podświetlone bąbelki i decyduj.")

    # ------------------------------------------------ geometria
    def rad(self, v):
        return self.max_r * (0.45 + 0.55 * v / 20)

    def sx(self, i):
        return AREA_L + self.slot * (i + 0.5)

    def base_y(self, i):
        b = self.bubbles[i]
        return SURFACE_Y + 16 + b.r if i in self.fixed else FLOOR_Y - b.r

    def gap_pos(self, g):
        return (AREA_L + self.slot * (g + 1), 626)

    # ------------------------------------------------ komunikaty i efekty
    def say(self, s, col=INK):
        self.msg, self.msg_col = s, col

    def popup(self, s, x, y, col):
        self.popups.append([s, x, y, 1.2, col])

    def do_swap(self, i):
        a, b = self.bubbles[i], self.bubbles[i + 1]
        self.bubbles[i], self.bubbles[i + 1] = b, a
        big, small = (a, b) if a.v > b.v else (b, a)
        dur = 0.5
        a.move_to(self.sx(i + 1), FLOOR_Y - a.r, dur, 70 if a is big else -26)
        b.move_to(self.sx(i), FLOOR_Y - b.r, dur, 70 if b is big else -26)
        self.swaps += 1
        self.app.audio.play("swap")
        for bb in (a, b):
            self.particles.burst(bb.x, bb.y, (220, 245, 255), 6, 90, up=True)

    def fix(self, k, sound=True):
        if k in self.fixed:
            return
        self.fixed.add(k)
        b = self.bubbles[k]
        b.style = "fixed"
        b.move_to(self.sx(k), self.base_y(k), 0.9)
        if sound:
            self.app.audio.play("fix")
        self.particles.burst(b.x, b.y, PEARL, 12, 140, up=True)

    def mistake(self, msg, pair=None):
        self.lives -= 1 if not self.puzzle else 0
        self.combo = 0
        self.mistakes += 1
        self.shake = 0.35
        self.app.audio.play("bad")
        self.mascot.feel("sad", 1.0)
        self.say(msg, ALARM)
        if pair:
            for i in pair:
                self.bubbles[i].shake = 1
        if not self.puzzle and self.lives <= 0:
            self.lose_reason = "Bąbelki pękły! Skończyły się życia."
            self.end_delay = [1.1, False]

    # ------------------------------------------------ tryb Decyzje
    def script(self):
        n = self.n
        for p in range(1, n):
            self.pass_no = p
            self.line = 0
            self.say(f"Przejście {p}. Pchamy największy bąbelek w prawo.")
            yield 0.7
            self.line = 1
            yield 0.3
            swapped = 0
            for i in range(n - p):
                a, b = self.bubbles[i], self.bubbles[i + 1]
                self.cmp_pair = (i, i + 1)
                a.style = b.style = "cmp"
                self.line = 3
                self.cmp += 1
                self.mascot.goto((a.x + b.x) / 2, min(a.y - a.r, b.y - b.r) - 70)
                self.say(f"Porównaj {a.v} i {b.v}. Zamienić?")
                yield ("ask", "swap", a.v > b.v)
                if a.v > b.v:
                    self.line = 4
                    self.do_swap(i)
                    swapped += 1
                    yield 0.55
                    self.line = 5
                    yield 0.15
                else:
                    yield 0.2
                for bb in (self.bubbles[i], self.bubbles[i + 1]):
                    if bb.style == "cmp":
                        bb.style = "normal"
                self.cmp_pair = None
            k = n - p
            self.line = 2
            self.fix(k)
            self.say(f"{self.bubbles[k].v} wypływa na powierzchnię. Jest na swoim miejscu!", PEARL)
            self.mascot.goto(self.sx(k), SURFACE_Y + 160)
            yield 0.8
            if p == n - 1:
                break
            if self.L["early"]:
                self.line = 6
                self.say(f"Koniec przejścia {p}. Zamian w tym przejściu: {swapped}. Gramy dalej czy koniec?")
                yield ("ask", "early", swapped > 0)
                if swapped == 0:
                    break
            elif swapped == 0:
                self.line = 6
                self.say("W tym przejściu nie było zamian, więc tablica jest gotowa!", KELP)
                yield 1.0
                break
        self.line = None
        for i in range(n):
            self.fix(i, sound=False)
        self.app.audio.play("fix")
        yield 1.0
        self.finish(True)

    def run_script(self, dt):
        if self.gen is None or self.pending or self.end_delay:
            return
        if self.wait > 0:
            self.wait -= dt
            return
        while self.gen is not None:
            try:
                cmd = next(self.gen)
            except StopIteration:
                self.gen = None
                return
            if isinstance(cmd, tuple):
                self.pending = cmd
                self.timer = self.timer_max
                return
            self.wait = cmd
            if cmd > 0:
                return

    def answer(self, left):
        if self.state != "play" or not self.pending:
            return
        _, kind, correct = self.pending
        self.pending = None
        ok = left == correct
        pair = self.cmp_pair
        if kind == "swap":
            a, b = self.bubbles[pair[0]], self.bubbles[pair[1]]
        if ok:
            bonus = int(60 * self.timer / self.timer_max) if self.timer_max else 0
            gain = 100 + 25 * min(self.combo, 8) + bonus
            self.score += gain
            self.combo += 1
            self.best_combo = max(self.best_combo, self.combo)
            q = self.app.quests
            q.emit("correct")
            q.emit("combo", n=self.combo)
            if kind == "early" and not correct:
                q.emit("early_end")
            self.app.audio.play("good")
            self.mascot.feel("happy", 0.7)
            px, py = (self.mascot.x, self.mascot.y - 40)
            self.popup(f"+{gain}", px, py, PEARL)
            self.particles.sparkle(px, py + 30, 8)
            if kind == "swap":
                self.say(f"Dobrze! {a.v} > {b.v}, więc zamieniamy." if correct
                         else (f"Dobrze! {a.v} = {b.v}, równych nie zamieniamy." if a.v == b.v
                               else f"Dobrze! {a.v} < {b.v}, mniejszy już jest po lewej."), KELP)
            else:
                self.say("Dobrze! Były zamiany, więc gramy dalej." if correct
                         else "Brawo! Zero zamian znaczy, że tablica jest posortowana.", KELP)
        else:
            if kind == "swap":
                msg = (f"Ups! {a.v} > {b.v}, trzeba było zamienić. Robię to za ciebie." if correct
                       else (f"Ups! {a.v} = {b.v}. Równych nie zamieniamy, dzięki temu sortowanie jest stabilne."
                             if a.v == b.v else f"Ups! {a.v} < {b.v}, zamiana była zbędna."))
                self.mistake(msg, pair)
            else:
                self.mistake("Ups! Były zamiany, więc trzeba grać dalej." if correct
                             else "Ups! Zero zamian oznacza koniec. Tablica była gotowa.")
        self.wait = 0.45

    def timeout(self):
        _, kind, correct = self.pending
        self.pending = None
        if kind == "swap":
            what = "Zamień" if correct else "Zostaw"
        else:
            what = "Dalej" if correct else "Koniec"
        self.mistake(f"Za wolno! Dobra odpowiedź to: {what}.", self.cmp_pair)
        self.wait = 0.45

    # ------------------------------------------------ tryb Układanka
    def try_swap(self, g):
        if self.state != "play" or self.solved or self.end_delay or any(b.busy for b in self.bubbles):
            return
        a, b = self.bubbles[g], self.bubbles[g + 1]
        good = a.v > b.v
        self.do_swap(g)
        self.moves += 1
        inv = inversions([x.v for x in self.bubbles])
        self.mascot.goto(self.gap_pos(g)[0], FLOOR_Y - 2 * self.max_r - 90)
        if good:
            self.combo += 1
            self.best_combo = max(self.best_combo, self.combo)
            self.app.quests.emit("correct")
            self.app.quests.emit("combo", n=self.combo)
            gain = 100 + 25 * min(self.combo - 1, 8)
            self.score += gain
            self.popup(f"+{gain}", self.gap_pos(g)[0], FLOOR_Y - 2 * self.max_r - 30, PEARL)
            self.app.audio.play("good")
            self.mascot.feel("happy", 0.6)
            self.say(f"Dobra zamiana: {a.v} > {b.v}. Jedna inwersja mniej, zostało {inv}.", KELP)
        else:
            if a.v == b.v:
                self.mistake(f"{a.v} = {b.v}: zamiana równych to zmarnowany ruch. Zostało {inv}.", (g, g + 1))
            else:
                self.mistake(f"{a.v} < {b.v}, więc ta zamiana dodała inwersję. Zostało {inv}.", (g, g + 1))
        if inv == 0:
            self.solved = True
            self.say("Posortowane! Wszystkie bąbelki wypływają.", KELP)
            for i in range(self.n):
                self.fix(i, sound=False)
            self.app.audio.play("fix")
            self.end_delay = [1.3, True]
        elif self.moves >= self.limit:
            self.lose_reason = f"Skończyły się ruchy. Zostało {inv} inwersji."
            self.end_delay = [1.0, False]

    # ------------------------------------------------ koniec poziomu
    def finish(self, win):
        a = self.app
        self.pending = None
        self.gen = None
        self.res_t = 0
        self.stars_played = 0
        self.mascot.goto(W / 2 - 330, 300)
        if win:
            if self.puzzle:
                extra = self.moves - self.min_moves
                self.stars = 3 if extra == 0 else (2 if extra <= 2 else 1)
            else:
                self.stars = max(1, self.lives)
            self.score += 250 * self.stars
            self.prev_best = a.save.best(self.lid)
            prev_time = a.save.best_time(self.lid)
            self.time_record = prev_time is None or self.play_time < prev_time
            a.save.record(self.lid, self.stars, self.score, self.play_time)
            a.quests.emit("level_win", lid=self.lid, mistakes=self.mistakes, time=self.play_time, stars=self.stars)
            if self.puzzle and self.moves == self.min_moves:
                a.quests.emit("puzzle_perfect")
            self.state = "win"
            a.audio.play("win")
            self.mascot.feel("happy", 999)
            last = self.lid == len(LEVELS)
            self.result_menu = ButtonList([
                Button("Mapa", (0, 0), (160, 64), "ghost", font_size=26, action="map"),
                Button("Powtórz", (0, 0), (200, 64), "primary", font_size=26, action="restart"),
                Button("Zakończenie" if last else "Następny poziom", (0, 0), (300, 64), "pearl", key="Enter",
                       font_size=26, action="next"),
            ], vertical=False)
            row(self.result_menu.buttons, RESULT_R.centerx, RESULT_R.bottom - 54, max_w=RESULT_R.w - 80)
            self.result_menu.index = 2
        else:
            self.state = "lose"
            a.audio.play("lose")
            self.mascot.feel("sad", 999)
            self.result_menu = ButtonList([
                Button("Mapa", (0, 0), (200, 64), "ghost", font_size=26, action="map"),
                Button("Spróbuj ponownie", (0, 0), (340, 64), "pearl", key="Enter", font_size=26, action="restart"),
            ], vertical=False)
            self.result_menu.index = 1
            row(self.result_menu.buttons, RESULT_R.centerx, RESULT_R.bottom - 54, max_w=RESULT_R.w - 80)

    def result_action(self, action):
        a = self.app
        if action == "next":
            if self.lid == len(LEVELS):
                a.go(EndingScene(a))
            else:
                a.go(GameScene(a, self.lid + 1))
        elif action == "restart":
            a.go(GameScene(a, self.lid))
        elif action == "map":
            a.go(LevelSelectScene(a, focus=min(self.lid + (1 if self.state == "win" else 0), len(LEVELS))))
        elif action == "menu":
            a.go(MenuScene(a))

    def start(self):
        self.state = "play"
        self.app.audio.play("pop")
        if not self.puzzle:
            self.gen = self.script()

    # ------------------------------------------------ zdarzenia
    def event(self, e):
        a = self.app
        if self.state == "intro":
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) \
                    and not self.intro_menu.using_keys:
                self.start()
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.result_action("map")
                return
            b = self.intro_menu.handle(e, a)
            if b:
                self.start() if b.action == "start" else self.result_action("map")
            return
        if self.state == "pause":
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_p):
                self.state = "play"
                return
            b = self.pause_menu.handle(e, a)
            if b:
                if b.action == "resume":
                    self.state = "play"
                else:
                    self.result_action(b.action)
            return
        if self.state in ("win", "lose"):
            if self.res_t < 0.6:
                return
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and not self.result_menu.using_keys:
                self.result_action("next" if self.state == "win" else "restart")
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.result_action("map")
                return
            b = self.result_menu.handle(e, a)
            if b:
                self.result_action(b.action)
            return
        # gra
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_p):
            self.state = "pause"
            self.pause_menu.index = 0
            a.audio.play("click")
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.pause_btn.hit(e.pos):
            self.state = "pause"
            a.audio.play("click")
            return
        if self.puzzle:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_LEFT, pygame.K_a):
                    self.cursor = max(0, self.cursor - 1)
                    a.audio.play("tick")
                elif e.key in (pygame.K_RIGHT, pygame.K_d):
                    self.cursor = min(self.n - 2, self.cursor + 1)
                    a.audio.play("tick")
                elif e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
                    self.try_swap(self.cursor)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for g in range(self.n - 1):
                    gx, gy = self.gap_pos(g)
                    if math.hypot(e.pos[0] - gx, e.pos[1] - gy) < 26:
                        self.cursor = g
                        self.try_swap(g)
        else:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_z, pygame.K_LEFT):
                    self.press(self.left_btn, True)
                elif e.key in (pygame.K_x, pygame.K_RIGHT):
                    self.press(self.right_btn, False)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.left_btn.hit(e.pos):
                    self.press(self.left_btn, True)
                elif self.right_btn.hit(e.pos):
                    self.press(self.right_btn, False)

    def press(self, btn, left):
        if self.pending:
            btn.flash = 1
            self.answer(left)

    # ------------------------------------------------ aktualizacja
    def update(self, dt):
        if self.warm_queue:
            b, st = self.warm_queue.pop()
            b.warm((st,))
        self.t += dt
        if self.hidden_mode:   # zamrożone: widać tylko porównywaną parę i bąbelki na powierzchni
            reveal = self.state in ("win", "lose")
            for b in self.bubbles:
                b.hidden = not reveal and b.style == "normal"
        self.world.update(dt)
        m = self.app.mouse
        if self.state == "intro":
            self.intro_menu.update(dt, m, self.app.mouse_moved)
        if self.state == "pause":
            self.pause_menu.update(dt, m, self.app.mouse_moved)
            return
        for b in self.bubbles:
            b.update(dt)
        self.mascot.update(dt)
        self.particles.update(dt)
        for p in self.popups:
            p[2] -= 40 * dt
            p[3] -= dt
        self.popups = [p for p in self.popups if p[3] > 0]
        self.shake = max(0.0, self.shake - dt)
        self.pause_btn.update(dt, m)

        if self.state == "play" and not self.end_delay:
            self.play_time += dt
        if self.state == "play":
            if self.end_delay:
                self.end_delay[0] -= dt
                if self.end_delay[0] <= 0:
                    win = self.end_delay[1]
                    self.end_delay = None
                    self.finish(win)
            elif self.puzzle:
                if self.app.mouse_moved:
                    for g in range(self.n - 1):
                        gx, gy = self.gap_pos(g)
                        if math.hypot(m[0] - gx, m[1] - gy) < 26:
                            self.cursor = g
                for i, b in enumerate(self.bubbles):
                    if i not in self.fixed:
                        b.style = "select" if i in (self.cursor, self.cursor + 1) else "normal"
                if not any(b.busy for b in self.bubbles):
                    gx = self.gap_pos(self.cursor)[0]
                    if abs(self.mascot.tx - gx) > 4 and self.mascot.mood == "idle":
                        self.mascot.goto(gx, FLOOR_Y - 2 * self.max_r - 90)
            else:
                if self.pending and self.timer_max:
                    self.timer -= dt
                    if self.timer <= 0:
                        self.timeout()
                self.run_script(dt)
            # przyciski decyzji
            kind = self.pending[1] if self.pending else (None)
            if kind == "early":
                self.left_btn.label, self.right_btn.label = "Dalej", "Koniec"
                self.left_btn.style, self.right_btn.style = "primary", "pearl"
            else:
                self.left_btn.label, self.right_btn.label = "Zamień", "Zostaw"
                self.left_btn.style, self.right_btn.style = "coral", "ghost"
            self.left_btn.enabled = self.right_btn.enabled = bool(self.pending)
            self.left_btn.update(dt, m)
            self.right_btn.update(dt, m)
        if self.state in ("win", "lose"):
            self.res_t += dt
            self.result_menu.update(dt, m, self.app.mouse_moved)
            if self.state == "win" and self.stars_played < self.stars and self.res_t > 0.6 + self.stars_played * 0.4:
                self.stars_played += 1
                self.app.audio.play("star")
                self.particles.burst(self.star_x(self.stars_played - 1), 238, PEARL, 18, 200)

    # ------------------------------------------------ rysowanie
    def star_x(self, k):
        return W / 2 - 90 + k * 90

    def draw(self, s):
        self.world.draw(s)
        self.draw_stage(s)
        self.draw_hud(s)
        self.draw_side(s)
        if self.state == "play":
            self.draw_controls(s)
        self.particles.draw(s)
        for txt, x, y, life, col in self.popups:
            text(s, txt, 30, col, (x, y), display=True, alpha=int(255 * min(1, life)))
        if self.shake > 0:
            dx = math.sin(self.t * 70) * 10 * self.shake / 0.35
            s.scroll(int(dx), 0)
        if self.state == "intro":
            self.draw_intro(s)
        elif self.state == "pause":
            self.draw_pause(s)
        elif self.state in ("win", "lose"):
            self.draw_result(s)

    def draw_stage(self, s):
        # powierzchnia
        pts = [(x, SURFACE_Y + math.sin(x * 0.03 + self.t * 2) * 3) for x in range(AREA_L - 10, AREA_R + 11, 8)]
        pygame.draw.lines(s, PEARL, False, pts, 2)
        text(s, "POWIERZCHNIA · POSORTOWANE", 15, PEARL, (AREA_R, SURFACE_Y - 14), "midright", bold=True)
        # dno z indeksami
        def make_strip():
            st = pygame.Surface((AREA_R - AREA_L + 20, 30), pygame.SRCALPHA)
            pygame.draw.rect(st, (2, 20, 32, 150), st.get_rect(), border_radius=10)
            return st
        s.blit(cached("floor_strip", make_strip), (AREA_L - 10, FLOOR_Y + 4))
        for i in range(self.n):
            text(s, f"t[{i}]", 16, MUTED, (self.sx(i), FLOOR_Y + 19), shadow=False)
        for b in sorted(self.bubbles, key=lambda b: b.style == "cmp"):
            b.draw(s, self.t)
        # znak porównania
        if self.pending and self.pending[1] == "swap" and self.cmp_pair:
            a, b = self.bubbles[self.cmp_pair[0]], self.bubbles[self.cmp_pair[1]]
            mx = (a.x + b.x) / 2
            text(s, "?", 34, CORAL, (mx, FLOOR_Y - max(a.r, b.r) * 0.4), display=True)
        self.mascot.draw(s)

    def draw_hud(self, s):
        def make_bar():
            b = pygame.Surface((W, 74), pygame.SRCALPHA)
            b.fill((3, 22, 36, 200))
            return b
        s.blit(cached("hud_bar", make_bar), (0, 0))
        pygame.draw.line(s, (60, 120, 150), (0, 74), (W, 74), 1)
        wname = WORLDS[self.L["world"]]["name"]
        text(s, f"Poziom {self.lid} · {wname}", 17, MUTED, (24, 22), "midleft", bold=True, shadow=False)
        text(s, self.L["name"], 28, INK, (24, 50), "midleft", display=True)
        if self.puzzle:
            left = self.limit - self.moves
            col = ALARM if left <= 1 else INK
            text(s, f"Ruchy: {self.moves} / {self.limit}", 28, col, (W / 2, 38), display=True)
        else:
            for k in range(3):
                draw_heart(s, W / 2 - 48 + k * 48, 36, 15, k < self.lives)
        text(s, "PUNKTY", 14, MUTED, (W - 96, 20), "midright", bold=True, shadow=False)
        text(s, f"{self.score}", 30, PEARL, (W - 96, 48), "midright", display=True)
        if self.combo >= 2:
            text(s, f"seria ×{self.combo}", 20, KELP, (W - 250, 38), "midright", bold=True)
        self.pause_btn.draw(s)

    def draw_side(self, s):
        # dymek Bulka
        r1 = pygame.Rect(SIDE.x, SIDE.y, SIDE.w, 156)
        panel(s, r1)
        text(s, "BULEK MÓWI", 14, MUTED, (r1.x + 20, r1.y + 22), "midleft", bold=True, shadow=False)
        text_block(s, self.msg, 21, self.msg_col, (r1.x + 20, r1.y + 40), r1.w - 40, 28, max_h=r1.h - 50)
        # pseudokod / inwersje
        r2 = pygame.Rect(SIDE.x, SIDE.y + 168, SIDE.w, 262)
        panel(s, r2)
        if self.puzzle:
            inv = inversions([b.v for b in self.bubbles])
            text(s, "INWERSJE", 14, MUTED, (r2.x + 20, r2.y + 22), "midleft", bold=True, shadow=False)
            text(s, str(inv), 72, PEARL if inv else KELP, (r2.x + 20, r2.y + 82), "midleft", display=True)
            text(s, "par w złej kolejności", 20, INK, (r2.x + 20 + font(72, display=True).size(str(inv))[0] + 16, r2.y + 86), "midleft", shadow=False)
            text_block(s, "Każda dobra zamiana sąsiadów usuwa dokładnie jedną inwersję. "
                          f"Dlatego minimum to {self.min_moves} ruchów: tyle samo zamian wykonałoby sortowanie bąbelkowe.",
                       18, MUTED, (r2.x + 20, r2.y + 136), r2.w - 40, 24)
        else:
            text(s, "PSEUDOKOD", 14, MUTED, (r2.x + 20, r2.y + 22), "midleft", bold=True, shadow=False)
            f = mono(16)
            y = r2.y + 46
            for i, ln in enumerate(CODE):
                on = i == self.line
                if on:
                    def make_hl():
                        h = pygame.Surface((r2.w - 24, 28), pygame.SRCALPHA)
                        pygame.draw.rect(h, (255, 125, 92, 70), h.get_rect(), border_radius=6)
                        return h
                    s.blit(cached("code_hl", make_hl), (r2.x + 12, y - 4))
                col = INK if on else (150, 185, 200)
                if not self.L["early"] and i == 6:
                    col = mix(col, (60, 90, 110), 0.3)
                s.blit(cached(("code", ln, col), lambda: f.render(ln, True, col)), (r2.x + 20, y))
                y += 30
        # liczniki
        r3 = pygame.Rect(SIDE.x, SIDE.y + 442, SIDE.w, SIDE.h - 442)
        panel(s, r3)
        if self.puzzle:
            items = [("Ruchy", f"{self.moves}"), ("Limit", f"{self.limit}"),
                     ("Minimum", f"{self.min_moves}"), ("Złe ruchy", f"{self.mistakes}")]
        else:
            items = [("Przejście", f"{self.pass_no}/{self.n - 1}" if self.pass_no else "–"), ("Porównania", f"{self.cmp}"),
                     ("Zamiany", f"{self.swaps}"), ("Najlepsza seria", f"{self.best_combo}")]
        for k, (lab, val) in enumerate(items):
            x = r3.x + 20 + (k % 2) * 168
            y = r3.y + 20 + (k // 2) * 76
            text(s, lab, 16, MUTED, (x, y), "topleft", shadow=False)
            text(s, val, 32, INK, (x, y + 22), "topleft", display=True, shadow=False)

    def draw_controls(self, s):
        if self.puzzle:
            busy = any(b.busy for b in self.bubbles)
            for g in range(self.n - 1):
                gx, gy = self.gap_pos(g)
                sel = g == self.cursor
                col = KELP if sel else (14, 58, 84)
                pygame.draw.circle(s, SHADOW, (gx, gy + 4), 24)
                pygame.draw.circle(s, col, (gx, gy), 24)
                pygame.draw.circle(s, (170, 230, 240), (gx, gy), 24, 2)
                draw_swap_icon(s, gx, gy, NAVY if sel else AQUA)
            text(s, "Strzałki: wybierz parę   ·   Spacja: zamień   ·   albo kliknij przycisk zamiany", 18, INK if not busy else MUTED,
                 ((AREA_L + AREA_R) / 2, 690))
            return
        if self.pending and self.timer_max:
            ratio = max(0, self.timer / self.timer_max)
            r = pygame.Rect(110, 606, 680, 14)
            pygame.draw.rect(s, (3, 22, 36), r, border_radius=7)
            col = KELP if ratio > 0.5 else (PEARL if ratio > 0.25 else ALARM)
            pygame.draw.rect(s, col, (r.x, r.y, r.w * ratio, r.h), border_radius=7)
            text(s, "TLEN", 14, MUTED, (r.x - 12, r.centery), "midright", bold=True, shadow=False)
        self.left_btn.draw(s)
        self.right_btn.draw(s)

    def overlay(self, s, a=150):
        dim(s, a)

    def draw_intro(self, s):
        self.overlay(s, 140)
        r = INTRO_R
        panel(s, r, 235)
        wname = WORLDS[self.L["world"]]["name"]
        text(s, f"Poziom {self.lid}  ·  {wname}", 22, AQUA, (W / 2, r.y + 44), bold=True)
        text(s, self.L["name"], 54, INK, (W / 2, r.y + 102), display=True, max_w=r.w - 80)
        mode = "Układanka" if self.puzzle else ("Decyzje + pytanie o koniec" if self.L["early"] else "Decyzje")
        info = f"{mode}  ·  {self.n} bąbelków"
        if self.timer_max:
            info += f"  ·  {self.timer_max:g} s na decyzję".replace(".", ",")
        if self.puzzle:
            info += f"  ·  limit ruchów: {self.limit}"
        if self.hidden_mode:
            info += "  ·  zamrożone liczby"
        if self.L.get("dupes"):
            info += "  ·  równe liczby"
        text(s, info, 22, PEARL, (W / 2, r.y + 152), bold=True, max_w=r.w - 60)
        y = text_block(s, self.L["goal"], 24, INK, (r.x + 60, r.y + 192), r.w - 120, 32, max_h=100)
        tip = pygame.Rect(r.x + 50, y + 14, r.w - 100, 96)
        pygame.draw.rect(s, (14, 60, 84), tip, border_radius=14)
        text(s, "WSKAZÓWKA", 14, KELP, (tip.x + 20, tip.y + 20), "midleft", bold=True, shadow=False)
        text_block(s, self.L["tip"], 20, INK, (tip.x + 20, tip.y + 36), tip.w - 40, 26, max_h=tip.h - 44)
        st = self.app.save.stars(self.lid)
        if st:
            for k in range(3):
                draw_star(s, r.right - 110 + k * 32, r.y + 44, 12, k < st)
        self.intro_menu.draw(s)

    def draw_pause(self, s):
        self.overlay(s, 170)
        r = PAUSE_R
        panel(s, r, 235)
        text(s, "Pauza", 48, INK, (W / 2, 220), display=True)
        self.pause_menu.draw(s)

    def draw_result(self, s):
        self.overlay(s, 150)
        r = RESULT_R
        panel(s, r, 238, edge=PEARL if self.state == "win" else ALARM)
        if self.state == "win":
            text(s, "Poziom ukończony!", 50, PEARL, (W / 2, r.y + 64), display=True)
            for k in range(3):
                shown = k < self.stars_played
                pop = 1.0
                if shown:
                    t0 = 0.6 + k * 0.4
                    pop = 1 + 0.4 * max(0, 1 - (self.res_t - t0) * 4)
                draw_star(s, self.star_x(k), 238 - (12 if k == 1 else 0), int(34 * pop), shown)
            stats = [("Punkty", f"{self.score}"),
                     ("Czas", f"{self.play_time:.1f} s".replace(".", ",") + ("  · rekord!" if self.time_record else ""))]
            if self.puzzle:
                stats += [("Ruchy", f"{self.moves} (minimum {self.min_moves})"), ("Złe ruchy", f"{self.mistakes}")]
            else:
                stats += [("Porównania / zamiany", f"{self.cmp} / {self.swaps}"), ("Błędy", f"{self.mistakes}"),
                          ("Najlepsza seria", f"{self.best_combo}")]
            y = r.y + 230
            for lab, val in stats:
                text(s, lab, 22, MUTED, (W / 2 - 20, y), "midright", shadow=False)
                text(s, val, 24, INK, (W / 2 + 20, y), "midleft", bold=True, shadow=False)
                y += 34
            if self.score > getattr(self, "prev_best", 0) and getattr(self, "prev_best", 0) > 0:
                text(s, "Nowy rekord!", 22, KELP, (W / 2, r.y + 190), bold=True)
        else:
            text(s, "Spróbuj jeszcze raz", 50, ALARM, (W / 2, r.y + 70), display=True)
            text_block(s, self.lose_reason, 26, INK, (r.x + 80, r.y + 140), r.w - 160, 34, max_h=72)
            text_block(s, self.L["tip"], 22, MUTED, (r.x + 80, r.y + 230), r.w - 160, 30, max_h=150)
        self.result_menu.draw(s)
