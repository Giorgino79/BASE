from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import (
    Case, DecimalField as DField, OuterRef, Q, Subquery, Sum, Value, When,
)
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView

from core.mixins import PrintDetailMixin, SidebarQrAllegatiMixin

from . import documenti
from . import controlli
from .forms import (
    ContoContabileForm, ImpostazioniContabilitaForm, MovimentoPrimaNotaForm,
    RegistrazioneIncassoForm, RegistrazionePagamentoForm,
)
from .models import (
    ContoContabile, ImpostazioniContabilita, MovimentoPrimaNota,
    data_minima_plausibile,
)
from .signals import _get_or_create_conto


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    # Crediti clienti: somma dare - somma avere sui conti tipo 'cliente'
    agg_cl = MovimentoPrimaNota.objects.filter(
        Q(conto_dare__tipo='cliente') | Q(conto_avere__tipo='cliente')
    ).aggregate(
        dare=Sum(Case(When(conto_dare__tipo='cliente', then='importo'),
                      default=0, output_field=DField())),
        avere=Sum(Case(When(conto_avere__tipo='cliente', then='importo'),
                       default=0, output_field=DField())),
    )
    crediti_clienti = (agg_cl['dare'] or Decimal('0')) - (agg_cl['avere'] or Decimal('0'))

    # Debiti fornitori: somma avere - somma dare sui conti tipo 'fornitore'
    agg_fo = MovimentoPrimaNota.objects.filter(
        Q(conto_dare__tipo='fornitore') | Q(conto_avere__tipo='fornitore')
    ).aggregate(
        dare=Sum(Case(When(conto_dare__tipo='fornitore', then='importo'),
                      default=0, output_field=DField())),
        avere=Sum(Case(When(conto_avere__tipo='fornitore', then='importo'),
                       default=0, output_field=DField())),
    )
    debiti_fornitori = (agg_fo['avere'] or Decimal('0')) - (agg_fo['dare'] or Decimal('0'))

    # Saldi casse e banche
    casse  = ContoContabile.objects.filter(tipo='cassa',  attivo=True)
    banche = ContoContabile.objects.filter(tipo='banca',  attivo=True)

    ultimi = (MovimentoPrimaNota.objects
              .select_related('conto_dare', 'conto_avere', 'creato_da')
              .order_by('-data', '-created_at')[:15])

    # Rete di sicurezza: i vincoli impediscono di registrare una scrittura
    # sbagliata, questi controlli fanno emergere quelle già a registro.
    anomalie, n_anomalie = controlli.anomalie()

    ctx = {
        'page_title':      'Contabilità — Prima Nota',
        'crediti_clienti': crediti_clienti,
        'debiti_fornitori': debiti_fornitori,
        'casse':           casse,
        'banche':          banche,
        'ultimi':          ultimi,
        'anomalie':        anomalie,
        'n_anomalie':      n_anomalie,
    }
    return render(request, 'contabilita/dashboard.html', ctx)


# ─────────────────────────────────────────────────────────────────────────────
# PRIMA NOTA — lista
# ─────────────────────────────────────────────────────────────────────────────

MOVIMENTI_PER_PAGINA = 50


