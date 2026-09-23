"""
Metoda babilońska (metoda Herona) obliczania pierwiastka kwadratowego.

Uruchomienie:  python3 babilonska.py
"""
import math

EPS = 1e-15  # dokładność: 15 miejsc po przecinku (błąd względny)


def sqrt_babylonian(s, eps=EPS):
    """Zwraca przybliżenie pierwiastka z s (s >= 0) metodą babilońską."""
    if s < 0:
        raise ValueError("Pierwiastek z liczby ujemnej nie istnieje w R")
    if s == 0:
        return 0.0
    x = float(s)                       # przybliżenie początkowe x0 = S
    while True:
        x_next = 0.5 * (x + s / x)     # średnia arytmetyczna x i S/x
        if abs(x - x_next) <= eps * x_next:
            return x_next
        x = x_next


def sqrt_babylonian_verbose(s, eps=EPS):
    """To samo co wyżej, ale wypisuje kolejne przybliżenia."""
    x = float(s)
    k = 0
    print(f"x{k:<2} = {x:.15f}")
    while True:
        x_next = 0.5 * (x + s / x)
        k += 1
        print(f"x{k:<2} = {x_next:.15f}")
        if abs(x - x_next) <= eps * x_next:
            return x_next, k
        x = x_next


if __name__ == "__main__":
    for s in (2, 10, 12345, 1000000):
        print(f"--- S = {s} ---")
        wynik, iteracje = sqrt_babylonian_verbose(s)
        print(f"metoda babilońska: {wynik:.15f}  ({iteracje} iteracji)")
        print(f"math.sqrt():       {math.sqrt(s):.15f}")
        print(f"różnica:           {abs(wynik - math.sqrt(s)):.3e}\n")
