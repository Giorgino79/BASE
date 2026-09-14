"""
Hook opzionali che magazzino espone ad altre app senza che quelle app
debbano importare magazzino direttamente (l'inverso e' gia' vero: magazzino
dipende da automezzi via FK dirette, vedi MODULE_DEPENDENCIES).

Usato da automezzi/views.py::AutomezzoDetailView per mostrare, se il
modulo magazzino e' installato e attivo, le card "Prodotti a bordo" e
"Attrezzature" nel dettaglio di un automezzo — senza che l'app automezzi
(che deve restare standard/generica) sappia nulla di magazzino.
"""


def automezzo_detail_extra(automezzo, request):
    """Ritorna il context extra per il template di dettaglio automezzo:
    scorte a bordo, fabbisogno dalle distinte aperte, attrezzature montate."""
    from .models import ScortaMezzo, TipoAttrezzatura

    ctx = {}

    ctx["attrezzature"] = automezzo.attrezzature.select_related("tipo").all()
    ctx["tipi_attrezzatura"] = TipoAttrezzatura.objects.all()

    scorte = list(
        ScortaMezzo.objects.filter(mezzo=automezzo)
        .select_related("prodotto")
        .order_by("prodotto__nome_prodotto")
    )
    ctx["scorte"] = scorte

    # Fabbisogno dalle distinte aperte: ConsumoMateriale confermato=False.
    # servizi e' un modulo diverso da magazzino: stesso pattern try/except
    # gia' in uso nel progetto per le soft-dependency (vedi module_manager.py).
    try:
        from django.db.models import Sum
        from servizi.models import Distinta, ConsumoMateriale
        distinte_aperte = Distinta.objects.filter(mezzo=automezzo, stato=Distinta.Stato.APERTA)
        fabbisogno_qs = (
            ConsumoMateriale.objects
            .filter(riga__ods__distinta__in=distinte_aperte, confermato=False)
            .values("prodotto__pk", "prodotto__nome_prodotto", "prodotto__unita_misura")
            .annotate(totale=Sum("quantita"))
            .order_by("prodotto__nome_prodotto")
        )
        scorte_map = {s.prodotto_id: s.quantita for s in scorte}
        fabbisogno = []
        for row in fabbisogno_qs:
            pid = row["prodotto__pk"]
            disponibile = scorte_map.get(pid)
            fabbisogno.append({
                "nome": row["prodotto__nome_prodotto"],
                "um": row["prodotto__unita_misura"] or "",
                "necessario": row["totale"],
                "disponibile": disponibile,
                "mancante": disponibile is None or disponibile < row["totale"],
            })
        ctx["fabbisogno"] = fabbisogno
    except Exception:
        ctx["fabbisogno"] = []

    return ctx
