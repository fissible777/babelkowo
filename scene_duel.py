"""Duel z AI: gracz i bot sortują tę samą tablicę. Wygrywa ten, kto pierwszy skończy. Błąd = 1,5 s kary."""
import math
import random

import pygame

from core import (W, H, INK, MUTED, AQUA, CORAL, PEARL, KELP, ALARM, NAVY, SHADOW, Button, ButtonList, cached,
                  text, text_block, panel, draw_star, dim, row)
from levels import make_values
from ludek import BOTS, draw_avatar, draw_pearl
from scenes_menu import Scene
from world import Bubble, Particles

PENALTY = 1.5


def go_menu(app):
    from scenes_menu import MenuScene
    app.go(MenuScene(app))


# ================================================================ wybór rywala
class DuelSetupScene(Scene):
    def __init__(self, app, pick=1, size=7):
        super().__init__(app)
        self.world = app.world("rafa")
        self.t = 0.0
        self.pick = pick
        self.size = size
        self.back = Button("Menu", (100, 46), (150, 50), "ghost", key="Esc", font_size=22)
        self.minus = Button("–", (W / 2 - 110, 560), (48, 44), "ghost", font_size=30)
        self.plus = Button("+", (W / 2 + 110, 560), (48, 44), "ghost", font_size=30)
        self.start = Button("Do boju!", (W / 2, 640), (300, 64), "coral", key="Enter", font_size=30)

    def card_rect(self, i):
        r = pygame.Rect(0, 0, 270, 330)
        r.center = (W / 2 + (i - 1.5) * 290, 318)
        return r

    def begin(self):
        self.app.go(DuelScene(self.app, BOTS[self.pick], self.size))

    def event(self, e):
        a = self.app
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                go_menu(a)
            elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.pick = (self.pick + (1 if e.key == pygame.K_RIGHT else -1)) % len(BOTS)
                a.audio.play("tick")
            elif e.key in (pygame.K_UP, pygame.K_DOWN):
                self.size = max(5, min(9, self.size + (1 if e.key == pygame.K_UP else -1)))
                a.audio.play("tick")
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                a.audio.play("click")
                self.begin()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.back.hit(e.pos):
                a.audio.play("click")
                go_menu(a)
            for i in range(len(BOTS)):
                if self.card_rect(i).collidepoint(e.pos):
                    self.pick = i
                    a.audio.play("tick")
            if self.minus.hit(e.pos):
                self.size = max(5, self.size - 1)
                a.audio.play("tick")
            if self.plus.hit(e.pos):
                self.size = min(9, self.size + 1)
                a.audio.play("tick")
            if self.start.hit(e.pos):
                a.audio.play("click")
                self.begin()

    def update(self, dt):
        self.t += dt
        self.world.update(dt)
        m = self.app.mouse
        if self.app.mouse_moved:
            for i in range(len(BOTS)):
                if self.card_rect(i).collidepoint(m):
                    self.pick = i
        self.minus.enabled = self.size > 5
        self.plus.enabled = self.size < 9
        for b in (self.back, self.minus, self.plus, self.start):
            b.update(dt, m)

    def draw(self, s):
        from scene_social import header
        self.world.draw(s)
        header(s, "Duel z AI", self.app)
        self.back.draw(s)
        text(s, "Wybierz rywala. Oboje sortujecie tę samą tablicę, kto pierwszy, ten lepszy!", 20, INK,
             (W / 2, 112), shadow=True)
        p = self.app.save.p
        for i, b in enumerate(BOTS):
            r = self.card_rect(i)
            sel = i == self.pick
            panel(s, r, 230, edge=PEARL if sel else (60, 120, 150))
            if sel:
                pygame.draw.rect(s, PEARL, r.inflate(6, 6), 3, border_radius=20)
            pygame.draw.ellipse(s, (3, 22, 36), (r.centerx - 60, r.y + 178, 120, 20))
            draw_avatar(s, r.centerx, r.y + 128, 0.78, b["avatar"], self.t + i, bubbles=sel)
            text(s, b["nick"], 22, INK, (r.centerx, r.y + 218), display=True, max_w=r.w - 20)
            col = {"Łatwy": KELP, "Średni": AQUA, "Trudny": CORAL, "Mistrz": ALARM}[b["diff"]]
            text(s, b["diff"], 18, col, (r.centerx, r.y + 246), bold=True, shadow=False)
            text(s, f"decyzja ~{b['react']:.1f} s · celność {int(b['acc'] * 100)}%".replace(".", ","), 15, MUTED,
                 (r.centerx, r.y + 272), shadow=False)
            w, l = p["duels"].get(b["id"], [0, 0])
            draw_pearl(s, r.centerx - 70, r.y + 304, 8)
            text(s, f"+{b['reward']}", 16, PEARL, (r.centerx - 58, r.y + 304), "midleft", bold=True, shadow=False)
            text(s, f"Ty: {w}–{l}", 16, INK, (r.centerx + 70, r.y + 304), bold=True, shadow=False)
        text(s, f"Bąbelki: {self.size}", 24, INK, (W / 2, 560), display=True)
        for b in (self.minus, self.plus, self.start):
            b.draw(s)
        text(s, "Strzałki lewo / prawo: rywal   ·   góra / dół: liczba bąbelków   ·   Enter: start", 16, MUTED,
             (W / 2, H - 14))


