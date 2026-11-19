"""Wspólne rzeczy: stałe, czcionki, rysowanie tekstu, przyciski, zapis gry i dźwięk."""
import array
import json
import math
import os
import random
import sys

import pygame

W, H = 1280, 720
FPS = 60
TITLE = "Bąbelkowo"

# ---------- kolory ----------
INK = (234, 247, 252)
MUTED = (150, 190, 208)
AQUA = (143, 224, 244)
CORAL = (255, 125, 92)
PEARL = (255, 211, 126)
KELP = (111, 220, 174)
ALARM = (255, 107, 129)
NAVY = (6, 30, 46)
PANEL = (7, 36, 56)
PANEL_EDGE = (60, 120, 150)
SHADOW = (2, 14, 24)

# ---------- czcionki (dołączone do gry, licencja SIL OFL, pełny polski alfabet) ----------
def asset(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", *parts)


FONT_FILES = {
    "display": "TitanOne-Regular.ttf",
    "bold": "AtkinsonHyperlegible-Bold.ttf",
    "body": "AtkinsonHyperlegible-Regular.ttf",
}
_fonts = {}


def font(size, bold=False, display=False):
    key = (size, bold, display)
    if key not in _fonts:
        kind = "display" if display else ("bold" if bold else "body")
        try:
            _fonts[key] = pygame.font.Font(asset("fonts", FONT_FILES[kind]), size)
        except (OSError, pygame.error):
            _fonts[key] = pygame.font.SysFont("segoeui,arial,dejavusans", size, bold=bold or display)
    return _fonts[key]


def draw_swap_icon(surf, cx, cy, color, s=1.0):
    """Ikona zamiany: dwie strzałki w przeciwne strony."""
    w, h, t = 11 * s, 5 * s, max(2, int(3 * s))
    pygame.draw.line(surf, color, (cx - w, cy - h), (cx + w - 3 * s, cy - h), t)
    pygame.draw.polygon(surf, color, [(cx + w + 2 * s, cy - h), (cx + w - 5 * s, cy - h - 5 * s), (cx + w - 5 * s, cy - h + 5 * s)])
    pygame.draw.line(surf, color, (cx + w, cy + h), (cx - w + 3 * s, cy + h), t)
    pygame.draw.polygon(surf, color, [(cx - w - 2 * s, cy + h), (cx - w + 5 * s, cy + h - 5 * s), (cx - w + 5 * s, cy + h + 5 * s)])


# ---------- pamięć podręczna rysowania (gotowe obrazki tekstu i paneli zamiast tworzenia ich co klatkę) ----------
_cache = {}


def cached(key, make):
    v = _cache.get(key)
    if v is None:
        if len(_cache) > 5000:
            _cache.clear()
        v = _cache[key] = make()
    return v


def _alpha_copy(img, a):
    c = img.copy()
    c.set_alpha(a)
    return c


def render(s, size, color, bold=False, display=False):
    return cached(("r", s, size, color, bold, display), lambda: font(size, bold, display).render(s, True, color))


def fit_size(s, size, max_w, bold=False, display=False):
    """Największy rozmiar czcionki (nie większy niż size), przy którym napis mieści się w max_w."""
    def make():
        sz = size
        while sz > 10 and font(sz, bold, display).size(s)[0] > max_w:
            sz -= 1
        return sz
    return cached(("fit", s, size, max_w, bold, display), make)


def text(surf, s, size, color, pos, anchor="center", bold=False, display=False, shadow=True, alpha=255, max_w=None):
    if max_w:
        size = fit_size(s, size, max_w, bold, display)
    a = 255 if alpha >= 255 else max(0, int(alpha)) // 16 * 16
    if a < 255:
        img = cached(("a", s, size, color, bold, display, a), lambda: _alpha_copy(render(s, size, color, bold, display), a))
    else:
        img = render(s, size, color, bold, display)
    rect = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if shadow:
        sa = 150 if a == 255 else a // 2
        sh = cached(("s", s, size, bold, display, sa), lambda: _alpha_copy(render(s, size, SHADOW, bold, display), sa))
        surf.blit(sh, rect.move(2, 3))
    surf.blit(img, rect)
    return rect


def wrap(s, size, width, bold=False):
    def make():
        f = font(size, bold)
        lines = []
        for para in s.split("\n"):
            cur = ""
            for word in para.split(" "):
                test = (cur + " " + word).strip()
                if f.size(test)[0] <= width:
                    cur = test
                else:
                    if cur:
                        lines.append(cur)
                    cur = word
            lines.append(cur)
        return tuple(lines)
    return cached(("w", s, size, width, bold), make)


def text_block(surf, s, size, color, topleft, width, line_h=None, bold=False, max_h=None):
    """Tekst łamany na linie. Z max_h czcionka zmniejsza się, aż całość zmieści się w ramce."""
    ratio = (line_h / size) if line_h else 1.35
    if max_h:
        while size > 12 and len(wrap(s, size, width, bold)) * int(size * ratio) > max_h:
            size -= 1
    lh = int(size * ratio)
    x, y = topleft
    for ln in wrap(s, size, width, bold):
        text(surf, ln, size, color, (x, y), "topleft", bold=bold, shadow=False)
        y += lh
    return y


def dim(surf, alpha, color=(2, 14, 24)):
    surf.blit(cached(("dim", alpha, color), lambda: _make_dim(alpha, color)), (0, 0))


def _make_dim(alpha, color):
    d = pygame.Surface((W, H))
    d.fill(color)
    d.set_alpha(alpha)
    return d


def row(buttons, cx, y, gap=18, max_w=None):
    """Układa przyciski w poziomym rzędzie wyśrodkowanym na cx, zmniejszając je, gdy się nie mieszczą."""
    widths = [b.rect.w for b in buttons]
    total = sum(widths) + gap * (len(buttons) - 1)
    if max_w and total > max_w:
        k = (max_w - gap * (len(buttons) - 1)) / sum(widths)
        widths = [int(w * k) for w in widths]
        total = sum(widths) + gap * (len(buttons) - 1)
    x = cx - total / 2
    for b, w in zip(buttons, widths):
        b.rect.w = w
        b.rect.center = (int(x + w / 2), int(y))
        x += w + gap


def lerp(a, b, t):
    return a + (b - a) * t


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(max(0, min(255, int(lerp(a, b, t)))) for a, b in zip(c1, c2))


def panel(surf, rect, alpha=215, radius=18, edge=PANEL_EDGE):
    def make():
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*PANEL, alpha), s.get_rect(), border_radius=radius)
        pygame.draw.rect(s, (*edge, 160), s.get_rect(), 2, border_radius=radius)
        return s
    surf.blit(cached(("panel", rect.w, rect.h, alpha, radius, edge), make), rect.topleft)


