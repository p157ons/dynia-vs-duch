"""Testy bez API: narzędzia i pętla agentów na udawanym kliencie.

Uruchom:  python -m pytest tests   (z folderu agenci-ai)
"""

from types import SimpleNamespace as NS

from agenci.narzedzia import PrzestrzenRobocza
from agenci.zespol import zbuduj_zespol


def _tekst(t):
    return NS(type="text", text=t)


def _narzedzie(id_, nazwa, wej):
    return NS(type="tool_use", id=id_, name=nazwa, input=wej)


class UdawanyKlient:
    """Zwraca kolejne zaplanowane odpowiedzi zamiast pytać API."""

    def __init__(self, odpowiedzi):
        self.odpowiedzi = list(odpowiedzi)
        self.zapytania = []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kw):
        self.zapytania.append({**kw, "messages": list(kw["messages"])})
        tresc, powod = self.odpowiedzi.pop(0)
        return NS(content=tresc, stop_reason=powod)


def test_wykonaj_python_pamieta_zmienne(tmp_path):
    p = PrzestrzenRobocza(tmp_path, tmp_path / "wyniki")
    p.wykonaj_python("x = 21")
    wynik, blad = p.wykonaj_python("print(x * 2)")
    assert (wynik, blad) == ("42", False)


def test_wykonaj_python_zwraca_blad(tmp_path):
    p = PrzestrzenRobocza(tmp_path, tmp_path / "wyniki")
    wynik, blad = p.wykonaj_python("1/0")
    assert blad and "ZeroDivisionError" in wynik


def test_zespol_konczy_raportem(tmp_path):
    (tmp_path / "s.csv").write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    p = PrzestrzenRobocza(tmp_path, tmp_path / "wyniki")
    koordynator = zbuduj_zespol(p, dziennik=lambda _: None)

    analityk = UdawanyKlient([
        ([_narzedzie("a1", "wykonaj_python",
                     {"kod": "dane['s'] = pd.read_csv(DANE / 's.csv'); print(dane['s']['a'].sum())"})], "tool_use"),
        ([_tekst("Suma kolumny a wynosi 4.")], "end_turn"),
    ])
    kord = UdawanyKlient([
        ([_narzedzie("k1", "zlec_zadanie", {"agent": "analityk", "zadanie": "Policz sumę a."})], "tool_use"),
        ([_narzedzie("k2", "zapisz_raport", {"tresc_markdown": "# Raport\nSuma a = 4"})], "tool_use"),
        ([_tekst("Suma a to 4.")], "end_turn"),
    ])
    koordynator._klient = kord
    koordynator.specjalisci["analityk"]._klient = analityk

    assert koordynator.uruchom("Jaka jest suma a?") == "Suma a to 4."
    assert (tmp_path / "wyniki" / "raport.md").read_text(encoding="utf-8").startswith("# Raport")

    # wynik kodu analityka wrócił do modelu jako tool_result
    wynik = analityk.zapytania[1]["messages"][-1]["content"][0]
    assert wynik["content"] == "4" and wynik["is_error"] is False
    # odpowiedź analityka wróciła do koordynatora
    assert "Suma kolumny a wynosi 4." in str(kord.zapytania[1]["messages"][-1])