@login_required
def prima_nota_list(request):
    """
    Ricerca sui movimenti: senza filtri non viene mostrato alcun dato, la
    tabella compare solo dopo una ricerca.
    """
    numero_f  = request.GET.get('numero', '').strip()
    tipo_f    = request.GET.get('tipo', '').strip()
    data_da   = request.GET.get('data_da', '').strip()
    data_a    = request.GET.get('data_a', '').strip()
    conto_f   = request.GET.get('conto', '').strip()

    ricerca_eseguita = bool(numero_f or tipo_f or data_da or data_a or conto_f)
    movimenti    = []
    page_obj     = None
    n_movimenti  = 0
    tot_importo  = Decimal('0.00')
    tot_pagina   = Decimal('0.00')

    if ricerca_eseguita:
        qs = (MovimentoPrimaNota.objects
              .select_related('conto_dare', 'conto_avere', 'creato_da',
                              'fattura_attiva', 'fattura_passiva')
              .order_by('-data', '-created_at'))

        if numero_f:
            # Si cerca sia "MOV-2026-0042" sia solo "42": il numero si cita a
            # voce senza il prefisso.
            qs = qs.filter(Q(numero__icontains=numero_f) | Q(causale__icontains=numero_f))
        if tipo_f:
            qs = qs.filter(tipo=tipo_f)
        if data_da:
            qs = qs.filter(data__gte=data_da)
        if data_a:
            qs = qs.filter(data__lte=data_a)
        if conto_f:
            qs = qs.filter(Q(conto_dare_id=conto_f) | Q(conto_avere_id=conto_f))

        # Il totale è su tutti i movimenti filtrati, non solo sulla pagina.
        tot_importo = qs.aggregate(tot=Sum('importo'))['tot'] or Decimal('0.00')

        paginator   = Paginator(qs, MOVIMENTI_PER_PAGINA)
        page_obj    = paginator.get_page(request.GET.get('page'))
        movimenti   = page_obj.object_list
        n_movimenti = paginator.count
        tot_pagina  = sum((m.importo for m in movimenti), Decimal('0.00'))

    ctx = {
        'page_title':       'Prima Nota',
        'movimenti':        movimenti,
        'page_obj':         page_obj,
        'n_movimenti':      n_movimenti,
        'tot_importo':      tot_importo,
        'tot_pagina':       tot_pagina,
        'ricerca_eseguita': ricerca_eseguita,
        'tipi':             MovimentoPrimaNota.Tipo.choices,
        'conti':            ContoContabile.objects.filter(attivo=True).order_by('tipo', 'nome'),
        'numero_f':         numero_f,
        'tipo_f':           tipo_f,
        'data_da':          data_da,
        'data_a':           data_a,
        'conto_f':          conto_f,
    }
    return render(request, 'contabilita/prima_nota_list.html', ctx)


# ─────────────────────────────────────────────────────────────────────────────
# MOVIMENTO — create / detail / delete
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def documenti_suggerimenti(request):
    """
    Autocomplete del campo "Documento di riferimento": cerca fra fatture
    attive e passive dalle prime 2 lettere.
    """
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    return JsonResponse({'results': documenti.cerca(q)})


@login_required
def movimento_create(request):
    form = MovimentoPrimaNotaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        mov = form.save(commit=False)
        mov.creato_da = request.user
        mov.save()
        messages.success(request, 'Movimento registrato in prima nota.')
        return redirect(reverse('contabilita:prima_nota_list'))

    # I tipi ammessi e le combinazioni dare/avere non stanno più qui: il form
    # espone la matrice del model (`regole_json`), unica fonte della regola.
    ctx = {
        'page_title': 'Nuovo Movimento',
        'form':       form,
        'documento':  form.documento_selezionato(),
    }
    return render(request, 'contabilita/movimento_form.html', ctx)