def star_points(cx, cy, r_out, r_in, rot=-math.pi / 2):
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / 5
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def draw_star(surf, cx, cy, r, filled):
    pts = star_points(cx, cy, r, r * 0.45)
    if filled:
        pygame.draw.polygon(surf, PEARL, pts)
        pygame.draw.polygon(surf, (255, 240, 200), pts, 2)
    else:
        pygame.draw.polygon(surf, (30, 60, 80), pts)
        pygame.draw.polygon(surf, (110, 150, 170), pts, 2)


def draw_heart(surf, cx, cy, s, filled):
    col = ALARM if filled else (40, 66, 84)
    edge = (255, 200, 210) if filled else (100, 130, 150)
    pygame.draw.circle(surf, col, (cx - s * 0.5, cy - s * 0.2), s * 0.55)
    pygame.draw.circle(surf, col, (cx + s * 0.5, cy - s * 0.2), s * 0.55)
    pygame.draw.polygon(surf, col, [(cx - s * 1.02, cy - 0.05 * s), (cx + s * 1.02, cy - 0.05 * s), (cx, cy + s)])
    if filled:
        pygame.draw.circle(surf, edge, (cx - s * 0.62, cy - s * 0.4), s * 0.16)


def draw_lock(surf, cx, cy, s=1.0, color=(170, 200, 215)):
    body = pygame.Rect(0, 0, 30 * s, 24 * s)
    body.center = (cx, cy + 6 * s)
    pygame.draw.arc(surf, color, pygame.Rect(cx - 10 * s, cy - 16 * s, 20 * s, 26 * s), 0, math.pi, int(4 * s))
    pygame.draw.rect(surf, color, body, border_radius=int(5 * s))
    pygame.draw.circle(surf, PANEL, (cx, cy + 5 * s), 3.5 * s)


