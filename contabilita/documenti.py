"""
Ricerca e descrizione dei documenti a cui un movimento di prima nota può
riferirsi: fatture attive (emesse) e fatture passive (ricevute).

Vive in un modulo a parte perché serve sia all'endpoint di autocomplete
(views) sia all'etichetta del documento già scelto (forms).
"""

from django.db.models import Q

ATTIVA = 'attiva'
PASSIVA = 'passiva'


def descrivi_attiva(f):
    return f'FA {f.numero} — {f.dest_nome}'


def descrivi_passiva(f):
    return f'FP {f.numero_fattura} — {f.fornitore}'


def cerca(q, limite=10):
    """
    Cerca fra fatture attive e passive per numero o controparte.
    Restituisce dizionari pronti per il JSON dell'autocomplete.
    """
    from acquisti.models import FatturaPassiva
    from fatturazione_attiva.models import Fattura

    risultati = []

    attive = (Fattura.objects
              .filter(Q(numero__icontains=q) | Q(dest_nome__icontains=q))
              .order_by('-data_emissione', '-numero')[:limite])
    for f in attive:
        risultati.append({
            'kind':        ATTIVA,
            'id':          f.pk,
            'etichetta':   descrivi_attiva(f),
            'numero':      f.numero,
            'controparte': f.dest_nome,
            'data':        f.data_emissione.strftime('%d/%m/%Y'),
            'totale':      str(f.totale),
            'stato':       f.get_stato_display(),
        })

    passive = (FatturaPassiva.objects
               .select_related('fornitore')
               .filter(Q(numero_fattura__icontains=q)
                       | Q(fornitore__ragione_sociale__icontains=q))
               .order_by('-data_fattura', '-numero_fattura')[:limite])
    for f in passive:
        risultati.append({
            'kind':        PASSIVA,
            'id':          f.pk,
            'etichetta':   descrivi_passiva(f),
            'numero':      f.numero_fattura,
            'controparte': str(f.fornitore),
            'data':        f.data_fattura.strftime('%d/%m/%Y'),
            'totale':      str(f.totale),
            'stato':       f.get_stato_pagamento_display(),
        })

    # Le più recenti per prime, indipendentemente dal tipo.
    risultati.sort(key=lambda r: r['data'].split('/')[::-1], reverse=True)
    return risultati[:limite]
