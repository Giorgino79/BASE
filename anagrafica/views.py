"""
Anagrafica Views - ModularBEF
=============================

Views per gestione Clienti e Fornitori: CRUD, Dashboard, API e PDF.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone

from core.pdf_generator import generate_pdf_response

from django import forms as django_forms

from .models import Cliente, Fornitore
from .forms import ClienteForm, FornitoreForm


# ============================================================================
# HELPERS RAPPRESENTANTE
# ============================================================================

def _get_repr_user(user):
    """Ritorna il Rappresentante collegato all'utente, se esiste."""
    try:
        return user.rappresentante
    except Exception:
        return None


def _is_admin_user(user):
    """True se l'utente è staff o ha il permesso gestisci_rappresentanti."""
    return user.is_staff or user.has_perm('rappresentanti.gestisci_rappresentanti')


# ============================================================================
# MIXIN
# ============================================================================

class AnagraficaAccessMixin(LoginRequiredMixin):
    """Mixin per controllo accesso alle viste anagrafica."""
    login_url = "/admin/login/"


# ============================================================================
# DASHBOARD
# ============================================================================

@login_required
def dashboard(request):
    """Dashboard principale anagrafica con statistiche."""

    # Statistiche clienti
    clienti_totali = Cliente.objects.filter(attivo=True).count()
    clienti_nuovi = Cliente.objects.filter(
        attivo=True,
        created_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).count()

    # Statistiche fornitori
    fornitori_totali = Fornitore.objects.filter(attivo=True).count()
    fornitori_per_categoria = Fornitore.objects.filter(attivo=True).values(
        "categoria"
    ).annotate(count=Count("id")).order_by("-count")[:5]

    # Ultimi clienti e fornitori
    ultimi_clienti = Cliente.objects.filter(attivo=True).order_by("-created_at")[:5]
    ultimi_fornitori = Fornitore.objects.filter(attivo=True).order_by("-created_at")[:5]

    context = {
        "clienti_totali": clienti_totali,
        "clienti_nuovi": clienti_nuovi,
        "fornitori_totali": fornitori_totali,
        "fornitori_per_categoria": fornitori_per_categoria,
        "ultimi_clienti": ultimi_clienti,
        "ultimi_fornitori": ultimi_fornitori,
    }
    return render(request, "anagrafica/dashboard.html", context)


# ============================================================================
# CLIENTI - CRUD
# ============================================================================

class ClienteListView(AnagraficaAccessMixin, ListView):
    """Elenco clienti con ricerca e filtri."""

    model = Cliente
    template_name = "anagrafica/clienti/elenco.html"
    context_object_name = "clienti"
    paginate_by = 20

    def get_queryset(self):
        queryset = Cliente.objects.all()

        # Filtraggio per rappresentante: non-admin reps vedono solo i propri clienti
        repr_utente = _get_repr_user(self.request.user)
        if repr_utente and not _is_admin_user(self.request.user):
            queryset = queryset.filter(rappresentante=repr_utente)
        elif _is_admin_user(self.request.user):
            # Admin: supporta filtro ?rappresentante=pk per vedere clienti di un rep specifico
            repr_pk = self.request.GET.get('rappresentante', '').strip()
            if repr_pk:
                queryset = queryset.filter(rappresentante_id=repr_pk)

        # Filtro credito
        credito = self.request.GET.get("credito", "").strip()
        if credito == "con_limite":
            queryset = queryset.filter(limite_credito__gt=0)
        elif credito == "senza_limite":
            queryset = queryset.filter(limite_credito=0)

        # Ricerca
        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(ragione_sociale__icontains=search) |
                Q(email__icontains=search) |
                Q(telefono__icontains=search) |
                Q(partita_iva__icontains=search) |
                Q(codice_fiscale__icontains=search)
            )

        # Ordinamento
        ordine = self.request.GET.get("ordine", "ragione_sociale")
        if ordine in ["ragione_sociale", "-ragione_sociale", "created_at", "-created_at", "citta", "-citta"]:
            queryset = queryset.order_by(ordine)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["credito_filter"] = self.request.GET.get("credito", "")
        context["ordine"] = self.request.GET.get("ordine", "ragione_sociale")
        context["totale_crediti"] = sum(
            c.limite_credito for c in Cliente.objects.filter(limite_credito__gt=0)
        )
        repr_utente = _get_repr_user(self.request.user)
        context["solo_miei"] = bool(repr_utente and not _is_admin_user(self.request.user))
        return context