# ---------- przycisk ----------
class Button:
    STYLES = {
        "primary": ((143, 224, 244), (190, 240, 252), NAVY),
        "coral": ((255, 125, 92), (255, 160, 132), (40, 12, 4)),
        "pearl": ((255, 211, 126), (255, 228, 170), (50, 30, 0)),
        "ghost": ((14, 58, 84), (24, 84, 116), INK),
    }

    def __init__(self, label, center, size=(320, 64), style="primary", key=None, font_size=28, action=None):
        self.label = label
        self.rect = pygame.Rect(0, 0, *size)
        self.rect.center = center
        self.style = style
        self.key = key
        self.font_size = font_size
        self.action = action
        self.hover = 0.0
        self.focus = False
        self.enabled = True
        self.flash = 0.0

    def update(self, dt, mouse):
        want = 1.0 if (self.enabled and (self.rect.collidepoint(mouse) or self.focus)) else 0.0
        self.hover += (want - self.hover) * min(1, dt * 14)
        self.flash = max(0.0, self.flash - dt * 3)

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)

    def draw(self, surf):
        base, light, fg = self.STYLES[self.style]
        col = mix(base, light, self.hover * 0.8 + self.flash)
        grow = int(self.hover * 4)
        r = self.rect.inflate(grow, grow)
        sh = r.move(0, 6)
        pygame.draw.rect(surf, SHADOW, sh, border_radius=18)
        if not self.enabled:
            col = mix(col, (40, 70, 90), 0.7)
            fg = mix(fg, (120, 140, 150), 0.6)
        pygame.draw.rect(surf, col, r, border_radius=18)
        pygame.draw.rect(surf, mix(col, (255, 255, 255), 0.35), r, 2, border_radius=18)
        hl_size = (r.w - 20, int(r.h * 0.32))

        def make_hl():
            s = pygame.Surface(hl_size, pygame.SRCALPHA)
            pygame.draw.rect(s, (255, 255, 255, 40), s.get_rect(), border_radius=12)
            return s
        surf.blit(cached(("btn_hl", hl_size), make_hl), (r.x + 10, r.y + 6))
        if self.focus and self.enabled:
            pygame.draw.rect(surf, PEARL, r.inflate(8, 8), 3, border_radius=21)
        # napis zawsze mieści się w przycisku: czcionka zmniejsza się, gdy trzeba
        inner = self.rect.w - 32
        if self.key:
            ksize = max(13, self.font_size - 10)
            kimg = render(self.key, ksize, fg, bold=True)
            kw = kimg.get_width() + 16
            size = fit_size(self.label, self.font_size, inner - kw - 12, display=True)
            img = render(self.label, size, fg, display=True)
            total = img.get_width() + 12 + kw
            x0 = r.centerx - total // 2
            surf.blit(img, img.get_rect(midleft=(x0, r.centery)))
            kr = pygame.Rect(0, 0, kw, kimg.get_height() + 6)
            kr.midleft = (x0 + img.get_width() + 12, r.centery)

            def make_key():
                ks = pygame.Surface(kr.size, pygame.SRCALPHA)
                pygame.draw.rect(ks, (*fg, 50), ks.get_rect(), border_radius=6)
                pygame.draw.rect(ks, (*fg, 120), ks.get_rect(), 1, border_radius=6)
                return ks
            surf.blit(cached(("btn_key", kr.size, fg), make_key), kr.topleft)
            surf.blit(kimg, kimg.get_rect(center=kr.center))
        else:
            size = fit_size(self.label, self.font_size, inner, display=True)
            img = render(self.label, size, fg, display=True)
            surf.blit(img, img.get_rect(center=r.center))


class ButtonList:
    """Pionowe lub poziome menu sterowane myszą i klawiaturą."""

    def __init__(self, buttons, vertical=True, grid=False):
        self.buttons = buttons
        self.vertical = vertical
        self.grid = grid   # siatka: wszystkie strzałki przechodzą po kolejnych przyciskach
        self.index = 0
        self.using_keys = False

    def update(self, dt, mouse, moved):
        if moved:
            self.using_keys = False
            for i, b in enumerate(self.buttons):
                if b.hit(mouse):
                    self.index = i
        for i, b in enumerate(self.buttons):
            b.focus = self.using_keys and i == self.index
            b.update(dt, mouse)

    def handle(self, e, app):
        """Zwraca kliknięty przycisk albo None."""
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self.buttons:
                if b.hit(e.pos):
                    app.audio.play("click")
                    b.flash = 1
                    return b
        if e.type == pygame.KEYDOWN:
            prev = (pygame.K_UP, pygame.K_w) if self.vertical else (pygame.K_LEFT, pygame.K_a)
            nxt = (pygame.K_DOWN, pygame.K_s) if self.vertical else (pygame.K_RIGHT, pygame.K_d)
            if self.grid:
                prev, nxt = (pygame.K_UP, pygame.K_LEFT), (pygame.K_DOWN, pygame.K_RIGHT)
            if e.key in prev + nxt:
                if self.using_keys:
                    step = -1 if e.key in prev else 1
                    for _ in range(len(self.buttons)):
                        self.index = (self.index + step) % len(self.buttons)
                        if self.buttons[self.index].enabled:
                            break
                self.using_keys = True
                app.audio.play("tick")
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.using_keys:
                b = self.buttons[self.index]
                if b.enabled:
                    app.audio.play("click")
                    b.flash = 1
                    return b
        return None

    def draw(self, surf):
        for b in self.buttons:
            b.draw(surf)