# ================================================================ tor jednego zawodnika
class Lane:
    def __init__(self, scene, values, rect, bot=None):
        self.scene = scene
        self.rect = rect
        self.bot = bot
        self.n = len(values)
        self.slot = (rect.w - 40) / self.n
        self.max_r = min(self.slot * 0.4, rect.h * 0.2)
        self.fixed = set()
        self.bubbles = [Bubble(v, self.sx(i), self.floor() - self.rad(v), self.rad(v)) for i, v in enumerate(values)]
        self.gen = self.script()
        self.wait = 0.0
        self.pending = None
        self.think = 0.0
        self.penalty = 0.0
        self.done = False
        self.finish_time = None
        self.mistakes = 0
        self.correct = 0
        self.combo = 0
        self.cmp_pair = None
        self.flash = 0.0
        self.msg = "Gotowy do startu"
        self.rnd = random.Random()

    def rad(self, v):
        return self.max_r * (0.5 + 0.5 * v / 20)

    def sx(self, i):
        return self.rect.x + 20 + self.slot * (i + 0.5)

    def floor(self):
        return self.rect.bottom - 14

    def base_y(self, i):
        b = self.bubbles[i]
        return self.rect.y + 30 + b.r if i in self.fixed else self.floor() - b.r

    def sorted_count(self):
        return len(self.fixed)

    def script(self):
        n = self.n
        for p in range(1, n):
            swapped = False
            for i in range(n - p):
                a, b = self.bubbles[i], self.bubbles[i + 1]
                a.style = b.style = "cmp"
                self.cmp_pair = (i, i + 1)
                yield ("ask", a.v > b.v)
                if a.v > b.v:
                    self.bubbles[i], self.bubbles[i + 1] = b, a
                    a.move_to(self.sx(i + 1), self.floor() - a.r, 0.32, 40)
                    b.move_to(self.sx(i), self.floor() - b.r, 0.32, -16)
                    swapped = True
                    yield 0.36
                else:
                    yield 0.12
                for bb in (self.bubbles[i], self.bubbles[i + 1]):
                    if bb.style == "cmp":
                        bb.style = "normal"
                self.cmp_pair = None
            self.fix(n - p)
            yield 0.25
            if not swapped:
                break
        for i in range(n):
            self.fix(i)
        yield 0.4

    def fix(self, k):
        if k in self.fixed:
            return
        self.fixed.add(k)
        b = self.bubbles[k]
        b.style = "fixed"
        b.move_to(self.sx(k), self.base_y(k), 0.5)

    def answer(self, swap):
        if not self.pending or self.penalty > 0:
            return False
        correct = self.pending[1]
        self.pending = None
        if swap == correct:
            self.correct += 1
            self.combo += 1
            self.wait = 0.08
            self.msg = "Dobrze!"
            return True
        self.mistakes += 1
        self.combo = 0
        self.penalty = PENALTY
        self.flash = 1.0
        for i in self.cmp_pair or ():
            self.bubbles[i].shake = 1
        self.msg = f"Błąd! Kara {PENALTY:.1f} s".replace(".", ",")
        return False

    def update(self, dt, elapsed, running):
        for b in self.bubbles:
            b.update(dt)
        self.flash = max(0.0, self.flash - dt * 2)
        if self.done or not running:
            return
        if self.penalty > 0:
            self.penalty -= dt
            if self.penalty <= 0:
                self.msg = "Dalej!"
            return
        if self.pending:
            if self.bot:
                self.think -= dt
                if self.think <= 0:
                    ok = self.rnd.random() < self.bot["acc"]
                    self.answer(self.pending[1] if ok else not self.pending[1])
            return
        if self.wait > 0:
            self.wait -= dt
            return
        while True:
            try:
                cmd = next(self.gen)
            except StopIteration:
                self.done = True
                self.finish_time = elapsed
                self.msg = "Posortowane!"
                return
            if isinstance(cmd, tuple):
                self.pending = cmd
                if self.bot:
                    self.think = max(0.3, self.rnd.gauss(self.bot["react"], self.bot["react"] * 0.25))
                    self.msg = "Myśli…"
                else:
                    a, b = self.bubbles[self.cmp_pair[0]], self.bubbles[self.cmp_pair[1]]
                    self.msg = f"Porównaj {a.v} i {b.v}"
                return
            self.wait = cmd
            if cmd > 0:
                return

    def draw(self, s, t, name, avatar, accent):
        r = self.rect

        def make_lane():
            sf = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(sf, (3, 22, 36, 150), sf.get_rect(), border_radius=18)
            return sf
        s.blit(cached(("lane", r.size), make_lane), r.topleft)
        pygame.draw.rect(s, accent, r, 2, border_radius=18)
        if self.flash > 0:
            pygame.draw.rect(s, ALARM, r, 4, border_radius=18)
        pygame.draw.line(s, PEARL, (r.x + 16, r.y + 26), (r.right - 16, r.y + 26), 1)
        for b in self.bubbles:
            b.draw(s, t)
        if self.pending and self.cmp_pair:
            a, b = self.bubbles[self.cmp_pair[0]], self.bubbles[self.cmp_pair[1]]
            mx = (a.x + b.x) / 2
            if self.bot:
                dots = "." * (1 + int(t * 3) % 3)
                text(s, dots, 30, CORAL, (mx, min(a.y - a.r, b.y - b.r) - 16), display=True)
            else:
                text(s, "?", 30, CORAL, (mx, self.floor() - max(a.r, b.r) * 0.4), display=True)
        # podpis toru: ludek, nick, stan
        sub = s.subsurface(pygame.Rect(r.x + 8, r.y - 46, 70, 46))
        draw_avatar(sub, 35, 60, 0.42, avatar, 0, bubbles=False)
        text(s, name, 22, INK, (r.x + 82, r.y - 22), "midleft", display=True)
        pr = f"{self.sorted_count()}/{self.n} na powierzchni"
        text(s, pr, 17, MUTED, (r.right - 12, r.y - 22), "midright", shadow=False)
        col = ALARM if self.penalty > 0 else (KELP if self.done else INK)
        text(s, self.msg, 18, col, (r.centerx, r.y - 22), bold=True, shadow=False)
        if self.penalty > 0:
            w = 200 * self.penalty / PENALTY
            pygame.draw.rect(s, ALARM, (r.centerx - 100, r.y - 6, w, 4), border_radius=2)


