"""Ludek-nurek gracza, sklep z dodatkami, perły oraz boty (rywale w duelach i rankingach)."""
import math
import random

import pygame

from core import PEARL, mix
from levels import LEVELS, make_values

# ---------- wygląd ludka ----------
SUITS = [("Pomarańczowy", (255, 128, 60)), ("Niebieski", (60, 140, 255)), ("Zielony", (70, 196, 120)),
         ("Różowy", (236, 92, 140)), ("Fioletowy", (150, 96, 224)), ("Czarny", (44, 46, 60)),
         ("Żółty", (250, 206, 70)), ("Biały", (236, 240, 246))]
SKINS = [("Jasna", (255, 222, 194)), ("Beżowa", (238, 194, 158)), ("Śniada", (206, 152, 112)),
         ("Brązowa", (156, 106, 72)), ("Ciemna", (104, 70, 48))]
# (nazwa, cena w perłach)
HATS = [("Brak", 0), ("Czapka", 0), ("Kokarda", 40), ("Kapelusz pirata", 80), ("Hełm nurka", 100),
        ("Rogi wikinga", 120), ("Korona", 150)]
ACCS = [("Brak", 0), ("Maska nurka", 0), ("Okulary", 30), ("Fajka", 50), ("Szalik", 60), ("Medal", 120)]


def owns(prof, kind, i):
    table = HATS if kind == "hat" else ACCS
    return table[i][1] == 0 or f"{kind}:{i}" in prof["owned"]


def draw_pearl(surf, x, y, r=9):
    pygame.draw.circle(surf, (250, 240, 252), (x, y), r)
    pygame.draw.circle(surf, (210, 190, 230), (x, y), r, 2)
    pygame.draw.circle(surf, (255, 255, 255), (x - r * 0.35, y - r * 0.35), max(2, r * 0.3))


