"""Wspólna przestrzeń robocza agentów: pliki z danymi, wykonywanie kodu Python, wyniki.

Wszyscy agenci dzielą jeden obiekt `PrzestrzenRobocza`, więc ramka danych wczytana
przez inspektora jest od razu dostępna dla analityka.

UWAGA: kod Python pisany przez model jest wykonywany lokalnie, w tym procesie.
Uruchamiaj agentów tylko na własnych danych i we własnym środowisku.
"""

from __future__ import annotations

import contextlib
import io
import traceback
from pathlib import Path

MAKS_DLUGOSC_WYNIKU = 20_000  # znaków zwracanych modelowi z jednego wykonania kodu

ROZSZERZENIA_DANYCH = {".csv", ".tsv", ".xlsx", ".xls", ".json", ".parquet", ".txt"}


class PrzestrzenRobocza:
    def __init__(self, katalog_danych: Path, katalog_wynikow: Path):
        self.katalog_danych = katalog_danych.resolve()
        self.katalog_wynikow = katalog_wynikow.resolve()
        self.katalog_wynikow.mkdir(parents=True, exist_ok=True)

        import matplotlib

        matplotlib.use("Agg")  # wykresy do plików, bez okna
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd

        pd.set_option("display.width", 200)
        pd.set_option("display.max_columns", 50)

        # Zmienne trwające między wywołaniami `wykonaj_python` (jak w notatniku Jupyter).
        self.przestrzen_nazw: dict = {
            "pd": pd,
            "np": np,
            "plt": plt,
            "Path": Path,
            "DANE": self.katalog_danych,
            "WYNIKI": self.katalog_wynikow,
            "dane": {},  # słownik: nazwa -> DataFrame, wypełniany przez agentów
        }

    # --- narzędzia ---------------------------------------------------------

    def lista_plikow(self) -> str:
        if not self.katalog_danych.exists():
            return f"Folder danych {self.katalog_danych} nie istnieje."
        pliki = [
            p
            for p in sorted(self.katalog_danych.rglob("*"))
            if p.is_file() and p.suffix.lower() in ROZSZERZENIA_DANYCH
        ]
        if not pliki:
            return f"Brak plików z danymi w {self.katalog_danych}."
        wiersze = [
            f"- {p.relative_to(self.katalog_danych)} ({p.stat().st_size / 1024:.1f} KB)"
            for p in pliki
        ]
        return "Pliki w folderze DANE:\n" + "\n".join(wiersze)

    def wykonaj_python(self, kod: str) -> tuple[str, bool]:
        """Wykonuje kod i zwraca (wyjście, czy_błąd)."""
        bufor = io.StringIO()
        blad = False
        try:
            with contextlib.redirect_stdout(bufor), contextlib.redirect_stderr(bufor):
                exec(compile(kod, "<agent>", "exec"), self.przestrzen_nazw)
        except Exception:
            blad = True
            bufor.write("\n" + traceback.format_exc(limit=3))
        finally:
            self.przestrzen_nazw["plt"].close("all")

        wynik = bufor.getvalue().strip() or "(kod wykonany, brak wydruku — użyj print())"
        if len(wynik) > MAKS_DLUGOSC_WYNIKU:
            wynik = (
                wynik[:MAKS_DLUGOSC_WYNIKU]
                + f"\n... [ucięto {len(wynik) - MAKS_DLUGOSC_WYNIKU} znaków — drukuj mniej, np. .head()]"
            )
        return wynik, blad

    def zapisz_raport(self, tresc: str, nazwa_pliku: str = "raport.md") -> str:
        nazwa = Path(nazwa_pliku).name or "raport.md"
        sciezka = self.katalog_wynikow / nazwa
        sciezka.write_text(tresc, encoding="utf-8")
        return f"Zapisano raport: {sciezka}"

    def pliki_wynikowe(self) -> list[str]:
        return sorted(p.name for p in self.katalog_wynikow.iterdir() if p.is_file())