def _registra_quote(request, form, *, tipo, verso):
    """
    Corpo condiviso di incasso e pagamento: per ogni fattura della ripartizione
    nasce un movimento di prima nota e la fattura accumula la quota.

    Chi salda tre fatture con un bonifico solo genera tre movimenti, uno per
    documento, coerente con la regola "un movimento, un documento".

    Il verso della scrittura è deciso qui, non dall'utente: `verso` dice quale
    lato prende il conto monetario e quale la controparte. È il motivo per cui
    da questi due flussi un'inversione dare/avere non è esprimibile.
    """
    conto   = form.cleaned_data['conto']
    data    = form.cleaned_data['data']
    note    = form.cleaned_data['note']
    creati  = []
    saldate = []

    with transaction.atomic():
        for fattura, quota in form.ripartizione.items():
            numero      = verso['numero'](fattura)
            controparte = verso['controparte'](fattura)
            conto_contro = _get_or_create_conto(verso['tipo_conto'], controparte)
            parziale = quota < fattura.residuo

            dare, avere = ((conto, conto_contro) if verso['monetario_in_dare']
                           else (conto_contro, conto))

            MovimentoPrimaNota.objects.create(
                data=data,
                causale=(
                    f'{verso["etichetta"]} {"parziale " if parziale else ""}fattura '
                    f'{numero} — {controparte}'
                ),
                importo=quota,
                tipo=tipo,
                conto_dare=dare,
                conto_avere=avere,
                numero_documento=numero,
                note=note,
                creato_da=request.user,
                **{verso['campo_fattura']: fattura},
            )
            verso['registra'](fattura, quota, data)
            creati.append(numero)
            if fattura.is_saldata:
                saldate.append(numero)

    messaggio = (
        f'{verso["etichetta"]} registrato su {conto.nome}: '
        f'{len(creati)} moviment{"o" if len(creati) == 1 else "i"} in prima nota.'
    )
    if saldate:
        messaggio += f' Fatture saldate: {", ".join(saldate)}.'
    aperte = [n for n in creati if n not in saldate]
    if aperte:
        messaggio += f' Ancora aperte (parziale): {", ".join(aperte)}.'
    messages.success(request, messaggio)


#: Come si scrive un incasso: il denaro entra, quindi il conto monetario va in
#: Dare e il cliente in Avere.
VERSO_INCASSO = {
    'etichetta':         'Incasso',
    'monetario_in_dare': True,
    'tipo_conto':        ContoContabile.Tipo.CLIENTE,
    'campo_fattura':     'fattura_attiva',
    'numero':            lambda f: f.numero,
    'controparte':       lambda f: f.dest_nome,
    'registra':          lambda f, q, d: f.registra_incasso(q, d),
}

#: Come si scrive un pagamento: il denaro esce, quindi il fornitore va in Dare
#: e il conto monetario in Avere. Esattamente lo specchio dell'incasso.
VERSO_PAGAMENTO = {
    'etichetta':         'Pagamento',
    'monetario_in_dare': False,
    'tipo_conto':        ContoContabile.Tipo.FORNITORE,
    'campo_fattura':     'fattura_passiva',
    'numero':            lambda f: f.numero_fattura,
    'controparte':       lambda f: str(f.fornitore),
    'registra':          lambda f, q, d: f.registra_pagamento(q, d),
}


# ── Endpoint dei flussi guidati ──────────────────────────────────────────────
# La pagina non contiene più l'elenco delle fatture aperte: si sceglie la
# controparte e le sue fatture arrivano da qui. Con qualche migliaio di
# documenti aperti è la differenza fra una pagina che si apre e una che no.

@login_required
def incasso_clienti(request):
    """Clienti con fatture attive aperte, per il select2 del flusso incasso."""
    q = request.GET.get('q', '').strip()
    return JsonResponse({'results': documenti.clienti_da_incassare(q)})


@login_required
def incasso_fatture(request):
    """Fatture attive aperte di un cliente."""
    cliente = request.GET.get('controparte', '').strip()
    if not cliente:
        return JsonResponse({'results': []})
    qs = documenti.fatture_da_incassare().filter(dest_nome=cliente)
    return JsonResponse({'results': documenti.righe_fatture(qs, lambda f: f.numero)})


@login_required
def pagamento_fornitori(request):
    """Fornitori con fatture passive aperte, per il select2 del flusso pagamento."""
    q = request.GET.get('q', '').strip()
    return JsonResponse({'results': documenti.fornitori_da_pagare(q)})


@login_required
def pagamento_fatture(request):
    """Fatture passive aperte di un fornitore."""
    fornitore = request.GET.get('controparte', '').strip()
    if not fornitore.isdigit():
        return JsonResponse({'results': []})
    qs = documenti.fatture_da_pagare().filter(fornitore_id=fornitore)
    return JsonResponse({'results': documenti.righe_fatture(qs, lambda f: f.numero_fattura)})


