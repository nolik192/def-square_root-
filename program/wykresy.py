"""Rysuje wykresy do strony na podstawie ../wyniki/wyniki_python.json.

Uruchomienie:  python3 wykresy.py   (wymaga: pip install matplotlib)
"""
import collections
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TU = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(TU, "..", "img")
NIEBIESKI, POMARANCZOWY = "#2a78d6", "#eb6834"
TEKST, TEKST2, SIATKA = "#1f2328", "#59636e", "#d8dee4"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "text.color": TEKST,
    "axes.edgecolor": SIATKA, "axes.labelcolor": TEKST2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
    "grid.color": SIATKA, "grid.linewidth": 0.8, "xtick.color": TEKST2,
    "ytick.color": TEKST2, "svg.fonttype": "none", "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def zapisz(fig, nazwa):
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, nazwa + ".svg"))
    fig.savefig(os.path.join(IMG, nazwa + ".png"), dpi=160)
    plt.close(fig)


def iteracje(s, eps=1e-15):
    x, k = float(s), 0
    while True:
        y = 0.5 * (x + s / x)
        k += 1
        if abs(x - y) <= eps * y:
            return k
        x = y


def wykres_czasow(dane):
    etykiety = [f"Próba {p['proba']}" for p in dane["proby"]] + ["Średnia"]
    t1 = [p["sqrt"] for p in dane["proby"]] + [dane["srednia"]["sqrt"]]
    t2 = [p["babilonska"] for p in dane["proby"]] + [dane["srednia"]["babilonska"]]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    x = range(len(etykiety))
    w = 0.36
    b1 = ax.bar([i - w / 2 - 0.01 for i in x], t1, w, color=NIEBIESKI, label="math.sqrt()")
    b2 = ax.bar([i + w / 2 + 0.01 for i in x], t2, w, color=POMARANCZOWY, label="metoda babilońska")
    for bars in (b1, b2):
        for b in bars:
            ax.annotate(f"{b.get_height():.3f}", (b.get_x() + b.get_width() / 2, b.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9, color=TEKST2)
    ax.set_xticks(list(x), etykiety)
    ax.set_ylabel("czas serii 1 000 000 obliczeń [s]")
    ax.set_ylim(0, max(t2) * 1.15)
    ax.legend(frameon=False, loc="upper left", ncols=2)
    ax.tick_params(axis="x", length=0)
    zapisz(fig, "wykres_czasy")


def wykres_iteracji():
    licznik = collections.Counter(iteracje(n) for n in range(1, 1_000_001))
    k = sorted(licznik)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    bars = ax.bar(k, [licznik[i] for i in k], 0.8, color=NIEBIESKI)
    for b, i in zip(bars, k):
        if licznik[i] > 1000:
            ax.annotate(f"{licznik[i]:,}".replace(",", " "), (b.get_x() + b.get_width() / 2, b.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9, color=TEKST2)
    ax.set_xticks(k)
    ax.set_xlabel("liczba iteracji potrzebnych do osiągnięcia dokładności 1e-15")
    ax.set_ylabel("ile liczb z zakresu 1…1 000 000")
    ax.yaxis.set_major_formatter(lambda v, _: f"{int(v):,}".replace(",", " "))
    ax.tick_params(axis="x", length=0)
    zapisz(fig, "wykres_iteracje")
    srednia = sum(i * c for i, c in licznik.items()) / 1_000_000
    return {str(i): licznik[i] for i in k}, srednia


def wykres_zbieznosci():
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for s, kolor in ((2, NIEBIESKI), (12345, POMARANCZOWY)):
        x, bledy = float(s), []
        prawdziwy = math.sqrt(s)
        for _ in range(14):
            bledy.append(max(abs(x - prawdziwy) / prawdziwy, 1e-17))
            x = 0.5 * (x + s / x)
        n = list(range(len(bledy)))
        ax.plot(n, bledy, color=kolor, lw=2, marker="o", ms=5, label=f"S = {s}")
        ax.annotate(f"S = {s}", (n[3], bledy[3]), xytext=(8, 4), textcoords="offset points",
                    color=TEKST, fontsize=10)
    ax.axhline(1e-15, color=TEKST2, lw=1, ls="--")
    ax.annotate("wymagana dokładność 10⁻¹⁵", (13, 1e-15), xytext=(0, 5), textcoords="offset points",
                ha="right", fontsize=9, color=TEKST2)
    ax.set_yscale("log")
    ax.set_ylim(3e-18, 1e4)
    ax.set_xlabel("numer iteracji n")
    ax.set_ylabel("błąd względny |xₙ − √S| / √S")
    ax.legend(frameon=False, loc="upper right")
    zapisz(fig, "wykres_zbieznosc")


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    with open(os.path.join(TU, "..", "wyniki", "wyniki_python.json")) as f:
        dane = json.load(f)
    wykres_czasow(dane)
    wykres_zbieznosci()
    hist, sr = wykres_iteracji()
    print("Histogram iteracji:", hist)
    print(f"Średnia liczba iteracji: {sr:.3f}")
