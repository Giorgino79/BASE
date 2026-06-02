from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
import csv

from core.pdf_generator import generate_pdf_response

from .models import Azienda, Filiale, Fornitore, Privato
from .forms import AziendaForm, FilialeForm, FornitoreForm, PrivatoForm


class AccessMixin(LoginRequiredMixin):
    pass


# ── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    trenta_giorni_fa = timezone.now() - timedelta(days=30)
    context = {
        'clienti_totali':      Azienda.objects.filter(attivo=True).count(),
        'clienti_nuovi':       Azienda.objects.filter(attivo=True, created_at__gte=trenta_giorni_fa).count(),
        'sedi_totali':         Filiale.objects.filter(attivo=True).count(),
        'sedi_installate':     Filiale.objects.filter(attivo=True, installato=True).count(),
        'sedi_da_installare':  Filiale.objects.filter(attivo=True, installato=False).count(),
        'fornitori_totali':    Fornitore.objects.filter(attivo=True).count(),
        'fornitori_nuovi':     Fornitore.objects.filter(attivo=True, created_at__gte=trenta_giorni_fa).count(),
        'privati_totali':      Privato.objects.filter(attivo=True).count(),
        'privati_nuovi':       Privato.objects.filter(attivo=True, created_at__gte=trenta_giorni_fa).count(),
        'ultimi_clienti':      Azienda.objects.filter(attivo=True).order_by('-created_at')[:5],
        'ultimi_fornitori':    Fornitore.objects.filter(attivo=True).order_by('-created_at')[:5],
        'ultimi_privati':      Privato.objects.filter(attivo=True).order_by('-created_at')[:5],
    }
    return render(request, 'anagrafica_r2/dashboard.html', context)


# ── Clienti (Aziende) ────────────────────────────────────────────────────────

class AziendaListView(AccessMixin, ListView):
    model = Azienda
    template_name = 'anagrafica_r2/clienti/elenco.html'
    context_object_name = 'clienti'
    paginate_by = 25

    def get_queryset(self):
        qs = Azienda.objects.annotate(n_sedi=Count('filiali'))

        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(ragione_sociale__icontains=search) |
                Q(partita_iva__icontains=search) |
                Q(citta__icontains=search)
            )

        stato = self.request.GET.get('stato', 'attivi')
        if stato == 'attivi':
            qs = qs.filter(attivo=True)
        elif stato == 'inattivi':
            qs = qs.filter(attivo=False)

        installato = self.request.GET.get('installato', '')
        if installato == 'si':
            qs = qs.filter(installato=True)
        elif installato == 'no':
            qs = qs.filter(installato=False)

        ordine = self.request.GET.get('ordine', 'ragione_sociale')
        campi_validi = ['ragione_sociale', '-ragione_sociale', 'citta', '-created_at']
        if ordine in campi_validi:
            qs = qs.order_by(ordine)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_query']     = self.request.GET.get('search', '')
        ctx['stato_filter']     = self.request.GET.get('stato', 'attivi')
        ctx['installato_filter'] = self.request.GET.get('installato', '')
        ctx['ordine']           = self.request.GET.get('ordine', 'ragione_sociale')
        ctx['totale']           = Azienda.objects.count()
        ctx['totale_attivi']    = Azienda.objects.filter(attivo=True).count()
        return ctx


class AziendaDetailView(AccessMixin, DetailView):
    model = Azienda
    template_name = 'anagrafica_r2/clienti/dettaglio.html'
    context_object_name = 'cliente'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        c = self.object
        ctx['filiali']    = c.filiali.filter(attivo=True).order_by('nome')
        ctx['n_filiali_da_installare'] = c.n_filiali - c.n_filiali_installate
        ctx['edit_url']   = reverse('anagrafica:azienda_update', kwargs={'pk': c.pk})
        ctx['delete_url'] = reverse('anagrafica:azienda_delete', kwargs={'pk': c.pk})
        ctx['back_url']   = reverse('anagrafica:azienda_list')
        ctx['nuova_filiale_url'] = reverse('anagrafica:filiale_create', kwargs={'cliente_pk': c.pk})
        ctx['content_type_id'] = ContentType.objects.get_for_model(Azienda).pk
        ctx['object_id']       = c.pk
        return ctx