class ClienteDetailView(AnagraficaAccessMixin, DetailView):
    """Dettaglio cliente."""

    model = Cliente
    template_name = "anagrafica/clienti/dettaglio.html"
    context_object_name = "cliente"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        repr_utente = _get_repr_user(request.user)
        if repr_utente and not _is_admin_user(request.user):
            if self.object.rappresentante != repr_utente:
                messages.error(request, 'Non hai accesso a questo cliente.')
                return redirect('anagrafica:cliente_list')
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self.object

        from django.contrib.contenttypes.models import ContentType
        from django.urls import reverse

        content_type = ContentType.objects.get_for_model(cliente)

        context["content_type_id"] = content_type.id
        context["edit_url"] = reverse("anagrafica:cliente_update", kwargs={"pk": cliente.pk})
        context["back_url"] = reverse("anagrafica:cliente_list")
        # Solo admin può eliminare
        if _is_admin_user(self.request.user):
            context["delete_url"] = reverse("anagrafica:cliente_delete", kwargs={"pk": cliente.pk})

        # Calcolo credito per i clienti
        if cliente.limite_credito > 0:
            # TODO: Implementare logica di calcolo credito utilizzato quando ci sarà il modulo vendite
            credito_utilizzato = 0  # Placeholder
            credito_disponibile = cliente.limite_credito - credito_utilizzato
            percentuale_uso = (credito_utilizzato / cliente.limite_credito * 100) if cliente.limite_credito > 0 else 0

            # Stato credito
            if percentuale_uso >= 90:
                stato = "critico"
                messaggio = "Credito esaurito"
                classe_css = "text-danger"
            elif percentuale_uso >= 75:
                stato = "attenzione"
                messaggio = "Credito in esaurimento"
                classe_css = "text-warning"
            else:
                stato = "normale"
                messaggio = "Credito disponibile"
                classe_css = "text-success"

            context["credito_utilizzato"] = credito_utilizzato
            context["credito_disponibile"] = credito_disponibile
            context["stato_credito"] = {
                "stato": stato,
                "messaggio": messaggio,
                "classe_css": classe_css,
                "percentuale_uso": percentuale_uso,
            }

        return context


class ClienteCreateView(AnagraficaAccessMixin, CreateView):
    """Creazione nuovo cliente."""

    model = Cliente
    form_class = ClienteForm
    template_name = "anagrafica/clienti/nuovo.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not _is_admin_user(self.request.user):
            # Non-admin: nasconde il campo rappresentante
            form.fields['rappresentante'].widget = django_forms.HiddenInput()
            repr_utente = _get_repr_user(self.request.user)
            if repr_utente:
                form.fields['rappresentante'].initial = repr_utente
        else:
            form.fields['rappresentante'].empty_label = '— Direzionale (nessun rappresentante) —'
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titolo"] = "Nuovo Cliente"
        context["submit_text"] = "Crea Cliente"
        return context

    def form_valid(self, form):
        repr_utente = _get_repr_user(self.request.user)
        if repr_utente and not _is_admin_user(self.request.user):
            form.instance.rappresentante = repr_utente
        messages.success(self.request, f"Cliente '{form.instance.ragione_sociale}' creato con successo!")
        return super().form_valid(form)


