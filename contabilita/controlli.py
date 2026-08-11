"""
Controlli di quadratura della prima nota.

I vincoli sul model rendono impossibile *registrare* una scrittura incoerente,
ma non dicono niente sui movimenti già a registro né sugli scostamenti che
nascono fra due dati che devono raccontare la stessa cosa (il saldo di un conto
e lo stato di una fattura). Questi controlli guardano i dati come stanno e
segnalano quello che non torna, senza toccarli.

Ogni anomalia è un dict con `titolo`, `dettaglio`, `gravita` ('alta'/'media'),
`url` e `url_label`: la dashboard li impagina senza sapere cosa siano.
"""

from decimal import Decimal

from django.db.models import Sum
from django.urls import reverse

from .models import ContoContabile, MovimentoPrimaNota, valida_dare_avere

#: Oltre questo numero l'elenco viene troncato: la dashboard segnala un
#: problema, non è il posto dove risolverlo riga per riga.
LIMITE = 20


def _conti_con_saldo():
    """
    Tutti i conti attivi con il saldo calcolato in SQL.
    Due aggregate separate: un unico annotate con due join moltiplicherebbe
    le righe e gonfierebbe entrambi i totali.
    """
    dare = dict(
        MovimentoPrimaNota.objects.values_list('conto_dare')
        .annotate(t=Sum('importo')).values_list('conto_dare', 't')
    )
    avere = dict(
        MovimentoPrimaNota.objects.values_list('conto_avere')
        .annotate(t=Sum('importo')).values_list('conto_avere', 't')
    )
    for conto in ContoContabile.objects.filter(attivo=True):
        saldo = (dare.get(conto.pk) or Decimal('0.00')) - (avere.get(conto.pk) or Decimal('0.00'))
        yield conto, saldo


def _saldi_anomali():
    """
    Saldi con il segno sbagliato per il tipo di conto.

    È la spia più diretta dei lati invertiti: un cliente che invece di doverci
    dei soldi risulta a credito, un conto in banca che va sotto zero. Non è
    sempre un errore — un acconto ricevuto mette davvero il cliente in avere —
    quindi è una segnalazione, non un blocco.
    """
    attese = {
        ContoContabile.Tipo.CLIENTE: (
            'dare', 'a credito',
            'Un cliente in avere di solito significa un incasso registrato al '
            'contrario, o un acconto ricevuto senza fattura.',
        ),
        ContoContabile.Tipo.FORNITORE: (
            'avere', 'a debito verso di noi',
            'Un fornitore in dare di solito significa un pagamento registrato '
            'al contrario, o un acconto versato senza fattura.',
        ),
        ContoContabile.Tipo.CASSA: (
            'dare', 'negativo',
            'Una cassa non può contenere meno di zero euro.',
        ),
        ContoContabile.Tipo.BANCA: (
            'dare', 'negativo',
            'Se non è uno scoperto reale, è un movimento registrato al contrario.',
        ),
    }

    for conto, saldo in _conti_con_saldo():
        regola = attese.get(conto.tipo)
        if regola is None or saldo == 0:
            continue
        segno_atteso, etichetta, spiegazione = regola
        sbagliato = saldo < 0 if segno_atteso == 'dare' else saldo > 0
        if not sbagliato:
            continue
        yield {
            'gravita':   'alta' if conto.tipo in (ContoContabile.Tipo.CASSA,
                                                  ContoContabile.Tipo.BANCA) else 'media',
            'titolo':    f'{conto.get_tipo_display()} "{conto.nome}" {etichetta}: € {abs(saldo)}',
            'dettaglio': spiegazione,
            'url':       reverse('contabilita:mastrino', kwargs={'pk': conto.pk}),
            'url_label': 'Apri il mastrino',
        }