def draw_avatar(surf, cx, cy, s, av, t=0.0, bubbles=True):
    """Ludek-nurek. (cx, cy) to środek tułowia, s to skala (1.0 ≈ 150 px wysokości)."""
    suit = SUITS[av.get("suit", 0) % len(SUITS)][1]
    skin = SKINS[av.get("skin", 0) % len(SKINS)][1]
    hat = av.get("hat", 0) % len(HATS)
    acc = av.get("acc", 0) % len(ACCS)
    dark = mix(suit, (0, 0, 0), 0.35)
    cy = cy + math.sin(t * 2.2) * 3 * s
    hy = cy - 46 * s           # środek głowy
    hr = 25 * s                # promień głowy
    S = lambda v: max(1, int(v * s))

    # butla z tlenem (za plecami)
    pygame.draw.rect(surf, (150, 160, 170), (cx + 14 * s, cy - 24 * s, 18 * s, 44 * s), border_radius=S(8))
    pygame.draw.rect(surf, (110, 120, 130), (cx + 14 * s, cy - 24 * s, 18 * s, 44 * s), S(2), border_radius=S(8))
    # płetwy i nogi
    kick = math.sin(t * 4) * 4 * s
    for side in (-1, 1):
        lx = cx + side * 10 * s
        pygame.draw.rect(surf, dark, (lx - 7 * s, cy + 18 * s, 14 * s, 26 * s), border_radius=S(5))
        pygame.draw.ellipse(surf, mix(suit, (255, 255, 255), 0.25),
                            (lx - 12 * s + side * 4 * s, cy + 40 * s + (kick if side > 0 else -kick), 24 * s, 12 * s))
    # tułów
    body = pygame.Rect(0, 0, 46 * s, 50 * s)
    body.center = (cx, cy)
    pygame.draw.rect(surf, suit, body, border_radius=S(16))
    pygame.draw.rect(surf, dark, body, S(2), border_radius=S(16))
    pygame.draw.rect(surf, (40, 40, 48), (body.x, cy + 8 * s, body.w, 7 * s))
    pygame.draw.rect(surf, (230, 200, 90), (cx - 5 * s, cy + 8 * s, 10 * s, 7 * s))
    # ręce
    wave = math.sin(t * 3) * 6 * s
    for side in (-1, 1):
        hx = cx + side * 34 * s
        hand_y = cy - 2 * s + (wave if side < 0 else 0)
        pygame.draw.line(surf, suit, (cx + side * 20 * s, cy - 14 * s), (hx, hand_y), S(10))
        pygame.draw.circle(surf, skin, (hx, hand_y), 7 * s)
    # szalik i medal (na tułowiu)
    if acc == 4:
        pygame.draw.rect(surf, (220, 60, 70), (cx - 22 * s, cy - 28 * s, 44 * s, 10 * s), border_radius=S(5))
        pygame.draw.rect(surf, (220, 60, 70), (cx + 6 * s, cy - 22 * s, 10 * s, 26 * s), border_radius=S(4))
        for k in range(3):
            pygame.draw.line(surf, (255, 230, 230), (cx + 7 * s, cy - 12 * s + k * 6 * s), (cx + 15 * s, cy - 12 * s + k * 6 * s), S(2))
    if acc == 5:
        pygame.draw.polygon(surf, (60, 120, 230), [(cx - 10 * s, cy - 25 * s), (cx, cy - 4 * s), (cx + 10 * s, cy - 25 * s)])
        pygame.draw.circle(surf, (250, 200, 60), (cx, cy - 2 * s), 9 * s)
        pygame.draw.circle(surf, (255, 236, 150), (cx, cy - 2 * s), 5 * s)
    # hełm nurka jest za głową (mosiężna kula z szybą)
    if hat == 4:
        pygame.draw.circle(surf, (196, 140, 60), (cx, hy), hr + 12 * s)
        for k in range(8):
            a = k * math.pi / 4
            pygame.draw.circle(surf, (240, 200, 110), (cx + math.cos(a) * (hr + 7 * s), hy + math.sin(a) * (hr + 7 * s)), 3 * s)
        pygame.draw.circle(surf, (170, 220, 236), (cx, hy), hr + 2 * s)
    # głowa i twarz
    pygame.draw.circle(surf, skin, (cx, hy), hr)
    pygame.draw.circle(surf, mix(skin, (0, 0, 0), 0.2), (cx, hy), hr, S(2))
    pygame.draw.circle(surf, (255, 150, 150), (cx - 15 * s, hy + 8 * s), 5 * s)
    pygame.draw.circle(surf, (255, 150, 150), (cx + 15 * s, hy + 8 * s), 5 * s)
    if acc in (1, 3):   # maska nurka (także z fajką)
        pygame.draw.line(surf, (40, 40, 50), (cx - hr, hy - 4 * s), (cx + hr, hy - 4 * s), S(4))
        m = pygame.Rect(0, 0, 40 * s, 20 * s)
        m.center = (cx, hy - 4 * s)
        pygame.draw.rect(surf, (170, 230, 246), m, border_radius=S(8))
        pygame.draw.rect(surf, (40, 40, 50), m, S(3), border_radius=S(8))
    for side in (-1, 1):   # oczy
        pygame.draw.circle(surf, (30, 30, 40), (cx + side * 8 * s, hy - 4 * s), 3.6 * s)
        pygame.draw.circle(surf, (255, 255, 255), (cx + side * 8 * s + 1.2 * s, hy - 5.4 * s), 1.3 * s)
    if acc == 2:   # okulary
        for side in (-1, 1):
            pygame.draw.circle(surf, (40, 40, 50), (cx + side * 9 * s, hy - 4 * s), 8 * s, S(2))
        pygame.draw.line(surf, (40, 40, 50), (cx - 2 * s, hy - 5 * s), (cx + 2 * s, hy - 5 * s), S(2))
    pygame.draw.arc(surf, (120, 50, 50), (cx - 8 * s, hy + 2 * s, 16 * s, 11 * s), 3.5, 5.9, S(2))
    if acc == 3:   # fajka do nurkowania
        pygame.draw.lines(surf, (250, 200, 60), False,
                          [(cx + 10 * s, hy + 8 * s), (cx + 22 * s, hy + 6 * s), (cx + 24 * s, hy - 34 * s)], S(5))
        pygame.draw.circle(surf, (240, 90, 70), (cx + 24 * s, hy - 36 * s), 4 * s)
    # nakrycia głowy
    if hat == 1:     # czapka z pomponem
        pygame.draw.circle(surf, suit, (cx, hy - 10 * s), hr - 2 * s, draw_top_left=True, draw_top_right=True)
        pygame.draw.rect(surf, mix(suit, (255, 255, 255), 0.4), (cx - hr, hy - 12 * s, 2 * hr, 7 * s), border_radius=S(3))
        pygame.draw.circle(surf, (255, 255, 255), (cx, hy - hr - 8 * s), 6 * s)
    elif hat == 2:   # kokarda
        for side in (-1, 1):
            pygame.draw.polygon(surf, (255, 120, 180), [(cx + 12 * s, hy - hr + 2 * s),
                                                        (cx + 12 * s + side * 14 * s, hy - hr - 8 * s),
                                                        (cx + 12 * s + side * 14 * s, hy - hr + 12 * s)])
        pygame.draw.circle(surf, (230, 80, 150), (cx + 12 * s, hy - hr + 2 * s), 5 * s)
    elif hat == 3:   # kapelusz pirata
        pygame.draw.polygon(surf, (30, 30, 36), [(cx - 34 * s, hy - 14 * s), (cx, hy - 44 * s), (cx + 34 * s, hy - 14 * s),
                                                 (cx, hy - 20 * s)])
        pygame.draw.circle(surf, (240, 240, 240), (cx, hy - 28 * s), 5 * s)
        pygame.draw.line(surf, (240, 240, 240), (cx - 5 * s, hy - 21 * s), (cx + 5 * s, hy - 21 * s), S(2))
    elif hat == 5:   # rogi wikinga
        pygame.draw.circle(surf, (150, 156, 170), (cx, hy - 8 * s), hr - 1 * s, draw_top_left=True, draw_top_right=True)
        for side in (-1, 1):
            pygame.draw.polygon(surf, (250, 246, 230), [(cx + side * 18 * s, hy - 18 * s), (cx + side * 40 * s, hy - 44 * s),
                                                        (cx + side * 26 * s, hy - 12 * s)])
    elif hat == 6:   # korona
        pts = [(cx - 22 * s, hy - 16 * s), (cx - 22 * s, hy - 40 * s), (cx - 11 * s, hy - 28 * s), (cx, hy - 46 * s),
               (cx + 11 * s, hy - 28 * s), (cx + 22 * s, hy - 40 * s), (cx + 22 * s, hy - 16 * s)]
        pygame.draw.polygon(surf, (250, 200, 60), pts)
        pygame.draw.polygon(surf, (200, 140, 30), pts, S(2))
        for k, col in enumerate(((230, 60, 80), (60, 160, 240), (230, 60, 80))):
            pygame.draw.circle(surf, col, (cx - 11 * s + k * 11 * s, hy - 22 * s), 3.5 * s)
    elif hat == 4:   # przednia ramka szyby hełmu
        pygame.draw.circle(surf, (196, 140, 60), (cx, hy), hr + 2 * s, S(4))
    # bąbelki z głowy
    if bubbles:
        for k in range(3):
            ph = (t * 0.6 + k / 3) % 1.0
            bx = cx + 18 * s + math.sin(ph * 6 + k) * 5 * s
            by = hy - 30 * s - ph * 70 * s
            pygame.draw.circle(surf, (220, 245, 255), (bx, by), (2 + k) * s, S(1))


