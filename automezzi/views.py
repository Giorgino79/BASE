from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.db import models as db_models
from django.utils import timezone
from datetime import date
from decimal import Decimal

from .models import Automezzo, Manutenzione, AllegatoManutenzione, Rifornimento, EventoAutomezzo
from .forms import (
    AutomezzoForm,
    ManutenzioneCreateForm, ManutenzioneUpdateForm,
    ManutenzioneResponsabileForm, ManutenzioneFinaleForm,
    AllegatoManutenzioneForm,
    RifornimentoForm, EventoAutomezzoForm,
)


# ============================================================
# MIXIN SIDEBAR QR + ALLEGATI
# ============================================================

class SidebarQrAllegatiMixin:
    """Aggiunge content_type_id e object_id al context per il componente sidebar_allegati_qr.html."""
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.contrib.contenttypes.models import ContentType
        ctx["content_type_id"] = ContentType.objects.get_for_model(self.model).pk
        ctx["object_id"] = self.object.pk
        return ctx


# ============================================================
# DASHBOARD
# ============================================================

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "automezzi/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["automezzi_count"] = Automezzo.objects.count()
        ctx["automezzi_attivi"] = Automezzo.objects.filter(attivo=True).count()
        ctx["automezzi_disponibili"] = Automezzo.objects.filter(attivo=True, disponibile=True, bloccata=False).count()
        ctx["manutenzioni_aperte"] = Manutenzione.objects.filter(stato="aperta").count()
        ctx["manutenzioni_in_corso"] = Manutenzione.objects.filter(stato="in_corso").count()
        ctx["ultimi_rifornimenti"] = Rifornimento.objects.select_related("automezzo").order_by("-data")[:5]
        ctx["eventi_recenti"] = EventoAutomezzo.objects.select_related("automezzo").filter(risolto=False).order_by("-data_evento")[:5]

        # Stat cross-app (stabilimenti e' un'app comune a se') — pattern
        # identico a em26 (automezzi->stabilimenti), dichiarato in
        # MODULE_DEPENDENCIES, non e' un modulo opzionale quindi import diretto.
        from stabilimenti.models import Stabilimento
        ctx["stabilimenti_count"] = Stabilimento.objects.count()
        ctx["stabilimenti_attivi"] = Stabilimento.objects.filter(attivo=True).count()
        return ctx


# ============================================================
# AUTOMEZZI
# ============================================================