class ClienteUpdateView(AnagraficaAccessMixin, UpdateView):
    """Modifica cliente esistente."""

    model = Cliente
    form_class = ClienteForm
    template_name = "anagrafica/clienti/modifica.html"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        repr_utente = _get_repr_user(request.user)
        if repr_utente and not _is_admin_user(request.user):
            if obj.rappresentante != repr_utente:
                messages.error(request, 'Non hai accesso a questo cliente.')
                return redirect('anagrafica:cliente_list')
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not _is_admin_user(self.request.user):
            # Non-admin: non può riassegnare il rappresentante
            form.fields['rappresentante'].widget = django_forms.HiddenInput()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titolo"] = f"Modifica Cliente: {self.object.ragione_sociale}"
        context["submit_text"] = "Salva Modifiche"
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Cliente '{form.instance.ragione_sociale}' modificato con successo!")
        return super().form_valid(form)


class ClienteDeleteView(AnagraficaAccessMixin, DeleteView):
    """Eliminazione cliente — solo amministratori."""

    model = Cliente
    template_name = "anagrafica/clienti/elimina.html"
    success_url = reverse_lazy("anagrafica:cliente_list")

    def dispatch(self, request, *args, **kwargs):
        if not _is_admin_user(request.user):
            messages.error(request, 'Solo gli amministratori possono eliminare clienti.')
            return redirect('anagrafica:cliente_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cliente = self.object
        cliente.soft_delete(user=self.request.user)
        messages.success(self.request, f"Cliente '{cliente.ragione_sociale}' eliminato con successo!")
        return redirect(self.success_url)


# ============================================================================
# FORNITORI - CRUD
# ============================================================================

class FornitoreListView(AnagraficaAccessMixin, ListView):
    """Elenco fornitori con ricerca e filtri."""

    model = Fornitore
    template_name = "anagrafica/fornitori/elenco.html"
    context_object_name = "fornitori"
    paginate_by = 20

    def get_queryset(self):
        queryset = Fornitore.objects.all()

        # Filtro stato
        stato = self.request.GET.get("stato", "").strip()
        if stato == "attivi":
            queryset = queryset.filter(attivo=True)
        elif stato == "inattivi":
            queryset = queryset.filter(attivo=False)
        else:
            # Default: mostra tutti
            pass

        # Ricerca
        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(ragione_sociale__icontains=search) |
                Q(email__icontains=search) |
                Q(telefono__icontains=search) |
                Q(partita_iva__icontains=search)
            )

        # Filtro categoria
        categoria = self.request.GET.get("categoria", "").strip()
        if categoria:
            queryset = queryset.filter(categoria=categoria)

        # Ordinamento
        ordine = self.request.GET.get("ordine", "ragione_sociale")
        if ordine in ["ragione_sociale", "-ragione_sociale", "created_at", "-created_at", "categoria"]:
            queryset = queryset.order_by(ordine)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["stato_filter"] = self.request.GET.get("stato", "")
        context["categoria_filtro"] = self.request.GET.get("categoria", "")
        context["ordine"] = self.request.GET.get("ordine", "ragione_sociale")
        context["categorie"] = Fornitore.CATEGORIA_CHOICES

        # Statistiche
        context["stats"] = {
            "totali": Fornitore.objects.count(),
            "attivi": Fornitore.objects.filter(attivo=True).count(),
            "inattivi": Fornitore.objects.filter(attivo=False).count(),
        }
        return context


class FornitoreDetailView(AnagraficaAccessMixin, DetailView):
    """Dettaglio fornitore."""

    model = Fornitore
    template_name = "anagrafica/fornitori/dettaglio.html"
    context_object_name = "fornitore"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fornitore = self.object

        from django.contrib.contenttypes.models import ContentType
        from django.urls import reverse

        content_type = ContentType.objects.get_for_model(fornitore)

        context["content_type_id"] = content_type.id
        context["edit_url"] = reverse("anagrafica:fornitore_update", kwargs={"pk": fornitore.pk})
        context["delete_url"] = reverse("anagrafica:fornitore_delete", kwargs={"pk": fornitore.pk})
        context["back_url"] = reverse("anagrafica:fornitore_list")

        return context


