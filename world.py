"""Grafika: tła trzech podwodnych światów, bąbelki, maskotka Bulek i cząsteczki. Wszystko rysowane w kodzie."""
import math
import random

import pygame

from core import W, H, INK, AQUA, CORAL, PEARL, KELP, font, mix, render, cached as _cache_get


def _fast(surf, alpha):
    """Zamienia obrazek na format ekranu, dzięki czemu kopiowanie na ekran jest dużo szybsze."""
    if pygame.display.get_surface() is None:
        return surf
    return surf.convert_alpha() if alpha else surf.convert()

WORLDS = {
    "plycizna": dict(
        name="Płycizna", top=(92, 210, 228), bottom=(10, 88, 124), far=(30, 120, 150),
        sand=(228, 206, 156), sand2=(200, 176, 124), rays=7, ray_alpha=34, weed=(40, 168, 112),
        fish=(14, 66, 92), coral=False, glow=False, rocks=(70, 120, 128)),
    "rafa": dict(
        name="Rafa koralowa", top=(60, 132, 206), bottom=(26, 32, 92), far=(52, 72, 140),
        sand=(222, 176, 146), sand2=(186, 136, 124), rays=5, ray_alpha=26, weed=(52, 150, 128),
        fish=(30, 30, 76), coral=True, glow=False, rocks=(84, 80, 130)),
    "glebina": dict(
        name="Głębina", top=(16, 44, 78), bottom=(2, 6, 18), far=(12, 30, 54),
        sand=(30, 42, 62), sand2=(18, 26, 42), rays=2, ray_alpha=12, weed=(16, 84, 96),
        fish=(70, 210, 230), coral=False, glow=True, rocks=(20, 34, 56)),
    "lod": dict(
        name="Lodowa zatoka", top=(196, 238, 248), bottom=(36, 104, 146), far=(150, 200, 222),
        sand=(236, 244, 250), sand2=(198, 220, 236), rays=6, ray_alpha=30, weed=(110, 180, 196),
        fish=(40, 92, 124), coral=False, glow=False, rocks=(168, 200, 216), weeds=5,
        motes="snow", extras=("icebergs",)),
    "wulkan": dict(
        name="Wulkan", top=(96, 56, 74), bottom=(20, 8, 14), far=(70, 36, 46),
        sand=(62, 40, 40), sand2=(40, 24, 26), rays=2, ray_alpha=10, weed=(80, 50, 40),
        fish=(34, 14, 20), coral=False, glow=False, rocks=(50, 30, 34), weeds=4,
        motes="embers", extras=("vents",)),
    "wrak": dict(
        name="Wrak statku", top=(72, 142, 122), bottom=(8, 38, 38), far=(40, 92, 80),
        sand=(176, 164, 122), sand2=(134, 122, 90), rays=4, ray_alpha=22, weed=(56, 128, 78),
        fish=(18, 50, 44), coral=False, glow=False, rocks=(58, 82, 70), weeds=10,
        extras=("wreck",)),
    # ostatni świat: na razie tylko podgląd na mapie („Wkrótce”)
    "palac": dict(
        name="Perłowy Pałac", top=(226, 186, 238), bottom=(58, 28, 92), far=(166, 116, 196),
        sand=(242, 222, 242), sand2=(212, 182, 224), rays=6, ray_alpha=40, weed=(196, 116, 200),
        fish=(110, 56, 140), coral=False, glow=False, rocks=(190, 150, 212), weeds=8,
        motes="pearls", extras=("palace",)),
}
WORLD_ORDER = ["plycizna", "rafa", "glebina", "lod", "wulkan", "wrak"]
PREVIEW_WORLD = "palac"


