"""Ekrany: profil gracza (nick, ludek, sklep, statystyki), zadania i rankingi."""
import datetime
import math

import pygame

from core import (W, H, INK, MUTED, AQUA, CORAL, PEARL, KELP, ALARM, NAVY, SHADOW, Button, ButtonList, cached,
                  text, text_block, panel, draw_star, draw_lock, mix, row)
from levels import LEVELS
from ludek import (SUITS, SKINS, HATS, ACCS, owns, draw_avatar, draw_pearl, RANK_BOTS, bot_time, bot_stars)
from scenes_menu import Scene
from world import WORLDS


def go_menu(app):
    from scenes_menu import MenuScene
    app.go(MenuScene(app))


def header(s, title, app):
    def make_band():
        band = pygame.Surface((W, 150), pygame.SRCALPHA)
        for y in range(150):
            pygame.draw.line(band, (3, 22, 36, int(190 * (1 - y / 150) ** 1.4)), (0, y), (W, y))
        return band
    s.blit(cached("social_band", make_band), (0, 0))
    text(s, title, 40, INK, (W / 2, 46), display=True)
    draw_pearl(s, W - 150, 46, 12)
    text(s, str(app.save.p["pearls"]), 26, PEARL, (W - 130, 46), "midleft", bold=True)


def bar(s, rect, ratio, col=KELP):
    pygame.draw.rect(s, (3, 22, 36), rect, border_radius=rect.h // 2)
    if ratio > 0:
        pygame.draw.rect(s, col, (rect.x, rect.y, max(rect.h, rect.w * min(1, ratio)), rect.h), border_radius=rect.h // 2)


def fmt_time(sec):
    return f"{sec:.1f} s".replace(".", ",")


# ================================================================ PROFIL
ROWS = [("suit", "Kolor stroju", SUITS), ("skin", "Kolor skóry", SKINS), ("hat", "Nakrycie głowy", HATS),
        ("acc", "Dodatek", ACCS)]


class ProfileScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.world = app.world("rafa")
        self.t = 0.0
        self.back = Button("Menu", (100, 46), (150, 50), "ghost", key="Esc", font_size=22)
        self.row = 0                # 0 = nick, 1..4 = wygląd
        self.editing = False
        self.typed = ""
        self.load()

    def load(self):
        p = self.app.save.p
        self.preview = dict(p["avatar"])
        self.buttons = []
        self.arrows = []
        for i, (kind, label, table) in enumerate(ROWS):
            y = 168 + i * 64
            self.arrows.append((Button("‹", (800, y), (48, 44), "ghost", font_size=30),
                                Button("›", (1040, y), (48, 44), "ghost", font_size=30)))
        self.buy = [Button("Kup", (1165, 168 + i * 64), (140, 44), "pearl", font_size=20) for i in range(4)]
        self.nick_rect = pygame.Rect(70, 548, 360, 54)
        self.prev_prof = Button("‹", (88, 640), (44, 44), "ghost", font_size=28)
        self.next_prof = Button("›", (300, 640), (44, 44), "ghost", font_size=28)
        self.new_prof = Button("Nowy profil", (390, 640), (120, 44), "primary", font_size=18)

    # ----- akcje -----
    def change(self, r, d):
        kind, _, table = ROWS[r]
        self.preview[kind] = (self.preview[kind] + d) % len(table)
        p = self.app.save.p
        if kind in ("suit", "skin") or owns(p, kind, self.preview[kind]):
            p["avatar"][kind] = self.preview[kind]
            self.app.save.dirty = True
        self.app.audio.play("tick")

    def try_buy(self, r):
        kind, _, table = ROWS[r]
        if kind not in ("hat", "acc"):
            return
        i = self.preview[kind]
        p = self.app.save.p
        name, cost = table[i]
        if owns(p, kind, i):
            return
        if p["pearls"] < cost:
            self.app.audio.play("bad")
            self.app.toast(f"Potrzebujesz {cost} pereł. Zdobywaj je w Zadaniach i duelach.")
            return
        p["pearls"] -= cost
        p["owned"].append(f"{kind}:{i}")
        p["avatar"][kind] = i
        self.app.save.write()
        self.app.audio.play("win")
        self.app.toast(f"Kupiono: {name}!")

    def start_edit(self, clear=False):
        self.editing = True
        self.typed = "" if clear else self.app.save.p["nick"]
        pygame.key.start_text_input()

    def end_edit(self, keep=True):
        self.editing = False
        pygame.key.stop_text_input()
        nick = " ".join(self.typed.split())[:14]
        if keep and nick:
            self.app.save.p["nick"] = nick
            self.app.save.write()

    def switch_profile(self, d):
        ids = self.app.save.profile_ids()
        cur = ids.index(self.app.save.data["current"])
        self.app.save.switch(ids[(cur + d) % len(ids)])
        self.load()
        self.app.audio.play("swap")

    def leave(self):
        if self.editing:
            self.end_edit()
        self.app.save.write()
        go_menu(self.app)

    # ----- zdarzenia -----
    def event(self, e):
        if self.editing:
            if e.type == pygame.TEXTINPUT:
                if len(self.typed) < 14:
                    self.typed += "".join(ch for ch in e.text if ch.isprintable())
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_BACKSPACE:
                    self.typed = self.typed[:-1]
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.end_edit()
                    self.app.audio.play("good")
                elif e.key == pygame.K_ESCAPE:
                    self.end_edit(keep=False)
            elif e.type == pygame.MOUSEBUTTONDOWN and not self.nick_rect.collidepoint(e.pos):
                self.end_edit()
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            pos = e.pos
            if self.back.hit(pos):
                self.app.audio.play("click")
                self.leave()
            elif self.nick_rect.collidepoint(pos):
                self.row = 0
                self.start_edit()
            elif self.prev_prof.hit(pos):
                self.switch_profile(-1)
            elif self.next_prof.hit(pos):
                self.switch_profile(1)
            elif self.new_prof.hit(pos):
                n = len(self.app.save.profile_ids()) + 1
                self.app.save.create_profile(f"Gracz {n}")
                self.load()
                self.app.audio.play("good")
                self.start_edit(clear=True)
            for r, (lb, rb) in enumerate(self.arrows):
                if lb.hit(pos):
                    self.row = r + 1
                    self.change(r, -1)
                elif rb.hit(pos):
                    self.row = r + 1
                    self.change(r, 1)
                elif self.buy[r].hit(pos) and self.buy_visible(r):
                    self.row = r + 1
                    self.try_buy(r)
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.leave()
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.row = (self.row - 1) % 5
                self.app.audio.play("tick")
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.row = (self.row + 1) % 5
                self.app.audio.play("tick")
            elif e.key in (pygame.K_LEFT, pygame.K_RIGHT) and self.row > 0:
                self.change(self.row - 1, -1 if e.key == pygame.K_LEFT else 1)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if self.row == 0:
                    self.start_edit()
                else:
                    self.try_buy(self.row - 1)

    def buy_visible(self, r):
        kind, _, table = ROWS[r]
        return kind in ("hat", "acc") and not owns(self.app.save.p, kind, self.preview[kind])

    def update(self, dt):
        self.t += dt
        self.world.update(dt)
        m = self.app.mouse
        p = self.app.save.p
        for r, (lb, rb) in enumerate(self.arrows):
            lb.update(dt, m)
            rb.update(dt, m)
            kind, _, table = ROWS[r]
            b = self.buy[r]
            if self.buy_visible(r):
                cost = table[self.preview[kind]][1]
                b.label = f"Kup · {cost}"
                b.enabled = p["pearls"] >= cost
            b.update(dt, m)
        for b in (self.back, self.prev_prof, self.next_prof, self.new_prof):
            b.update(dt, m)
        self.prev_prof.enabled = self.next_prof.enabled = len(self.app.save.profile_ids()) > 1

    # ----- rysowanie -----
    def draw(self, s):
        save = self.app.save
        p = save.p
        self.world.draw(s)
        header(s, "Profil gracza", self.app)
        self.back.draw(s)
        # lewy panel: ludek, nick, profile
        left = pygame.Rect(40, 92, 430, 600)
        panel(s, left, 220)
        pygame.draw.ellipse(s, (3, 22, 36), (left.centerx - 110, 470, 220, 34))
        draw_avatar(s, left.centerx, 370, 1.9, self.preview, self.t)
        r = self.nick_rect
        active = self.row == 0
        pygame.draw.rect(s, (8, 46, 70), r, border_radius=14)
        pygame.draw.rect(s, PEARL if (active or self.editing) else (60, 120, 150), r, 3 if self.editing else 2, border_radius=14)
        nick = self.typed if self.editing else p["nick"]
        shown = nick + ("|" if self.editing and int(self.t * 2) % 2 == 0 else "")
        text(s, shown, 30, INK, r.center, display=True, shadow=False, max_w=r.w - 30)
        hint = "Pisz nick, Enter zapisuje" if self.editing else "Kliknij, aby zmienić nick"
        text(s, hint, 15, MUTED, (r.centerx, r.bottom + 14), shadow=False)
        ids = save.profile_ids()
        text(s, f"Profil {ids.index(save.data['current']) + 1} z {len(ids)}", 18, INK,
             (194, 640), bold=True, shadow=False)
        for b in (self.prev_prof, self.next_prof, self.new_prof):
            b.draw(s)
        text(s, "NA TYM KOMPUTERZE", 13, MUTED, (left.x + 24, left.y + 26), "midleft", bold=True, shadow=False)
        # prawy panel: wygląd
        right = pygame.Rect(492, 92, 748, 600)
        panel(s, right, 220)
        text(s, "WYGLĄD LUDKA", 14, MUTED, (right.x + 28, right.y + 26), "midleft", bold=True, shadow=False)
        for i, (kind, label, table) in enumerate(ROWS):
            y = 168 + i * 64
            if self.row == i + 1:
                hl = pygame.Rect(right.x + 14, y - 28, right.w - 28, 56)
                pygame.draw.rect(s, (14, 60, 84), hl, border_radius=12)
            text(s, label, 22, INK, (right.x + 28, y), "midleft", bold=True, shadow=False)
            lb, rb = self.arrows[i]
            lb.draw(s)
            rb.draw(s)
            idx = self.preview[kind]
            name = table[idx][0]
            if kind in ("suit", "skin"):
                pygame.draw.circle(s, table[idx][1], (858, y), 12)
                pygame.draw.circle(s, INK, (858, y), 12, 2)
                text(s, name, 20, INK, (936, y), shadow=False, max_w=140)
            else:
                text(s, name, 20, INK, (920, y), shadow=False, max_w=170)
            if self.buy_visible(i):
                self.buy[i].draw(s)
            elif kind in ("hat", "acc"):
                text(s, "Masz", 18, KELP, (1165, y), bold=True, shadow=False)
        # statystyki
        text(s, "STATYSTYKI", 14, MUTED, (right.x + 28, 432), "midleft", bold=True, shadow=False)
        st = p["stats"]
        hl = save.highest_level()
        tiles = [("Najwyższy poziom", f"{hl}" if hl else "–"), ("Gwiazdki", f"{save.total_stars()} / {len(LEVELS) * 3}"),
                 ("Dobre odpowiedzi", str(st["correct"])), ("Najdłuższa seria", str(st["best_combo"])),
                 ("Duele wygrane", str(st["duel_win"])), ("Duele przegrane", str(st["duel_loss"]))]
        for k, (lab, val) in enumerate(tiles):
            x = right.x + 28 + (k % 3) * 236
            y = 456 + (k // 3) * 106
            tile = pygame.Rect(x, y, 220, 92)
            pygame.draw.rect(s, (8, 46, 70), tile, border_radius=12)
            text(s, lab, 16, MUTED, (x + 16, y + 22), "midleft", shadow=False)
            text(s, val, 34, INK, (x + 16, y + 60), "midleft", display=True, shadow=False)
        text(s, "Strzałki: wybór i zmiana   ·   Enter: edytuj nick / kup   ·   Esc: menu", 16, MUTED, (W / 2, H - 14))


# ================================================================ ZADANIA
class QuestsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.world = app.world("wrak")
        self.t = 0.0
        self.back = Button("Menu", (100, 46), (150, 50), "ghost", key="Esc", font_size=22)
        self.build()

    def build(self):
        q = self.app.quests
        self.daily = q.daily()
        self.chal = q.challenges()
        btns = []
        for i, d in enumerate(self.daily):
            b = Button("Odbierz", (520, 196 + i * 166), (140, 46), "pearl", font_size=20, action=("d", d["id"]))
            b.enabled = d["done"] and not d["claimed"]
            btns.append(b)
        for i, c in enumerate(self.chal):
            b = Button("Odbierz", (1150, 196 + i * 100), (130, 42), "pearl", font_size=19, action=("c", c["id"]))
            b.enabled = c["claimable"]
            btns.append(b)
        self.menu = ButtonList(btns, grid=True)

    def event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            go_menu(self.app)
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.back.hit(e.pos):
            self.app.audio.play("click")
            go_menu(self.app)
            return
        b = self.menu.handle(e, self.app)
        if b:
            kind, qid = b.action
            got = self.app.quests.claim_daily(qid) if kind == "d" else self.app.quests.claim_challenge(qid)
            if got:
                self.app.audio.play("win")
                self.app.toast(f"+{got} pereł!")
            idx = self.menu.index
            self.build()
            self.menu.index = idx

    def update(self, dt):
        self.t += dt
        self.world.update(dt)
        self.back.update(dt, self.app.mouse)
        self.menu.update(dt, self.app.mouse, self.app.mouse_moved)

    def draw(self, s):
        self.world.draw(s)
        header(s, "Zadania", self.app)
        self.back.draw(s)
        # zadania dnia
        left = pygame.Rect(40, 92, 610, 600)
        panel(s, left, 222)
        text(s, "Zadania dnia", 30, INK, (left.x + 28, left.y + 34), "midleft", display=True)
        now = datetime.datetime.now()
        left_min = int((datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time()) - now).total_seconds() // 60)
        text(s, f"Nowe za {left_min // 60} h {left_min % 60} min", 17, MUTED, (left.right - 28, left.y + 34), "midright", shadow=False)
        for i, d in enumerate(self.daily):
            card = pygame.Rect(left.x + 20, 140 + i * 166, left.w - 40, 148)
            pygame.draw.rect(s, (8, 46, 70), card, border_radius=14)
            if d["claimed"]:
                pygame.draw.rect(s, KELP, card, 2, border_radius=14)
            text_block(s, d["text"], 22, INK, (card.x + 20, card.y + 16), 380, 28, bold=True, max_h=58)
            bar(s, pygame.Rect(card.x + 20, card.y + 92, 380, 14), d["progress"] / d["target"])
            text(s, f"{d['progress']} / {d['target']}", 17, MUTED, (card.x + 20, card.y + 124), "midleft", shadow=False)
            draw_pearl(s, card.x + 330, card.y + 124, 9)
            text(s, f"+{d['reward']}", 19, PEARL, (card.x + 346, card.y + 124), "midleft", bold=True, shadow=False)
        # wyzwania
        right = pygame.Rect(670, 92, 570, 600)
        panel(s, right, 222)
        text(s, "Wyzwania", 30, INK, (right.x + 28, right.y + 34), "midleft", display=True)
        for i, c in enumerate(self.chal):
            y = 148 + i * 100
            rowr = pygame.Rect(right.x + 18, y, right.w - 36, 90)
            pygame.draw.rect(s, (8, 46, 70), rowr, border_radius=12)
            text(s, c["name"], 21, INK, (rowr.x + 18, y + 22), "midleft", bold=True, shadow=False)
            for k in range(3):
                draw_star(s, rowr.x + 250 + k * 22, y + 22, 9, k < c["claimed"])
            if c["finished"]:
                text(s, f"{c['desc']}: {c['value']} · ukończone", 16, KELP, (rowr.x + 18, y + 50), "midleft", shadow=False)
            else:
                text(s, f"{c['desc']}: {min(c['value'], c['target'])} / {c['target']}", 16, MUTED,
                     (rowr.x + 18, y + 50), "midleft", shadow=False, max_w=300)
                bar(s, pygame.Rect(rowr.x + 18, y + 66, 300, 10), c["value"] / c["target"], AQUA)
                draw_pearl(s, rowr.x + 352, y + 66, 8)
                text(s, f"+{c['reward']}", 17, PEARL, (rowr.x + 366, y + 66), "midleft", bold=True, shadow=False)
        self.menu.draw(s)
        text(s, "Perły wydasz w Profilu na czapki i dodatki dla ludka", 17, MUTED, (W / 2, H - 14))


# ================================================================ RANKINGI
TABS = ["Najszybsze przejścia", "Najwyższy poziom", "Duele z AI"]


class RankingScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.world = app.world("glebina")
        self.t = 0.0
        self.tab = 0
        self.lid = max(1, app.save.highest_level() or 1)
        self.back = Button("Menu", (100, 46), (150, 50), "ghost", key="Esc", font_size=22)
        self.tabs = [Button(name, (0, 0), (300, 48), "ghost", font_size=20) for name in TABS]
        row(self.tabs, W / 2, 116, gap=14)
        self.prev = Button("‹", (W / 2 - 300, 176), (48, 44), "ghost", font_size=30)
        self.next = Button("›", (W / 2 + 300, 176), (48, 44), "ghost", font_size=30)
        self._bot_times = {}

    def bot_time(self, bot, lid):
        key = (bot["id"], lid)
        if key not in self._bot_times:
            self._bot_times[key] = bot_time(bot, lid)
        return self._bot_times[key]

    def entries(self):
        save = self.app.save
        me = save.data["current"]
        out = []
        for pid in save.profile_ids():
            prof = save.data["profiles"][pid]
            e = dict(nick=prof["nick"], avatar=prof["avatar"], bot=False, me=pid == me)
            if self.tab == 0:
                tm = prof["times"].get(str(self.lid))
                if tm is None:
                    continue
                e.update(key=tm, value=fmt_time(tm))
            elif self.tab == 1:
                hl, st = save.highest_level(prof), save.total_stars(prof)
                e.update(key=(-hl, -st), value=f"poziom {hl}", stars=st)
            else:
                w, l = prof["stats"]["duel_win"], prof["stats"]["duel_loss"]
                e.update(key=(-w, l), value=f"{w} wygr. · {l} przegr.")
            out.append(e)
        for b in RANK_BOTS:
            e = dict(nick=b["nick"], avatar=b["avatar"], bot=True, me=False)
            if self.tab == 0:
                if b["level"] < self.lid:
                    continue
                tm = self.bot_time(b, self.lid)
                e.update(key=tm, value=fmt_time(tm))
            elif self.tab == 1:
                st = bot_stars(b)
                e.update(key=(-b["level"], -st), value=f"poziom {b['level']}", stars=st)
            else:
                e.update(key=(-b["wins"], 0), value=f"{b['wins']} wygr.")
            out.append(e)
        out.sort(key=lambda e: e["key"])
        return out

    def event(self, e):
        a = self.app
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                go_menu(a)
            elif e.key in (pygame.K_TAB, pygame.K_e):
                self.tab = (self.tab + 1) % 3
                a.audio.play("swap")
            elif e.key == pygame.K_q:
                self.tab = (self.tab - 1) % 3
                a.audio.play("swap")
            elif e.key in (pygame.K_LEFT, pygame.K_RIGHT) and self.tab == 0:
                self.lid = max(1, min(len(LEVELS), self.lid + (1 if e.key == pygame.K_RIGHT else -1)))
                a.audio.play("tick")
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.back.hit(e.pos):
                a.audio.play("click")
                go_menu(a)
            for i, b in enumerate(self.tabs):
                if b.hit(e.pos):
                    self.tab = i
                    a.audio.play("swap")
            if self.tab == 0 and self.prev.hit(e.pos):
                self.lid = max(1, self.lid - 1)
                a.audio.play("tick")
            if self.tab == 0 and self.next.hit(e.pos):
                self.lid = min(len(LEVELS), self.lid + 1)
                a.audio.play("tick")

    def update(self, dt):
        self.t += dt
        self.world.update(dt)
        m = self.app.mouse
        for i, b in enumerate(self.tabs):
            b.style = "pearl" if i == self.tab else "ghost"
            b.update(dt, m)
        for b in (self.back, self.prev, self.next):
            b.update(dt, m)
        self.prev.enabled = self.lid > 1
        self.next.enabled = self.lid < len(LEVELS)

    def draw(self, s):
        self.world.draw(s)
        header(s, "Rankingi", self.app)
        self.back.draw(s)
        for b in self.tabs:
            b.draw(s)
        top = 160
        if self.tab == 0:
            L = LEVELS[self.lid - 1]
            self.prev.draw(s)
            self.next.draw(s)
            text(s, f"Poziom {self.lid} · {L['name']}", 24, INK, (W / 2, 176), display=True, max_w=520)
            top = 206
        tbl = pygame.Rect(170, top, 940, H - top - 30)
        panel(s, tbl, 225)
        rows = self.entries()
        me_idx = next((i for i, e in enumerate(rows) if e["me"]), None)
        rh = 44
        max_rows = (tbl.h - 20) // rh
        shown = list(enumerate(rows[:max_rows]))
        if me_idx is not None and me_idx >= max_rows:
            shown = shown[:max_rows - 1] + [(me_idx, rows[me_idx])]
        if not rows:
            text(s, "Nikt jeszcze nie przeszedł tego poziomu.", 22, MUTED, tbl.center, shadow=False)
        for k, (rank, e) in enumerate(shown):
            y = tbl.y + 12 + k * rh
            r = pygame.Rect(tbl.x + 12, y, tbl.w - 24, rh - 6)
            if e["me"]:
                pygame.draw.rect(s, (40, 80, 70), r, border_radius=10)
                pygame.draw.rect(s, KELP, r, 2, border_radius=10)
            elif k % 2 == 0:
                pygame.draw.rect(s, (8, 46, 70), r, border_radius=10)
            medal = {0: PEARL, 1: (210, 220, 230), 2: (220, 150, 90)}.get(rank)
            if medal:
                pygame.draw.circle(s, medal, (r.x + 28, r.centery), 15)
                text(s, str(rank + 1), 18, NAVY, (r.x + 28, r.centery), bold=True, shadow=False)
            else:
                text(s, str(rank + 1), 18, MUTED, (r.x + 28, r.centery), bold=True, shadow=False)
            sub = s.subsurface(r)   # mały ludek przycięty do wiersza
            draw_avatar(sub, 82, r.h * 0.5 + 16, 0.36, e["avatar"], 0, bubbles=False)
            x = r.x + 120
            name_r = text(s, e["nick"], 21, INK, (x, r.centery), "midleft", bold=True, shadow=False, max_w=330)
            chip = "TY" if e["me"] else ("BOT" if e["bot"] else None)
            if chip:
                cr = pygame.Rect(name_r.right + 10, r.centery - 11, 46, 22)
                pygame.draw.rect(s, KELP if e["me"] else (90, 110, 130), cr, border_radius=11)
                text(s, chip, 13, NAVY, cr.center, bold=True, shadow=False)
            if self.tab == 1:
                draw_star(s, r.right - 250, r.centery, 10, True)
                text(s, str(e["stars"]), 18, PEARL, (r.right - 236, r.centery), "midleft", bold=True, shadow=False)
            text(s, e["value"], 22, INK, (r.right - 18, r.centery), "midright", display=True, shadow=False)
        foot = "Q / E: zmiana rankingu   ·   strzałki: poziom   ·   Boty to komputerowi rywale" if self.tab == 0 \
            else "Q / E: zmiana rankingu   ·   Ranking obejmuje profile z tego komputera i boty"
        text(s, foot, 16, MUTED, (W / 2, H - 14))