def _fatture_disallineate():
    """
    Fatture il cui stato non corrisponde ai movimenti che le riguardano.

    Nasce dai movimenti registrati col form libero, che scrivono in prima nota
    senza passare da `registra_incasso`: la contabilità dice incassato, la
    fattura dice ancora da incassare. Il flusso guidato non può produrla, ma i
    movimenti già a registro sì.
    """
    from acquisti.models import FatturaPassiva
    from fatturazione_attiva.models import Fattura

    # Somma dei movimenti di incasso per fattura, storni esclusi: uno storno e
    # il suo originale si annullano e non devono contare come incassato.
    def _totali(campo, tipo):
        return dict(
            MovimentoPrimaNota.objects
            .filter(**{f'{campo}__isnull': False}, tipo=tipo,
                    storna__isnull=True, storno__isnull=True)
            .values_list(campo)
            .annotate(t=Sum('importo'))
            .values_list(campo, 't')
        )

    incassi = _totali('fattura_attiva', MovimentoPrimaNota.Tipo.INCASSO)
    if incassi:
        for f in Fattura.objects.filter(pk__in=incassi):
            registrato = incassi[f.pk] or Decimal('0.00')
            if registrato == (f.importo_incassato or Decimal('0.00')):
                continue
            yield {
                'gravita':   'alta',
                'titolo':    f'Fattura {f.numero}: in prima nota € {registrato}, sulla fattura € {f.importo_incassato}',
                'dettaglio': (
                    'I movimenti di incasso e lo stato della fattura non coincidono. '
                    'Storna i movimenti sbagliati e rifai l\'incasso dal flusso guidato.'
                ),
                'url':       reverse('fatturazione_attiva:fattura_detail', kwargs={'pk': f.pk}),
                'url_label': 'Apri la fattura',
            }

    pagamenti = _totali('fattura_passiva', MovimentoPrimaNota.Tipo.PAGAMENTO)
    if pagamenti:
        for f in FatturaPassiva.objects.filter(pk__in=pagamenti).select_related('fornitore'):
            registrato = pagamenti[f.pk] or Decimal('0.00')
            if registrato == (f.importo_pagato or Decimal('0.00')):
                continue
            yield {
                'gravita':   'alta',
                'titolo':    f'Fattura fornitore {f.numero_fattura}: in prima nota € {registrato}, sulla fattura € {f.importo_pagato}',
                'dettaglio': (
                    'I movimenti di pagamento e lo stato della fattura non coincidono. '
                    'Storna i movimenti sbagliati e rifai il pagamento dal flusso guidato.'
                ),
                'url':       reverse('acquisti:fattura_detail', kwargs={'pk': f.pk}),
                'url_label': 'Apri la fattura',
            }


def _movimenti_fuori_regola():
    """
    Movimenti a registro che oggi non sarebbero registrabili.

    Sono le scritture entrate prima che la matrice dare/avere diventasse un
    vincolo. Il model non le tocca — sono già salvate — quindi vanno trovate
    rileggendole con la regola di adesso.
    """
    qs = (MovimentoPrimaNota.objects
          .select_related('conto_dare', 'conto_avere')
          .filter(storna__isnull=True, storno__isnull=True)
          .order_by('-data'))

    for mov in qs.iterator(chunk_size=500):
        errore = valida_dare_avere(mov.tipo, mov.conto_dare, mov.conto_avere)
        if not errore:
            continue
        yield {
            'gravita':   'alta',
            'titolo':    f'Movimento del {mov.data:%d/%m/%Y} — {mov.causale}',
            'dettaglio': errore,
            'url':       mov.get_absolute_url(),
            'url_label': 'Apri e storna',
        }


def anomalie(limite=LIMITE):
    """
    Tutte le anomalie trovate, le più gravi per prime, troncate a `limite`.
    Restituisce (elenco, totale_trovate).
    """
    trovate = [
        *_movimenti_fuori_regola(),
        *_fatture_disallineate(),
        *_saldi_anomali(),
    ]
    trovate.sort(key=lambda a: 0 if a['gravita'] == 'alta' else 1)
    return trovate[:limite], len(trovate)
