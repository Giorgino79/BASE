from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db import models as db_models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    Automezzo, Manutenzione, AllegatoManutenzione,
    Rifornimento, EventoAutomezzo,
    Stabilimento, CostiStabilimento, DocStabilimento,
)
from .forms import (
    AutomezzoForm,
    ManutenzioneCreateForm, ManutenzioneUpdateForm,
    ManutenzioneResponsabileForm, ManutenzioneFinaleForm,
    AllegatoManutenzioneForm,
    RifornimentoForm, EventoAutomezzoForm,
    StabilimentoForm, CostiStabilimentoForm, UtenzaForm,
    DocStabilimentoForm, StabilimentiSearchForm, CostiSearchForm,
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
    template_name = "cespiti/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        ctx["automezzi_count"] = Automezzo.objects.count()
        ctx["automezzi_attivi"] = Automezzo.objects.filter(attivo=True).count()
        ctx["automezzi_disponibili"] = Automezzo.objects.filter(attivo=True, disponibile=True, bloccata=False).count()
        ctx["manutenzioni_aperte"] = Manutenzione.objects.filter(stato="aperta").count()
        ctx["manutenzioni_in_corso"] = Manutenzione.objects.filter(stato="in_corso").count()
        ctx["stabilimenti_count"] = Stabilimento.objects.count()
        ctx["stabilimenti_attivi"] = Stabilimento.objects.filter(attivo=True).count()
        ctx["scadenze_urgenti"] = CostiStabilimento.objects.filter(
            data_scadenza_servizio__gte=today,
            data_scadenza_servizio__lte=today + timedelta(days=7),
        ).count()
        ctx["ultimi_rifornimenti"] = Rifornimento.objects.select_related("automezzo").order_by("-data")[:5]
        ctx["eventi_recenti"] = EventoAutomezzo.objects.select_related("automezzo").filter(risolto=False).order_by("-data_evento")[:5]
        return ctx


# ============================================================
# AUTOMEZZI
# ============================================================

class AutomezzoListView(LoginRequiredMixin, ListView):
    model = Automezzo
    template_name = "cespiti/automezzi/list.html"
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
    template_name = "cespiti/automezzi/dettaglio.html"
    context_object_name = "automezzo"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        a = self.object
        from datetime import date
        from django.contrib.contenttypes.models import ContentType
        ctx["edit_url"] = reverse_lazy("cespiti:automezzo_update", kwargs={"pk": a.pk})
        ctx["delete_url"] = reverse_lazy("cespiti:automezzo_delete", kwargs={"pk": a.pk})
        ctx["back_url"] = reverse_lazy("cespiti:automezzo_list")
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

        # Scorte a bordo
        from magazzino.models import ScortaMezzo
        scorte = list(
            ScortaMezzo.objects.filter(mezzo=a)
            .select_related("prodotto")
            .order_by("prodotto__nome_prodotto")
        )
        ctx["scorte"] = scorte

        # Fabbisogno dalle distinte aperte: ConsumoMateriale confermato=False
        try:
            from django.db.models import Sum
            from servizi.models import Distinta, ConsumoMateriale
            distinte_aperte = Distinta.objects.filter(mezzo=a, stato=Distinta.Stato.APERTA)
            fabbisogno_qs = (
                ConsumoMateriale.objects
                .filter(riga__ods__distinta__in=distinte_aperte, confermato=False)
                .values("prodotto__pk", "prodotto__nome_prodotto", "prodotto__unita_misura")
                .annotate(totale=Sum("quantita"))
                .order_by("prodotto__nome_prodotto")
            )
            scorte_map = {s.prodotto_id: s.quantita for s in scorte}
            fabbisogno = []
            for row in fabbisogno_qs:
                pid = row["prodotto__pk"]
                disponibile = scorte_map.get(pid)
                fabbisogno.append({
                    "nome": row["prodotto__nome_prodotto"],
                    "um": row["prodotto__unita_misura"] or "",
                    "necessario": row["totale"],
                    "disponibile": disponibile,
                    "mancante": disponibile is None or disponibile < row["totale"],
                })
            ctx["fabbisogno"] = fabbisogno
        except Exception:
            ctx["fabbisogno"] = []

        return ctx


class AutomezzoCreateView(LoginRequiredMixin, CreateView):
    model = Automezzo
    form_class = AutomezzoForm
    template_name = "cespiti/automezzi/form.html"
    success_url = reverse_lazy("cespiti:automezzo_list")


class AutomezzoUpdateView(LoginRequiredMixin, UpdateView):
    model = Automezzo
    form_class = AutomezzoForm
    template_name = "cespiti/automezzi/form.html"
    success_url = reverse_lazy("cespiti:automezzo_list")


class AutomezzoDeleteView(LoginRequiredMixin, DeleteView):
    model = Automezzo
    template_name = "cespiti/automezzi/conferma_elimina.html"
    success_url = reverse_lazy("cespiti:automezzo_list")


# ============================================================
# MANUTENZIONI
# ============================================================

class ManutenzioneListView(LoginRequiredMixin, ListView):
    model = Manutenzione
    template_name = "cespiti/manutenzioni/list.html"
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
    template_name = "cespiti/manutenzioni/dettaglio.html"
    context_object_name = "manutenzione"

    def get_context_data(self, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        ctx = super().get_context_data(**kwargs)
        m = self.object
        ctx["edit_url"] = reverse_lazy("cespiti:manutenzione_update", kwargs={"pk": m.pk})
        ctx["back_url"] = reverse_lazy("cespiti:manutenzione_list")
        ctx["utenti_attivi"] = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        return ctx


class ManutenzioneCreateView(LoginRequiredMixin, CreateView):
    model = Manutenzione
    form_class = ManutenzioneCreateForm
    template_name = "cespiti/manutenzioni/form.html"

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
        return reverse_lazy("cespiti:manutenzione_list")


class ManutenzioneUpdateView(LoginRequiredMixin, UpdateView):
    model = Manutenzione
    form_class = ManutenzioneUpdateForm
    template_name = "cespiti/manutenzioni/form.html"
    success_url = reverse_lazy("cespiti:manutenzione_list")


class ManutenzioneDeleteView(LoginRequiredMixin, DeleteView):
    model = Manutenzione
    template_name = "cespiti/manutenzioni/conferma_elimina.html"
    success_url = reverse_lazy("cespiti:manutenzione_list")


class ManutenzioneResponsabileView(LoginRequiredMixin, UpdateView):
    model = Manutenzione
    form_class = ManutenzioneResponsabileForm
    template_name = "cespiti/manutenzioni/form_responsabile.html"

    def get_queryset(self):
        return super().get_queryset().filter(stato="aperta")

    def form_valid(self, form):
        form.instance.data_inizio_manutenzione = timezone.now()
        form.instance.stato = "in_corso"
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("cespiti:manutenzione_detail", kwargs={"pk": self.object.pk})


class ManutenzioneFinaleView(LoginRequiredMixin, UpdateView):
    model = Manutenzione
    form_class = ManutenzioneFinaleForm
    template_name = "cespiti/manutenzioni/form_finale.html"

    def get_queryset(self):
        return super().get_queryset().filter(stato="in_corso")

    def form_valid(self, form):
        form.instance.data_completamento = timezone.now()
        form.instance.stato = "terminata"
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("cespiti:manutenzione_detail", kwargs={"pk": self.object.pk})


class AllegatoManutenzioneCreateView(LoginRequiredMixin, CreateView):
    model = AllegatoManutenzione
    form_class = AllegatoManutenzioneForm
    template_name = "cespiti/manutenzioni/allegato_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["manutenzione"] = get_object_or_404(Manutenzione, pk=self.kwargs["manutenzione_pk"])
        return ctx

    def form_valid(self, form):
        form.instance.manutenzione = get_object_or_404(Manutenzione, pk=self.kwargs["manutenzione_pk"])
        form.instance.caricato_da = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("cespiti:manutenzione_detail", kwargs={"pk": self.kwargs["manutenzione_pk"]})


@login_required
def manutenzione_prendi_carico_inline(request, pk):
    manutenzione = get_object_or_404(Manutenzione, pk=pk, stato="aperta")
    if request.method != "POST":
        return redirect("cespiti:manutenzione_detail", pk=pk)
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
    return redirect("cespiti:manutenzione_detail", pk=pk)


@login_required
def manutenzione_completa_inline(request, pk):
    manutenzione = get_object_or_404(Manutenzione, pk=pk, stato="in_corso")
    if request.method != "POST":
        return redirect("cespiti:manutenzione_detail", pk=pk)
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
    return redirect("cespiti:manutenzione_detail", pk=pk)


# ============================================================
# RIFORNIMENTI
# ============================================================

class RifornimentoListView(LoginRequiredMixin, ListView):
    model = Rifornimento
    template_name = "cespiti/rifornimenti/list.html"
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
    template_name = "cespiti/rifornimenti/dettaglio.html"
    context_object_name = "rifornimento"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["edit_url"] = reverse_lazy("cespiti:rifornimento_update", kwargs={"pk": self.object.pk})
        ctx["delete_url"] = reverse_lazy("cespiti:rifornimento_delete", kwargs={"pk": self.object.pk})
        ctx["back_url"] = reverse_lazy("cespiti:rifornimento_list")
        return ctx


class RifornimentoCreateView(LoginRequiredMixin, CreateView):
    model = Rifornimento
    form_class = RifornimentoForm
    template_name = "cespiti/rifornimenti/form.html"

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get("automezzo_pk")
        if pk:
            initial["automezzo"] = pk
        return initial

    def get_success_url(self):
        return reverse_lazy("cespiti:rifornimento_list")


class RifornimentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Rifornimento
    form_class = RifornimentoForm
    template_name = "cespiti/rifornimenti/form.html"
    success_url = reverse_lazy("cespiti:rifornimento_list")


class RifornimentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Rifornimento
    template_name = "cespiti/rifornimenti/conferma_elimina.html"
    success_url = reverse_lazy("cespiti:rifornimento_list")


# ============================================================
# EVENTI
# ============================================================

class EventoListView(LoginRequiredMixin, ListView):
    model = EventoAutomezzo
    template_name = "cespiti/eventi/list.html"
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
    template_name = "cespiti/eventi/dettaglio.html"
    context_object_name = "evento"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["edit_url"] = reverse_lazy("cespiti:evento_update", kwargs={"pk": self.object.pk})
        ctx["delete_url"] = reverse_lazy("cespiti:evento_delete", kwargs={"pk": self.object.pk})
        ctx["back_url"] = reverse_lazy("cespiti:evento_list")
        return ctx


class EventoCreateView(LoginRequiredMixin, CreateView):
    model = EventoAutomezzo
    form_class = EventoAutomezzoForm
    template_name = "cespiti/eventi/form.html"

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get("automezzo_pk")
        if pk:
            initial["automezzo"] = pk
        return initial

    def get_success_url(self):
        return reverse_lazy("cespiti:evento_list")


class EventoUpdateView(LoginRequiredMixin, UpdateView):
    model = EventoAutomezzo
    form_class = EventoAutomezzoForm
    template_name = "cespiti/eventi/form.html"
    success_url = reverse_lazy("cespiti:evento_list")


class EventoDeleteView(LoginRequiredMixin, DeleteView):
    model = EventoAutomezzo
    template_name = "cespiti/eventi/conferma_elimina.html"
    success_url = reverse_lazy("cespiti:evento_list")


# ============================================================
# STABILIMENTI
# ============================================================

@login_required
def stabilimento_list(request):
    form = StabilimentiSearchForm(request.GET or None)
    qs = Stabilimento.objects.select_related("responsabile_operativo", "responsabile_amministrativo")
    if form.is_valid():
        q = form.cleaned_data.get("q")
        if q:
            qs = qs.filter(
                db_models.Q(nome__icontains=q) | db_models.Q(codice_stabilimento__icontains=q)
                | db_models.Q(citta__icontains=q)
            )
        provincia = form.cleaned_data.get("provincia")
        if provincia:
            qs = qs.filter(provincia__iexact=provincia)
        attivo = form.cleaned_data.get("attivo")
        if attivo == "true":
            qs = qs.filter(attivo=True)
        elif attivo == "false":
            qs = qs.filter(attivo=False)
    qs = qs.order_by("nome")
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    stats = {
        "totali": Stabilimento.objects.count(),
        "attivi": Stabilimento.objects.filter(attivo=True).count(),
        "con_scadenze": Stabilimento.objects.con_scadenze_prossime().count(),
    }
    return render(request, "cespiti/stabilimenti/list.html", {"form": form, "page_obj": page_obj, "stats": stats})


@login_required
def stabilimento_create(request):
    if request.method == "POST":
        form = StabilimentoForm(request.POST, user=request.user)
        if form.is_valid():
            stab = form.save(commit=False)
            stab.creato_da = request.user
            stab.modificato_da = request.user
            stab.save()
            messages.success(request, f'Stabilimento "{stab.nome}" creato.')
            return redirect("cespiti:stabilimento_detail", pk=stab.pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = StabilimentoForm(user=request.user)
    return render(request, "cespiti/stabilimenti/form.html", {"form": form, "action": "Nuovo Stabilimento"})


@login_required
def stabilimento_detail(request, pk):
    stab = get_object_or_404(
        Stabilimento.objects.select_related("responsabile_operativo", "responsabile_amministrativo", "creato_da"),
        pk=pk,
    )
    costi_recenti = stab.costi.select_related("fornitore").order_by("-data_creazione")[:5]
    documenti_recenti = stab.documenti.order_by("-data_inserimento")[:5]
    scadenze_prossime = stab.get_prossime_scadenze(30)
    costi_anno = stab.get_costi_anno_corrente()
    from django.contrib.contenttypes.models import ContentType
    return render(request, "cespiti/stabilimenti/dettaglio.html", {
        "stabilimento": stab,
        "object": stab,
        "costi_recenti": costi_recenti,
        "documenti_recenti": documenti_recenti,
        "scadenze_prossime": scadenze_prossime,
        "costi_anno": costi_anno,
        "edit_url": reverse("cespiti:stabilimento_update", kwargs={"pk": pk}),
        "back_url": reverse("cespiti:stabilimento_list"),
        "content_type_id": ContentType.objects.get_for_model(Stabilimento).pk,
        "object_id": stab.pk,
    })


@login_required
def stabilimento_update(request, pk):
    stab = get_object_or_404(Stabilimento, pk=pk)
    if request.method == "POST":
        form = StabilimentoForm(request.POST, instance=stab, user=request.user)
        if form.is_valid():
            s = form.save(commit=False)
            s.modificato_da = request.user
            s.save()
            messages.success(request, f'Stabilimento "{stab.nome}" modificato.')
            return redirect("cespiti:stabilimento_detail", pk=pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = StabilimentoForm(instance=stab, user=request.user)
    return render(request, "cespiti/stabilimenti/form.html", {
        "form": form, "stabilimento": stab, "action": f"Modifica {stab.nome}",
    })


@login_required
def toggle_attivo_stabilimento(request, pk):
    if request.method != "POST":
        return JsonResponse({"success": False})
    stab = get_object_or_404(Stabilimento, pk=pk)
    stab.attivo = not stab.attivo
    stab.data_chiusura = None if stab.attivo else timezone.now().date()
    stab.modificato_da = request.user
    stab.save()
    stato = "attivato" if stab.attivo else "disattivato"
    messages.success(request, f"Stabilimento {stato}.")
    return JsonResponse({"success": True, "attivo": stab.attivo})


# ============================================================
# COSTI STABILIMENTO
# ============================================================

@login_required
def costo_list(request):
    form = CostiSearchForm(request.GET or None)
    qs = CostiStabilimento.objects.select_related("stabilimento", "fornitore", "incaricato")
    if form.is_valid():
        stab = form.cleaned_data.get("stabilimento")
        if stab:
            qs = qs.filter(stabilimento=stab)
        causale = form.cleaned_data.get("causale")
        if causale:
            qs = qs.filter(causale=causale)
        stato = form.cleaned_data.get("stato")
        if stato:
            qs = qs.filter(stato=stato)
        anno = form.cleaned_data.get("anno")
        if anno:
            qs = qs.filter(data_fattura__year=anno)
        if form.cleaned_data.get("scadenze_prossime"):
            qs = qs.scadenze_prossime()
    qs = qs.order_by("-data_creazione")
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "cespiti/costi/list.html", {"form": form, "page_obj": page_obj})


@login_required
def costo_create(request, stabilimento_pk):
    stab = get_object_or_404(Stabilimento, pk=stabilimento_pk)
    if request.method == "POST":
        form = CostiStabilimentoForm(request.POST, request.FILES, user=request.user, stabilimento=stab)
        if form.is_valid():
            costo = form.save(commit=False)
            costo.incaricato = request.user
            costo.save()
            messages.success(request, f'Costo "{costo.titolo}" creato.')
            return redirect("cespiti:stabilimento_detail", pk=stab.pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = CostiStabilimentoForm(user=request.user, stabilimento=stab)
    return render(request, "cespiti/costi/form.html", {"form": form, "stabilimento": stab, "action": "Nuovo Costo"})


@login_required
def costo_detail(request, pk):
    costo = get_object_or_404(
        CostiStabilimento.objects.select_related("stabilimento", "fornitore", "incaricato"),
        pk=pk,
    )
    from django.contrib.contenttypes.models import ContentType
    return render(request, "cespiti/costi/dettaglio.html", {
        "costo": costo,
        "object": costo,
        "edit_url": reverse("cespiti:costo_update", kwargs={"pk": pk}) if costo.can_be_modified() else None,
        "back_url": reverse("cespiti:costo_list"),
        "content_type_id": ContentType.objects.get_for_model(CostiStabilimento).pk,
        "object_id": costo.pk,
    })


@login_required
def costo_update(request, pk):
    costo = get_object_or_404(CostiStabilimento, pk=pk)
    if not costo.can_be_modified():
        messages.error(request, "Non è possibile modificare un costo già pagato")
        return redirect("cespiti:costo_detail", pk=pk)
    if request.method == "POST":
        form = CostiStabilimentoForm(request.POST, request.FILES, instance=costo, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Costo "{costo.titolo}" modificato.')
            return redirect("cespiti:costo_detail", pk=pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = CostiStabilimentoForm(instance=costo, user=request.user)
    return render(request, "cespiti/costi/form.html", {"form": form, "costo": costo, "action": f"Modifica {costo.numero_pratica}"})


# ============================================================
# UTENZE
# ============================================================

UTENZE_TYPES = ["energia_elettrica", "gas_naturale", "acqua", "telefonia", "rifiuti"]


@login_required
def utenza_create(request, stabilimento_pk):
    stab = get_object_or_404(Stabilimento, pk=stabilimento_pk)
    if request.method == "POST":
        form = UtenzaForm(request.POST, request.FILES, user=request.user, stabilimento=stab)
        if form.is_valid():
            utenza = form.save(commit=False)
            utenza.incaricato = request.user
            utenza.save()
            messages.success(request, f'Utenza "{utenza.titolo}" creata.')
            return redirect("cespiti:stabilimento_detail", pk=stab.pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = UtenzaForm(user=request.user, stabilimento=stab)
    return render(request, "cespiti/costi/utenza_form.html", {"form": form, "stabilimento": stab})


@login_required
def utenza_update(request, pk):
    utenza = get_object_or_404(CostiStabilimento, pk=pk)
    if utenza.causale not in UTENZE_TYPES:
        messages.error(request, "Questo costo non è un'utenza")
        return redirect("cespiti:costo_detail", pk=pk)
    if not utenza.can_be_modified():
        messages.error(request, "Non è possibile modificare un'utenza già pagata")
        return redirect("cespiti:costo_detail", pk=pk)
    if request.method == "POST":
        form = UtenzaForm(request.POST, request.FILES, instance=utenza, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Utenza modificata.")
            return redirect("cespiti:costo_detail", pk=pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = UtenzaForm(instance=utenza, user=request.user)
    return render(request, "cespiti/costi/utenza_form.html", {"form": form, "utenza": utenza, "stabilimento": utenza.stabilimento})


# ============================================================
# DOCUMENTI
# ============================================================

@login_required
def documento_list(request, stabilimento_pk):
    stab = get_object_or_404(Stabilimento, pk=stabilimento_pk)
    documenti = stab.documenti.order_by("-data_inserimento")
    paginator = Paginator(documenti, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "cespiti/documenti/list.html", {"stabilimento": stab, "page_obj": page_obj})


@login_required
def documento_create(request, stabilimento_pk):
    stab = get_object_or_404(Stabilimento, pk=stabilimento_pk)
    if request.method == "POST":
        form = DocStabilimentoForm(request.POST, request.FILES, user=request.user, stabilimento=stab)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.stabilimento = stab
            doc.caricato_da = request.user
            doc.save()
            messages.success(request, f'Documento "{doc.nome_documento}" caricato.')
            return redirect("cespiti:documento_list", stabilimento_pk=stab.pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = DocStabilimentoForm(user=request.user, stabilimento=stab)
    return render(request, "cespiti/documenti/form.html", {"form": form, "stabilimento": stab})


# ============================================================
# SCADENZE
# ============================================================

@login_required
def scadenze_dashboard(request):
    oggi = timezone.now().date()
    scadute = DocStabilimento.objects.filter(data_scadenza__lt=oggi, attivo=True).select_related("stabilimento")
    questa_settimana = DocStabilimento.objects.filter(
        data_scadenza__gte=oggi, data_scadenza__lte=oggi + timedelta(days=7), attivo=True,
    ).select_related("stabilimento")
    prossimi_30 = DocStabilimento.objects.filter(
        data_scadenza__gt=oggi + timedelta(days=7), data_scadenza__lte=oggi + timedelta(days=30), attivo=True,
    ).select_related("stabilimento")
    scadenze_costi_urgenti = CostiStabilimento.objects.filter(
        data_scadenza_servizio__gte=oggi, data_scadenza_servizio__lte=oggi + timedelta(days=30),
    ).select_related("stabilimento")
    return render(request, "cespiti/scadenze.html", {
        "scadute": scadute,
        "questa_settimana": questa_settimana,
        "prossimi_30": prossimi_30,
        "scadenze_costi_urgenti": scadenze_costi_urgenti,
        "oggi": oggi,
    })
