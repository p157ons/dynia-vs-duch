"""Zespół agentów: koordynator zleca pracę inspektorowi danych i analitykowi,
a na końcu sam pisze raport."""

from __future__ import annotations

from typing import Callable

from .narzedzia import PrzestrzenRobocza
from .petla import Agent


def _schemat(wlasciwosci: dict, wymagane: list[str]) -> dict:
    return {
        "type": "object",
        "properties": wlasciwosci,
        "required": wymagane,
        "additionalProperties": False,
    }


NARZEDZIE_LISTA_PLIKOW = {
    "name": "lista_plikow",
    "description": "Wyświetla pliki z danymi (CSV, Excel, JSON, Parquet) dostępne w folderze DANE.",
    "input_schema": _schemat({}, []),
    "strict": True,
}

NARZEDZIE_PYTHON = {
    "name": "wykonaj_python",
    "description": (
        "Wykonuje kod Python i zwraca to, co wydrukowano (print). Zmienne zostają między "
        "wywołaniami, jak w notatniku. Dostępne: pd (pandas), np, plt (matplotlib), "
        "DANE i WYNIKI (pathlib.Path do folderów), oraz słownik `dane` na wczytane DataFrame'y "
        "— wspólny dla wszystkich agentów. Wykresy zapisuj: plt.savefig(WYNIKI / 'nazwa.png', dpi=120, bbox_inches='tight')."
    ),
    "input_schema": _schemat({"kod": {"type": "string", "description": "Kod Python do wykonania."}}, ["kod"]),
    "strict": True,
}

SYSTEM_INSPEKTOR = """Jesteś inspektorem danych w zespole analitycznym. Twoje zadanie to wczytać pliki \
i opisać, co w nich jest, zanim ktokolwiek zacznie wyciągać wnioski.

- Wczytuj pliki do słownika `dane` pod krótkimi nazwami (np. dane['sprzedaz'] = pd.read_csv(...)), \
żeby analityk mógł z nich korzystać.
- Sprawdź: liczbę wierszy i kolumn, typy, braki, duplikaty, zakresy dat, podejrzane wartości \
(ujemne kwoty, literówki w kategoriach, daty jako tekst). Popraw oczywiste typy (daty, liczby z przecinkiem).
- Niczego nie usuwaj po cichu — jeśli czyścisz dane, napisz co i dlaczego.
- Na koniec zwróć zwięzły opis po polsku: jakie ramki są w `dane`, kolumny i ich znaczenie, \
problemy z jakością i co zrobiłeś."""

SYSTEM_ANALITYK = """Jesteś analitykiem danych. Dostajesz konkretne zadanie od koordynatora \
i odpowiadasz liczbami, które sam policzyłeś narzędziem `wykonaj_python`.

- Ramki danych są już w słowniku `dane` (sprawdź `dane.keys()`). Jeśli go brak, wczytaj pliki z DANE.
- Każda liczba w odpowiedzi musi pochodzić z wykonanego kodu — nie szacuj z głowy.
- Gdy wykres pomaga, zapisz go do WYNIKI jako PNG z polskim tytułem i opisanymi osiami, \
i podaj nazwę pliku.
- Zwróć wyniki po polsku: najważniejsze liczby, tabele (krótkie, w Markdown), nazwy wykresów \
oraz zastrzeżenia (mała próba, braki danych, korelacja ≠ przyczynowość)."""

SYSTEM_KOORDYNATOR = """Jesteś koordynatorem zespołu analizy danych. Użytkownik zadaje pytanie \
o swoje dane, a ty planujesz pracę i zlecasz ją specjalistom:

- `inspektor` — wczytuje pliki do wspólnego słownika `dane` i ocenia jakość danych. \
Zleć mu to najpierw, jeśli dane nie były jeszcze wczytane.
- `analityk` — liczy statystyki, porównania, trendy i robi wykresy. Dawaj mu konkretne, \
ograniczone zadania; kilka mniejszych zleceń jest lepsze niż jedno ogromne.

Sam nie liczysz — opierasz się na wynikach specjalistów. Gdy masz odpowiedź, wywołaj \
`zapisz_raport` z raportem w Markdown po polsku: krótkie podsumowanie na górze, potem \
wnioski z liczbami, wykresy wstawione jako ![opis](nazwa.png), zastrzeżenia i sugestie dalszych \
analiz. Po zapisaniu raportu odpowiedz jednym, dwoma zdaniami z głównym wnioskiem."""


def zbuduj_zespol(przestrzen: PrzestrzenRobocza, dziennik: Callable[[str], None] = print) -> Agent:
    def lista_plikow(_):
        return przestrzen.lista_plikow(), False

    def wykonaj_python(wej):
        return przestrzen.wykonaj_python(wej["kod"])

    narzedzia_specjalisty = [NARZEDZIE_LISTA_PLIKOW, NARZEDZIE_PYTHON]
    obsluga_specjalisty = {"lista_plikow": lista_plikow, "wykonaj_python": wykonaj_python}

    specjalisci = {
        "inspektor": Agent("inspektor", SYSTEM_INSPEKTOR, narzedzia_specjalisty, obsluga_specjalisty,
                           wysilek="medium", dziennik=dziennik),
        "analityk": Agent("analityk", SYSTEM_ANALITYK, narzedzia_specjalisty, obsluga_specjalisty,
                          wysilek="high", dziennik=dziennik),
    }

    def zlec(wej):
        agent = specjalisci[wej["agent"]]
        return agent.uruchom(wej["zadanie"]) or "(specjalista nie zwrócił tekstu)", False

    def zapisz_raport(wej):
        return przestrzen.zapisz_raport(wej["tresc_markdown"]), False

    narzedzia_koordynatora = [
        NARZEDZIE_LISTA_PLIKOW,
        {
            "name": "zlec_zadanie",
            "description": "Zleca zadanie specjaliście i zwraca jego odpowiedź. Specjalista nie widzi tej rozmowy — opisz zadanie samodzielnie i konkretnie.",
            "input_schema": _schemat(
                {
                    "agent": {"type": "string", "enum": sorted(specjalisci)},
                    "zadanie": {"type": "string", "description": "Pełny opis zadania."},
                },
                ["agent", "zadanie"],
            ),
            "strict": True,
        },
        {
            "name": "zapisz_raport",
            "description": "Zapisuje końcowy raport (Markdown) do folderu WYNIKI jako raport.md.",
            "input_schema": _schemat({"tresc_markdown": {"type": "string"}}, ["tresc_markdown"]),
            "strict": True,
        },
    ]
    obsluga_koordynatora = {
        "lista_plikow": lista_plikow,
        "zlec_zadanie": zlec,
        "zapisz_raport": zapisz_raport,
    }

    return Agent("koordynator", SYSTEM_KOORDYNATOR, narzedzia_koordynatora, obsluga_koordynatora,
                 wysilek="high", dziennik=dziennik, specjalisci=specjalisci)
