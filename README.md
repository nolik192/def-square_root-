# Jak komputer oblicza pierwiastek kwadratowy?
### Od metody babilońskiej do współczesnych algorytmów

Projekt indywidualny: strona internetowa (HTML + CSS), programy w Pythonie, arkusz Excel
oraz eksperyment porównujący czas obliczania pierwiastka funkcją `math.sqrt()` i metodą babilońską (Herona).

**Start:** otwórz plik `index.html` w przeglądarce.

## Struktura

| Ścieżka | Zawartość |
|---|---|
| `index.html` | strona główna |
| `historia.html` | historia (YBC 7289, Heron, Newton, IEEE 754) |
| `matematyka.html` | podstawy matematyczne, liczby double |
| `metoda-babilonska.html` | teoria metody babilońskiej, dowód zbieżności |
| `inne-metody.html` | bisekcja, metoda pisemna, 1/√x, Quake III, sprzęt |
| `implementacja.html` | pseudokod, Python, C++, Excel |
| `eksperyment.html` / `wyniki.html` / `wnioski.html` | część badawcza |
| `zrodla.html` | źródła |
| `css/style.css` | arkusz stylów (responsywny, tryb ciemny) |
| `program/babilonska.py` | implementacja metody babilońskiej + przykład działania |
| `program/benchmark.py` | eksperyment: 5 × milion obliczeń, zapis wyników |
| `program/wykresy.py` | wykresy (matplotlib) → `img/` |
| `program/excel_generator.py` | tworzy `excel/metoda_babilonska.xlsx` (openpyxl) |
| `wyniki/` | wyniki pomiarów (CSV, JSON, TXT) |

## Uruchomienie

```bash
cd program
python3 babilonska.py        # przykład działania metody
python3 benchmark.py         # eksperyment -> ../wyniki/
pip install matplotlib openpyxl
python3 wykresy.py           # wykresy -> ../img/
python3 excel_generator.py   # arkusz -> ../excel/
```

## Wyniki (Python 3.11, Linux x86_64)

| Próba | sqrt() | Metoda babilońska |
|---|---|---|
| 1 | 0,0347 s | 1,0112 s |
| 2 | 0,0337 s | 1,0353 s |
| 3 | 0,0342 s | 1,0255 s |
| 4 | 0,0369 s | 1,0123 s |
| 5 | 0,0348 s | 1,0582 s |
| **Średnia** | **0,0349 s** | **1,0285 s** |

Metoda babilońska (ε = 10⁻¹⁵) okazała się ok. 29,5 razy wolniejsza. Wyniki obu metod różnią się najwyżej o 1 ostatni bit (błąd względny ≤ 2,2·10⁻¹⁶).
