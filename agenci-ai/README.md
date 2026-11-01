# Agenci AI do analizy danych

Mały zespół agentów, który odpowiada na pytania o Twoje dane: wczytuje pliki,
sam liczy statystyki, robi wykresy i pisze raport po polsku.

```
                 Ty: „Jakie produkty sprzedają się najlepiej w październiku?”
                                      │
                               ┌──────▼──────┐
                               │ koordynator │  planuje, zleca, pisze raport
                               └──┬───────┬──┘
                    zlec_zadanie  │       │  zlec_zadanie
                    ┌─────────────▼┐     ┌▼─────────────┐
                    │  inspektor   │     │   analityk   │
                    │ wczytuje i   │     │ liczy, robi  │
                    │ sprawdza dane│     │ wykresy      │
                    └──────┬───────┘     └──────┬───────┘
                           └──── wspólne `dane` ┘   (pandas, kod Python)
                                      │
                         wyniki/raport.md + wykresy PNG
```

| Agent | Co robi | Narzędzia |
|---|---|---|
| **koordynator** | Rozbija pytanie na zadania, zleca je specjalistom, pisze raport | `lista_plikow`, `zlec_zadanie`, `zapisz_raport` |
| **inspektor** | Wczytuje pliki, sprawdza typy, braki, duplikaty, dziwne wartości | `lista_plikow`, `wykonaj_python` |
| **analityk** | Liczy statystyki, trendy, porównania; zapisuje wykresy | `lista_plikow`, `wykonaj_python` |

Wszyscy korzystają z modelu Claude Opus 5.5 (`claude-opus-5-5`).
Każda liczba w raporcie pochodzi z kodu, który agent naprawdę wykonał.

## Uruchomienie na swoim komputerze

```bash
cd agenci-ai
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...                  # Windows: set ANTHROPIC_API_KEY=...

# wrzuć swoje pliki (CSV, Excel, JSON, Parquet) do folderu dane/
python -m agenci "Przeanalizuj sprzedaż: trendy miesięczne, najlepsze produkty i regiony."
```

Raport i wykresy pojawią się w `wyniki/`. Inne foldery: `--dane ŚCIEŻKA --wyniki ŚCIEŻKA`.

W `dane/` jest przykładowy plik `przyklad_sprzedaz.csv` (fikcyjna sprzedaż, styczeń–październik 2026), żeby było od czego zacząć.

## Uruchomienie w chmurze (GitHub Actions)

1. Na GitHubie: **Settings → Secrets and variables → Actions → New repository secret**,
   nazwa `ANTHROPIC_API_KEY`, wartość: Twój klucz z https://console.anthropic.com.
2. **Actions → „Agenci AI – analiza danych” → Run workflow**, wpisz pytanie.
3. Po zakończeniu pobierz artefakt **wyniki-analizy** (raport + wykresy).

> ⚠️ **To repozytorium jest publiczne.** Wszystko, co do niego wypchniesz (także dane w `dane/`),
> zobaczy każdy, a logi i artefakty Actions w publicznym repo też są widoczne dla innych.
> Prawdziwe dane analizuj lokalnie (folder `dane/` jest w `.gitignore`) albo przenieś projekt
> do **prywatnego** repozytorium.

## Bezpieczeństwo

Agenci piszą i wykonują kod Python **na Twoim komputerze** (albo na maszynie GitHub Actions).
Uruchamiaj ich na własnych danych i w środowisku, któremu ufasz.

## Testy (bez klucza API)

```bash
python -m pytest -q tests
```

## Jak dodać nowego agenta

W `agenci/zespol.py` dopisz prompt systemowy i dodaj agenta do słownika `specjalisci`, np.
`"prognostyk"` od prognoz. Koordynator od razu zobaczy go na liście w narzędziu `zlec_zadanie`;
dopisz jedno zdanie o nim w `SYSTEM_KOORDYNATOR`, żeby wiedział, kiedy go używać.