# ---------- zapis: ustawienia i profile graczy ----------
def new_profile(nick):
    return {
        "nick": nick,
        "avatar": {"suit": 0, "skin": 0, "hat": 1, "acc": 1},
        "owned": ["hat:0", "hat:1", "acc:0", "acc:1"],
        "stars": {}, "best": {}, "times": {},
        "pearls": 0,
        "stats": {"correct": 0, "best_combo": 0, "duel_win": 0, "duel_loss": 0, "levels_won": 0},
        "duels": {},
        "daily": {}, "ach": {},
    }


class Save:
    DIR = os.path.join(os.path.expanduser("~"), ".babelkowo")
    PATH = os.path.join(DIR, "zapis.json")
    DEFAULT = {"music": True, "sfx": True, "fullscreen": False, "seen_help": False,
               "profiles": {}, "current": "1", "next_id": 1}

    def __init__(self):
        self.data = json.loads(json.dumps(self.DEFAULT))
        loaded = {}
        try:
            with open(self.PATH, encoding="utf-8") as f:
                loaded = json.load(f)
        except (OSError, ValueError):
            pass
        self.data.update({k: v for k, v in loaded.items() if k in self.DEFAULT})
        if not self.data["profiles"]:
            self.create_profile("Gracz")
            # przeniesienie postępu ze starszej wersji gry (bez profili)
            self.p["stars"] = loaded.get("stars", {})
            self.p["best"] = loaded.get("best", {})
        for prof in self.data["profiles"].values():   # uzupełnienie brakujących pól
            base = new_profile(prof.get("nick", "Gracz"))
            for k, v in base.items():
                prof.setdefault(k, v)
            for k, v in base["stats"].items():
                prof["stats"].setdefault(k, v)
        if self.data["current"] not in self.data["profiles"]:
            self.data["current"] = next(iter(self.data["profiles"]))
        self.dirty = False

    # ----- profile -----
    @property
    def p(self):
        return self.data["profiles"][self.data["current"]]

    def profile_ids(self):
        return sorted(self.data["profiles"], key=int)

    def create_profile(self, nick):
        self.data["next_id"] = max(self.data.get("next_id", 1), 1)
        pid = str(self.data["next_id"])
        self.data["next_id"] += 1
        self.data["profiles"][pid] = new_profile(nick)
        self.data["current"] = pid
        self.write()
        return pid

    def switch(self, pid):
        if pid in self.data["profiles"]:
            self.data["current"] = pid
            self.write()

    # ----- postęp aktualnego gracza -----
    def write(self):
        self.dirty = False
        try:
            os.makedirs(self.DIR, exist_ok=True)
            tmp = self.PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.PATH)
        except OSError:
            pass

    def stars(self, lid):
        return self.p["stars"].get(str(lid), 0)

    def best(self, lid):
        return self.p["best"].get(str(lid), 0)

    def best_time(self, lid):
        return self.p["times"].get(str(lid))

    def unlocked(self, lid):
        return lid == 1 or self.stars(lid - 1) > 0

    def record(self, lid, stars, score, seconds=None):
        k = str(lid)
        p = self.p
        p["stars"][k] = max(stars, p["stars"].get(k, 0))
        p["best"][k] = max(score, p["best"].get(k, 0))
        if seconds is not None and (k not in p["times"] or seconds < p["times"][k]):
            p["times"][k] = round(seconds, 2)
        self.write()

    def total_stars(self, prof=None):
        return sum((prof or self.p)["stars"].values())

    def highest_level(self, prof=None):
        done = [int(k) for k, v in (prof or self.p)["stars"].items() if v > 0]
        return max(done) if done else 0

    def reset(self):
        """Zeruje postęp aktualnego gracza (nick, ludek i kupione rzeczy zostają)."""
        p = self.p
        for k in ("stars", "best", "times", "duels", "daily", "ach"):
            p[k] = {}
        p["stats"] = new_profile("")["stats"]
        self.write()


# ---------- dźwięk (generowany w kodzie, bez plików) ----------
RATE = 22050


def _render(dur, fn, vol=0.5):
    n = int(RATE * dur)
    buf = array.array("h")
    for i in range(n):
        v = fn(i / RATE, i)
        v = -1.0 if v < -1 else (1.0 if v > 1 else v)
        s = int(v * 32767 * vol)
        buf.append(s)
        buf.append(s)
    return buf


