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


def fatture_da_incassare():
    """
    Fatture attive ancora aperte: emesse e non ancora coperte da incassi.
    Sono le sole selezionabili quando si registra un incasso.
    """
    from django.db.models import F

    from fatturazione_attiva.models import Fattura

    return (Fattura.objects
            .filter(stato=Fattura.Stato.EMESSA, importo_incassato__lt=F('totale'))
            .order_by('data_emissione', 'numero'))


def fatture_da_pagare():
    """
    Fatture passive ancora aperte: registrate e non ancora coperte da
    pagamenti. Sono le sole selezionabili quando si registra un pagamento.
    """
    from django.db.models import F

    from acquisti.models import FatturaPassiva

    return (FatturaPassiva.objects
            .select_related('fornitore')
            .filter(stato_pagamento=FatturaPassiva.StatoPagamento.DA_PAGARE,
                    importo_pagato__lt=F('totale'))
            .order_by('data_scadenza', 'data_fattura', 'numero_fattura'))


def dettaglio(mov):
    """
    Dati completi del documento collegato a un movimento, normalizzati fra
    fattura attiva e passiva per la pagina di dettaglio.
    Restituisce None se il movimento non ha (più) un documento collegato.
    """
    from django.urls import reverse

    if mov.fattura_attiva_id:
        from fatturazione_attiva.views import calcola_data_scadenza
        f = mov.fattura_attiva
        return {
            'kind':           ATTIVA,
            'kind_label':     'Fattura attiva',
            'kind_icona':     'bi-receipt',
            'controparte_label': 'Destinatario',
            'numero':         f.numero,
            'controparte':    f.dest_nome,
            'data_label':     'Data emissione',
            'data':           f.data_emissione,
            'data_scadenza':  calcola_data_scadenza(f.data_emissione, f.note_pagamento),
            'imponibile':     f.imponibile,
            'aliquota_iva':   f.aliquota_iva,
            'importo_iva':    f.importo_iva,
            'totale':         f.totale,
            'stato':          f.get_stato_display(),
            'condizioni':     f.note_pagamento,
            'partita_iva':    f.dest_partita_iva,
            'codice_fiscale': f.dest_codice_fiscale,
            'url_detail':     reverse('fatturazione_attiva:fattura_detail', kwargs={'pk': f.pk}),
            'url_pdf':        reverse('fatturazione_attiva:fattura_pdf', kwargs={'pk': f.pk}),
        }

    if mov.fattura_passiva_id:
        f = mov.fattura_passiva
        return {
            'kind':           PASSIVA,
            'kind_label':     'Fattura passiva',
            'kind_icona':     'bi-receipt-cutoff',
            'controparte_label': 'Fornitore',
            'numero':         f.numero_fattura,
            'controparte':    str(f.fornitore),
            'data_label':     'Data fattura',
            'data':           f.data_fattura,
            'data_scadenza':  f.data_scadenza,
            'imponibile':     f.imponibile,
            'aliquota_iva':   f.aliquota_iva,
            'importo_iva':    f.importo_iva,
            'totale':         f.totale,
            'stato':          f.get_stato_pagamento_display(),
            'condizioni':     '',
            'partita_iva':    getattr(f.fornitore, 'partita_iva', ''),
            'codice_fiscale': getattr(f.fornitore, 'codice_fiscale', ''),
            'data_pagamento': f.data_pagamento,
            'url_detail':     reverse('acquisti:fattura_detail', kwargs={'pk': f.pk}),
            'url_pdf':        f.file_fattura.url if f.file_fattura else '',
        }

    return None


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