class AziendaCreateView(AccessMixin, CreateView):
    model = Azienda
    form_class = AziendaForm
    template_name = 'anagrafica_r2/clienti/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titolo']      = 'Nuovo Cliente'
        ctx['submit_text'] = 'Crea Cliente'
        ctx['back_url']    = reverse('anagrafica:azienda_list')
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Cliente «{form.instance.ragione_sociale}» creato con successo.')
        return super().form_valid(form)


class AziendaUpdateView(AccessMixin, UpdateView):
    model = Azienda
    form_class = AziendaForm
    template_name = 'anagrafica_r2/clienti/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titolo']      = f'Modifica: {self.object.ragione_sociale}'
        ctx['submit_text'] = 'Salva Modifiche'
        ctx['back_url']    = self.object.get_absolute_url()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Cliente «{form.instance.ragione_sociale}» aggiornato.')
        return super().form_valid(form)


class AziendaDeleteView(AccessMixin, DeleteView):
    model = Azienda
    template_name = 'anagrafica_r2/clienti/elimina.html'
    success_url = reverse_lazy('anagrafica:azienda_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Solo gli amministratori possono eliminare i clienti.')
            return redirect('anagrafica:azienda_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Cliente «{self.object.ragione_sociale}» eliminato.')
        return super().form_valid(form)


# ── Filiali ───────────────────────────────────────────────────────────────────

class FilialeCreateView(AccessMixin, CreateView):
    model = Filiale
    form_class = FilialeForm
    template_name = 'anagrafica_r2/filiali/form.html'

    def get_cliente(self):
        return get_object_or_404(Azienda, pk=self.kwargs['cliente_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cliente = self.get_cliente()
        ctx['cliente']     = cliente
        ctx['titolo']      = f'Nuova Sede — {cliente.ragione_sociale}'
        ctx['submit_text'] = 'Crea Sede'
        ctx['back_url']    = cliente.get_absolute_url()
        return ctx

    def form_valid(self, form):
        form.instance.cliente = self.get_cliente()
        messages.success(self.request, f'Sede «{form.instance.nome}» creata con successo.')
        return super().form_valid(form)

    def get_success_url(self):
        return self.get_cliente().get_absolute_url()


class FilialeDetailView(AccessMixin, DetailView):
    model = Filiale
    template_name = 'anagrafica_r2/filiali/dettaglio.html'
    context_object_name = 'filiale'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        f = self.object
        ctx['edit_url']   = reverse('anagrafica:filiale_update', kwargs={'pk': f.pk})
        ctx['delete_url'] = reverse('anagrafica:filiale_delete', kwargs={'pk': f.pk})
        ctx['back_url']   = f.cliente.get_absolute_url()
        ctx['content_type_id'] = ContentType.objects.get_for_model(Filiale).pk
        ctx['object_id']       = f.pk
        return ctx


class FilialeUpdateView(AccessMixin, UpdateView):
    model = Filiale
    form_class = FilialeForm
    template_name = 'anagrafica_r2/filiali/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cliente']     = self.object.cliente
        ctx['titolo']      = f'Modifica Sede: {self.object.nome}'
        ctx['submit_text'] = 'Salva Modifiche'
        ctx['back_url']    = self.object.get_absolute_url()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Sede «{form.instance.nome}» aggiornata.')
        return super().form_valid(form)


class FilialeDeleteView(AccessMixin, DeleteView):
    model = Filiale
    template_name = 'anagrafica_r2/filiali/elimina.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Solo gli amministratori possono eliminare le sedi.')
            return redirect('anagrafica:azienda_list')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.object.cliente.get_absolute_url()

    def form_valid(self, form):
        cliente_url = self.object.cliente.get_absolute_url()
        nome = self.object.nome
        self.object.delete()
        messages.success(self.request, f'Sede «{nome}» eliminata.')
        return redirect(cliente_url)


# ── Utility ───────────────────────────────────────────────────────────────────

