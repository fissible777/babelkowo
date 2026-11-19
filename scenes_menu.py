"""Sceny poza rozgrywką: menu główne, mapa poziomów, samouczek, ustawienia, zakończenie."""
import math
import random

import pygame

from core import (cached, W, H, INK, MUTED, AQUA, CORAL, PEARL, KELP, ALARM, NAVY, Button, ButtonList, font, text, draw_swap_icon,
                  text_block, panel, draw_star, draw_lock, mix)
from levels import LEVELS, COMING_SOON
from world import WORLDS, WORLD_ORDER, PREVIEW_WORLD, Mascot, Bubble, draw_bubble, bubble_label_cols


class Scene:
    def __init__(self, app):
        self.app = app

    def event(self, e):
        pass

    def update(self, dt):
        pass

    def draw(self, s):
        pass


def draw_title(s, t, y=165, size=128):
    word = "Bąbelkowo"
    f = font(size, display=True)
    widths = [f.size(ch)[0] for ch in word]
    x = W / 2 - sum(widths) / 2
    for i, ch in enumerate(word):
        dy = math.sin(t * 2.2 + i * 0.55) * 7
        col = PEARL if ch in "ąo" else INK
        sh = f.render(ch, True, (3, 26, 40))
        s.blit(sh, (x + 4, y - size * 0.6 + dy + 7))
        img = f.render(ch, True, col)
        s.blit(img, (x, y - size * 0.6 + dy))
        x += widths[i]


# ---------------------------------------------------------------- menu
class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.world = app.world("plycizna")
        self.t = 0
        self.mascot = Mascot(160, 470)
        self.next_wander = 2
        cx = W // 2
        small = (184, 52)
        self.menu = ButtonList([
            Button("Graj", (cx, 318), (380, 62), "pearl", font_size=32, action="play"),
            Button("Duel z AI", (cx, 390), (380, 56), "coral", font_size=28, action="duel"),
            Button("Zadania", (cx - 98, 456), small, "primary", font_size=24, action="quests"),
            Button("Rankingi", (cx + 98, 456), small, "primary", font_size=24, action="ranking"),
            Button("Profil", (cx - 98, 520), small, "primary", font_size=24, action="profile"),
            Button("Jak grać", (cx + 98, 520), small, "primary", font_size=24, action="help"),
            Button("Ustawienia", (cx - 98, 584), small, "ghost", font_size=22, action="settings"),
            Button("Wyjście", (cx + 98, 584), small, "ghost", font_size=22, action="quit"),
        ], grid=True)
        self.card = pygame.Rect(20, 16, 300, 92)
        self.claimable = app.quests.claimable_count()
        self.deco = [[random.uniform(80, W - 80), random.uniform(0, H), random.uniform(10, 34), random.uniform(18, 40)]
                     for _ in range(10)]

    def event(self, e):
        b = self.menu.handle(e, self.app)
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.quit()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.card.collidepoint(e.pos):
            self.app.audio.play("click")
            from scene_social import ProfileScene
            self.app.go(ProfileScene(self.app))
            return
        if not b:
            return
        if b.action in ("duel", "quests", "ranking", "profile"):
            import scene_social
            import scene_duel
            scene = {"duel": scene_duel.DuelSetupScene, "quests": scene_social.QuestsScene,
                     "ranking": scene_social.RankingScene, "profile": scene_social.ProfileScene}[b.action]
            self.app.go(scene(self.app))
            return
        if b.action == "play":
            if not self.app.save.data["seen_help"]:
                self.app.save.data["seen_help"] = True
                self.app.save.write()
                self.app.go(HowToScene(self.app, then_play=True))
            else:
                self.app.go(LevelSelectScene(self.app))
        elif b.action == "help":
            self.app.go(HowToScene(self.app))
        elif b.action == "settings":
            self.app.go(SettingsScene(self.app))
        elif b.action == "quit":
            self.app.quit()

    def update(self, dt):
        self.t += dt
        self.world.update(dt)
        self.mascot.update(dt)
        self.next_wander -= dt
        if self.next_wander <= 0:
            self.next_wander = random.uniform(2.5, 4.5)
            side = random.choice([(random.uniform(90, 320), random.uniform(330, 600)),
                                  (random.uniform(960, 1190), random.uniform(330, 600))])
            self.mascot.goto(*side)
        for d in self.deco:
            d[1] -= d[3] * dt
            if d[1] < -50:
                d[1] = H + 50
                d[0] = random.uniform(80, W - 80)
        self.menu.update(dt, self.app.mouse, self.app.mouse_moved)

    def draw(self, s):
        self.world.draw(s)
        for x, y, r, _ in self.deco:
            draw_bubble(s, x, y, r, alpha=140)
        draw_title(s, self.t, y=150, size=116)
        text(s, "Gra o sortowaniu bąbelkowym", 28, AQUA, (W / 2, 238), bold=True)
        self.mascot.draw(s)
        self.menu.draw(s)
        if self.claimable:   # znaczek: nagrody czekają w Zadaniach
            qb = self.menu.buttons[2].rect
            pygame.draw.circle(s, ALARM, (qb.right - 6, qb.y + 4), 14)
            text(s, str(self.claimable), 16, INK, (qb.right - 6, qb.y + 4), bold=True, shadow=False)
        self.draw_card(s)
        text(s, "Strzałki i Enter albo mysz  ·  F11 pełny ekran", 18, MUTED, (W / 2, H - 22))

    def draw_card(self, s):
        """Karta gracza w rogu: ludek, nick, perły i najwyższy poziom. Kliknięcie otwiera profil."""
        from ludek import draw_avatar, draw_pearl
        save = self.app.save
        p = save.p
        r = self.card
        hover = r.collidepoint(self.app.mouse)
        panel(s, r, 225, edge=PEARL if hover else (60, 120, 150))
        sub = s.subsurface(pygame.Rect(r.x + 6, r.y + 6, 80, r.h - 12))
        draw_avatar(sub, 40, 70, 0.5, p["avatar"], self.t, bubbles=False)
        text(s, p["nick"], 24, INK, (r.x + 92, r.y + 28), "midleft", display=True, max_w=r.w - 104)
        draw_pearl(s, r.x + 102, r.y + 64, 9)
        text(s, str(p["pearls"]), 19, PEARL, (r.x + 116, r.y + 64), "midleft", bold=True, shadow=False)
        draw_star(s, r.x + 186, r.y + 64, 10, True)
        hl = save.highest_level()
        text(s, f"poz. {hl}" if hl else "start", 18, INK, (r.x + 202, r.y + 64), "midleft", bold=True, shadow=False)


