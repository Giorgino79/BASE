"""
Provider calendario per l'app automezzi (estratta da cespiti il 26/08/2026).

- get_manutenzioni_programmate: manutenzioni aperte/in corso con data prevista
- get_revisioni_in_scadenza: automezzi con revisione in arrivo (data_revisione + 1 anno)
- get_assicurazioni_in_scadenza: polizze assicurative per veicoli attivi
"""

from datetime import date, timedelta


def _colore_scadenza(delta_giorni):
    if delta_giorni < 0:
        return '#dc3545'   # rosso — scaduto
    elif delta_giorni <= 7:
        return '#fd7e14'   # arancio — urgente
    elif delta_giorni <= 30:
        return '#ffc107'   # giallo — in scadenza
    return '#6c757d'       # grigio — normale


def get_manutenzioni_programmate(user, start_date, end_date):
    """Manutenzioni aperte o in corso con data_prevista."""
    from .models import Manutenzione
    from django.urls import reverse

    today = date.today()
    qs = Manutenzione.objects.filter(
        stato__in=['aperta', 'in_corso'],
        data_prevista__isnull=False,
    ).select_related('automezzo', 'fornitore')

    if start_date:
        inizio = start_date.date() if hasattr(start_date, 'date') else start_date
        qs = qs.filter(data_prevista__gte=inizio)
    if end_date:
        qs = qs.filter(data_prevista__lte=end_date.date() if hasattr(end_date, 'date') else end_date)

    eventi = []
    for m in qs[:300]:
        delta = (m.data_prevista - today).days
        if delta < 0:
            color = '#dc3545'
        elif delta <= 3:
            color = '#fd7e14'
        elif delta <= 7:
            color = '#ffc107'
        else:
            color = '#6f42c1'

        icona = '⚙️' if m.stato == 'in_corso' else '🔧'
        eventi.append({
            'id': f'automezzi-man-{m.pk}',
            'title': f'{icona} {m.automezzo.targa} — {m.descrizione[:45]}',
            'start': m.data_prevista.isoformat(),
            'allDay': True,
            'color': color,
            'url': reverse('automezzi:manutenzione_detail', kwargs={'pk': m.pk}),
            'extendedProps': {
                'tipo': 'manutenzione',
                'stato': m.get_stato_display(),
                'automezzo': str(m.automezzo),
                'descrizione': m.descrizione,
            },
        })
    return eventi


def get_revisioni_in_scadenza(user, start_date, end_date):
    """Revisioni obbligatorie stimate: data_revisione + 12 mesi."""
    from .models import Automezzo
    from django.urls import reverse

    today = date.today()
    CICLO = timedelta(days=365)

    qs = Automezzo.objects.filter(attivo=True, data_revisione__isnull=False)
    if end_date:
        limite = end_date.date() if hasattr(end_date, 'date') else end_date
        qs = qs.filter(data_revisione__gt=limite - CICLO)

    eventi = []
    for mezzo in qs:
        data_prossima = mezzo.data_revisione + CICLO
        if end_date:
            limite = end_date.date() if hasattr(end_date, 'date') else end_date
            if data_prossima > limite:
                continue

        delta = (data_prossima - today).days
        label = f"M{mezzo.numero_mezzo}" if mezzo.numero_mezzo else mezzo.targa
        eventi.append({
            'id': f'automezzi-revisione-{mezzo.pk}',
            'title': f'🔍 Revisione {label} ({mezzo.targa})',
            'start': data_prossima.isoformat(),
            'allDay': True,
            'color': _colore_scadenza(delta),
            'url': reverse('automezzi:automezzo_detail', kwargs={'pk': mezzo.pk}),
            'extendedProps': {
                'tipo': 'revisione',
                'automezzo': str(mezzo),
                'ultima_revisione': mezzo.data_revisione.strftime('%d/%m/%Y'),
            },
        })
    return eventi


def get_assicurazioni_in_scadenza(user, start_date, end_date):
    """Polizze assicurative in scadenza per veicoli attivi."""
    from .models import Automezzo
    from django.urls import reverse

    today = date.today()
    qs = Automezzo.objects.filter(attivo=True, data_scadenza_assicurazione__isnull=False)
    if start_date:
        inizio = start_date.date() if hasattr(start_date, 'date') else start_date
        qs = qs.filter(data_scadenza_assicurazione__gte=inizio)
    if end_date:
        limite = end_date.date() if hasattr(end_date, 'date') else end_date
        qs = qs.filter(data_scadenza_assicurazione__lte=limite)

    eventi = []
    for mezzo in qs:
        data_scad = mezzo.data_scadenza_assicurazione
        delta = (data_scad - today).days
        label = f"M{mezzo.numero_mezzo}" if mezzo.numero_mezzo else mezzo.targa
        eventi.append({
            'id': f'automezzi-assicurazione-{mezzo.pk}',
            'title': f'🛡️ Assicurazione {label} ({mezzo.targa})',
            'start': data_scad.isoformat(),
            'allDay': True,
            'color': _colore_scadenza(delta),
            'url': reverse('automezzi:automezzo_detail', kwargs={'pk': mezzo.pk}),
            'extendedProps': {
                'tipo': 'assicurazione',
                'automezzo': str(mezzo),
                'scadenza': data_scad.strftime('%d/%m/%Y'),
            },
        })
    return eventi