@login_required
def nuova_registrazione(request):
    """
    Selettore dell'operazione da registrare.

    Non si arriva più al form libero per inerzia: si dichiara prima *cosa* si
    sta registrando, e per le operazioni frequenti si finisce in un flusso che
    la scrittura la compone da sé.
    """
    return render(request, 'contabilita/nuova_registrazione.html', {
        'page_title': 'Nuova registrazione',
        'n_da_incassare': documenti.fatture_da_incassare().count(),
        'n_da_pagare':    documenti.fatture_da_pagare().count(),
    })


def _flusso_incasso():
    """Etichette ed endpoint della pagina di incasso (template condiviso)."""
    return {
        'titolo':      'Registra incasso',
        'icona':       'bi-bank',
        'sottotitolo': ('Il movimento bancario che chiude una o più fatture. '
                        'Lo stato della fattura cambia solo da qui.'),
        'passo_controparte': 'Chi ha pagato',
        'passo_fatture':     'Quali fatture chiude',
        'aiuto_controparte': ('Compaiono solo i clienti con almeno una fattura '
                             'ancora da incassare.'),
        'aiuto_fatture':     'Scegli prima il cliente.',
        'placeholder_controparte': 'Cerca il cliente per nome…',
        'vuoto_controparte': 'Nessun cliente con fatture da incassare',
        'colonna_quota':  'Incasso',
        'parola_importo': 'ricevuti',
        'prefisso_quota': 'incasso',
        'url_controparte': reverse('contabilita:incasso_clienti'),
        'url_fatture':     reverse('contabilita:incasso_fatture'),
        'annulla_url':     reverse('fatturazione_attiva:da_incassare'),
        'spiegazione': [
            'Per ogni fattura selezionata nasce <strong>un movimento</strong> in prima nota: '
            'Dare il conto banca/cassa, Avere il conto del cliente.',
            'La fattura accumula l\'incasso e passa a <strong>pagata</strong> '
            'solo quando è coperta per intero.',
            'Se incassi meno del residuo la fattura resta <strong>emessa</strong>, '
            'con il residuo aggiornato.',
            'La somma delle quote deve fare esattamente l\'importo ricevuto.',
        ],
    }


def _flusso_pagamento():
    """Etichette ed endpoint della pagina di pagamento (template condiviso)."""
    return {
        'titolo':      'Registra pagamento',
        'icona':       'bi-cash-stack',
        'sottotitolo': ('Il pagamento che chiude una o più fatture ricevute. '
                        'Lo stato della fattura passiva cambia solo da qui.'),
        'passo_controparte': 'Chi hai pagato',
        'passo_fatture':     'Quali fatture chiude',
        'aiuto_controparte': ('Compaiono solo i fornitori con almeno una fattura '
                             'ancora da pagare.'),
        'aiuto_fatture':     'Scegli prima il fornitore.',
        'placeholder_controparte': 'Cerca il fornitore per ragione sociale…',
        'vuoto_controparte': 'Nessun fornitore con fatture da pagare',
        'colonna_quota':  'Pagamento',
        'parola_importo': 'pagati',
        'prefisso_quota': 'pagamento',
        'url_controparte': reverse('contabilita:pagamento_fornitori'),
        'url_fatture':     reverse('contabilita:pagamento_fatture'),
        'annulla_url':     reverse('acquisti:fattura_list'),
        'spiegazione': [
            'Per ogni fattura selezionata nasce <strong>un movimento</strong> in prima nota: '
            'Dare il conto del fornitore, Avere il conto banca/cassa.',
            'La fattura accumula il pagamento e passa a <strong>pagata</strong> '
            'solo quando è coperta per intero.',
            'Se paghi meno del residuo la fattura resta <strong>da pagare</strong>, '
            'con il residuo aggiornato.',
            'La somma delle quote deve fare esattamente l\'importo pagato.',
        ],
    }