@login_required
def toggle_attivo(request, tipo, pk):
    if tipo == 'cliente':
        obj = get_object_or_404(Azienda, pk=pk)
        redirect_url = obj.get_absolute_url()
    elif tipo == 'filiale':
        obj = get_object_or_404(Filiale, pk=pk)
        redirect_url = obj.cliente.get_absolute_url()
    elif tipo == 'fornitore':
        obj = get_object_or_404(Fornitore, pk=pk)
        redirect_url = obj.get_absolute_url()
    elif tipo == 'privato':
        obj = get_object_or_404(Privato, pk=pk)
        redirect_url = obj.get_absolute_url()
    else:
        messages.error(request, 'Tipo non valido.')
        return redirect('anagrafica:dashboard')

    obj.attivo = not obj.attivo
    obj.save(update_fields=['attivo'])
    stato = 'attivato' if obj.attivo else 'disattivato'
    messages.success(request, f'«{obj}» {stato}.')
    return redirect(redirect_url)


# ── Fornitori ─────────────────────────────────────────────────────────────────

class FornitoreListView(AccessMixin, ListView):
    model = Fornitore
    template_name = 'anagrafica_r2/fornitori/elenco.html'
    context_object_name = 'fornitori'
    paginate_by = 25

    def get_queryset(self):
        qs = Fornitore.objects.all()

        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(ragione_sociale__icontains=search) |
                Q(email__icontains=search) |
                Q(partita_iva__icontains=search) |
                Q(citta__icontains=search)
            )

        stato = self.request.GET.get('stato', 'attivi')
        if stato == 'attivi':
            qs = qs.filter(attivo=True)
        elif stato == 'inattivi':
            qs = qs.filter(attivo=False)

        categoria = self.request.GET.get('categoria', '').strip()
        if categoria:
            qs = qs.filter(categoria=categoria)

        ordine = self.request.GET.get('ordine', 'ragione_sociale')
        if ordine in ['ragione_sociale', '-ragione_sociale', '-created_at', 'categoria']:
            qs = qs.order_by(ordine)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_query']     = self.request.GET.get('search', '')
        ctx['stato_filter']     = self.request.GET.get('stato', 'attivi')
        ctx['categoria_filter'] = self.request.GET.get('categoria', '')
        ctx['ordine']           = self.request.GET.get('ordine', 'ragione_sociale')
        ctx['categorie']        = Fornitore.CATEGORIA_CHOICES
        ctx['totale']           = Fornitore.objects.count()
        ctx['totale_attivi']    = Fornitore.objects.filter(attivo=True).count()
        return ctx


class FornitoreDetailView(AccessMixin, DetailView):
    model = Fornitore
    template_name = 'anagrafica_r2/fornitori/dettaglio.html'
    context_object_name = 'fornitore'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        f = self.object
        ctx['edit_url']   = reverse('anagrafica:fornitore_update', kwargs={'pk': f.pk})
        ctx['delete_url'] = reverse('anagrafica:fornitore_delete', kwargs={'pk': f.pk})
        ctx['back_url']   = reverse('anagrafica:fornitore_list')
        ctx['pdf_url']    = reverse('anagrafica:fornitore_pdf', kwargs={'pk': f.pk})
        ctx['content_type_id'] = ContentType.objects.get_for_model(Fornitore).pk
        ctx['object_id']       = f.pk
        return ctx


class FornitoreCreateView(AccessMixin, CreateView):
    model = Fornitore
    form_class = FornitoreForm
    template_name = 'anagrafica_r2/fornitori/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titolo']      = 'Nuovo Fornitore'
        ctx['submit_text'] = 'Crea Fornitore'
        ctx['back_url']    = reverse('anagrafica:fornitore_list')
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Fornitore «{form.instance.ragione_sociale}» creato con successo.')
        return super().form_valid(form)


class FornitoreUpdateView(AccessMixin, UpdateView):
    model = Fornitore
    form_class = FornitoreForm
    template_name = 'anagrafica_r2/fornitori/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titolo']      = f'Modifica: {self.object.ragione_sociale}'
        ctx['submit_text'] = 'Salva Modifiche'
        ctx['back_url']    = self.object.get_absolute_url()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Fornitore «{form.instance.ragione_sociale}» aggiornato.')
        return super().form_valid(form)