class AutomezzoListView(LoginRequiredMixin, ListView):
    model = Automezzo
    template_name = "automezzi/list.html"
    context_object_name = "automezzi"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(
                db_models.Q(targa__icontains=q) | db_models.Q(marca__icontains=q) | db_models.Q(modello__icontains=q)
            )
        attivo = self.request.GET.get("attivo", "")
        if attivo == "si":
            qs = qs.filter(attivo=True)
        elif attivo == "no":
            qs = qs.filter(attivo=False)
        disponibile = self.request.GET.get("disponibile", "")
        if disponibile == "si":
            qs = qs.filter(disponibile=True)
        elif disponibile == "no":
            qs = qs.filter(disponibile=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["attivo_filter"] = self.request.GET.get("attivo", "")
        ctx["disponibile_filter"] = self.request.GET.get("disponibile", "")
        return ctx


class AutomezzoDetailView(LoginRequiredMixin, DetailView):
    model = Automezzo
    template_name = "automezzi/dettaglio.html"
    context_object_name = "automezzo"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        a = self.object
        from django.contrib.contenttypes.models import ContentType
        ctx["edit_url"] = reverse_lazy("automezzi:automezzo_update", kwargs={"pk": a.pk})
        ctx["delete_url"] = reverse_lazy("automezzi:automezzo_delete", kwargs={"pk": a.pk})
        ctx["back_url"] = reverse_lazy("automezzi:automezzo_list")
        ctx["today"] = date.today()
        ctx["content_type_id"] = ContentType.objects.get_for_model(Automezzo).pk
        ctx["object_id"] = a.pk
        if a.data_scadenza_assicurazione:
            delta = (a.data_scadenza_assicurazione - date.today()).days
            ctx["giorni_assicurazione"] = delta
            if delta < 0:
                ctx["urgenza_assicurazione"] = "scaduta"
            elif delta <= 30:
                ctx["urgenza_assicurazione"] = "urgente"
            elif delta <= 60:
                ctx["urgenza_assicurazione"] = "in_scadenza"
            else:
                ctx["urgenza_assicurazione"] = "ok"

        # Contenuto extra di settore (scorte/attrezzature) — automezzi resta
        # un'app standard che non conosce magazzino: se il modulo e' attivo
        # e installato, il context extra arriva da un hook opzionale.
        # Vedi magazzino/hooks.py::automezzo_detail_extra(). magazzino_attivo
        # e' un flag esplicito (non basato sulla presenza/vuotezza dei dati)
        # cosi' il template sa se deve mostrare la sezione o no.
        ctx["magazzino_attivo"] = False
        try:
            from core.module_gating import is_module_active
            if is_module_active("magazzino"):
                from magazzino.hooks import automezzo_detail_extra
                ctx.update(automezzo_detail_extra(a, self.request))
                ctx["magazzino_attivo"] = True
        except ImportError:
            pass

        return ctx


class AutomezzoCreateView(LoginRequiredMixin, CreateView):
    model = Automezzo
    form_class = AutomezzoForm
    template_name = "automezzi/form.html"
    success_url = reverse_lazy("automezzi:automezzo_list")


class AutomezzoUpdateView(LoginRequiredMixin, UpdateView):
    model = Automezzo
    form_class = AutomezzoForm
    template_name = "automezzi/form.html"
    success_url = reverse_lazy("automezzi:automezzo_list")


class AutomezzoDeleteView(LoginRequiredMixin, DeleteView):
    model = Automezzo
    template_name = "automezzi/conferma_elimina.html"
    success_url = reverse_lazy("automezzi:automezzo_list")


# ============================================================
# MANUTENZIONI
# ============================================================

class ManutenzioneListView(LoginRequiredMixin, ListView):
    model = Manutenzione
    template_name = "automezzi/manutenzioni/list.html"
    context_object_name = "manutenzioni"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("automezzo", "responsabile")
        pk = self.kwargs.get("automezzo_pk")
        if pk:
            qs = qs.filter(automezzo_id=pk)
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(
                db_models.Q(automezzo__targa__icontains=q) | db_models.Q(descrizione__icontains=q)
            )
        stato = self.request.GET.get("stato", "")
        if stato:
            qs = qs.filter(stato=stato)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["stato_filter"] = self.request.GET.get("stato", "")
        ctx["stato_choices"] = Manutenzione.STATO_CHOICES
        return ctx


class ManutenzioneDetailView(LoginRequiredMixin, SidebarQrAllegatiMixin, DetailView):
    model = Manutenzione
    template_name = "automezzi/manutenzioni/dettaglio.html"
    context_object_name = "manutenzione"

    def get_context_data(self, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        ctx = super().get_context_data(**kwargs)
        m = self.object
        ctx["edit_url"] = reverse_lazy("automezzi:manutenzione_update", kwargs={"pk": m.pk})
        ctx["back_url"] = reverse_lazy("automezzi:manutenzione_list")
        ctx["utenti_attivi"] = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        return ctx


class ManutenzioneCreateView(LoginRequiredMixin, CreateView):
    model = Manutenzione
    form_class = ManutenzioneCreateForm
    template_name = "automezzi/manutenzioni/form.html"

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get("automezzo_pk")
        if pk:
            initial["automezzo"] = pk
        return initial

    def form_valid(self, form):
        form.instance.seguito_da = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("automezzi:manutenzione_list")


class ManutenzioneUpdateView(LoginRequiredMixin, UpdateView):
    model = Manutenzione
    form_class = ManutenzioneUpdateForm
    template_name = "automezzi/manutenzioni/form.html"
    success_url = reverse_lazy("automezzi:manutenzione_list")


class ManutenzioneDeleteView(LoginRequiredMixin, DeleteView):
    model = Manutenzione
    template_name = "automezzi/manutenzioni/conferma_elimina.html"
    success_url = reverse_lazy("automezzi:manutenzione_list")


class ManutenzioneResponsabileView(LoginRequiredMixin, UpdateView):
    model = Manutenzione
    form_class = ManutenzioneResponsabileForm
    template_name = "automezzi/manutenzioni/form_responsabile.html"

    def get_queryset(self):
        return super().get_queryset().filter(stato="aperta")

    def form_valid(self, form):
        form.instance.data_inizio_manutenzione = timezone.now()
        form.instance.stato = "in_corso"
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("automezzi:manutenzione_detail", kwargs={"pk": self.object.pk})


class ManutenzioneFinaleView(LoginRequiredMixin, UpdateView):
    model = Manutenzione
    form_class = ManutenzioneFinaleForm
    template_name = "automezzi/manutenzioni/form_finale.html"

    def get_queryset(self):
        return super().get_queryset().filter(stato="in_corso")

    def form_valid(self, form):
        form.instance.data_completamento = timezone.now()
        form.instance.stato = "terminata"
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("automezzi:manutenzione_detail", kwargs={"pk": self.object.pk})


class AllegatoManutenzioneCreateView(LoginRequiredMixin, CreateView):
    model = AllegatoManutenzione
    form_class = AllegatoManutenzioneForm
    template_name = "automezzi/manutenzioni/allegato_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["manutenzione"] = get_object_or_404(Manutenzione, pk=self.kwargs["manutenzione_pk"])
        return ctx

    def form_valid(self, form):
        form.instance.manutenzione = get_object_or_404(Manutenzione, pk=self.kwargs["manutenzione_pk"])
        form.instance.caricato_da = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("automezzi:manutenzione_detail", kwargs={"pk": self.kwargs["manutenzione_pk"]})


@login_required
def manutenzione_prendi_carico_inline(request, pk):
    manutenzione = get_object_or_404(Manutenzione, pk=pk, stato="aperta")
    if request.method != "POST":
        return redirect("automezzi:manutenzione_detail", pk=pk)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    km_str = request.POST.get("km_consegna", "").strip()
    responsabile_id = request.POST.get("responsabile", "").strip()
    note = request.POST.get("note_responsabile", "").strip()
    foglio = request.FILES.get("foglio_accettazione")
    if km_str:
        try:
            manutenzione.km_consegna = int(km_str)
        except ValueError:
            pass
    if responsabile_id:
        try:
            manutenzione.responsabile = User.objects.get(pk=int(responsabile_id))
        except (ValueError, User.DoesNotExist):
            pass
    manutenzione.note_responsabile = note
    manutenzione.stato = "in_corso"
    manutenzione.data_inizio_manutenzione = timezone.now()
    if foglio:
        manutenzione.foglio_accettazione = foglio
    manutenzione.save()
    messages.success(request, "Mezzo consegnato. Manutenzione in corso.")
    return redirect("automezzi:manutenzione_detail", pk=pk)


@login_required
def manutenzione_completa_inline(request, pk):
    manutenzione = get_object_or_404(Manutenzione, pk=pk, stato="in_corso")
    if request.method != "POST":
        return redirect("automezzi:manutenzione_detail", pk=pk)
    note_finali = request.POST.get("note_finali", "").strip()
    costo_str = request.POST.get("costo", "").strip()
    fattura = request.FILES.get("fattura_fornitore")
    manutenzione.note_finali = note_finali
    if costo_str:
        try:
            manutenzione.costo = Decimal(costo_str)
        except Exception:
            pass
    manutenzione.stato = "terminata"
    manutenzione.data_completamento = timezone.now()
    if fattura:
        manutenzione.fattura_fornitore = fattura
    manutenzione.save()
    messages.success(request, "Manutenzione completata.")
    return redirect("automezzi:manutenzione_detail", pk=pk)


# ============================================================
# RIFORNIMENTI
# ============================================================

class RifornimentoListView(LoginRequiredMixin, ListView):
    model = Rifornimento
    template_name = "automezzi/rifornimenti/list.html"
    context_object_name = "rifornimenti"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("automezzo")
        pk = self.kwargs.get("automezzo_pk")
        if pk:
            qs = qs.filter(automezzo_id=pk)
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(automezzo__targa__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class RifornimentoDetailView(LoginRequiredMixin, SidebarQrAllegatiMixin, DetailView):
    model = Rifornimento
    template_name = "automezzi/rifornimenti/dettaglio.html"
    context_object_name = "rifornimento"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["edit_url"] = reverse_lazy("automezzi:rifornimento_update", kwargs={"pk": self.object.pk})
        ctx["delete_url"] = reverse_lazy("automezzi:rifornimento_delete", kwargs={"pk": self.object.pk})
        ctx["back_url"] = reverse_lazy("automezzi:rifornimento_list")
        return ctx


class RifornimentoCreateView(LoginRequiredMixin, CreateView):
    model = Rifornimento
    form_class = RifornimentoForm
    template_name = "automezzi/rifornimenti/form.html"

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get("automezzo_pk")
        if pk:
            initial["automezzo"] = pk
        return initial

    def get_success_url(self):
        return reverse_lazy("automezzi:rifornimento_list")


class RifornimentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Rifornimento
    form_class = RifornimentoForm
    template_name = "automezzi/rifornimenti/form.html"
    success_url = reverse_lazy("automezzi:rifornimento_list")


class RifornimentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Rifornimento
    template_name = "automezzi/rifornimenti/conferma_elimina.html"
    success_url = reverse_lazy("automezzi:rifornimento_list")


# ============================================================
# EVENTI
# ============================================================

class EventoListView(LoginRequiredMixin, ListView):
    model = EventoAutomezzo
    template_name = "automezzi/eventi/list.html"
    context_object_name = "eventi"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("automezzo", "dipendente_coinvolto")
        pk = self.kwargs.get("automezzo_pk")
        if pk:
            qs = qs.filter(automezzo_id=pk)
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(automezzo__targa__icontains=q)
        tipo = self.request.GET.get("tipo", "")
        if tipo:
            qs = qs.filter(tipo=tipo)
        risolto = self.request.GET.get("risolto", "")
        if risolto == "si":
            qs = qs.filter(risolto=True)
        elif risolto == "no":
            qs = qs.filter(risolto=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["tipo_filter"] = self.request.GET.get("tipo", "")
        ctx["risolto_filter"] = self.request.GET.get("risolto", "")
        ctx["tipo_choices"] = EventoAutomezzo.TIPO_EVENTO_CHOICES
        return ctx


class EventoDetailView(LoginRequiredMixin, SidebarQrAllegatiMixin, DetailView):
    model = EventoAutomezzo
    template_name = "automezzi/eventi/dettaglio.html"
    context_object_name = "evento"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["edit_url"] = reverse_lazy("automezzi:evento_update", kwargs={"pk": self.object.pk})
        ctx["delete_url"] = reverse_lazy("automezzi:evento_delete", kwargs={"pk": self.object.pk})
        ctx["back_url"] = reverse_lazy("automezzi:evento_list")
        return ctx


class EventoCreateView(LoginRequiredMixin, CreateView):
    model = EventoAutomezzo
    form_class = EventoAutomezzoForm
    template_name = "automezzi/eventi/form.html"

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get("automezzo_pk")
        if pk:
            initial["automezzo"] = pk
        return initial

    def get_success_url(self):
        return reverse_lazy("automezzi:evento_list")


class EventoUpdateView(LoginRequiredMixin, UpdateView):
    model = EventoAutomezzo
    form_class = EventoAutomezzoForm
    template_name = "automezzi/eventi/form.html"
    success_url = reverse_lazy("automezzi:evento_list")


class EventoDeleteView(LoginRequiredMixin, DeleteView):
    model = EventoAutomezzo
    template_name = "automezzi/eventi/conferma_elimina.html"
    success_url = reverse_lazy("automezzi:evento_list")