class World:
    def __init__(self, key, seed=3):
        self.key = key
        self.p = WORLDS[key]
        self.t = random.random() * 10
        rnd = random.Random(seed + len(key))
        self.static = self._build_static(rnd)
        self.weeds = [(rnd.randint(0, W), rnd.randint(9, 16), rnd.random() * 6, rnd.randint(7, 11))
                      for _ in range(self.p.get("weeds", 14))]
        self.fish = [self._new_fish(rnd, True) for _ in range(7)]
        self.vents = getattr(self, "vents", [])
        self.smoke = []
        self.motes = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1, 3.2), rnd.uniform(14, 40), rnd.random() * 6]
                      for _ in range(40)]
        self.jellies = [[rnd.uniform(100, W - 100), rnd.uniform(150, 500), rnd.uniform(26, 44), rnd.random() * 6,
                         rnd.choice([(120, 220, 255), (200, 140, 255), (120, 255, 200)])]
                        for _ in range(4)] if self.p["glow"] else []
        self.rnd = rnd

    # ----- warstwa statyczna -----
    def _build_static(self, rnd):
        p = self.p
        s = pygame.Surface((W, H))
        for y in range(H):
            pygame.draw.line(s, mix(p["top"], p["bottom"], (y / H) ** 0.9), (0, y), (W, y))
        # dalekie skały
        far = pygame.Surface((W, H), pygame.SRCALPHA)
        pts = [(0, H)]
        x = 0
        while x <= W + 80:
            pts.append((x, H - 150 - rnd.randint(0, 120)))
            x += rnd.randint(60, 140)
        pts.append((W, H))
        pygame.draw.polygon(far, (*p["far"], 150), pts)
        s.blit(far, (0, 0))
        for extra in p.get("extras", ()):
            getattr(self, "_extra_" + extra)(s, rnd)
        # skały
        for _ in range(6):
            cx, cy = rnd.randint(0, W), H - rnd.randint(40, 90)
            rw, rh = rnd.randint(90, 200), rnd.randint(50, 110)
            pygame.draw.ellipse(s, p["rocks"], (cx - rw // 2, cy - rh // 2, rw, rh))
            pygame.draw.ellipse(s, mix(p["rocks"], (255, 255, 255), 0.12), (cx - rw // 2 + 14, cy - rh // 2 + 8, rw // 2, rh // 3))
        if p["coral"]:
            for _ in range(9):
                self._coral(s, rnd, rnd.randint(20, W - 20), H - rnd.randint(30, 60))
            for _ in range(5):
                cx = rnd.randint(40, W - 40)
                col = rnd.choice([(255, 140, 120), (250, 190, 90), (200, 120, 220)])
                for k in range(5):
                    pygame.draw.ellipse(s, mix(col, (0, 0, 0), k * 0.08),
                                        (cx - 40 + k * 4, H - 150 + k * 10, 80 - k * 8, 110 - k * 14), 3)
        # piasek
        pts = [(0, H)]
        for x in range(0, W + 41, 40):
            pts.append((x, H - 46 - 14 * math.sin(x * 0.012 + 1) - 8 * math.sin(x * 0.031)))
        pts.append((W, H))
        pygame.draw.polygon(s, p["sand2"], pts)
        pts2 = [(x, y + 18) for x, y in pts[1:-1]]
        pygame.draw.polygon(s, p["sand"], [(0, H)] + pts2 + [(W, H)])
        for _ in range(140):
            x, y = rnd.randint(0, W), rnd.randint(H - 26, H)
            pygame.draw.circle(s, mix(p["sand"], (0, 0, 0), 0.15), (x, y), rnd.randint(1, 2))
        for _ in range(5):
            x = rnd.randint(30, W - 30)
            self._shell(s, x, H - rnd.randint(8, 22), rnd)
        if "vents" in p.get("extras", ()):
            for _ in range(9):   # świecące szczeliny lawy w dnie
                x = rnd.randint(20, W - 60)
                y = H - rnd.randint(6, 30)
                pts = [(x + k * 14, y + rnd.randint(-5, 5)) for k in range(5)]
                pygame.draw.lines(s, (255, 120, 40), False, pts, 3)
                pygame.draw.lines(s, (255, 210, 120), False, pts, 1)
        if "palace" in p.get("extras", ()):
            for _ in range(14):  # perły na dnie
                x, y = rnd.randint(20, W - 20), H - rnd.randint(8, 30)
                r = rnd.randint(4, 8)
                pygame.draw.circle(s, (250, 240, 252), (x, y), r)
                pygame.draw.circle(s, (255, 255, 255), (x - r // 3, y - r // 3), max(1, r // 3))
        return s

    # ----- dodatki nowych światów (rysowane raz, w warstwie statycznej) -----
    def _silhouette(self, col, y, k=0.45):
        """Kolor sylwetki lekko zmieszany z wodą, żeby była „w tle”."""
        bg = mix(self.p["top"], self.p["bottom"], (max(0, min(H - 1, y)) / H) ** 0.9)
        return mix(col, bg, k)

    def _extra_icebergs(self, s, rnd):
        # kry wiszące pod powierzchnią
        x = -40
        while x < W + 40:
            w = rnd.randint(120, 260)
            depth = rnd.randint(50, 150)
            pts = [(x, 0)]
            for k in range(1, 6):
                pts.append((x + w * k / 6 + rnd.randint(-12, 12), depth * (0.5 + 0.5 * math.sin(k / 6 * math.pi)) + rnd.randint(-10, 10)))
            pts.append((x + w, 0))
            pygame.draw.polygon(s, self._silhouette((236, 250, 255), depth / 2, 0.25), pts)
            pygame.draw.lines(s, (255, 255, 255), False, pts[1:-1], 2)
            x += w + rnd.randint(10, 60)
        # góra lodowa w oddali
        for cx in (rnd.randint(150, 350), rnd.randint(850, 1100)):
            base = H - 150
            pts = [(cx - 150, base), (cx - 90, base - 160), (cx - 30, base - 120), (cx + 10, base - 230),
                   (cx + 70, base - 140), (cx + 150, base)]
            pygame.draw.polygon(s, self._silhouette((210, 236, 248), base - 120, 0.4), pts)

    def _extra_vents(self, s, rnd):
        self.vents = []
        for cx in (rnd.randint(80, 260), rnd.randint(420, 600), rnd.randint(760, 900), rnd.randint(1060, 1200)):
            h = rnd.randint(130, 240)
            base = H - 40
            top = base - h
            w0, w1 = rnd.randint(46, 70), rnd.randint(18, 28)
            col = self._silhouette((24, 14, 18), top, 0.2)
            pygame.draw.polygon(s, col, [(cx - w0, base), (cx - w1, top), (cx + w1, top), (cx + w0, base)])
            for k in range(3):  # pęknięcia z lawą
                yy = top + 30 + k * (h - 40) / 3
                pygame.draw.line(s, (220, 90, 40), (cx - w1 + 6, yy), (cx + rnd.randint(-6, 6), yy + 16), 2)
            pygame.draw.circle(s, (255, 140, 60), (cx, top), w1 - 6)
            pygame.draw.circle(s, (255, 220, 140), (cx, top), max(3, w1 - 14))
            self.vents.append((cx, top))

    def _extra_wreck(self, s, rnd):
        cx, base = 860, H - 70
        hull = [(cx - 300, base - 60), (cx + 230, base - 120), (cx + 300, base - 40), (cx + 200, base + 10),
                (cx - 240, base + 30)]
        col = self._silhouette((70, 52, 38), base - 60, 0.35)
        pygame.draw.polygon(s, col, hull)
        for k in range(1, 5):   # deski
            a = (cx - 290 + k * 6, base - 60 + k * 18 - k * 8)
            b = (cx + 250, base - 110 + k * 26)
            pygame.draw.line(s, mix(col, (0, 0, 0), 0.25), a, b, 2)
        for k in range(4):      # bulaje
            pygame.draw.circle(s, mix(col, (200, 230, 200), 0.35), (cx - 170 + k * 110, base - 50 - k * 16), 11)
            pygame.draw.circle(s, mix(col, (0, 0, 0), 0.3), (cx - 170 + k * 110, base - 50 - k * 16), 11, 3)
        # złamany maszt i reja
        pygame.draw.line(s, mix(col, (0, 0, 0), 0.1), (cx - 20, base - 90), (cx + 90, base - 380), 12)
        pygame.draw.line(s, mix(col, (0, 0, 0), 0.1), (cx - 10, base - 300), (cx + 170, base - 250), 7)
        # podarty żagiel
        pygame.draw.polygon(s, self._silhouette((200, 196, 170), base - 300, 0.5),
                            [(cx + 60, base - 330), (cx + 160, base - 262), (cx + 120, base - 200), (cx + 70, base - 230)])
        # skrzynia skarbów
        ch = pygame.Rect(180, H - 92, 70, 44)
        pygame.draw.rect(s, (110, 70, 34), ch, border_radius=6)
        pygame.draw.rect(s, (220, 180, 70), ch, 3, border_radius=6)
        pygame.draw.circle(s, (255, 220, 110), (ch.centerx, ch.y + 4), 22)
        for k in range(6):
            pygame.draw.circle(s, (255, 214, 90), (ch.x + 8 + k * 11, ch.y - 2 - (k % 2) * 5), 6)
        pygame.draw.rect(s, (130, 84, 40), ch.inflate(0, -18).move(0, 9), border_radius=4)

    def _extra_palace(self, s, rnd):
        cx, base = W // 2, H - 60
        wall = self._silhouette((246, 214, 246), base - 150, 0.25)
        dark = mix(wall, (90, 40, 120), 0.35)
        glow = (255, 236, 180)
        pygame.draw.rect(s, wall, (cx - 330, base - 170, 660, 170))
        for i, (dx, h, w) in enumerate(((-300, 300, 70), (-160, 380, 80), (0, 460, 110), (160, 380, 80), (300, 300, 70))):
            x = cx + dx
            pygame.draw.rect(s, wall, (x - w // 2, base - h, w, h))
            pygame.draw.circle(s, wall, (x, base - h), w // 2 + 6)
            pygame.draw.polygon(s, wall, [(x - 6, base - h - w // 2 - 4), (x, base - h - w // 2 - 46), (x + 6, base - h - w // 2 - 4)])
            pygame.draw.circle(s, (255, 250, 255), (x, base - h - w // 2 - 50), 9)   # perła na szczycie
            for k in range(3):   # świecące okna
                wy = base - h + 40 + k * 70
                if wy < base - 40:
                    pygame.draw.ellipse(s, glow, (x - 11, wy, 22, 34))
        # wielka brama
        pygame.draw.rect(s, dark, (cx - 70, base - 150, 140, 150), border_top_left_radius=70, border_top_right_radius=70)
        pygame.draw.circle(s, glow, (cx, base - 110), 26)
        pygame.draw.circle(s, (255, 255, 255), (cx - 8, base - 118), 8)

    def _coral(self, s, rnd, x, y):
        col = rnd.choice([(255, 120, 110), (255, 170, 90), (230, 110, 190), (255, 210, 120)])

        def branch(x, y, ang, length, width, depth):
            x2 = x + math.cos(ang) * length
            y2 = y + math.sin(ang) * length
            pygame.draw.line(s, col, (x, y), (x2, y2), max(2, int(width)))
            pygame.draw.circle(s, col, (int(x2), int(y2)), max(1, int(width / 2)))
            if depth > 0:
                for d in (-0.45, 0.4):
                    branch(x2, y2, ang + d + rnd.uniform(-0.15, 0.15), length * 0.72, width * 0.7, depth - 1)
        branch(x, y, -math.pi / 2 + rnd.uniform(-0.2, 0.2), rnd.randint(36, 56), 9, 4)

    def _shell(self, s, x, y, rnd):
        col = rnd.choice([(255, 220, 210), (250, 200, 160), (240, 240, 230)])
        pygame.draw.ellipse(s, col, (x - 10, y - 7, 20, 14))
        for k in range(-2, 3):
            pygame.draw.line(s, mix(col, (120, 80, 60), 0.4), (x, y + 6), (x + k * 4, y - 6), 1)

    def _new_fish(self, rnd, anywhere=False):
        d = rnd.choice([-1, 1])
        x = rnd.uniform(0, W) if anywhere else (-60 if d > 0 else W + 60)
        return [x, rnd.uniform(110, H - 200), d, rnd.uniform(30, 70), rnd.uniform(0.6, 1.3), rnd.random() * 6]

    # ----- animacja -----
    def update(self, dt):
        self.t += dt
        for f in self.fish:
            f[0] += f[2] * f[3] * dt
            if f[0] < -100 or f[0] > W + 100:
                f[:] = self._new_fish(self.rnd)
        down = self.p.get("motes") == "snow"
        for m in self.motes:
            m[1] += (m[3] * 0.7 if down else -m[3]) * dt
            if m[1] < -10 or m[1] > H + 10:
                m[1] = -8 if down else H + 10
                m[0] = self.rnd.uniform(0, W)
        # dym z kominów wulkanicznych
        for vx, vy in self.vents:
            if self.rnd.random() < dt * 5:
                self.smoke.append([vx + self.rnd.uniform(-6, 6), vy - 6, self.rnd.uniform(6, 10), 0.0])
        for p in self.smoke:
            p[1] -= 34 * dt
            p[0] += math.sin(self.t * 1.3 + p[2]) * 10 * dt
            p[2] += 7 * dt
            p[3] += dt
        self.smoke = [p for p in self.smoke if p[3] < 4.5 and p[1] > -40]
        for j in self.jellies:
            j[1] += math.sin(self.t * 0.6 + j[3]) * 12 * dt

    # Rysowanie bez pełnoekranowej przezroczystej warstwy: kolory „półprzezroczyste” są
    # z góry zmieszane z kolorem wody na danej wysokości, a promienie światła to jedna gotowa warstwa.
    def _prepare_fast(self):
        p = self.p
        self.bg = [mix(p["top"], p["bottom"], (y / H) ** 0.9) for y in range(H)]
        rays = pygame.Surface((W + 200, H), pygame.SRCALPHA)
        for k in range(p["rays"]):
            x = 100 + (k + 0.5) * W / p["rays"]
            w1, w2 = 40 + k % 3 * 20, 160 + k % 2 * 90
            pygame.draw.polygon(rays, (255, 255, 240, p["ray_alpha"]),
                                [(x - w1, 0), (x + w1, 0), (x + w2 - 120, H), (x - w2 - 120, H)])
        self.rays = _fast(rays, True)
        self.static = _fast(self.static, False)

    def tint(self, col, a, y):
        return mix(self.bg[max(0, min(H - 1, int(y)))], col, a / 255)

    def draw(self, surf, dim=0):
        p = self.p
        if not hasattr(self, "bg"):
            self._prepare_fast()
        surf.blit(self.static, (0, 0))
        # promienie światła: jedna gotowa warstwa, która powoli się kołysze
        surf.blit(self.rays, (round(-100 + math.sin(self.t * 0.3) * 45), 0))
        for sx, sy, sr, age in self.smoke:
            a = max(0, int(150 * (1 - age / 4.5)))
            pygame.draw.circle(surf, self.tint((40, 30, 34), a, sy), (sx, sy), sr)
        for f in self.fish:
            self._fish(surf, f)
        for j in self.jellies:
            self._jelly(surf, j)
        # glony
        weed_tip = mix(p["weed"], (255, 255, 255), .2)
        for x0, segs, ph, wdt in self.weeds:
            prev = (x0, H - 30)
            for k in range(1, segs):
                x = x0 + math.sin(self.t * 1.4 + ph + k * 0.45) * k * 1.8
                y = H - 30 - k * 16
                pygame.draw.line(surf, p["weed"], prev, (x, y), max(3, wdt - k // 2))
                prev = (x, y)
            pygame.draw.circle(surf, weed_tip, prev, 4)
        # drobinki / mini bąbelki
        for m in self.motes:
            x = m[0] + math.sin(self.t + m[4]) * 4
            y = m[1]
            kind = p.get("motes")
            if p["glow"]:
                a = max(0, int(120 + 100 * math.sin(self.t * 2 + m[4])))
                pygame.draw.circle(surf, self.tint((120, 240, 255), a // 3, y), (x, y), m[2] * 3)
                pygame.draw.circle(surf, self.tint((200, 255, 255), a, y), (x, y), m[2] * 0.8)
            elif kind == "snow":
                pygame.draw.circle(surf, self.tint((255, 255, 255), 220, y), (x + math.sin(self.t * 0.7 + m[4]) * 10, y), m[2])
            elif kind == "embers":
                a = max(0, int(150 + 100 * math.sin(self.t * 3 + m[4])))
                pygame.draw.circle(surf, self.tint((255, 140, 50), a // 3, y), (x, y), m[2] * 2.4)
                pygame.draw.circle(surf, self.tint((255, 210, 120), a, y), (x, y), m[2] * 0.7)
            elif kind == "pearls":
                pygame.draw.circle(surf, self.tint((255, 246, 255), 200, y), (x, y), m[2] * 1.2)
            else:
                pygame.draw.circle(surf, self.tint((230, 250, 255), 140, y), (x, y), m[2], 1)
        if dim:
            from core import dim as _dim
            _dim(surf, dim)

    def _fish(self, s, f):
        x, y, d, _, sc, ph = f
        y = y + math.sin(self.t * 2 + ph) * 6
        col = self.tint(self.p["fish"], 150 if not self.p["glow"] else 120, y)
        bw, bh = 46 * sc, 20 * sc
        pygame.draw.ellipse(s, col, (x - bw / 2, y - bh / 2, bw, bh))
        tx = x - d * bw / 2
        wag = math.sin(self.t * 9 + ph) * 4 * sc
        pygame.draw.polygon(s, col, [(tx + d * 4, y), (tx - d * 16 * sc, y - 10 * sc + wag), (tx - d * 16 * sc, y + 10 * sc + wag)])
        if self.p["glow"]:
            pygame.draw.circle(s, (180, 255, 255), (x + d * bw * 0.3, y - 2), 2.5 * sc)

    def _jelly(self, s, j):
        x, y, r, ph, col = j
        y2 = y + math.sin(self.t * 0.9 + ph) * 10

        def make_glow():
            g = pygame.Surface((int(r * 4), int(r * 4)), pygame.SRCALPHA)
            pygame.draw.circle(g, (*col, 30), (r * 2, r * 2), r * 1.9)
            return _fast(g, True)
        glow = _cache_get(("jglow", r, col), make_glow)
        s.blit(glow, (x - r * 2, y2 - r * 2))
        dw, dh = int(r * 2 * (1 + 0.08 * math.sin(self.t * 3 + ph))) // 2 * 2, int(r * 1.6)

        def make_dome():
            dome = pygame.Surface((dw, dh // 2 + 2), pygame.SRCALPHA)
            pygame.draw.ellipse(dome, (*col, 120), (0, 0, dw, dh))
            return _fast(dome, True)
        s.blit(_cache_get(("jdome", dw, dh, col), make_dome), (x - dw / 2, y2 - dh / 2))
        tcol = self.tint(col, 140, y2 + 30)
        for k in range(5):
            tx = x - r * 0.7 + k * r * 0.35
            pts = [(tx + math.sin(self.t * 2 + k + i * 0.6) * 5, y2 + i * 9) for i in range(8)]
            pygame.draw.lines(s, tcol, False, pts, 2)


# ---------- bąbelki ----------
_bubble_cache = {}
STYLES = {
    "normal": ((143, 224, 244), (210, 245, 255)),
    "cmp": ((255, 150, 120), (255, 125, 92)),
    "fixed": ((255, 211, 126), (255, 230, 170)),
    "select": ((111, 220, 174), (170, 255, 215)),
    "wrong": ((255, 107, 129), (255, 170, 180)),
}


def bubble_surface(r, style="normal"):
    r = int(r)
    key = (r, style)
    if key in _bubble_cache:
        return _bubble_cache[key]
    tint, rim = STYLES[style]
    size = r * 2 + 8
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    if style != "normal":
        pygame.draw.circle(s, (*rim, 50), (c, c), r + 4)
    for k in range(r, 0, -1):
        t = k / r
        a = int(14 + 120 * t ** 4)
        pygame.draw.circle(s, (*tint, a), (c, c), k)
    pygame.draw.circle(s, (*rim, 235), (c, c), r, 3 if style != "normal" else 2)
    hl = pygame.Rect(0, 0, r * 0.62, r * 0.42)
    hl.center = (c - r * 0.36, c - r * 0.44)
    pygame.draw.ellipse(s, (255, 255, 255, 190), hl)
    pygame.draw.circle(s, (255, 255, 255, 120), (c + r * 0.45, c + r * 0.42), max(2, r * 0.09))
    s = _fast(s, True)
    _bubble_cache[key] = s
    return s


# ---------- bąbelki z dokładnością do ćwierć piksela ----------
# Gra może stawiać obrazki tylko w pełnych pikselach, więc powolne kołysanie skakało o piksel
# (na ekranie Retina o 2 fizyczne piksele) i wyglądało jak drżenie. Dlatego każdy bąbelek
# razem z liczbą jest rysowany 4× większy i zmniejszany z wygładzaniem w 4 wersjach
# przesuniętych o 0, ¼, ½ i ¾ piksela. Przy rysowaniu wybierana jest wersja pasująca do pozycji.
SUB = 4


def _bubble_hires(r, style, label, label_col, shadow_col, label_size):
    tint, rim = STYLES[style]

    def make():
        R = r * SUB
        size = (r * 2 + 8) * SUB
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        s.fill((*rim, 0))
        c = size // 2
        if style != "normal":
            pygame.draw.circle(s, (*rim, 50), (c, c), R + 4 * SUB)
        for k in range(R, 0, -2):
            t = k / R
            pygame.draw.circle(s, (*tint, int(14 + 120 * t ** 4)), (c, c), k)
        pygame.draw.circle(s, (*rim, 235), (c, c), R, (3 if style != "normal" else 2) * SUB)
        hl = pygame.Rect(0, 0, R * 0.62, R * 0.42)
        hl.center = (c - R * 0.36, c - R * 0.44)
        pygame.draw.ellipse(s, (255, 255, 255, 190), hl)
        pygame.draw.circle(s, (255, 255, 255, 120), (c + R * 0.45, c + R * 0.42), max(2 * SUB, R * 0.09))
        if label:
            f = font(label_size * SUB, display=True)
            sh = f.render(label, True, shadow_col)
            s.blit(sh, sh.get_rect(center=(c + SUB, c + 2 * SUB)))
            img = f.render(label, True, label_col)
            s.blit(img, img.get_rect(center=(c, c)))
        return s
    return _cache_get(("bh", r, style, label, label_col, shadow_col, label_size), make)


def bubble_img(r, style="normal", fy=0, label=None, label_col=INK, shadow_col=(4, 30, 46), label_size=None, alpha=255):
    r = int(r)
    label_size = label_size or max(16, int(r * 0.62))

    def make():
        hi = _bubble_hires(r, style, label, label_col, shadow_col, label_size)
        w = hi.get_width()
        canvas = pygame.Surface((w, w + SUB), pygame.SRCALPHA)
        canvas.fill((*STYLES[style][1], 0))
        canvas.blit(hi, (0, fy))
        out = pygame.transform.smoothscale(canvas, (w // SUB, w // SUB + 1))
        if alpha < 255:
            out.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        return _fast(out, True)
    return _cache_get(("bs", r, style, fy, label, label_col, shadow_col, label_size, alpha), make)


def draw_bubble(surf, x, y, r, style="normal", label=None, label_col=INK, shadow_col=(4, 30, 46),
                label_size=None, alpha=255):
    iy = math.floor(y)
    fy = min(SUB - 1, int((y - iy) * SUB))
    img = bubble_img(r, style, fy, label, label_col, shadow_col, label_size, alpha)
    half = int(r) + 4
    surf.blit(img, (round(x) - half, iy - half))


def warm_bubble(r, styles, label=None, label_cols=None, label_size=None):
    """Przygotowuje obrazki z góry (podczas przejścia między ekranami), żeby gra nie przycinała."""
    for style in styles:
        col, sh = label_cols(style) if label_cols else (INK, (4, 30, 46))
        for fy in range(SUB):
            bubble_img(r, style, fy, label, col, sh, label_size)


def bubble_label_cols(style):
    return ((255, 244, 214), (90, 50, 0)) if style == "fixed" else (INK, (4, 30, 46))


class Bubble:
    def __init__(self, v, x, y, r):
        self.v = v
        self.x, self.y = x, y
        self.r = r
        self.anim = None
        self.phase = random.random() * 6
        self.style = "normal"
        self.shake = 0.0
        self.pop = 0.0
        self.calm = 1.0
        self.hidden = False   # „zamrożona” liczba: zamiast niej znak zapytania

    def move_to(self, x, y, dur=0.5, arc=0.0):
        self.anim = [self.x, self.y, x, y, 0.0, dur, arc]

    @property
    def busy(self):
        return self.anim is not None

    def update(self, dt):
        self.shake = max(0.0, self.shake - dt * 2.5)
        self.pop = max(0.0, self.pop - dt * 3)
        target = 0.0 if self.anim else 1.0
        self.calm += (target - self.calm) * min(1.0, dt * (10 if self.anim else 2.5))
        if self.anim:
            a = self.anim
            a[4] += dt
            p = min(1.0, a[4] / a[5])
            e = p * p * (3 - 2 * p)
            self.x = a[0] + (a[2] - a[0]) * e
            self.y = a[1] + (a[3] - a[1]) * e - math.sin(math.pi * p) * a[6]
            if p >= 1:
                self.anim = None

    def draw(self, surf, t):
        # kołysanie płynnie wygasa w ruchu i płynnie wraca po nim (bez skoku na końcu animacji)
        bob = math.sin(t * 2.2 + self.phase) * 3 * self.calm
        sx = math.sin(t * 50) * 8 * self.shake
        col, sh = bubble_label_cols(self.style)
        label = "?" if self.hidden else str(self.v)
        draw_bubble(surf, self.x + sx, self.y + bob, self.r, self.style, label, col, sh)

    def warm(self, styles=("normal", "cmp", "fixed")):
        warm_bubble(self.r, styles, "?" if self.hidden else str(self.v), bubble_label_cols)


# ---------- Bulek, maskotka ----------
class Mascot:
    BODY = (255, 158, 64)

    def __init__(self, x=640, y=300):
        self.x, self.y = x, y
        self.tx, self.ty = x, y
        self.face = 1
        self.mood = "idle"
        self.mood_t = 0.0
        self.t = 0.0
        self.scale = 1.0

    def goto(self, x, y):
        self.tx, self.ty = x, y

    def feel(self, mood, dur=0.9):
        self.mood, self.mood_t = mood, dur

    def update(self, dt):
        self.t += dt
        dx = self.tx - self.x
        if abs(dx) > 2:
            self.face = 1 if dx > 0 else -1
        k = min(1, dt * 3.5)
        self.x += dx * k
        self.y += (self.ty - self.y) * k
        if self.mood_t > 0:
            self.mood_t -= dt
            if self.mood_t <= 0:
                self.mood = "idle"

    def draw(self, surf):
        s = self.scale
        x = self.x
        y = self.y + math.sin(self.t * 2.5) * 5
        if self.mood == "happy":
            y -= abs(math.sin(self.t * 12)) * 16
        if self.mood == "sad":
            x += math.sin(self.t * 40) * 4
        f = self.face
        body = self.BODY if self.mood != "sad" else (190, 150, 170)
        belly = mix(body, (255, 255, 255), 0.45)
        wag = math.sin(self.t * 10) * 6
        tail_x = x - f * 34 * s
        pygame.draw.polygon(surf, mix(body, (0, 0, 0), 0.15),
                            [(tail_x + f * 8 * s, y), (tail_x - f * 26 * s, y - 20 * s + wag), (tail_x - f * 20 * s, y + wag * 0.3), (tail_x - f * 26 * s, y + 20 * s + wag)])
        pygame.draw.ellipse(surf, body, (x - 40 * s, y - 30 * s, 80 * s, 60 * s))
        pygame.draw.ellipse(surf, belly, (x - 26 * s, y + 2 * s, 52 * s, 24 * s))
        # płetwa grzbietowa
        pygame.draw.polygon(surf, mix(body, (0, 0, 0), 0.15),
                            [(x - 12 * s, y - 26 * s), (x + 6 * s * f, y - 44 * s), (x + 16 * s * f, y - 24 * s)])
        # paski
        for k in (-8, 6):
            pygame.draw.arc(surf, mix(body, (255, 255, 255), 0.6), (x + k * s - 8 * s, y - 28 * s, 16 * s, 56 * s), -1.2, 1.2, 3)
        # oko
        ex, ey = x + f * 18 * s, y - 8 * s
        pygame.draw.circle(surf, (255, 255, 255), (ex, ey), 11 * s)
        pygame.draw.circle(surf, (20, 30, 40), (ex + f * 3 * s, ey + 1), 6 * s)
        pygame.draw.circle(surf, (255, 255, 255), (ex + f * 5 * s, ey - 2 * s), 2 * s)
        # buzia
        mx = x + f * 30 * s
        if self.mood == "sad":
            pygame.draw.arc(surf, (90, 30, 30), (mx - 8 * s, y + 8 * s, 14 * s, 10 * s), 0.3, 2.8, 2)
        else:
            pygame.draw.arc(surf, (90, 30, 30), (mx - 9 * s, y - 2 * s, 14 * s, 12 * s), 3.6, 5.9, 3)
        # policzek
        pygame.draw.circle(surf, (255, 120, 120), (x + f * 8 * s, y + 6 * s), 5 * s)


# ---------- cząsteczki ----------
class Particles:
    def __init__(self):
        self.items = []

    def burst(self, x, y, color, n=18, speed=220, up=False):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(0.3, 1) * speed
            vy = math.sin(a) * sp - (120 if up else 0)
            self.items.append([x, y, math.cos(a) * sp, vy, random.uniform(0.5, 1.0), random.uniform(2, 6), color])

    def sparkle(self, x, y, n=10):
        self.burst(x, y, PEARL, n, 160)

    def update(self, dt):
        damp = 0.94 ** (dt * 60)  # tak samo przy 60 i 120 klatkach na sekundę
        for p in self.items:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= damp
            p[3] = p[3] * damp - 30 * dt
            p[4] -= dt
        self.items = [p for p in self.items if p[4] > 0]

    def draw(self, surf):
        for x, y, _, _, life, r, col in self.items:
            a = max(0, min(255, int(255 * life))) // 32 * 32
            ri = int(r)

            def make(ri=ri, col=col, a=a):
                s = pygame.Surface((ri * 2 + 4, ri * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(s, (*col, a), (ri + 2, ri + 2), ri, 0 if ri < 3 else 2)
                return _fast(s, True)
            s = _cache_get(("part", ri, col, a), make)
            surf.blit(s, (x - r - 2, y - r - 2))


def bubble_icon(size=64):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    b = bubble_surface(size // 2 - 6, "normal")
    s.blit(b, b.get_rect(center=(size // 2, size // 2)))
    return s
