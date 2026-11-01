"""Uruchomienie:  python -m agenci "Twoje pytanie o dane" [--dane FOLDER] [--wyniki FOLDER]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import anthropic

from .narzedzia import PrzestrzenRobocza
from .zespol import zbuduj_zespol

KATALOG = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Zespół agentów AI do analizy danych.")
    parser.add_argument("pytanie", help="Co chcesz wiedzieć o swoich danych?")
    parser.add_argument("--dane", type=Path, default=KATALOG / "dane", help="Folder z plikami danych.")
    parser.add_argument("--wyniki", type=Path, default=KATALOG / "wyniki", help="Folder na raport i wykresy.")
    args = parser.parse_args()

    przestrzen = PrzestrzenRobocza(args.dane, args.wyniki)
    koordynator = zbuduj_zespol(przestrzen)

    try:
        odpowiedz = koordynator.uruchom(args.pytanie)
    except anthropic.AuthenticationError:
        print("Brak lub zły klucz API. Ustaw zmienną ANTHROPIC_API_KEY.", file=sys.stderr)
        return 1
    except anthropic.RateLimitError:
        print("Przekroczony limit zapytań API. Spróbuj za chwilę.", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError:
        print("Brak połączenia z API Anthropic.", file=sys.stderr)
        return 1
    except anthropic.APIStatusError as e:
        print(f"Błąd API ({e.status_code}): {e.message}", file=sys.stderr)
        return 1

    print("\n=== Odpowiedź ===\n" + odpowiedz)
    pliki = przestrzen.pliki_wynikowe()
    if pliki:
        print(f"\nPliki w {przestrzen.katalog_wynikow}: " + ", ".join(pliki))
    return 0


if __name__ == "__main__":
    sys.exit(main())
