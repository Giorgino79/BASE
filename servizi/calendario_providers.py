from django.urls import reverse
from django.db.models import F


def get_ods_eventi(user, start_date, end_date):
    """
    Restituisce gli ODS programmati/da espletare come eventi FullCalendar.
    Mostra tutti gli ODS non ancora completati/annullati nel periodo.
    """
    from .models import ODS
    from datetime import datetime

    qs = ODS.objects.select_related(
        "filiale__cliente", "privato", "tecnico"
    ).prefetch_related("righe__servizio").exclude(stato__in=["completato", "annullato"])

    if start_date:
        qs = qs.filter(data_servizio__gte=start_date.date())
    if end_date:
        qs = qs.filter(data_servizio__lte=end_date.date())

    COLORI = {
        "da_espletare": "#6c757d",
        "programmato":  "#fd7e14",
    }

    eventi = []
    for ods in qs.order_by("data_servizio", F("ora_inizio").asc(nulls_last=True))[:300]:
        cliente = ods.cliente_display
        tecnico = ods.tecnico.get_full_name() if ods.tecnico else ""
        servizio = ods.servizio_principale

        if ods.ora_inizio:
            title = f"{ods.ora_inizio.strftime('%H:%M')} — {servizio or 'N/D'} — {cliente}"
        else:
            title = f"--:-- — {servizio or 'N/D'} — {cliente}"
        if tecnico:
            title += f" [{tecnico}]"
        if ods.incasso_al_servizio:
            title += " 💰"

        start = ods.data_servizio.isoformat()
        if ods.ora_inizio:
            start = datetime.combine(ods.data_servizio, ods.ora_inizio).isoformat()
        end = None
        if ods.ora_fine:
            end = datetime.combine(ods.data_servizio, ods.ora_fine).isoformat()

        eventi.append({
            "id": f"ods-{ods.pk}",
            "title": title,
            "start": start,
            "end": end,
            "allDay": not ods.ora_inizio,
            "color": COLORI.get(ods.stato, "#6c757d"),
            "url": reverse("servizi:ods_detail", kwargs={"pk": ods.pk}),
            "extendedProps": {
                "tipo": "ods",
                "numero": ods.numero,
                "stato": ods.get_stato_display(),
                "cliente": cliente,
                "servizio": str(servizio) if servizio else "",
                "tecnico": tecnico,
                "incasso_al_servizio": ods.incasso_al_servizio,
            },
        })

    # Divisori pomeriggio: solo per giorni con eventi sia mattina (<13:00) che pomeriggio (≥13:00)
    am_dates, pm_dates = set(), set()
    for ev in eventi:
        if not ev.get("allDay") and "T" in ev["start"]:
            date = ev["start"][:10]
            (am_dates if int(ev["start"][11:13]) < 13 else pm_dates).add(date)

    for date in sorted(am_dates & pm_dates):
        eventi.append({
            "id": f"sep-pm-{date}",
            "title": "Pomeriggio",
            "start": f"{date}T13:00:00",
            "allDay": False,
            "color": "#f8f9fa",
            "textColor": "#6c757d",
            "classNames": ["sep-pomeriggio"],
            "extendedProps": {"tipo": "separatore"},
        })

    return eventi


def get_condomini_eventi(user, start_date, end_date):
    """
    Restituisce i CondominioODS da espletare come eventi FullCalendar.
    """
    from .models import CondominioODS

    qs = CondominioODS.objects.select_related(
        "tecnico", "assistente"
    ).exclude(stato__in=["completato", "annullato"])

    if end_date:
        qs = qs.filter(data__lte=end_date.date())

    eventi = []
    for c in qs.order_by("data", "ora")[:200]:
        tecnico = c.tecnico.get_full_name() if c.tecnico else "—"
        title = f"🏢 {c.titolo}"
        if c.tecnico:
            title += f" [{tecnico}]"

        start = c.data.isoformat()
        if c.ora:
            from datetime import datetime
            start = datetime.combine(c.data, c.ora).isoformat()

        eventi.append({
            "id": f"con-{c.pk}",
            "title": title,
            "start": start,
            "allDay": not c.ora,
            "color": "#0d6efd",
            "url": c.get_absolute_url(),
            "extendedProps": {
                "tipo": "condominio",
                "numero": c.numero,
                "stato": c.get_stato_display(),
                "cliente": c.titolo,
                "indirizzo": c.indirizzo,
                "tecnico": tecnico,
            },
        })

    return eventi