@login_required
def incasso_create(request):
    """
    Registra un movimento bancario che incassa una o più fatture attive.
    È l'unico punto da cui una fattura attiva passa a 'pagata'.
    """
    form = RegistrazioneIncassoForm(request.POST or None, initial={
        'data': timezone.localdate(),
    })
    if request.method == 'POST' and form.is_valid():
        _registra_quote(request, form,
                        tipo=MovimentoPrimaNota.Tipo.INCASSO, verso=VERSO_INCASSO)
        return redirect(reverse('contabilita:prima_nota_list') + '?tipo=incasso')

    return render(request, 'contabilita/registrazione_form.html', {
        'page_title': 'Registra incasso',
        'form':       form,
        'flusso':     _flusso_incasso(),
    })


@login_required
def pagamento_create(request):
    """
    Registra il pagamento di una o più fatture passive.
    È l'unico punto da cui una fattura passiva passa a 'pagata'.
    """
    form = RegistrazionePagamentoForm(request.POST or None, initial={
        'data': timezone.localdate(),
    })
    if request.method == 'POST' and form.is_valid():
        _registra_quote(request, form,
                        tipo=MovimentoPrimaNota.Tipo.PAGAMENTO, verso=VERSO_PAGAMENTO)
        return redirect(reverse('contabilita:prima_nota_list') + '?tipo=pagamento')

    return render(request, 'contabilita/registrazione_form.html', {
        'page_title': 'Registra pagamento',
        'form':       form,
        'flusso':     _flusso_pagamento(),
    })


