"""
Eksperyment: czas obliczenia pierwiastków liczb 1..1 000 000
funkcją biblioteczną math.sqrt() oraz własną metodą babilońską.
Każdy pomiar powtarzany jest 5 razy.

Uruchomienie:  python3 benchmark.py
Wyniki zapisywane są do ../wyniki/wyniki_python.csv i .json
"""
import csv
import json
import math
import os
import platform
import sys
import time

from babilonska import sqrt_babylonian

N = 1_000_000
PROBY = 5


def seria_sqrt():
    f = math.sqrt
    suma = 0.0
    for n in range(1, N + 1):
        suma += f(n)
    return suma


def seria_babilonska():
    f = sqrt_babylonian
    suma = 0.0
    for n in range(1, N + 1):
        suma += f(n)
    return suma


def zmierz(funkcja):
    start = time.perf_counter()
    suma = funkcja()
    return time.perf_counter() - start, suma


def kontrola_dokladnosci():
    """Porównuje wyniki obu metod dla całego zakresu."""
    max_abs = max_rel = 0.0
    identyczne = 0
    iteracje = []
    for n in range(1, N + 1):
        a = math.sqrt(n)
        b = sqrt_babylonian(n)
        d = abs(a - b)
        max_abs = max(max_abs, d)
        max_rel = max(max_rel, d / a)
        identyczne += (a == b)
    # liczba iteracji dla wybranych liczb
    for s in (1, 2, 10, 100, 1000, 10_000, 100_000, 1_000_000):
        x, k = float(s), 0
        while True:
            x_next = 0.5 * (x + s / x)
            k += 1
            if abs(x - x_next) <= 1e-15 * x_next:
                break
            x = x_next
        iteracje.append({"n": s, "iteracje": k})
    return {"max_blad_bezwzgledny": max_abs, "max_blad_wzgledny": max_rel,
            "identyczne_wyniki": identyczne, "iteracje": iteracje}


def main():
    wyniki = []
    print(f"Python {platform.python_version()} | {platform.processor() or platform.machine()}")
    print(f"{'Próba':<8}{'sqrt() [s]':>14}{'babilońska [s]':>18}")
    for p in range(1, PROBY + 1):
        t_sqrt, s1 = zmierz(seria_sqrt)
        t_bab, s2 = zmierz(seria_babilonska)
        wyniki.append({"proba": p, "sqrt": t_sqrt, "babilonska": t_bab})
        print(f"{p:<8}{t_sqrt:>14.4f}{t_bab:>18.4f}")
    sr_sqrt = sum(w["sqrt"] for w in wyniki) / PROBY
    sr_bab = sum(w["babilonska"] for w in wyniki) / PROBY
    print(f"{'Średnia':<8}{sr_sqrt:>14.4f}{sr_bab:>18.4f}")
    print(f"Metoda babilońska jest {sr_bab / sr_sqrt:.1f}x wolniejsza")
    print(f"Kontrola: suma sqrt = {s1:.6f}, suma bab. = {s2:.6f}")

    dokl = kontrola_dokladnosci()
    print(f"Maks. błąd bezwzględny: {dokl['max_blad_bezwzgledny']:.3e}")
    print(f"Maks. błąd względny:    {dokl['max_blad_wzgledny']:.3e}")
    print(f"Wyniki identyczne bit w bit: {dokl['identyczne_wyniki']} / {N}")

    katalog = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "wyniki")
    os.makedirs(katalog, exist_ok=True)
    with open(os.path.join(katalog, "wyniki_python.csv"), "w", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Próba", "sqrt() [s]", "Metoda babilońska [s]"])
        for r in wyniki:
            w.writerow([r["proba"], f"{r['sqrt']:.4f}", f"{r['babilonska']:.4f}"])
        w.writerow(["Średnia", f"{sr_sqrt:.4f}", f"{sr_bab:.4f}"])
    with open(os.path.join(katalog, "wyniki_python.json"), "w") as f:
        json.dump({"jezyk": f"Python {platform.python_version()}",
                   "system": f"{platform.system()} {platform.machine()}",
                   "proby": wyniki, "srednia": {"sqrt": sr_sqrt, "babilonska": sr_bab},
                   "dokladnosc": dokl}, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
