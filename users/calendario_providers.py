"""
Provider calendario per l'app users.

Fornisce eventi al CalendarioRegistry per:
- Ferie approvate (calendario aziendale, visibile con permesso approva_ferie)
- Permessi approvati (calendario aziendale, visibile con permesso approva_ferie)
"""

from datetime import timedelta


def get_ferie_approvate(user, start_date, end_date):
    """
    Ferie approvate di tutti gli utenti (vista aziendale).
    Richiede permesso users.approva_ferie.
    """
    from .models import RichiestaFerie
    from django.urls import reverse

    qs = RichiestaFerie.objects.filter(stato='approvata').select_related('user')

    if start_date:
        qs = qs.filter(data_fine__gte=start_date.date())
    if end_date:
        qs = qs.filter(data_inizio__lte=end_date.date())

    eventi = []
    for feria in qs[:200]:
        # FullCalendar: end è esclusivo, aggiungere 1 giorno per visualizzare correttamente
        data_fine_display = feria.data_fine + timedelta(days=1)
        nome = feria.user.get_full_name() or feria.user.username
        eventi.append({
            'id': f'ferie-az-{feria.pk}',
            'title': f'Ferie: {nome}',
            'start': feria.data_inizio.isoformat(),
            'end': data_fine_display.isoformat(),
            'allDay': True,
            'color': '#28a745',
            'url': reverse('users:richiesta_ferie_gestisci', kwargs={'pk': feria.pk}),
            'extendedProps': {
                'tipo': 'ferie',
                'dipendente': nome,
                'giorni': feria.giorni_richiesti,
            }
        })

    return eventi


def get_permessi_approvati(user, start_date, end_date):
    """
    Permessi orari approvati di tutti gli utenti (vista aziendale).
    Richiede permesso users.approva_ferie.
    """
    from .models import RichiestaPermesso
    from django.urls import reverse
    from datetime import datetime as dt

    qs = RichiestaPermesso.objects.filter(stato='approvata').select_related('user')

    if start_date:
        qs = qs.filter(data__gte=start_date.date())
    if end_date:
        qs = qs.filter(data__lte=end_date.date())

    eventi = []
    for permesso in qs[:200]:
        ora_inizio = dt.combine(permesso.data, permesso.ora_inizio)
        ora_fine = dt.combine(permesso.data, permesso.ora_fine)
        nome = permesso.user.get_full_name() or permesso.user.username
        eventi.append({
            'id': f'permesso-az-{permesso.pk}',
            'title': f'Permesso: {nome}',
            'start': ora_inizio.isoformat(),
            'end': ora_fine.isoformat(),
            'allDay': False,
            'color': '#17a2b8',
            'url': reverse('users:richiesta_permesso_gestisci', kwargs={'pk': permesso.pk}),
            'extendedProps': {
                'tipo': 'permesso',
                'dipendente': nome,
                'ore': str(permesso.ore_richieste),
            }
        })

    return eventi
