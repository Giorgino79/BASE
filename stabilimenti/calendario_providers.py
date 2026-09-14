"""
Provider calendario per l'app stabilimenti (estratta da cespiti il 26/08/2026).

- get_scadenze_documenti_stabilimenti: documenti stabilimenti con data_scadenza
- get_scadenze_servizi_stabilimenti: costi/servizi con prossima scadenza servizio
"""

from datetime import date


def _colore_scadenza(delta_giorni):
    if delta_giorni < 0:
        return '#dc3545'   # rosso — scaduto
    elif delta_giorni <= 7:
        return '#fd7e14'   # arancio — urgente
    elif delta_giorni <= 30:
        return '#ffc107'   # giallo — in scadenza
    return '#6c757d'       # grigio — normale


def get_scadenze_documenti_stabilimenti(user, start_date, end_date):
    """Documenti stabilimento con data_scadenza."""
    from .models import DocStabilimento
    from django.urls import reverse

    today = date.today()
    qs = DocStabilimento.objects.filter(
        data_scadenza__isnull=False,
        attivo=True,
    ).select_related('stabilimento')

    if start_date:
        inizio = start_date.date() if hasattr(start_date, 'date') else start_date
        qs = qs.filter(data_scadenza__gte=inizio)
    if end_date:
        limite = end_date.date() if hasattr(end_date, 'date') else end_date
        qs = qs.filter(data_scadenza__lte=limite)

    eventi = []
    for doc in qs[:300]:
        delta = (doc.data_scadenza - today).days
        eventi.append({
            'id': f'stabilimenti-doc-{doc.pk}',
            'title': f'📄 {doc.stabilimento.nome} — {doc.nome_documento[:40]}',
            'start': doc.data_scadenza.isoformat(),
            'allDay': True,
            'color': _colore_scadenza(delta),
            'url': reverse('stabilimenti:stabilimento_detail', kwargs={'pk': doc.stabilimento.pk}),
            'extendedProps': {
                'tipo': 'documento_stabilimento',
                'stabilimento': doc.stabilimento.nome,
                'documento': doc.nome_documento,
                'tipo_documento': doc.get_tipo_documento_display(),
            },
        })
    return eventi


def get_scadenze_servizi_stabilimenti(user, start_date, end_date):
    """Costi/servizi stabilimento con prossima scadenza servizio."""
    from .models import CostiStabilimento
    from django.urls import reverse

    today = date.today()
    qs = CostiStabilimento.objects.filter(
        data_scadenza_servizio__isnull=False,
    ).select_related('stabilimento')

    if start_date:
        inizio = start_date.date() if hasattr(start_date, 'date') else start_date
        qs = qs.filter(data_scadenza_servizio__gte=inizio)
    if end_date:
        limite = end_date.date() if hasattr(end_date, 'date') else end_date
        qs = qs.filter(data_scadenza_servizio__lte=limite)

    eventi = []
    for costo in qs[:300]:
        delta = (costo.data_scadenza_servizio - today).days
        eventi.append({
            'id': f'stabilimenti-servizio-{costo.pk}',
            'title': f'🏭 {costo.stabilimento.nome} — {costo.titolo[:40]}',
            'start': costo.data_scadenza_servizio.isoformat(),
            'allDay': True,
            'color': _colore_scadenza(delta),
            'url': reverse('stabilimenti:costo_detail', kwargs={'pk': costo.pk}),
            'extendedProps': {
                'tipo': 'servizio_stabilimento',
                'stabilimento': costo.stabilimento.nome,
                'causale': costo.get_causale_display(),
                'stato': costo.get_stato_display(),
            },
        })
    return eventi