class FornitoreCreateView(AnagraficaAccessMixin, CreateView):
    """Creazione nuovo fornitore."""

    model = Fornitore
    form_class = FornitoreForm
    template_name = "anagrafica/fornitori/nuovo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titolo"] = "Nuovo Fornitore"
        context["submit_text"] = "Crea Fornitore"
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f"Fornitore '{form.instance.ragione_sociale}' creato con successo!")
        return super().form_valid(form)


class FornitoreUpdateView(AnagraficaAccessMixin, UpdateView):
    """Modifica fornitore esistente."""

    model = Fornitore
    form_class = FornitoreForm
    template_name = "anagrafica/fornitori/modifica.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titolo"] = f"Modifica Fornitore: {self.object.ragione_sociale}"
        context["submit_text"] = "Salva Modifiche"
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Fornitore '{form.instance.ragione_sociale}' modificato con successo!")
        return super().form_valid(form)


class FornitoreDeleteView(AnagraficaAccessMixin, DeleteView):
    """Eliminazione fornitore (soft delete)."""

    model = Fornitore
    template_name = "anagrafica/fornitori/elimina.html"
    success_url = reverse_lazy("anagrafica:fornitore_list")

    def form_valid(self, form):
        fornitore = self.object
        fornitore.soft_delete(user=self.request.user)
        messages.success(self.request, f"Fornitore '{fornitore.ragione_sociale}' eliminato con successo!")
        return redirect(self.success_url)


# ============================================================================
# PDF EXPORT
# ============================================================================

@login_required
def cliente_pdf(request, pk):
    """Genera PDF scheda cliente."""
    cliente = get_object_or_404(Cliente, pk=pk)

    data = [{
        "Campo": "Ragione Sociale",
        "Valore": cliente.ragione_sociale
    }, {
        "Campo": "Indirizzo",
        "Valore": cliente.get_indirizzo_completo(),
    }, {
    }, {
        "Campo": "Telefono",
        "Valore": cliente.telefono,
    }, {
        "Campo": "Email",
        "Valore": cliente.email,
    }, {
        "Campo": "Partita IVA",
        "Valore": cliente.partita_iva or "-",
    }, {
        "Campo": "Codice Fiscale",
        "Valore": cliente.codice_fiscale or "-",
    }, {
        "Campo": "Codice Univoco SDI",
        "Valore": cliente.codice_univoco or "-",
    }, {
        "Campo": "PEC",
        "Valore": cliente.pec or "-",
    }, {
        "Campo": "Tipo Pagamento",
        "Valore": cliente.get_tipo_pagamento_display(),
    }, 
    {
        "Campo": "Orario Consegna",
        "Valore": cliente.orario_consegna or "-",
    }]

    return generate_pdf_response(
        data=data,
        filename=f"cliente_{cliente.pk}",
        title=f"Scheda Cliente: {cliente.ragione_sociale}",
        headers=["Campo", "Valore"]
    )


