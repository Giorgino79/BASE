def get_installazioni_eventi(user, start_date, end_date):
    """
    Restituisce le Installazioni come eventi FullCalendar (data_installazione).
    Mostra solo le installazioni non ancora completate nel periodo.
    """
    from .models import Installazione

    qs = Installazione.objects.select_related(
        "filiale__cliente", "privato", "servizio",
    ).exclude(stato=Installazione.Stato.COMPLETATA)

    if start_date:
        qs = qs.filter(data_installazione__gte=start_date.date())
    if end_date:
        qs = qs.filter(data_installazione__lte=end_date.date())

    eventi = []
    for inst in qs.order_by("data_installazione")[:200]:
        title = f"🔧 {inst.servizio.nome} — {inst.cliente_display}"

        eventi.append({
            "id": f"inst-{inst.pk}",
            "title": title,
            "start": inst.data_installazione.isoformat(),
            "allDay": True,
            "color": "#20c997",
            "url": inst.get_absolute_url(),
            "extendedProps": {
                "tipo": "installazione",
                "numero": inst.numero,
                "stato": inst.get_stato_display(),
                "cliente": inst.cliente_display,
                "servizio": inst.servizio.nome,
            },
        })

    return eventi
