from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import (
    Case, DecimalField as DField, OuterRef, Q, Subquery, Sum, Value, When,
)
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import DetailView

from core.mixins import PrintDetailMixin, SidebarQrAllegatiMixin

from . import documenti
from .forms import ContoContabileForm, MovimentoPrimaNotaForm
from .models import ContoContabile, MovimentoPrimaNota


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

    ctx = {
        'page_title':      'Contabilità — Prima Nota',
        'crediti_clienti': crediti_clienti,
        'debiti_fornitori': debiti_fornitori,
        'casse':           casse,
        'banche':          banche,
        'ultimi':          ultimi,
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
    tipo_f    = request.GET.get('tipo', '').strip()
    data_da   = request.GET.get('data_da', '').strip()
    data_a    = request.GET.get('data_a', '').strip()
    conto_f   = request.GET.get('conto', '').strip()

    ricerca_eseguita = bool(tipo_f or data_da or data_a or conto_f)
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

    ctx = {
        'page_title': 'Nuovo Movimento',
        'form':       form,
        'documento':  form.documento_selezionato(),
        'tipi_suggeriti': {
            'fattura_cliente':   ('cliente', 'generico'),
            'fattura_fornitore': ('fornitore', 'generico'),
            'incasso':           ('cassa', 'cliente'),
            'pagamento':         ('fornitore', 'cassa'),
            'giroconto':         ('banca', 'cassa'),
            'stipendi':          ('generico', 'cassa'),
        },
    }
    return render(request, 'contabilita/movimento_form.html', ctx)


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
        'data', 'tipo', 'causale', 'importo',
        'numero_documento', 'note', 'created_at',
    ]

    def get_queryset(self):
        return (super().get_queryset()
                .select_related('conto_dare', 'conto_avere', 'creato_da',
                                'fattura_attiva', 'fattura_passiva__fornitore'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        mov = self.object
        ctx['page_title'] = f'Movimento — {mov.data:%d/%m/%Y}'
        ctx['documento']  = documenti.dettaglio(mov)
        ctx['allegati']   = mov.allegati
        return ctx


@login_required
def movimento_delete(request, pk):
    mov = get_object_or_404(MovimentoPrimaNota, pk=pk)
    if mov.is_automatico:
        messages.error(request, 'I movimenti generati automaticamente non possono essere eliminati.')
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