# ================================================================ duel
class DuelScene(Scene):
    def __init__(self, app, bot, size):
        super().__init__(app)
        self.bot = bot
        self.size = size
        self.world = app.world(bot["world"])
        values = make_values(size, "random")
        self.ai = Lane(self, values, pygame.Rect(40, 130, W - 80, 200), bot)
        self.me = Lane(self, values, pygame.Rect(40, 400, W - 80, 200))
        for b in self.me.bubbles:      # obrazki bąbelków przygotowane z góry (te same liczby w obu torach)
            b.warm(("normal", "cmp", "fixed"))
        self.t = 0.0
        self.countdown = 3.4
        self.elapsed = 0.0
        self.state = "count"     # count, run, pause, end
        self.particles = Particles()
        self.left_btn = Button("Zamień", (W / 2 - 170, 668), (300, 64), "coral", key="Z", font_size=28)
        self.right_btn = Button("Zostaw", (W / 2 + 170, 668), (300, 64), "ghost", key="X", font_size=28)
        self.pause_menu = ButtonList([
            Button("Wznów", (W / 2, 320), (320, 60), "pearl", key="Esc", action="resume"),
            Button("Poddaj się", (W / 2, 396), (320, 56), "primary", action="giveup"),
        ])
        self.result = None
        self.last_count = 4

    def finish(self, won):
        a = self.app
        p = a.save.p
        rec = p["duels"].setdefault(self.bot["id"], [0, 0])
        rec[0 if won else 1] += 1
        reward = self.bot["reward"] if won else 0
        p["pearls"] += reward
        a.quests.emit("duel_win" if won else "duel_loss", bot=self.bot["id"])
        a.save.write()
        self.state = "end"
        self.won = won
        self.reward = reward
        a.audio.play("win" if won else "lose")
        if won:
            self.particles.burst(W / 2, 260, PEARL, 40, 320)
        self.result = ButtonList([
            Button("Zmień rywala", (0, 0), (240, 60), "ghost", font_size=22, action="setup"),
            Button("Rewanż", (0, 0), (240, 60), "pearl", key="Enter", font_size=24, action="again"),
            Button("Menu", (0, 0), (160, 60), "ghost", font_size=22, action="menu"),
        ], vertical=False)
        row(self.result.buttons, W / 2, 520, max_w=720)
        self.result.index = 1

    def result_action(self, act):
        from scene_duel import DuelSetupScene
        if act == "again":
            self.app.go(DuelScene(self.app, self.bot, self.size))
        elif act == "setup":
            self.app.go(DuelSetupScene(self.app, BOTS.index(self.bot), self.size))
        else:
            go_menu(self.app)

    def press(self, btn, swap):
        if self.state != "run" or not self.me.pending or self.me.penalty > 0:
            return
        btn.flash = 1
        ok = self.me.answer(swap)
        q = self.app.quests
        if ok:
            self.app.audio.play("good")
            q.emit("correct")
            q.emit("combo", n=self.me.combo)
            if swap:
                self.app.audio.play("swap")
        else:
            self.app.audio.play("bad")

    def event(self, e):
        a = self.app
        if self.state == "end":
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and not self.result.using_keys:
                self.result_action("again")
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.result_action("setup")
                return
            b = self.result.handle(e, a)
            if b:
                self.result_action(b.action)
            return
        if self.state == "pause":
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.state = "run"
                return
            b = self.pause_menu.handle(e, a)
            if b:
                if b.action == "resume":
                    self.state = "run"
                else:
                    self.finish(False)
            return
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_p) and self.state == "run":
                self.state = "pause"
            elif e.key in (pygame.K_z, pygame.K_LEFT):
                self.press(self.left_btn, True)
            elif e.key in (pygame.K_x, pygame.K_RIGHT):
                self.press(self.right_btn, False)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.left_btn.hit(e.pos):
                self.press(self.left_btn, True)
            elif self.right_btn.hit(e.pos):
                self.press(self.right_btn, False)

    def update(self, dt):
        self.t += dt
        self.world.update(dt)
        self.particles.update(dt)
        m = self.app.mouse
        if self.state == "pause":
            self.pause_menu.update(dt, m, self.app.mouse_moved)
            return
        if self.state == "count":
            self.countdown -= dt
            c = math.ceil(self.countdown - 0.4)
            if c != self.last_count:
                self.last_count = c
                self.app.audio.play("pop" if c > 0 else "win")
            if self.countdown <= 0.4:
                self.state = "run"
        running = self.state == "run"
        if running:
            self.elapsed += dt
        self.ai.update(dt, self.elapsed, running)
        self.me.update(dt, self.elapsed, running)
        if running and (self.me.done or self.ai.done):
            me_t = self.me.finish_time if self.me.done else None
            ai_t = self.ai.finish_time if self.ai.done else None
            self.finish(me_t is not None and (ai_t is None or me_t <= ai_t))
        # przyciski nie migają między porównaniami; wyłączają się tylko na czas kary
        self.left_btn.enabled = self.right_btn.enabled = running and self.me.penalty <= 0 and not self.me.done
        self.left_btn.update(dt, m)
        self.right_btn.update(dt, m)
        if self.state == "end":
            self.result.update(dt, m, self.app.mouse_moved)

    def draw(self, s):
        self.world.draw(s)

        def make_bar():
            b = pygame.Surface((W, 74), pygame.SRCALPHA)
            b.fill((3, 22, 36, 200))
            return b
        s.blit(cached("hud_bar", make_bar), (0, 0))
        p = self.app.save.p
        text(s, "DUEL Z AI", 16, MUTED, (24, 22), "midleft", bold=True, shadow=False)
        text(s, f"{p['nick']}  kontra  {self.bot['nick']}", 26, INK, (24, 50), "midleft", display=True, max_w=560)
        tm = f"{self.elapsed:.1f} s".replace(".", ",")
        text(s, tm, 34, PEARL, (W / 2, 38), display=True)
        text(s, f"Poziom rywala: {self.bot['diff']}", 18, MUTED, (W - 24, 38), "midright", bold=True, shadow=False)
        self.ai.draw(s, self.t, self.bot["nick"], self.bot["avatar"], CORAL)
        self.me.draw(s, self.t, p["nick"] + " (ty)", p["avatar"], KELP)
        if self.state in ("run", "count"):
            self.left_btn.draw(s)
            self.right_btn.draw(s)
        self.particles.draw(s)
        if self.state == "count":
            c = math.ceil(self.countdown - 0.4)
            label = str(c) if c > 0 else "Start!"
            k = (self.countdown - 0.4) % 1
            text(s, label, int(90 + 40 * k), PEARL, (W / 2, 365), display=True)
        if self.state == "pause":
            dim(s, 170)
            r = pygame.Rect(0, 0, 420, 260)
            r.center = (W / 2, 350)
            panel(s, r, 235)
            text(s, "Pauza", 44, INK, (W / 2, 254), display=True)
            self.pause_menu.draw(s)
        if self.state == "end":
            dim(s, 150)
            r = pygame.Rect(0, 0, 780, 420)
            r.center = (W / 2, 380)
            panel(s, r, 238, edge=PEARL if self.won else ALARM)
            text(s, "Wygrana!" if self.won else "Tym razem lepszy był rywal", 48, PEARL if self.won else ALARM,
                 (W / 2, r.y + 56), display=True, max_w=r.w - 60)
            me_t = self.me.finish_time
            ai_t = self.ai.finish_time
            fmt = lambda v: "nie ukończono" if v is None else f"{v:.1f} s".replace(".", ",")
            lines = [("Twój czas", fmt(me_t)), (f"Czas: {self.bot['nick']}", fmt(ai_t)),
                     ("Twoje błędy", str(self.me.mistakes)), ("Dobre odpowiedzi", str(self.me.correct))]
            y = r.y + 120
            for lab, val in lines:
                text(s, lab, 22, MUTED, (W / 2 - 20, y), "midright", shadow=False)
                text(s, val, 24, INK, (W / 2 + 20, y), "midleft", bold=True, shadow=False)
                y += 36
            if self.reward:
                draw_pearl(s, W / 2 - 50, r.y + 290, 12)
                text(s, f"+{self.reward} pereł", 26, PEARL, (W / 2 - 32, r.y + 290), "midleft", display=True)
            self.result.draw(s)
