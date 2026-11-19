"""Zadania dnia (3 losowane codziennie) i stałe wyzwania z poziomami. Nagrodą są perły."""
import datetime
import random

# Każde zadanie dnia: tekst, cel, nagroda i funkcja, która z bieżącego postępu i zdarzenia liczy nowy postęp.
DAILY = {
    "win3": ("Przejdź 3 poziomy", 3, 30,
             lambda cur, ev, kw: cur + 1 if ev == "level_win" else cur),
    "correct50": ("Udziel 50 dobrych odpowiedzi", 50, 30,
                  lambda cur, ev, kw: cur + 1 if ev == "correct" else cur),
    "combo10": ("Zrób serię 10 dobrych odpowiedzi z rzędu", 10, 25,
                lambda cur, ev, kw: max(cur, kw.get("n", 0)) if ev == "combo" else cur),
    "flawless": ("Przejdź poziom bez żadnego błędu", 1, 25,
                 lambda cur, ev, kw: 1 if ev == "level_win" and kw.get("mistakes") == 0 else cur),
    "duel": ("Wygraj duel z AI", 1, 40,
             lambda cur, ev, kw: cur + 1 if ev == "duel_win" else cur),
    "puzzle": ("Ułóż Układankę w najmniejszej liczbie ruchów", 1, 30,
               lambda cur, ev, kw: 1 if ev == "puzzle_perfect" else cur),
    "fast": ("Przejdź poziom w mniej niż 40 sekund", 1, 25,
             lambda cur, ev, kw: 1 if ev == "level_win" and kw.get("time", 999) < 40 else cur),
    "early": ("Trafnie wybierz Koniec 3 razy", 3, 25,
              lambda cur, ev, kw: cur + 1 if ev == "early_end" else cur),
    "stars5": ("Zdobądź 5 gwiazdek (powtórki też się liczą)", 5, 30,
               lambda cur, ev, kw: cur + kw.get("stars", 0) if ev == "level_win" else cur),
}

# Wyzwania: (id, nazwa, opis, progi, nagrody, wartość z profilu)
CHALLENGES = [
    ("stars", "Zbieracz gwiazdek", "Zebrane gwiazdki", [10, 36, 72], [50, 100, 200],
     lambda save, p: save.total_stars(p)),
    ("levels", "Odkrywca", "Najwyższy ukończony poziom", [6, 12, 24], [40, 80, 160],
     lambda save, p: save.highest_level(p)),
    ("correct", "Bystre oko", "Dobre odpowiedzi", [100, 500, 2000], [40, 100, 250],
     lambda save, p: p["stats"]["correct"]),
    ("combo", "Mistrz serii", "Najdłuższa seria", [10, 25, 45], [30, 80, 150],
     lambda save, p: p["stats"]["best_combo"]),
    ("duels", "Pojedynkowicz", "Wygrane duele z AI", [1, 5, 20], [40, 100, 250],
     lambda save, p: p["stats"]["duel_win"]),
]


def today():
    return datetime.date.today().isoformat()


class Quests:
    def __init__(self, app):
        self.app = app

    @property
    def save(self):
        return self.app.save

    def ensure_daily(self):
        p = self.save.p
        d = p.get("daily") or {}
        if d.get("date") != today():
            rnd = random.Random(today() + p["nick"])
            ids = rnd.sample(sorted(DAILY), 3)
            p["daily"] = {"date": today(), "ids": ids, "progress": {i: 0 for i in ids}, "claimed": [], "told": []}
            self.save.dirty = True
        return p["daily"]

    # ----- zdarzenia z gry -----
    def emit(self, ev, **kw):
        save = self.save
        p = save.p
        st = p["stats"]
        if ev == "correct":
            st["correct"] += 1
        elif ev == "combo":
            st["best_combo"] = max(st["best_combo"], kw.get("n", 0))
        elif ev == "level_win":
            st["levels_won"] += 1
        elif ev == "duel_win":
            st["duel_win"] += 1
        elif ev == "duel_loss":
            st["duel_loss"] += 1
        d = self.ensure_daily()
        for qid in d["ids"]:
            text, target, _, fn = DAILY[qid]
            d["progress"][qid] = min(target, fn(d["progress"].get(qid, 0), ev, kw))
            if d["progress"][qid] >= target and qid not in d["told"]:
                d["told"].append(qid)
                self.app.toast("Zadanie dnia wykonane! Odbierz perły w Zadaniach.")
                self.app.audio.play("star")
        for cid, name, _, targets, _, value in CHALLENGES:
            a = p["ach"].setdefault(cid, {"claimed": 0, "told": 0})
            reached = sum(1 for t in targets if value(save, p) >= t)
            if reached > a["told"]:
                a["told"] = reached
                self.app.toast(f"Wyzwanie „{name}”: poziom {reached}!")
        save.dirty = True
        if ev in ("level_win", "duel_win", "duel_loss"):
            save.write()

    # ----- odczyt i odbieranie nagród -----
    def daily(self):
        d = self.ensure_daily()
        out = []
        for qid in d["ids"]:
            text, target, reward, _ = DAILY[qid]
            prog = d["progress"].get(qid, 0)
            out.append(dict(id=qid, text=text, target=target, reward=reward, progress=prog,
                            done=prog >= target, claimed=qid in d["claimed"]))
        return out

    def claim_daily(self, qid):
        d = self.ensure_daily()
        q = next(q for q in self.daily() if q["id"] == qid)
        if q["done"] and not q["claimed"]:
            d["claimed"].append(qid)
            self.save.p["pearls"] += q["reward"]
            self.save.write()
            return q["reward"]
        return 0

    def challenges(self):
        save, p = self.save, self.save.p
        out = []
        for cid, name, desc, targets, rewards, value in CHALLENGES:
            a = p["ach"].setdefault(cid, {"claimed": 0, "told": 0})
            v = value(save, p)
            reached = sum(1 for t in targets if v >= t)
            nxt = min(a["claimed"], len(targets) - 1)
            out.append(dict(id=cid, name=name, desc=desc, value=v, targets=targets, reached=reached,
                            claimed=a["claimed"], target=targets[nxt],
                            reward=rewards[a["claimed"]] if a["claimed"] < len(rewards) else 0,
                            claimable=a["claimed"] < reached, finished=a["claimed"] >= len(targets)))
        return out

    def claim_challenge(self, cid):
        c = next(c for c in self.challenges() if c["id"] == cid)
        if c["claimable"]:
            self.save.p["ach"][cid]["claimed"] += 1
            self.save.p["pearls"] += c["reward"]
            self.save.write()
            return c["reward"]
        return 0

    def claimable_count(self):
        return sum(1 for q in self.daily() if q["done"] and not q["claimed"]) + \
            sum(1 for c in self.challenges() if c["claimable"])