class MovimentoDetailView(LoginRequiredMixin, SidebarQrAllegatiMixin,
                          PrintDetailMixin, DetailView):
    """
    Dettaglio del movimento. I mixin abilitano le funzioni d'oggetto del FAB
    "Strumenti" (allegati, QR code, invio) e la stampa della scheda.
    """
    model               = MovimentoPrimaNota
    template_name       = 'contabilita/movimento_detail.html'
    context_object_name = 'mov'
    print_title         = 'Movimento di prima nota'
    print_fields        = [
        'numero', 'data', 'tipo', 'causale', 'importo',
        'numero_documento', 'note', 'created_at',
    ]

    def get_queryset(self):
        return (super().get_queryset()
                .select_related('conto_dare', 'conto_avere', 'creato_da',
                                'fattura_attiva', 'fattura_passiva__fornitore'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        mov = self.object
        ctx['page_title'] = f'{mov.numero or "Movimento"} — {mov.data:%d/%m/%Y}'
        ctx['documento']  = documenti.dettaglio(mov)
        ctx['allegati']   = mov.allegati
        return ctx


@login_required
def movimento_storna(request, pk):
    """
    Registra il movimento uguale e contrario che annulla `pk`.

    Un movimento sbagliato non si corregge e non si cancella: in un registro
    contabile la traccia dell'errore fa parte del registro. Lo storno copia i
    conti dall'originale e li scambia — nessuno li riscrive a mano — e se
    l'originale aveva mosso lo stato di una fattura, lo riporta indietro.
    """
    mov = get_object_or_404(
        MovimentoPrimaNota.objects.select_related(
            'conto_dare', 'conto_avere', 'fattura_attiva', 'fattura_passiva'),
        pk=pk,
    )

    if mov.is_storno:
        messages.error(request, 'Questo movimento è già uno storno: non si storna a sua volta.')
        return redirect(mov.get_absolute_url())
    if mov.is_stornato:
        messages.warning(request, 'Movimento già stornato.')
        return redirect(mov.storno.get_absolute_url())

    if request.method == 'POST':
        with transaction.atomic():
            storno = MovimentoPrimaNota.objects.create(
                data=timezone.localdate(),
                causale=f'STORNO — {mov.causale}',
                importo=mov.importo,
                tipo=mov.tipo,
                # I due lati scambiati: è tutta la sostanza dello storno.
                conto_dare=mov.conto_avere,
                conto_avere=mov.conto_dare,
                numero_documento=mov.numero_documento,
                fattura_attiva=mov.fattura_attiva,
                fattura_passiva=mov.fattura_passiva,
                note=(request.POST.get('motivo') or '').strip(),
                creato_da=request.user,
                storna=mov,
            )

            # Se l'originale aveva chiuso (in tutto o in parte) una fattura,
            # lo storno la riapre. Il metodo regge anche il caso dei movimenti
            # registrati a mano, che la fattura non l'avevano mai toccata.
            if mov.tipo == MovimentoPrimaNota.Tipo.INCASSO and mov.fattura_attiva:
                mov.fattura_attiva.storna_incasso(mov.importo)
            elif mov.tipo == MovimentoPrimaNota.Tipo.PAGAMENTO and mov.fattura_passiva:
                mov.fattura_passiva.storna_pagamento(mov.importo)

        messages.success(
            request,
            'Storno registrato: il movimento originale resta a registro, '
            'il suo effetto sui saldi è annullato.',
        )
        return redirect(storno.get_absolute_url())

    return render(request, 'contabilita/movimento_confirm_storno.html', {
        'page_title': 'Storna movimento',
        'mov':        mov,
    })


@login_required
def movimento_delete(request, pk):
    mov = get_object_or_404(MovimentoPrimaNota, pk=pk)
    if mov.is_automatico:
        messages.error(request, 'I movimenti generati automaticamente non possono essere eliminati.')
        return redirect(mov.get_absolute_url())
    if mov.is_storno or mov.is_stornato:
        messages.error(
            request,
            'Un movimento legato a uno storno non si elimina: la coppia '
            'originale/storno è la traccia dell\'errore e resta a registro.',
        )
        return redirect(mov.get_absolute_url())
    if request.method == 'POST':
        mov.delete()
        messages.success(request, 'Movimento eliminato.')
        return redirect(reverse('contabilita:prima_nota_list'))
    ctx = {'page_title': 'Elimina Movimento', 'mov': mov}
    return render(request, 'contabilita/movimento_confirm_delete.html', ctx)


# ─────────────────────────────────────────────────────────────────────────────
# MASTRINO — per singolo conto
# ─────────────────────────────────────────────────────────────────────────────

MOVIMENTI_MASTRINO_PER_PAGINA = 50


def _dare_avere(qs, conto):
    """Totale dare e totale avere di un conto su un insieme di movimenti."""
    agg = qs.aggregate(
        tot_dare=Sum(Case(When(conto_dare=conto, then='importo'),
                          default=0, output_field=DField())),
        tot_avere=Sum(Case(When(conto_avere=conto, then='importo'),
                           default=0, output_field=DField())),
    )
    return (agg['tot_dare'] or Decimal('0.00'),
            agg['tot_avere'] or Decimal('0.00'))


@login_required
def mastrino(request, pk):
    conto = get_object_or_404(ContoContabile, pk=pk)

    data_da = request.GET.get('data_da', '').strip()
    data_a  = request.GET.get('data_a', '').strip()

    # `pk` in coda all'ordinamento: data e created_at possono coincidere (es.
    # movimenti creati nella stessa transazione) e senza un criterio univoco
    # la paginazione può ripetere o saltare righe.
    qs = (MovimentoPrimaNota.objects
          .filter(Q(conto_dare=conto) | Q(conto_avere=conto))
          .select_related('conto_dare', 'conto_avere', 'creato_da')
          .order_by('data', 'created_at', 'pk'))

    if data_da:
        qs = qs.filter(data__gte=data_da)
    if data_a:
        qs = qs.filter(data__lte=data_a)

    paginator = Paginator(qs, MOVIMENTI_MASTRINO_PER_PAGINA)
    page_obj  = paginator.get_page(request.GET.get('page'))

    # Saldo di apertura: dare - avere dei movimenti che precedono questa pagina
    # nello stesso ordinamento, così il progressivo resta corretto anche
    # dalla seconda pagina in poi. L'aggregate sul queryset affettato diventa
    # una subquery con LIMIT: non materializza le righe precedenti.
    precedenti = page_obj.start_index() - 1 if paginator.count else 0
    if precedenti > 0:
        ap_dare, ap_avere = _dare_avere(qs[:precedenti], conto)
        saldo_apertura = ap_dare - ap_avere
    else:
        saldo_apertura = Decimal('0.00')

    # Saldo progressivo sulle righe della pagina
    saldo     = saldo_apertura
    movimenti = list(page_obj.object_list)
    for m in movimenti:
        if m.conto_dare_id == conto.pk:
            m.lato   = 'dare'
            m.valore = m.importo
            saldo   += m.importo
        else:
            m.lato   = 'avere'
            m.valore = m.importo
            saldo   -= m.importo
        m.saldo_progressivo = saldo

    # Totali su tutto il periodo filtrato, non sulla singola pagina
    tot_dare, tot_avere = _dare_avere(qs, conto)

    ctx = {
        'page_title':     f'Mastrino — {conto.nome}',
        'conto':          conto,
        'movimenti':      movimenti,
        'page_obj':       page_obj,
        'n_movimenti':    paginator.count,
        'saldo_apertura': saldo_apertura,
        'saldo_chiusura': saldo,
        'tot_dare':       tot_dare,
        'tot_avere':      tot_avere,
        'saldo':          tot_dare - tot_avere,
        'data_da':        data_da,
        'data_a':         data_a,
    }
    return render(request, 'contabilita/mastrino.html', ctx)


# ─────────────────────────────────────────────────────────────────────────────
# IMPOSTAZIONI — chiusura di periodo
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def impostazioni(request):
    """
    Chiusura di periodo. Solo per amministratori: spostarla in avanti congela
    dei mesi, spostarla indietro li riapre — non è una scelta operativa.
    """
    if not request.user.is_staff:
        messages.error(request, 'Solo un amministratore può modificare la chiusura di periodo.')
        return redirect(reverse('contabilita:dashboard'))

    impo = ImpostazioniContabilita.carica()
    form = ImpostazioniContabilitaForm(request.POST or None, instance=impo)

    if request.method == 'POST' and form.is_valid():
        impo = form.save(commit=False)
        impo.aggiornata_da = request.user
        impo.save()
        if impo.chiusa_fino_al:
            messages.success(request, (
                f'Contabilità chiusa fino al {impo.chiusa_fino_al:%d/%m/%Y}: '
                'da ora nessun movimento può avere una data pari o precedente.'
            ))
        else:
            messages.success(request, 'Chiusura di periodo rimossa: nessuna data è più bloccata.')
        return redirect(reverse('contabilita:dashboard'))

    # Quanti movimenti resterebbero congelati dalla chiusura attuale.
    n_congelati = (MovimentoPrimaNota.objects.filter(data__lte=impo.chiusa_fino_al).count()
                   if impo.chiusa_fino_al else 0)

    return render(request, 'contabilita/impostazioni.html', {
        'page_title':   'Impostazioni contabilità',
        'form':         form,
        'impostazioni': impo,
        'n_congelati':  n_congelati,
        'data_minima':  data_minima_plausibile(),
    })


# ─────────────────────────────────────────────────────────────────────────────
# CONTI CONTABILI — gestione
# ─────────────────────────────────────────────────────────────────────────────

CONTI_LIMITE = 100


@login_required
def conti_list(request):
    """
    Ricerca sui conti: senza filtri non viene mostrato alcun dato, la tabella
    dei risultati compare solo dopo una ricerca.
    """
    q       = request.GET.get('q', '').strip()
    tipo_f  = request.GET.get('tipo', '').strip()
    stato_f = request.GET.get('stato', '').strip()

    ricerca_eseguita = bool(q or tipo_f or stato_f)
    conti    = []
    troncato = False

    if ricerca_eseguita:
        # Saldo calcolato in SQL: la property `saldo` costerebbe 2 query a riga.
        zero = Value(Decimal('0.00'), output_field=DField(max_digits=14, decimal_places=2))
        dare_sq = (MovimentoPrimaNota.objects
                   .filter(conto_dare=OuterRef('pk'))
                   .values('conto_dare')
                   .annotate(tot=Sum('importo'))
                   .values('tot'))
        avere_sq = (MovimentoPrimaNota.objects
                    .filter(conto_avere=OuterRef('pk'))
                    .values('conto_avere')
                    .annotate(tot=Sum('importo'))
                    .values('tot'))

        qs = ContoContabile.objects.annotate(
            saldo_calcolato=Coalesce(Subquery(dare_sq), zero) - Coalesce(Subquery(avere_sq), zero)
        )

        if q:
            qs = qs.filter(
                Q(nome__icontains=q)
                | Q(iban__icontains=q)
                | Q(descrizione__icontains=q)
            )
        if tipo_f:
            qs = qs.filter(tipo=tipo_f)
        if stato_f == 'attivi':
            qs = qs.filter(attivo=True)
        elif stato_f == 'disattivi':
            qs = qs.filter(attivo=False)

        conti    = list(qs.order_by('tipo', 'nome')[:CONTI_LIMITE + 1])
        troncato = len(conti) > CONTI_LIMITE
        conti    = conti[:CONTI_LIMITE]

    ctx = {
        'page_title':       'Conti Contabili',
        'conti':            conti,
        'ricerca_eseguita': ricerca_eseguita,
        'troncato':         troncato,
        'limite':           CONTI_LIMITE,
        'q':                q,
        'tipo_f':           tipo_f,
        'stato_f':          stato_f,
        'tipi':             ContoContabile.Tipo.choices,
    }
    return render(request, 'contabilita/conti_list.html', ctx)


@login_required
def conti_suggerimenti(request):
    """
    Autocomplete del campo di ricerca conti: risponde dalle prime 2 lettere.
    Rispetta i filtri tipo/stato già impostati nel form.
    """
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    qs = ContoContabile.objects.filter(
        Q(nome__icontains=q) | Q(iban__icontains=q)
    )

    tipo_f = request.GET.get('tipo', '').strip()
    if tipo_f:
        qs = qs.filter(tipo=tipo_f)

    stato_f = request.GET.get('stato', '').strip()
    if stato_f == 'attivi':
        qs = qs.filter(attivo=True)
    elif stato_f == 'disattivi':
        qs = qs.filter(attivo=False)

    results = [
        {
            'nome':       c.nome,
            'tipo':       c.get_tipo_display(),
            'attivo':     c.attivo,
            'iban':       c.iban,
        }
        for c in qs.order_by('tipo', 'nome')[:10]
    ]
    return JsonResponse({'results': results})


@login_required
def conto_create(request):
    form = ContoContabileForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        conto = form.save()
        messages.success(request, f'Conto "{conto.nome}" creato.')
        return redirect(reverse('contabilita:conti_list'))
    ctx = {'page_title': 'Nuovo Conto', 'form': form}
    return render(request, 'contabilita/conto_form.html', ctx)


@login_required
def conto_edit(request, pk):
    conto = get_object_or_404(ContoContabile, pk=pk)
    form  = ContoContabileForm(request.POST or None, instance=conto)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Conto aggiornato.')
        return redirect(reverse('contabilita:conti_list'))
    ctx = {'page_title': f'Modifica — {conto.nome}', 'form': form, 'conto': conto}
    return render(request, 'contabilita/conto_form.html', ctx)


@login_required
def conto_delete(request, pk):
    conto = get_object_or_404(ContoContabile, pk=pk)
    ha_movimenti = (conto.movimenti_dare.exists() or conto.movimenti_avere.exists())
    if ha_movimenti:
        messages.error(request, 'Impossibile eliminare: il conto ha movimenti collegati.')
        return redirect(reverse('contabilita:conti_list'))
    if request.method == 'POST':
        nome = conto.nome
        conto.delete()
        messages.success(request, f'Conto "{nome}" eliminato.')
        return redirect(reverse('contabilita:conti_list'))
    ctx = {'page_title': 'Elimina Conto', 'conto': conto}
    return render(request, 'contabilita/conto_confirm_delete.html', ctx)
