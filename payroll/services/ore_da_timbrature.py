"""
Calcolo ore mensili per la busta paga partendo dalle GiornataLavorativa.

Regole applicate (D.Lgs. 66/2003 + CCNL Pulizia/Multiservizi):
  - Straordinario feriale : ore settimanali oltre il limite contrattuale (di norma 40h)
    calcolate per ISO-settimana, considerando solo i giorni dentro il mese richiesto.
  - Straordinario festivo  : tutte le ore lavorate in domenica o festivo nazionale.
  - Straordinario notturno : ore_notte presenti nella GiornataLavorativa (turno notte,
    registrate tramite timbratura con turno="notte" tra le 22:00 e le 06:00).
  - Ferie / Permessi       : sommati dalle RichiestaFerie/RichiestaPermesso approvate
    con data_inizio (o data) nel mese.
  - Malattia               : non ricavabile automaticamente dalle timbrature; va inserita
    manualmente nella form di elaborazione.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import Sum


# ---------------------------------------------------------------------------
# Festività italiane
# ---------------------------------------------------------------------------

_FESTIVI_FISSI = {
    (1, 1), (1, 6), (4, 25), (5, 1), (6, 2),
    (8, 15), (11, 1), (12, 8), (12, 25), (12, 26),
}


def _calcola_pasqua(anno: int) -> date:
    """Algoritmo di Butcher/Gauss per il calcolo della data di Pasqua."""
    a = anno % 19
    b, c = divmod(anno, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    mese = (h + ll - 7 * m + 114) // 31
    giorno = (h + ll - 7 * m + 114) % 31 + 1
    return date(anno, mese, giorno)


def get_festivi_italiani(anno: int) -> frozenset[tuple[int, int]]:
    """Restituisce l'insieme di (mese, giorno) dei festivi italiani per l'anno."""
    pasqua = _calcola_pasqua(anno)
    lunedi_angelo = pasqua + timedelta(days=1)
    extra = {(pasqua.month, pasqua.day), (lunedi_angelo.month, lunedi_angelo.day)}
    return frozenset(_FESTIVI_FISSI | extra)


def is_festivo(d: date, festivi: frozenset) -> bool:
    """True se domenica o festivo nazionale."""
    return d.weekday() == 6 or (d.month, d.day) in festivi


# ---------------------------------------------------------------------------
# Calcolo principale
# ---------------------------------------------------------------------------

def calcola_ore_mese_payroll(user, mese: int, anno: int) -> dict[str, Any]:
    """
    Calcola il riepilogo ore mensili pronto per PayrollCalculator.

    Restituisce:
        {
          "ore_ordinarie":            Decimal,
          "ore_straordinario": {
              "feriale":  Decimal,
              "festivo":  Decimal,
              "notturno": Decimal,
          },
          "assenze": {
              "ferie":    Decimal,   # ore
              "permessi": Decimal,   # ore
              "malattia": Decimal,   # sempre 0 (manuale)
          },
          "riepilogo": {
              "giorni_lavorati":      int,
              "giorni_festivi":       int,
              "giorni_con_notte":     int,
              "ore_totali_lavorate":  Decimal,
              "settimane":            list[dict],   # dettaglio per settimana
              "giornate_non_concluse": int,
              "avvisi":               list[str],
          }
        }
    """
    from users.models import GiornataLavorativa, RichiestaFerie, RichiestaPermesso

    avvisi: list[str] = []

    # ── Recupera giornate ────────────────────────────────────────────────────
    tutte = GiornataLavorativa.objects.filter(
        user=user, data__year=anno, data__month=mese
    ).order_by("data")

    concluse = tutte.filter(conclusa=True)
    non_concluse = tutte.filter(conclusa=False).count()
    if non_concluse:
        avvisi.append(
            f"{non_concluse} giornata/e ancora aperta/e esclusa/e dal calcolo."
        )
    if not concluse.exists():
        avvisi.append("Nessuna giornata lavorativa conclusa trovata per il mese.")

    # ── Contratto ────────────────────────────────────────────────────────────
    try:
        dati = user.dati_payroll
        ore_sett_contratto = dati.ore_settimanali  # es. Decimal("40")
    except Exception:
        ore_sett_contratto = Decimal("40")
    ore_giorno_contratto = (ore_sett_contratto / 5).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    festivi = get_festivi_italiani(anno)

    # ── Raggruppa per ISO-settimana ───────────────────────────────────────────
    settimane: dict[int, list] = {}
    for g in concluse:
        wk = g.data.isocalendar()[1]
        settimane.setdefault(wk, []).append(g)

    ore_ordinarie = Decimal("0")
    ore_straord_feriale = Decimal("0")
    ore_straord_festivo = Decimal("0")
    ore_straord_notturno = Decimal("0")
    giorni_lavorati = 0
    giorni_festivi = 0
    giorni_con_notte = 0
    ore_totali_lavorate = Decimal("0")
    dettaglio_settimane = []

    for wk, giorni in sorted(settimane.items()):
        feriali_sett = Decimal("0")   # ore diurne feriali della settimana
        festivi_sett = Decimal("0")   # ore festive della settimana
        notturno_sett = Decimal("0")  # ore notte della settimana

        righe = []
        for g in giorni:
            ore_notte = Decimal(str(g.ore_notte))
            # Ore diurne = totale meno la parte notturna (già separata da calcola_ore)
            ore_diurne = (Decimal(str(g.ore_totali)) - ore_notte).max(Decimal("0"))
            fest = is_festivo(g.data, festivi)

            if fest:
                festivi_sett += ore_diurne
                giorni_festivi += 1
            else:
                feriali_sett += ore_diurne

            notturno_sett += ore_notte
            if ore_notte > 0:
                giorni_con_notte += 1

            giorni_lavorati += 1
            ore_totali_lavorate += Decimal(str(g.ore_totali))
            righe.append({
                "data": g.data,
                "festivo": fest,
                "ore_diurne": ore_diurne,
                "ore_notte": ore_notte,
                "ore_totali": Decimal(str(g.ore_totali)),
            })

        # Straordinario feriale = feriali eccedenti il limite settimanale contrattuale
        straord_fer_sett = (feriali_sett - ore_sett_contratto).max(Decimal("0"))
        ordinarie_sett = feriali_sett - straord_fer_sett

        ore_ordinarie += ordinarie_sett
        ore_straord_feriale += straord_fer_sett
        ore_straord_festivo += festivi_sett
        ore_straord_notturno += notturno_sett

        dettaglio_settimane.append({
            "settimana": wk,
            "giorni": righe,
            "feriali": feriali_sett,
            "straord_feriale": straord_fer_sett,
            "festivo": festivi_sett,
            "notturno": notturno_sett,
        })

    # ── Ferie approvate nel mese ──────────────────────────────────────────────
    ferie_qs = RichiestaFerie.objects.filter(
        user=user,
        stato="approvata",
        data_inizio__year=anno,
        data_inizio__month=mese,
    )
    ore_ferie = sum(
        (r.giorni_richiesti * ore_giorno_contratto) for r in ferie_qs
    ) or Decimal("0")

    # ── Permessi approvati nel mese ───────────────────────────────────────────
    permessi_qs = RichiestaPermesso.objects.filter(
        user=user,
        stato="approvata",
        data__year=anno,
        data__month=mese,
    )
    ore_permessi = permessi_qs.aggregate(
        tot=Sum("ore_richieste")
    )["tot"] or Decimal("0")

    # ── Avvisi utili ─────────────────────────────────────────────────────────
    if ore_straord_festivo:
        avvisi.append(
            f"{giorni_festivi} giornata/e festiva/e → {ore_straord_festivo:.2f}h retribuite al 50%."
        )
    if ore_straord_notturno:
        avvisi.append(
            f"{giorni_con_notte} turno/i notturno/i → {ore_straord_notturno:.2f}h retribuite al 50%."
        )
    avvisi.append(
        "Malattia non ricavabile automaticamente: inseriscila manualmente se necessario."
    )

    def q(v):
        return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "ore_ordinarie": q(ore_ordinarie),
        "ore_straordinario": {
            "feriale": q(ore_straord_feriale),
            "festivo": q(ore_straord_festivo),
            "notturno": q(ore_straord_notturno),
        },
        "assenze": {
            "ferie": q(ore_ferie),
            "permessi": q(ore_permessi),
            "malattia": Decimal("0"),
        },
        "riepilogo": {
            "giorni_lavorati": giorni_lavorati,
            "giorni_festivi": giorni_festivi,
            "giorni_con_notte": giorni_con_notte,
            "ore_totali_lavorate": q(ore_totali_lavorate),
            "settimane": dettaglio_settimane,
            "giornate_non_concluse": non_concluse,
            "avvisi": avvisi,
        },
    }
