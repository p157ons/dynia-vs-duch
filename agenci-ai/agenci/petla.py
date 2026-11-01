"""Pętla agenta: wywołuje Claude, wykonuje narzędzia, powtarza aż agent skończy."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

import anthropic

MODEL = "claude-opus-5-5"
MAKS_KROKOW = 30

# Każde narzędzie zwraca (treść, czy_błąd).
Obsluga = Callable[[dict], tuple[str, bool]]


@dataclass
class Agent:
    nazwa: str
    system: str
    narzedzia: list[dict]
    obsluga: dict[str, Obsluga]
    wysilek: str = "high"  # low | medium | high | xhigh | max
    dziennik: Callable[[str], None] = print
    specjalisci: dict[str, "Agent"] = field(default_factory=dict)
    _klient: anthropic.Anthropic | None = field(default=None, repr=False)

    @property
    def klient(self) -> anthropic.Anthropic:
        if self._klient is None:
            self._klient = anthropic.Anthropic()  # klucz z ANTHROPIC_API_KEY
        return self._klient

    def uruchom(self, zadanie: str) -> str:
        wiadomosci: list = [{"role": "user", "content": zadanie}]
        self.dziennik(f"[{self.nazwa}] start: {zadanie[:200]}")

        for _ in range(MAKS_KROKOW):
            odp = self.klient.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=self.system,
                tools=self.narzedzia,
                messages=wiadomosci,
                output_config={"effort": self.wysilek},
                # Jeśli filtr bezpieczeństwa odrzuci zapytanie, API samo ponowi je na innym modelu.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            # Pełna treść (z blokami myślenia) musi wrócić do historii bez zmian.
            wiadomosci.append({"role": "assistant", "content": odp.content})

            if odp.stop_reason == "refusal":
                return f"[{self.nazwa}] Model odmówił wykonania zadania."
            if odp.stop_reason == "pause_turn":
                continue
            if odp.stop_reason != "tool_use":
                tekst = "\n".join(b.text for b in odp.content if b.type == "text").strip()
                if odp.stop_reason == "max_tokens":
                    tekst += "\n[odpowiedź ucięta — limit tokenów]"
                self.dziennik(f"[{self.nazwa}] koniec")
                return tekst

            wyniki = []
            for blok in odp.content:
                if blok.type != "tool_use":
                    continue
                tresc, blad = self._wykonaj(blok.name, blok.input)
                wyniki.append(
                    {"type": "tool_result", "tool_use_id": blok.id, "content": tresc, "is_error": blad}
                )
            wiadomosci.append({"role": "user", "content": wyniki})

        return f"[{self.nazwa}] Przerwano po {MAKS_KROKOW} krokach bez końcowej odpowiedzi."

    def _wykonaj(self, nazwa: str, wejscie) -> tuple[str, bool]:
        if isinstance(wejscie, str):
            try:
                wejscie = json.loads(wejscie)
            except json.JSONDecodeError:
                return "Błąd: niepoprawny JSON argumentów narzędzia.", True
        funkcja = self.obsluga.get(nazwa)
        if funkcja is None:
            return f"Błąd: nieznane narzędzie {nazwa}.", True
        podglad = json.dumps(wejscie, ensure_ascii=False)
        self.dziennik(f"[{self.nazwa}] → {nazwa}: {podglad[:300]}")
        try:
            return funkcja(wejscie)
        except Exception as e:  # błąd narzędzia wraca do modelu, nie przerywa pracy
            return f"Błąd narzędzia {nazwa}: {e}", True