@login_required
def fornitore_pdf(request, pk):
    """Genera PDF scheda fornitore."""
    fornitore = get_object_or_404(Fornitore, pk=pk)

    data = [{
        "Campo": "Ragione Sociale",
        "Valore": fornitore.ragione_sociale,
    }, {
        "Campo": "Indirizzo",
        "Valore": fornitore.get_indirizzo_completo(),
    }, {
        "Campo": "Categoria",
        "Valore": fornitore.get_categoria_display(),
    }, {
        "Campo": "Telefono",
        "Valore": fornitore.telefono,
    }, {
        "Campo": "Email",
        "Valore": fornitore.email,
    }, {
        "Campo": "Partita IVA",
        "Valore": fornitore.partita_iva,
    }, {
        "Campo": "Codice Fiscale",
        "Valore": fornitore.codice_fiscale or "-",
    }, {
        "Campo": "PEC",
        "Valore": fornitore.pec or "-",
    }, {
        "Campo": "Codice Destinatario SDI",
        "Valore": fornitore.codice_destinatario or "-",
    }, {
        "Campo": "IBAN",
        "Valore": fornitore.iban or "-",
    }, {
        "Campo": "Tipo Pagamento",
        "Valore": fornitore.get_tipo_pagamento_display(),
    }, {
        "Campo": "Priorità Pagamento",
        "Valore": fornitore.get_priorita_pagamento_default_display(),
    }, {
        "Campo": "Referente",
        "Valore": fornitore.referente_nome or "-",
    }, {
        "Campo": "Tel. Referente",
        "Valore": fornitore.referente_telefono or "-",
    }, {
        "Campo": "Email Referente",
        "Valore": fornitore.referente_email or "-",
    }]

    return generate_pdf_response(
        data=data,
        filename=f"fornitore_{fornitore.pk}",
        title=f"Scheda Fornitore: {fornitore.ragione_sociale}",
        headers=["Campo", "Valore"]
    )


@login_required
def clienti_lista_pdf(request):
    """Genera PDF elenco clienti."""
    clienti = Cliente.objects.filter(attivo=True).order_by("ragione_sociale")

    data = []
    for cliente in clienti:
        data.append({
            "Ragione Sociale": cliente.ragione_sociale,
            "Città": cliente.citta or "-",
            "Telefono": cliente.telefono,
            "Email": cliente.email,
            "P.IVA": cliente.partita_iva or "-",
            "Pagamento": cliente.get_tipo_pagamento_display(),
        })

    return generate_pdf_response(
        data=data,
        filename="cliente_list",
        title="Elenco Clienti",
        headers=["Ragione Sociale", "Città", "Telefono", "Email", "P.IVA", "Pagamento"]
    )


@login_required
def fornitori_lista_pdf(request):
    """Genera PDF elenco fornitori."""
    fornitori = Fornitore.objects.filter(attivo=True).order_by("ragione_sociale")

    data = []
    for fornitore in fornitori:
        data.append({
            "Ragione_sociale": fornitore.ragione_sociale,
            "Categoria": fornitore.get_categoria_display(),
            "Telefono": fornitore.telefono,
            "Email": fornitore.email,
            "P.IVA": fornitore.partita_iva,
            "Pagamento": fornitore.get_tipo_pagamento_display(),
        })

    return generate_pdf_response(
        data=data,
        filename="fornitore_list",
        title="Elenco Fornitori",
        headers=["Ragione Sociale", "Categoria", "Telefono", "Email", "P.IVA", "Pagamento"]
    )


# ============================================================================
# API
# ============================================================================

@login_required
def api_search(request):
    """API per ricerca globale anagrafica."""
    query = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")

    if len(query) < 2:
        return JsonResponse({"results": []})

    results = []

    # Ricerca clienti
    if tipo in ["", "clienti"]:
        clienti = Cliente.objects.filter(
            attivo=True
        ).filter(
            Q(ragione_sociale__icontains=query) |
            Q(email__icontains=query) |
            Q(telefono__icontains=query)
        )[:10]

        for cliente in clienti:
            results.append({
                "tipo": "cliente",
                "id": str(cliente.pk),
                "ragione_sociale": cliente.ragione_sociale,
                "dettaglio": f"{cliente.email} - {cliente.telefono}",
                "url": cliente.get_absolute_url(),
            })

    # Ricerca fornitori
    if tipo in ["", "fornitori"]:
        fornitori = Fornitore.objects.filter(
            attivo=True
        ).filter(
            Q(ragione_sociale__icontains=query) |
            Q(email__icontains=query) |
            Q(telefono__icontains=query)
        )[:10]

        for fornitore in fornitori:
            results.append({
                "tipo": "fornitore",
                "id": str(fornitore.pk),
                "ragione_sociale": fornitore.ragione_sociale,
                "dettaglio": f"{fornitore.get_categoria_display()} - {fornitore.email}",
                "url": fornitore.get_absolute_url(),
            })

    return JsonResponse({"results": results})


