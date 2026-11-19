"""Definicje 12 poziomów w trzech światach i generowanie tablic."""
import random

# mode: "decide" – gracz decyduje przy każdym porównaniu (Zamień / Zostaw)
#       "puzzle" – gracz sam zamienia sąsiadów, liczba ruchów jest ograniczona
# early: po każdym przejściu pytanie, czy kontynuować (flaga „zamieniono”)
# timer: sekundy na decyzję (0 = bez limitu)
# hidden: liczby są „zamrożone”, widać tylko porównywaną parę i bąbelki już posortowane
# dupes: w tablicy są powtórzone liczby (równych nie zamieniamy, dlatego algorytm jest stabilny)
LEVELS = [
    dict(id=1, world="plycizna", name="Pierwsze bąbelki", mode="decide", n=4, layout="random", timer=0, early=False,
         goal="Przy każdym porównaniu zdecyduj: zamienić czy zostawić?",
         tip="Zasada jest jedna: jeśli lewy bąbelek jest większy od prawego, zamień je."),
    dict(id=2, world="plycizna", name="Dwa przejścia", mode="decide", n=5, layout="random", timer=0, early=False,
         goal="Posortuj 5 bąbelków. Uważaj na serie: każda dobra decyzja z rzędu daje więcej punktów.",
         tip="Po każdym przejściu największy z pozostałych bąbelków wypływa na powierzchnię."),
    dict(id=3, world="plycizna", name="Pierwsza układanka", mode="puzzle", n=5, layout="random", slack=3,
         goal="Sam zamieniaj sąsiednie bąbelki. Masz ograniczoną liczbę ruchów.",
         tip="Inwersja to para w złej kolejności. Dobra zamiana usuwa dokładnie jedną inwersję."),
    dict(id=4, world="plycizna", name="Prawie w porządku", mode="decide", n=6, layout="nearly", timer=0, early=True,
         goal="Nowość: po każdym przejściu zdecyduj, czy grać dalej, czy tablica jest już gotowa.",
         tip="Jeśli w całym przejściu nie było żadnej zamiany, tablica jest posortowana. Wybierz Koniec!"),

    dict(id=5, world="rafa", name="Koralowy zegar", mode="decide", n=6, layout="random", timer=6, early=True,
         goal="Na rafie liczy się czas: na każdą decyzję masz 6 sekund.",
         tip="Szybka i dobra decyzja daje bonus czasowy."),
    dict(id=6, world="rafa", name="Ciasna szczelina", mode="puzzle", n=7, layout="random", slack=1,
         goal="7 bąbelków i tylko 1 zapasowy ruch. Każda zamiana musi się liczyć.",
         tip="Zamieniaj tylko pary, w których lewy jest większy. Wtedy nie zmarnujesz ruchu."),
    dict(id=7, world="rafa", name="Odwrócony prąd", mode="decide", n=7, layout="reversed", timer=5, early=False,
         goal="Najgorszy przypadek: tablica odwrócona. Ile tu będzie zamian?",
         tip="W odwróconej tablicy każde porównanie kończy się zamianą: n(n−1)/2 razy."),
    dict(id=8, world="rafa", name="Spokojna laguna", mode="decide", n=7, layout="nearly", timer=5, early=True,
         goal="Prawie posortowana tablica i 5 sekund na decyzję. Nie przegap momentu na Koniec.",
         tip="Najlepszy przypadek z flagą to jedno przejście: O(n)."),

    dict(id=9, world="glebina", name="Bez zapasu", mode="puzzle", n=8, layout="random", slack=0,
         goal="Głębina nie wybacza: liczba ruchów równa liczbie inwersji. Zero pomyłek.",
         tip="Sortowanie bąbelkowe robi dokładnie tyle zamian, ile jest inwersji. Mniej się nie da."),
    dict(id=10, world="glebina", name="Świecące meduzy", mode="decide", n=8, layout="random", timer=4, early=True,
         goal="8 bąbelków, 4 sekundy na decyzję.",
         tip="Patrz tylko na dwa podświetlone bąbelki. Reszta nie ma znaczenia."),
    dict(id=11, world="glebina", name="Rów oceaniczny", mode="decide", n=9, layout="nearly", timer=3.5, early=True,
         goal="9 bąbelków, 3,5 sekundy. Prawie posortowane, więc koniec może przyjść szybko.",
         tip="Licz zamiany w przejściu. Zero zamian oznacza Koniec."),
    dict(id=12, world="glebina", name="Wielki Bąbel", mode="decide", n=10, layout="random", timer=3, early=True,
         goal="Ostatni poziom Głębiny: 10 bąbelków i 3 sekundy na decyzję. Pokaż, co umiesz!",
         tip="Porównań może być nawet 45. Zachowaj spokój i pilnuj serii."),

    dict(id=13, world="lod", name="Zamarznięte bąbelki", mode="decide", n=7, layout="random", timer=5, early=True,
         hidden=True,
         goal="Nowość: liczby zamarzły. Widzisz tylko dwa porównywane bąbelki i te, które już wypłynęły.",
         tip="Algorytm i tak patrzy tylko na parę sąsiadów. Reszta tablicy nie jest potrzebna do decyzji."),
    dict(id=14, world="lod", name="Pękająca kra", mode="puzzle", n=8, layout="random", slack=2,
         goal="Układanka na lodzie: 8 bąbelków i tylko 2 zapasowe ruchy.",
         tip="Szukaj par, w których większy stoi po lewej. Każda taka zamiana usuwa jedną inwersję."),
    dict(id=15, world="lod", name="Zorza polarna", mode="decide", n=8, layout="nearly", timer=4, early=True,
         hidden=True,
         goal="Prawie posortowane, zamrożone liczby i 4 sekundy. Uważaj na pytanie o koniec.",
         tip="Licz w myślach zamiany w przejściu. Zero zamian oznacza Koniec."),
    dict(id=16, world="lod", name="Lodowiec", mode="decide", n=8, layout="reversed", timer=4, early=False,
         hidden=True,
         goal="Odwrócona tablica pod lodem: najwięcej zamian w całej grze.",
         tip="Gdy tablica jest odwrócona, zawsze lewy jest większy. To najgorszy przypadek: n(n−1)/2 zamian."),

    dict(id=17, world="wulkan", name="Gorące źródła", mode="decide", n=8, layout="random", timer=3.5, early=True,
         goal="Wulkan przyspiesza: 3,5 sekundy na każdą decyzję.",
         tip="Najpierw spójrz na lewy bąbelek, potem na prawy. Lewy większy oznacza Zamień."),
    dict(id=18, world="wulkan", name="Rzeka magmy", mode="puzzle", n=9, layout="random", slack=1,
         goal="9 bąbelków i tylko 1 zapasowy ruch.",
         tip="Najpierw przepchnij największy bąbelek na koniec, tak jak robi to algorytm."),
    dict(id=19, world="wulkan", name="Erupcja", mode="decide", n=9, layout="random", timer=3, early=True,
         goal="9 bąbelków i 3 sekundy na decyzję.",
         tip="Seria dobrych odpowiedzi daje coraz więcej punktów. Nie spiesz się bardziej, niż trzeba."),
    dict(id=20, world="wulkan", name="Krater", mode="decide", n=10, layout="nearly", timer=2.5, early=True,
         goal="10 bąbelków, prawie posortowane, 2,5 sekundy. Najszybszy poziom w grze.",
         tip="W prawie posortowanej tablicy większość odpowiedzi to Zostaw."),

    dict(id=21, world="wrak", name="Bliźniacze bąbelki", mode="decide", n=7, layout="random", timer=5, early=True,
         dupes=True,
         goal="Nowość: niektóre liczby się powtarzają. Co zrobić, gdy porównujesz dwie równe?",
         tip="Równych nie zamieniamy! Dzięki temu równe elementy zachowują kolejność, czyli sortowanie jest stabilne."),
    dict(id=22, world="wrak", name="Skrzynia skarbów", mode="puzzle", n=8, layout="random", slack=1, dupes=True,
         goal="Układanka z powtórzonymi liczbami. Zamiana dwóch równych to zmarnowany ruch.",
         tip="Para równych liczb nie jest inwersją. Zamieniaj tylko, gdy lewy jest ściśle większy."),
    dict(id=23, world="wrak", name="Kotwica", mode="decide", n=9, layout="random", timer=3.5, early=True,
         dupes=True, hidden=True,
         goal="Powtórzone liczby pod mułem: widać tylko porównywaną parę.",
         tip="Ściśle większy po lewej: Zamień. Mniejszy albo równy: Zostaw."),
    dict(id=24, world="wrak", name="Kapitan Bąbel", mode="decide", n=10, layout="random", timer=3, early=True,
         dupes=True,
         goal="Finał: 10 bąbelków, powtórzone liczby i 3 sekundy na decyzję. Pokaż, co umiesz!",
         tip="Wszystko naraz: porównanie sąsiadów, równe liczby i pytanie o koniec."),
]

# podgląd ostatniego świata pokazywany na mapie jako „Wkrótce”
COMING_SOON = dict(
    world="palac", name="Perłowy Pałac",
    text="Ostatnia mapa: 4 mistrzowskie poziomy w pałacu z pereł. Pojawi się w następnej wersji gry.")


def inversions(a):
    return sum(1 for i in range(len(a)) for j in range(i + 1, len(a)) if a[i] > a[j])


def make_values(n, layout, rnd=random, dupes=False):
    if dupes:
        # co najmniej dwie pary równych liczb, a tablica wciąż wyraźnie nieposortowana
        while True:
            pool = [rnd.randint(3, 3 + n) for _ in range(n)]
            repeats = n - len(set(pool))
            if 2 <= repeats <= n // 2 and inversions(pool) >= n:
                return pool
    while True:
        pool = rnd.sample(range(2, 21), n)
        if layout == "random":
            if inversions(pool) >= n // 2:
                return pool
            continue
        pool.sort()
        if layout == "reversed":
            return pool[::-1]
        k = max(1, n // 4)
        for _ in range(k):
            i = rnd.randrange(n - 1)
            pool[i], pool[i + 1] = pool[i + 1], pool[i]
        if inversions(pool) > 0:
            return pool