class FornitoreDeleteView(AccessMixin, DeleteView):
    model = Fornitore
    template_name = 'anagrafica_r2/fornitori/elimina.html'
    success_url = reverse_lazy('anagrafica:fornitore_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Solo gli amministratori possono eliminare i fornitori.')
            return redirect('anagrafica:fornitore_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Fornitore «{self.object.ragione_sociale}» eliminato.')
        return super().form_valid(form)


# ── Filiali — vista globale ───────────────────────────────────────────────────

class FilialeGlobaleListView(AccessMixin, ListView):
    model = Filiale
    template_name = 'anagrafica_r2/filiali/elenco.html'
    context_object_name = 'filiali'
    paginate_by = 30

    def get_queryset(self):
        qs = Filiale.objects.select_related('cliente').order_by('cliente__ragione_sociale', 'nome')

        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(nome__icontains=search) |
                Q(citta__icontains=search) |
                Q(cliente__ragione_sociale__icontains=search)
            )

        stato = self.request.GET.get('stato', 'attive')
        if stato == 'attive':
            qs = qs.filter(attivo=True)
        elif stato == 'inattive':
            qs = qs.filter(attivo=False)

        installato = self.request.GET.get('installato', '')
        if installato == 'si':
            qs = qs.filter(installato=True)
        elif installato == 'no':
            qs = qs.filter(installato=False)

        tipo = self.request.GET.get('tipo', '')
        if tipo:
            qs = qs.filter(tipo_sede=tipo)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_query']    = self.request.GET.get('search', '')
        ctx['stato_filter']    = self.request.GET.get('stato', 'attive')
        ctx['installato_filter'] = self.request.GET.get('installato', '')
        ctx['tipo_filter']     = self.request.GET.get('tipo', '')
        ctx['tipi_sede']       = Filiale.TIPO_SEDE_CHOICES
        ctx['totale']          = Filiale.objects.count()
        ctx['totale_attive']   = Filiale.objects.filter(attivo=True).count()
        ctx['installate']      = Filiale.objects.filter(attivo=True, installato=True).count()
        return ctx


# ── PDF ───────────────────────────────────────────────────────────────────────

@login_required
def fornitore_pdf(request, pk):
    f = get_object_or_404(Fornitore, pk=pk)
    data = [
        {'Campo': 'Ragione Sociale',    'Valore': f.ragione_sociale},
        {'Campo': 'Indirizzo',          'Valore': f.get_indirizzo_completo()},
        {'Campo': 'Categoria',          'Valore': f.get_categoria_display()},
        {'Campo': 'Telefono',           'Valore': f.telefono},
        {'Campo': 'Email',              'Valore': f.email},
        {'Campo': 'Partita IVA',        'Valore': f.partita_iva},
        {'Campo': 'Codice Fiscale',     'Valore': f.codice_fiscale or '—'},
        {'Campo': 'PEC',                'Valore': f.pec or '—'},
        {'Campo': 'Codice SDI',         'Valore': f.codice_destinatario or '—'},
        {'Campo': 'IBAN',               'Valore': f.iban or '—'},
        {'Campo': 'Tipo Pagamento',     'Valore': f.get_tipo_pagamento_display()},
        {'Campo': 'Priorità Pagamento', 'Valore': f.get_priorita_pagamento_display()},
        {'Campo': 'Referente',          'Valore': f.referente_nome or '—'},
        {'Campo': 'Tel. Referente',     'Valore': f.referente_telefono or '—'},
        {'Campo': 'Email Referente',    'Valore': f.referente_email or '—'},
    ]
    return generate_pdf_response(
        data=data,
        filename=f'fornitore_{f.pk}',
        title=f'Scheda Fornitore: {f.ragione_sociale}',
        headers=['Campo', 'Valore'],
    )


# ── CSV ───────────────────────────────────────────────────────────────────────

@login_required
def export_fornitori_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="fornitori.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Ragione Sociale', 'Indirizzo', 'CAP', 'Città', 'Provincia', 'Regione',
        'Telefono', 'Email', 'P.IVA', 'CF', 'PEC', 'Codice SDI', 'IBAN',
        'Categoria', 'Tipo Pagamento', 'Priorità',
        'Referente', 'Tel. Referente', 'Email Referente',
        'Attivo', 'Note',
    ])
    for f in Fornitore.objects.all().order_by('ragione_sociale'):
        writer.writerow([
            f.ragione_sociale, f.indirizzo, f.cap, f.citta, f.provincia, f.regione,
            f.telefono, f.email, f.partita_iva, f.codice_fiscale,
            f.pec, f.codice_destinatario, f.iban,
            f.get_categoria_display(), f.get_tipo_pagamento_display(), f.get_priorita_pagamento_display(),
            f.referente_nome, f.referente_telefono, f.referente_email,
            'Sì' if f.attivo else 'No', f.note,
        ])
    return response