# ---------- boty: rywale w duelach i wpisy w rankingach ----------
# react: średni czas decyzji (s), acc: celność, level: najwyższy ukończony poziom w rankingu
BOTS = [
    dict(id="zolw", nick="Żółw Tadek", react=2.1, acc=0.80, level=5, wins=3, reward=10, diff="Łatwy",
         world="plycizna", avatar={"suit": 2, "skin": 1, "hat": 1, "acc": 0}),
    dict(id="delfin", nick="Delfinka Ola", react=1.4, acc=0.90, level=11, wins=12, reward=20, diff="Średni",
         world="rafa", avatar={"suit": 1, "skin": 0, "hat": 2, "acc": 1}),
    dict(id="rekin", nick="Rekin Bruno", react=0.95, acc=0.95, level=17, wins=27, reward=35, diff="Trudny",
         world="glebina", avatar={"suit": 5, "skin": 3, "hat": 3, "acc": 2}),
    dict(id="kraken", nick="Kraken", react=0.65, acc=0.98, level=24, wins=54, reward=60, diff="Mistrz",
         world="wulkan", avatar={"suit": 4, "skin": 4, "hat": 6, "acc": 5}),
]
# dodatkowe boty tylko do rankingów
RANK_BOTS = BOTS + [
    dict(id="meduza", nick="Meduza Zu", react=2.4, acc=0.75, level=3, wins=1, avatar={"suit": 3, "skin": 0, "hat": 2, "acc": 2}),
    dict(id="osmiornica", nick="Ośmiornica Ina", react=1.8, acc=0.85, level=8, wins=6, avatar={"suit": 4, "skin": 2, "hat": 0, "acc": 1}),
    dict(id="konik", nick="Konik Morski Leo", react=1.2, acc=0.92, level=14, wins=18, avatar={"suit": 6, "skin": 1, "hat": 4, "acc": 0}),
    dict(id="rozgwiazda", nick="Rozgwiazda Mia", react=0.85, acc=0.96, level=20, wins=35, avatar={"suit": 7, "skin": 2, "hat": 5, "acc": 4}),
]


def bot_time(bot, lid):
    """Szacowany czas przejścia poziomu przez bota: te same animacje co u gracza + czas decyzji."""
    L = LEVELS[lid - 1]
    rnd = random.Random(f"{bot['id']}-{lid}")
    vals = make_values(L["n"], L["layout"], rnd, dupes=L.get("dupes", False))
    react = bot["react"] * (0.85 + 0.3 * rnd.random())
    if L["mode"] == "puzzle":
        inv = sum(1 for i in range(len(vals)) for j in range(i + 1, len(vals)) if vals[i] > vals[j])
        return round(1.5 + inv * (react + 0.55), 2)
    t = 1.0
    a = list(vals)
    n = len(a)
    for p in range(1, n):
        t += 1.0
        swapped = False
        for i in range(n - p):
            t += react + 0.45
            if a[i] > a[i + 1]:
                a[i], a[i + 1] = a[i + 1], a[i]
                swapped = True
                t += 0.7
            else:
                t += 0.2
            if rnd.random() > bot["acc"]:
                t += 0.4
        t += 0.8
        if p == n - 1:
            break
        if L["early"]:
            t += react + 0.45
            if not swapped:
                break
        elif not swapped:
            t += 1.0
            break
    return round(t, 2)


def bot_stars(bot):
    return sum(3 if (bot["acc"] > 0.9 or k % 3) else 2 for k in range(1, bot["level"] + 1))