@login_required
def api_stats(request):
    """API per statistiche dashboard."""
    stats = {
        "clienti_totali": Cliente.objects.filter(attivo=True).count(),
        "fornitori_totali": Fornitore.objects.filter(attivo=True).count(),
        "clienti_nuovi_mese": Cliente.objects.filter(
            attivo=True,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count(),
        "fornitori_nuovi_mese": Fornitore.objects.filter(
            attivo=True,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count(),
    }
    return JsonResponse(stats)


@login_required
def toggle_attivo(request, tipo, pk):
    """Toggle stato attivo/inattivo per cliente o fornitore."""
    if tipo == "cliente":
        obj = get_object_or_404(Cliente, pk=pk)
    elif tipo == "fornitore":
        obj = get_object_or_404(Fornitore, pk=pk)
    else:
        messages.error(request, "Tipo non valido")
        return redirect("anagrafica:dashboard")

    if obj.attivo:
        obj.attivo = False
        obj.save()
        stato = "disattivato"
    else:
        obj.attivo = True
        obj.save()
        stato = "attivato"

    messages.success(request, f"{tipo.capitalize()} {obj.ragione_sociale} {stato} con successo!")

    # Redirect alla lista appropriata
    if tipo == "cliente":
        return redirect("anagrafica:cliente_list")
    return redirect("anagrafica:fornitore_list")


# ============================================================================
# EXPORT CSV
# ============================================================================

@login_required
def export_clienti_csv(request):
    """Export clienti in formato CSV."""
    import csv

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="clienti.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Ragione Sociale", "Indirizzo", "CAP", "Città", 
        "Telefono", "Email", "P.IVA", "CF",
        "Codice Univoco", "PEC", "Tipo Pagamento",
        "Giorno Chiusura", "Orario Consegna", "Note"
    ])

    for cliente in Cliente.objects.filter(attivo=True).order_by("ragione_sociale"):
        writer.writerow([
            cliente.ragione_sociale,
            cliente.indirizzo,
            cliente.cap,
            cliente.citta,
            cliente.telefono,
            cliente.email,
            cliente.partita_iva,
            cliente.codice_fiscale,
            cliente.codice_univoco,
            cliente.pec,
            cliente.get_tipo_pagamento_display(),
            cliente.note,
        ])

    return response


@login_required
def export_fornitori_csv(request):
    """Export fornitori in formato CSV."""
    import csv

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="fornitori.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Ragione Sociale", "Indirizzo", "CAP", "Città",
        "Telefono", "Email", "P.IVA", "CF", "PEC",
        "Codice SDI", "IBAN", "Categoria",
        "Tipo Pagamento", "Priorità Pagamento",
        "Referente", "Tel. Referente", "Email Referente", "Note"
    ])

    for fornitore in Fornitore.objects.filter(attivo=True).order_by("ragione_sociale"):
        writer.writerow([
            fornitore.ragione_sociale,
            fornitore.indirizzo,
            fornitore.cap,
            fornitore.citta,
            fornitore.telefono,
            fornitore.email,
            fornitore.partita_iva,
            fornitore.codice_fiscale,
            fornitore.pec,
            fornitore.codice_destinatario,
            fornitore.iban,
            fornitore.get_categoria_display(),
            fornitore.get_tipo_pagamento_display(),
            fornitore.get_priorita_pagamento_default_display(),
            fornitore.referente_nome,
            fornitore.referente_telefono,
            fornitore.referente_email,
            fornitore.note,
        ])

    return response