def _sweep(f0, f1, dur, decay):
    k = (f1 - f0) / dur

    def fn(t, i):
        ph = 2 * math.pi * (f0 * t + 0.5 * k * t * t)
        return math.sin(ph) * math.exp(-t * decay) * min(1, t * 400)
    return fn


def _notes(seq, wave="sine"):
    """seq: lista (częstotliwość, start, długość)."""
    def fn(t, i):
        v = 0.0
        for f, st, d in seq:
            if st <= t < st + d + 0.25:
                tt = t - st
                env = min(1, tt * 300) * math.exp(-tt * 7)
                ph = 2 * math.pi * f * tt
                v += (math.sin(ph) + 0.3 * math.sin(2 * ph)) * env
        return v * 0.6
    return fn


def _noise_whoosh(dur):
    state = [0.0]
    rnd = random.Random(7)

    def fn(t, i):
        x = rnd.uniform(-1, 1)
        a = 0.08 + 0.25 * math.sin(math.pi * t / dur)
        state[0] += (x - state[0]) * a
        return state[0] * math.sin(math.pi * t / dur) * 1.6
    return fn


def _music():
    # spokojna pętla: Am – F – C – G, pad + arpeggio, 12 sekund
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (130.81, 196.0, 261.63), (196.0, 246.94, 293.66)]
    seg = 3.0
    arp = []
    for c, ch in enumerate(chords):
        tones = [ch[0] * 2, ch[1] * 2, ch[2] * 2, ch[1] * 2]
        for k in range(8):
            arp.append((tones[k % 4], c * seg + k * seg / 8))

    def fn(t, i):
        c = int(t // seg) % 4
        tt = t - c * seg
        env = min(1, tt / 0.6) * min(1, (seg - tt) / 0.6)
        v = 0.0
        for f in chords[c]:
            v += math.sin(2 * math.pi * f * t) * 0.18 * env
        idx = int(t // (seg / 8))
        f, st = arp[idx % len(arp)]
        d = t - st
        v += math.sin(2 * math.pi * f * d) * math.exp(-d * 6) * 0.22
        return v
    return fn


class Audio:
    def __init__(self, save):
        self.save = save
        self.sounds = {}
        self.ok = False
        try:
            pygame.mixer.pre_init(RATE, -16, 2, 512)
            pygame.mixer.init(RATE, -16, 2, 512)
            if pygame.mixer.get_init()[0] != RATE:
                pygame.mixer.quit()
                pygame.mixer.init(RATE, -16, 2, 512)
            self.ok = True
        except pygame.error:
            return
        make = lambda buf: pygame.mixer.Sound(buffer=buf.tobytes())
        self.sounds = {
            "pop": make(_render(0.14, _sweep(950, 300, 0.14, 26), 0.45)),
            "tick": make(_render(0.04, _sweep(1500, 1300, 0.04, 80), 0.25)),
            "click": make(_render(0.08, _sweep(700, 1100, 0.08, 40), 0.35)),
            "swap": make(_render(0.35, _noise_whoosh(0.35), 0.35)),
            "good": make(_render(0.45, _notes([(659.25, 0, 0.1), (987.77, 0.09, 0.2)]), 0.4)),
            "bad": make(_render(0.38, lambda t, i: (1 if math.sin(2 * math.pi * 140 * t) > 0 else -1) * math.exp(-t * 7) * 0.5, 0.3)),
            "star": make(_render(0.5, _notes([(1318.5, 0, 0.3)]), 0.35)),
            "win": make(_render(1.1, _notes([(523.25, 0, .12), (659.25, .12, .12), (783.99, .24, .12), (1046.5, .36, .5)]), 0.4)),
            "lose": make(_render(1.0, _notes([(392.0, 0, .2), (329.63, .22, .2), (261.63, .44, .45)]), 0.4)),
            "fix": make(_render(0.5, _sweep(400, 900, 0.5, 6), 0.25)),
        }
        self.music = make(_render(12.0, _music(), 0.55))
        self.music_channel = None
        self.apply_music()

    def play(self, name):
        if self.ok and self.save.data["sfx"] and name in self.sounds:
            self.sounds[name].play()

    def apply_music(self):
        if not self.ok:
            return
        if self.save.data["music"]:
            if self.music_channel is None or not self.music_channel.get_busy():
                self.music_channel = self.music.play(loops=-1, fade_ms=1500)
                if self.music_channel:
                    self.music_channel.set_volume(0.5)
        elif self.music_channel is not None:
            self.music_channel.fadeout(400)
            self.music_channel = None