# ── Privati ───────────────────────────────────────────────────────────────────

class PrivatoListView(AccessMixin, ListView):
    model = Privato
    template_name = 'anagrafica_r2/privati/elenco.html'
    context_object_name = 'privati'
    paginate_by = 25

    def get_queryset(self):
        qs = Privato.objects.all()
        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(nome__icontains=search) |
                Q(cognome__icontains=search) |
                Q(telefono__icontains=search) |
                Q(citta__icontains=search) |
                Q(zona__icontains=search)
            )
        stato = self.request.GET.get('stato', 'attivi')
        if stato == 'attivi':
            qs = qs.filter(attivo=True)
        elif stato == 'inattivi':
            qs = qs.filter(attivo=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_query']  = self.request.GET.get('search', '')
        ctx['stato_filter']  = self.request.GET.get('stato', 'attivi')
        ctx['totale']        = Privato.objects.count()
        ctx['totale_attivi'] = Privato.objects.filter(attivo=True).count()
        return ctx


class PrivatoDetailView(AccessMixin, DetailView):
    model = Privato
    template_name = 'anagrafica_r2/privati/dettaglio.html'
    context_object_name = 'privato'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        p = self.object
        ctx['edit_url']   = reverse('anagrafica:privato_update', kwargs={'pk': p.pk})
        ctx['delete_url'] = reverse('anagrafica:privato_delete', kwargs={'pk': p.pk})
        ctx['back_url']   = reverse('anagrafica:privato_list')
        ctx['content_type_id'] = ContentType.objects.get_for_model(Privato).pk
        ctx['object_id']       = p.pk
        return ctx


class PrivatoCreateView(AccessMixin, CreateView):
    model = Privato
    form_class = PrivatoForm
    template_name = 'anagrafica_r2/privati/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titolo']      = 'Nuovo Cliente Privato'
        ctx['submit_text'] = 'Crea Cliente'
        ctx['back_url']    = reverse('anagrafica:privato_list')
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Cliente «{form.instance}» creato con successo.')
        return super().form_valid(form)


class PrivatoUpdateView(AccessMixin, UpdateView):
    model = Privato
    form_class = PrivatoForm
    template_name = 'anagrafica_r2/privati/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titolo']      = f'Modifica: {self.object}'
        ctx['submit_text'] = 'Salva Modifiche'
        ctx['back_url']    = self.object.get_absolute_url()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Cliente «{form.instance}» aggiornato.')
        return super().form_valid(form)


class PrivatoDeleteView(AccessMixin, DeleteView):
    model = Privato
    template_name = 'anagrafica_r2/privati/elimina.html'
    success_url = reverse_lazy('anagrafica:privato_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Solo gli amministratori possono eliminare i clienti privati.')
            return redirect('anagrafica:privato_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Cliente «{self.object}» eliminato.')
        return super().form_valid(form)


@login_required
def export_filiali_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sedi.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Cliente', 'Nome Sede', 'Tipo', 'Indirizzo', 'CAP', 'Città', 'Provincia', 'Regione',
        'Telefono', 'Email', 'Referente', 'Tel. Referente',
        'Orario Apertura', 'Giorno Chiusura', 'Installato', 'Attivo',
    ])
    for f in Filiale.objects.select_related('cliente').order_by('cliente__ragione_sociale', 'nome'):
        writer.writerow([
            f.cliente.ragione_sociale, f.nome, f.get_tipo_sede_display(),
            f.indirizzo, f.cap, f.citta, f.provincia, f.regione,
            f.telefono, f.email, f.referente_nome, f.referente_tel,
            f.orario_apertura, f.get_giorno_chiusura_display(),
            'Sì' if f.installato else 'No',
            'Sì' if f.attivo else 'No',
        ])
    return response