# ---------------------------------------------------------------- mapa poziomów
NODE_POS = [(230 + j * 273, 410 + math.sin(j * 1.9 + 0.5) * 70) for j in range(4)]
NW = len(WORLD_ORDER)          # liczba światów z poziomami
SOON = NW                      # indeks ostatniej zakładki: „Wkrótce”


class LevelSelectScene(Scene):
    def __init__(self, app, focus=None):
        super().__init__(app)
        save = app.save
        if focus is None:
            focus = max([l["id"] for l in LEVELS if save.unlocked(l["id"])])
        self.sel = focus
        self.wi = WORLD_ORDER.index(LEVELS[focus - 1]["world"])
        self.t = 0
        self.hover = None
        self.back = Button("Menu", (100, 46), (150, 50), "ghost", key="Esc", font_size=22)
        self.prev = Button("‹", (52, 410), (64, 84), "ghost", font_size=44)
        self.next = Button("›", (W - 52, 410), (64, 84), "ghost", font_size=44)
        self.bubble_r = 62
        self.grow = [0.0] * 4

    def world_key(self):
        return PREVIEW_WORLD if self.wi == SOON else WORLD_ORDER[self.wi]

    def world_unlocked(self, wi):
        return wi < NW and self.app.save.unlocked(wi * 4 + 1)

    def node_at(self, pos):
        if self.wi == SOON:
            return None
        for j, (x, y) in enumerate(NODE_POS):
            if math.hypot(pos[0] - x, pos[1] - y) < self.bubble_r + 6:
                return self.wi * 4 + j + 1
        return None

    def start(self, lid):
        if self.app.save.unlocked(lid):
            from scene_game import GameScene
            self.app.go(GameScene(self.app, lid))
        else:
            self.app.audio.play("bad")

    def show_world(self, wi):
        if wi == self.wi or not (0 <= wi <= SOON):
            return
        self.wi = wi
        self.app.audio.play("swap")
        if wi < NW and not (wi * 4 < self.sel <= wi * 4 + 4):
            self.sel = wi * 4 + 1

    def event(self, e):
        a = self.app
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.back.hit(e.pos):
                a.audio.play("click")
                a.go(MenuScene(a))
                return
            if self.prev.hit(e.pos):
                self.show_world(self.wi - 1)
                return
            if self.next.hit(e.pos):
                self.show_world(self.wi + 1)
                return
            for k in range(SOON + 1):
                if self.tab_rect(k).collidepoint(e.pos):
                    self.show_world(k)
                    return
            lid = self.node_at(e.pos)
            if lid:
                a.audio.play("click")
                self.start(lid)
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                a.go(MenuScene(a))
            elif e.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_LEFT, pygame.K_a):
                d = 1 if e.key in (pygame.K_RIGHT, pygame.K_d) else -1
                a.audio.play("tick")
                if self.wi == SOON:
                    if d < 0:
                        self.wi, self.sel = NW - 1, len(LEVELS)
                    return
                if d > 0 and self.sel == len(LEVELS):
                    self.wi = SOON          # za ostatnim poziomem: podgląd „Wkrótce”
                    return
                self.sel = max(1, min(len(LEVELS), self.sel + d))
                self.wi = (self.sel - 1) // 4
            elif e.key in (pygame.K_q, pygame.K_PAGEUP):
                self.show_world(self.wi - 1)
            elif e.key in (pygame.K_e, pygame.K_PAGEDOWN):
                self.show_world(self.wi + 1)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                if self.wi == SOON:
                    a.audio.play("bad")
                else:
                    self.start(self.sel)

    def update(self, dt):
        self.t += dt
        self.app.world(self.world_key()).update(dt)
        m = self.app.mouse
        self.hover = self.node_at(m)
        if self.hover:
            self.sel = self.hover
        for j in range(4):   # zaznaczony bąbelek rośnie płynnie zamiast skokiem
            want = 8.0 if self.wi * 4 + j + 1 == self.sel else 0.0
            self.grow[j] += (want - self.grow[j]) * min(1.0, dt * 12)
        self.prev.enabled = self.wi > 0
        self.next.enabled = self.wi < SOON
        for b in (self.back, self.prev, self.next):
            b.update(dt, m)

    def tab_rect(self, k):
        n = SOON + 1
        gap = 8
        w = min(200, (W - 80 - gap * (n - 1)) // n)
        r = pygame.Rect(0, 0, w, 44)
        r.center = (W / 2 + (k - (n - 1) / 2) * (w + gap), 114)
        return r

    def draw(self, s):
        save = self.app.save
        self.app.world(self.world_key()).draw(s)

        def make_band():   # ciemniejszy pas pod nagłówkiem: napisy czytelne także na jasnych światach
            band = pygame.Surface((W, 160), pygame.SRCALPHA)
            for y in range(160):
                pygame.draw.line(band, (3, 22, 36, int(190 * (1 - y / 160) ** 1.4)), (0, y), (W, y))
            return band
        s.blit(cached("map_band", make_band), (0, 0))
        text(s, "Mapa poziomów", 40, INK, (W / 2, 46), display=True)
        draw_star(s, W - 150, 46, 16, True)
        text(s, f"{save.total_stars()} / {len(LEVELS) * 3}", 26, PEARL, (W - 126, 46), "midleft", bold=True)
        # zakładki światów + „Wkrótce”
        for k in range(SOON + 1):
            r = self.tab_rect(k)
            active = k == self.wi
            soon = k == SOON
            col = (255, 211, 126) if active else ((44, 24, 66) if soon else (10, 50, 74))
            pygame.draw.rect(s, (2, 14, 24), r.move(0, 4), border_radius=22)
            pygame.draw.rect(s, col, r, border_radius=22)
            if soon:
                pygame.draw.rect(s, (230, 190, 250) if not active else (255, 240, 200), r, 2, border_radius=22)
            fg = NAVY if active else INK
            name = "Wkrótce" if soon else WORLDS[WORLD_ORDER[k]]["name"]
            pad = 16
            if not soon and not self.world_unlocked(k):
                fg = MUTED if not active else NAVY
                draw_lock(s, r.x + 20, r.centery - 2, 0.55, fg)
                pad = 34
            text(s, name, 20, fg, (r.centerx + (pad - 16) / 2, r.centery), bold=True, shadow=False, max_w=r.w - pad - 12)
        if self.wi == SOON:
            self.draw_soon(s)
        else:
            self.draw_nodes(s)
        for b in (self.back, self.prev, self.next):
            b.draw(s)
        def make_foot():
            f = pygame.Surface((620, 30), pygame.SRCALPHA)
            pygame.draw.rect(f, (3, 22, 36, 160), f.get_rect(), border_radius=15)
            return f
        s.blit(cached("map_foot", make_foot), (W / 2 - 310, H - 35))
        text(s, "Strzałki: wybór poziomu   ·   Q / E: zmiana świata   ·   Enter: start", 18, (200, 225, 235), (W / 2, H - 20))

    def draw_nodes(self, s):
        save = self.app.save
        pts = []
        for j in range(3):
            (x1, y1), (x2, y2) = NODE_POS[j], NODE_POS[j + 1]
            for q in range(1, 12):
                u = q / 12
                pts.append((x1 + (x2 - x1) * u, y1 + (y2 - y1) * u + math.sin(u * math.pi) * -40))
        for i, (x, y) in enumerate(pts):
            pygame.draw.circle(s, (230, 250, 255), (x, y), 3 + (i % 2))
        for j, (x, y) in enumerate(NODE_POS):
            lid = self.wi * 4 + j + 1
            L = LEVELS[lid - 1]
            unlocked = save.unlocked(lid)
            st = save.stars(lid)
            selected = lid == self.sel
            # bąbelek kołysze się płynnie (co ¼ piksela), a podpisy pod nim stoją w miejscu
            bob = math.sin(self.t * 2 + j) * 5
            r = self.bubble_r + round(self.grow[j])
            style = "fixed" if st == 3 else ("select" if selected and unlocked else "normal")
            if unlocked:
                col, sh = bubble_label_cols(style)
                draw_bubble(s, x, y + bob, r, style, str(lid), col, sh, label_size=46)
                for k in range(3):
                    draw_star(s, x - 30 + k * 30, y + self.bubble_r + 32, 13, k < st)
            else:
                draw_bubble(s, x, y + bob, r, style, alpha=110)
                draw_lock(s, x, round(y + bob) - 4, 1.5)
            name_col = INK if unlocked else MUTED

            def make_plate():
                pl = pygame.Surface((264, 58), pygame.SRCALPHA)
                pygame.draw.rect(pl, (3, 22, 36, 150), pl.get_rect(), border_radius=14)
                return pl
            s.blit(cached("node_plate", make_plate), (x - 132, y + self.bubble_r + 45))
            text(s, L["name"], 22, name_col, (x, y + self.bubble_r + 62), bold=True, max_w=250)
            tag = "Układanka" if L["mode"] == "puzzle" else ("Decyzje + koniec" if L["early"] else "Decyzje")
            if L.get("timer"):
                tag += f" · {L['timer']:g} s".replace(".", ",")
            if L.get("hidden"):
                tag += " · lód"
            if L.get("dupes"):
                tag += " · równe"
            text(s, tag, 17, MUTED, (x, y + self.bubble_r + 86), max_w=250)

    def draw_soon(self, s):
        """Podgląd ostatniej mapy: tło świata widać w pełni, na środku tabliczka „Wkrótce”."""
        r = pygame.Rect(0, 0, 560, 250)
        r.center = (W / 2, 440)
        panel(s, r, 225, edge=(230, 190, 250))
        text(s, "PODGLĄD OSTATNIEJ MAPY", 16, (230, 190, 250), (W / 2, r.y + 32), bold=True)
        text(s, COMING_SOON["name"], 48, INK, (W / 2, r.y + 80), display=True)
        pulse = 0.5 + 0.5 * math.sin(self.t * 3)
        badge = pygame.Rect(0, 0, 200, 44)
        badge.center = (W / 2, r.y + 136)
        pygame.draw.rect(s, mix((255, 211, 126), (255, 236, 190), pulse), badge, border_radius=22)
        draw_lock(s, badge.x + 30, badge.centery - 2, 0.6, NAVY)
        text(s, "WKRÓTCE", 24, NAVY, (badge.centerx + 14, badge.centery), display=True, shadow=False)
        text_block(s, COMING_SOON["text"], 20, INK, (r.x + 40, r.y + 172), r.w - 80, 26, max_h=60)


# ---------------------------------------------------------------- samouczek
PAGES = [
    ("Na czym polega sortowanie bąbelkowe?",
     "Idziemy od lewej do prawej i porównujemy dwa sąsiednie bąbelki. Jeśli lewy jest większy, zamieniamy je. "
     "Dzięki temu największy bąbelek „płynie” w prawo aż na koniec, jak bąbelek powietrza do powierzchni. "
     "Potem powtarzamy to samo dla reszty, za każdym razem o jeden krócej.", "compare"),
    ("Tryb Decyzje",
     "Dwa podświetlone bąbelki to aktualne porównanie. Wciśnij Z, aby je zamienić, albo X, aby je zostawić. "
     "Możesz też klikać przyciski. Masz 3 życia, a w dalszych światach także limit czasu na decyzję. "
     "Dobre decyzje z rzędu budują serię i dają więcej punktów.", "keys"),
    ("Pytanie o koniec",
     "W niektórych poziomach po każdym przejściu pada pytanie: grać dalej czy koniec? "
     "Jeśli w całym przejściu nie było ani jednej zamiany, tablica jest już posortowana i trzeba wybrać Koniec. "
     "To właśnie flaga „zamieniono” z pseudokodu, dzięki której najlepszy przypadek trwa tylko O(n).", "flag"),
    ("Tryb Układanka",
     "Tu sam wybierasz, które sąsiednie bąbelki zamienić: strzałkami i spacją albo klikając przycisk zamiany pod bąbelkami. "
     "Inwersja to para liczb w złej kolejności. Każda dobra zamiana usuwa dokładnie jedną inwersję, "
     "więc najmniejsza możliwa liczba ruchów to liczba inwersji. Tyle samo zamian robi sortowanie bąbelkowe!", "puzzle"),
    ("Lód i równe liczby",
     "W Lodowej zatoce liczby zamarzają: widzisz tylko dwa porównywane bąbelki. To wystarczy, bo algorytm "
     "też patrzy tylko na parę sąsiadów. We Wraku statku liczby się powtarzają. Gdy porównujesz dwie równe, "
     "wybierz Zostaw. Równych nie zamieniamy, dlatego sortowanie bąbelkowe jest stabilne: równe elementy "
     "zachowują swoją kolejność.", "equal"),
]


class HowToScene(Scene):
    def __init__(self, app, then_play=False):
        super().__init__(app)
        self.world = app.world("plycizna")
        self.page = 0
        self.t = 0
        self.then_play = then_play
        self.nav = ButtonList([
            Button("Wstecz", (W / 2 - 170, 622), (220, 58), "ghost", font_size=24, action="prev"),
            Button("Dalej", (W / 2 + 170, 622), (220, 58), "pearl", font_size=24, action="next"),
        ], vertical=False)
        self.nav.index = 1

    def leave(self):
        if self.then_play:
            self.app.go(LevelSelectScene(self.app))
        else:
            self.app.go(MenuScene(self.app))

    def turn(self, d):
        np = self.page + d
        if np < 0:
            return
        if np >= len(PAGES):
            self.leave()
            return
        self.page = np
        self.t = 0
        self.app.audio.play("swap")

    def event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.leave()
                return
            if e.key in (pygame.K_RIGHT, pygame.K_d) and not self.nav.using_keys:
                self.turn(1)
                return
            if e.key in (pygame.K_LEFT, pygame.K_a) and not self.nav.using_keys:
                self.turn(-1)
                return
        b = self.nav.handle(e, self.app)
        if b:
            self.turn(1 if b.action == "next" else -1)

    def update(self, dt):
        self.t += dt
        self.world.update(dt)
        last = self.page == len(PAGES) - 1
        self.nav.buttons[1].label = ("Graj!" if self.then_play else "Gotowe") if last else "Dalej"
        self.nav.buttons[0].enabled = self.page > 0
        self.nav.update(dt, self.app.mouse, self.app.mouse_moved)

    def draw(self, s):
        self.world.draw(s, dim=90)
        title, body, ill = PAGES[self.page]
        r = pygame.Rect(90, 40, W - 180, 640)
        panel(s, r, 225)
        text(s, f"Jak grać · {self.page + 1}/{len(PAGES)}", 20, AQUA, (r.x + 40, r.y + 38), "midleft", bold=True)
        text(s, title, 40, INK, (r.x + 40, r.y + 84), "midleft", display=True)
        text_block(s, body, 24, INK, (r.x + 40, r.y + 130), 520, 34, max_h=380)
        self.illustrate(s, ill, pygame.Rect(r.x + 620, r.y + 110, 480, 400))
        # kropki stron
        for k in range(len(PAGES)):
            pygame.draw.circle(s, PEARL if k == self.page else (60, 100, 120), (W / 2 - (len(PAGES) - 1) * 12 + k * 24, 560), 6)
        self.nav.draw(s)

    def illustrate(self, s, kind, area):
        t = self.t
        cx, cy = area.center
        if kind == "compare":
            vals = [12, 5, 17, 8]
            p = (t % 4) / 4
            for i, v in enumerate(vals):
                x = area.x + 70 + i * 112
                y = cy + 30
                if i in (0, 1):
                    swap = min(1, max(0, (p - 0.35) / 0.3))
                    e = swap * swap * (3 - 2 * swap)
                    x = x + (112 if i == 0 else -112) * e
                    y = y - math.sin(math.pi * e) * (60 if i == 0 else -20)
                b = Bubble(v, x, y, 30 + v * 1.6)
                b.phase = i * 1.3  # stała faza kołysania, inaczej bąbelek drga co klatkę
                b.style = "cmp" if i in (0, 1) and p < 0.7 else "normal"
                b.draw(s, t)
            text(s, "12 > 5, więc zamień", 30, CORAL, (cx, area.y + 40), bold=True)
        elif kind == "keys":
            for k, (lab, hint, style) in enumerate((("Zamień", "Z", "coral"), ("Zostaw", "X", "ghost"))):
                b = Button(lab, (cx, area.y + 110 + k * 100), (300, 72), style, key=hint, font_size=30)
                b.hover = 0.5 + 0.5 * math.sin(t * 3 + k * 3)
                b.draw(s)
            for k in range(3):
                from core import draw_heart
                draw_heart(s, cx - 50 + k * 50, area.y + 320, 16, True)
        elif kind == "flag":
            vals = [3, 6, 9, 14]
            for i, v in enumerate(vals):
                b = Bubble(v, area.x + 70 + i * 112, cy - 20, 30 + v * 1.6)
                b.phase = i * 1.3  # stała faza kołysania, inaczej bąbelek drga co klatkę
                b.draw(s, t)
            text(s, "zamiany w tym przejściu: 0", 26, INK, (cx, cy + 90), bold=True)
            b = Button("Koniec", (cx, cy + 165), (260, 66), "pearl", key="X", font_size=28)
            b.hover = 0.5 + 0.5 * math.sin(t * 4)
            b.draw(s)
        elif kind == "equal":
            vals = [("?", 11), (7, 7), (7, 7), ("?", 15)]
            for i, (lab, v) in enumerate(vals):
                b = Bubble(v, area.x + 70 + i * 112, cy - 10, 30 + v * 1.6)
                b.phase = i * 1.3  # stała faza kołysania, inaczej bąbelek drga co klatkę
                b.hidden = lab == "?"
                b.style = "cmp" if lab != "?" else "normal"
                b.draw(s, t)
            text(s, "7 = 7, więc zostaw", 30, KELP, (cx, area.y + 40), bold=True)
            b = Button("Zostaw", (cx, cy + 120), (260, 66), "ghost", key="X", font_size=28)
            b.hover = 0.5 + 0.5 * math.sin(t * 4)
            b.draw(s)
        elif kind == "puzzle":
            vals = [9, 4, 13, 7]
            for i, v in enumerate(vals):
                b = Bubble(v, area.x + 70 + i * 112, cy, 30 + v * 1.6)
                b.phase = i * 1.3  # stała faza kołysania, inaczej bąbelek drga co klatkę
                b.draw(s, t)
            for g in range(3):
                gx = area.x + 126 + g * 112
                sel = g == int(t) % 3
                pygame.draw.circle(s, KELP if sel else (14, 58, 84), (gx, cy + 95), 22)
                draw_swap_icon(s, gx, cy + 95, NAVY if sel else AQUA)
            text(s, "inwersje: (9,4) (9,7) (13,7)  =  3", 24, PEARL, (cx, area.y + 40), bold=True)


# ---------------------------------------------------------------- ustawienia
class SettingsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.world = app.world("rafa")
        self.confirm = False
        cx = W // 2
        self.menu = ButtonList([
            Button("", (cx, 250), (440, 62), "primary", action="music"),
            Button("", (cx, 330), (440, 62), "primary", action="sfx"),
            Button("", (cx, 410), (440, 62), "primary", action="full"),
            Button("", (cx, 490), (440, 62), "ghost", action="reset"),
            Button("Powrót", (cx, 600), (300, 60), "pearl", key="Esc", action="back"),
        ])

    def refresh(self):
        d = self.app.save.data
        on = lambda v: "wł." if v else "wył."
        self.menu.buttons[0].label = f"Muzyka: {on(d['music'])}"
        self.menu.buttons[1].label = f"Efekty dźwiękowe: {on(d['sfx'])}"
        self.menu.buttons[2].label = f"Pełny ekran: {on(d['fullscreen'])}"
        self.menu.buttons[3].label = "Na pewno? Kliknij jeszcze raz" if self.confirm else "Wyzeruj postęp"
        self.menu.buttons[3].style = "coral" if self.confirm else "ghost"

    def event(self, e):
        a = self.app
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            a.go(MenuScene(a))
            return
        b = self.menu.handle(e, a)
        if not b:
            return
        d = a.save.data
        if b.action != "reset":
            self.confirm = False
        if b.action == "music":
            d["music"] = not d["music"]
            a.audio.apply_music()
        elif b.action == "sfx":
            d["sfx"] = not d["sfx"]
        elif b.action == "full":
            a.toggle_fullscreen()
        elif b.action == "reset":
            if self.confirm:
                a.save.reset()
                self.confirm = False
                a.toast("Postęp wyzerowany")
            else:
                self.confirm = True
        elif b.action == "back":
            a.go(MenuScene(a))
        a.save.write()

    def update(self, dt):
        self.world.update(dt)
        self.refresh()
        self.menu.update(dt, self.app.mouse, self.app.mouse_moved)

    def draw(self, s):
        self.world.draw(s, dim=60)
        panel(s, pygame.Rect(W / 2 - 300, 110, 600, 560), 210)
        text(s, "Ustawienia", 46, INK, (W / 2, 168), display=True)
        self.menu.draw(s)


# ---------------------------------------------------------------- zakończenie
class EndingScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.world = app.world(PREVIEW_WORLD)
        self.t = 0
        self.mascot = Mascot(W / 2, 470)
        self.mascot.feel("happy", 999)
        self.btn = ButtonList([Button("Menu główne", (W / 2, 640), (320, 62), "pearl", action="menu")])
        self.confetti = [[random.uniform(0, W), random.uniform(-H, 0), random.uniform(40, 120),
                          random.choice([PEARL, CORAL, AQUA, KELP])] for _ in range(70)]

    def event(self, e):
        if self.btn.handle(e, self.app) or (e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_RETURN)):
            self.app.go(MenuScene(self.app))

    def update(self, dt):
        self.t += dt
        self.world.update(dt)
        self.mascot.update(dt)
        for c in self.confetti:
            c[1] += c[2] * dt
            if c[1] > H + 10:
                c[1] = -10
        self.btn.update(dt, self.app.mouse, self.app.mouse_moved)

    def draw(self, s):
        self.world.draw(s)
        for x, y, _, col in self.confetti:
            pygame.draw.circle(s, col, (x + math.sin(self.t * 2 + y * 0.02) * 10, y), 5)
        panel(s, pygame.Rect(W / 2 - 470, 70, 940, 380), 225)
        text(s, "Wszystkie poziomy ukończone!", 52, PEARL, (W / 2, 120), display=True)
        st = self.app.save.total_stars()
        text(s, f"Zebrane gwiazdki: {st} / {len(LEVELS) * 3}", 30, INK, (W / 2, 190), bold=True)
        lines = [
            "Sortowanie bąbelkowe: porównuj sąsiadów, większy w prawo.",
            "Najgorszy i średni przypadek: O(n²). Najlepszy, z flagą: O(n).",
            "Liczba zamian = liczba inwersji. Sortuje w miejscu i jest stabilne.",
            "",
            f"Następna mapa, {COMING_SOON['name']}, już wkrótce!",
        ]
        for i, ln in enumerate(lines):
            if ln:
                text(s, ln, 24, PEARL if "wkrótce" in ln else INK, (W / 2, 260 + i * 38), bold="wkrótce" in ln)
        self.mascot.draw(s)
        self.btn.draw(s)
