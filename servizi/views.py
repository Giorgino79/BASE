from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Servizio, Contratto, ContrattoFiliale, ContrattoFilialeRiga, ContrattoRiga, ODS, ODSRiga, Distinta, ConsumoMateriale, CondominioODS, RigaUnitaAbitativa, RigaProdottoCondominio
from .forms import (
    ServizioForm, ContrattoForm, ContrattoRigaFormSet, ContrattoFilialeRigaFormSet,
    ODSForm, ODSRigaFormSet,
    ConsumoMaterialeForm, ChiudiServizioForm, ProdottoPrevitoForm,
    CondominioODSForm, RigaUnitaAbitativaFormSet, RigaProdottoCondominioFormSet,
    RigaUnitaAbitativaEseguiFormSet, RigaProdottoCondominioEseguiFormSet,
)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    oggi = timezone.now()
    ctx = {
        "servizi_attivi":      Servizio.objects.filter(attivo=True).count(),
        "contratti_attivi":    Contratto.objects.filter(stato="attivo").count(),
        "ods_programmati":     ODS.objects.filter(stato__in=["da_espletare", "programmato"]).count(),
        "ods_completati_mese": ODS.objects.filter(
            stato="completato",
            data_servizio__year=oggi.year,
            data_servizio__month=oggi.month,
        ).count(),
        "ods_da_incassare": ODS.objects.filter(incasso_al_servizio=True, incassato=False, stato="completato").count(),
        "ultimi_ods": ODS.objects.select_related(
            "filiale__cliente", "privato", "tecnico"
        ).prefetch_related("righe__servizio").order_by("-created_at")[:8],
    }
    return render(request, "servizi/dashboard.html", ctx)


# ── Servizi ───────────────────────────────────────────────────────────────────

class ServizioListView(LoginRequiredMixin, ListView):
    model = Servizio
    template_name = "servizi/servizi/list.html"
    context_object_name = "servizi"

    def get_queryset(self):
        qs = Servizio.objects.all()
        if self.request.GET.get("stato", "attivi") == "attivi":
            qs = qs.filter(attivo=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stato_sel"] = self.request.GET.get("stato", "attivi")
        return ctx


class ServizioDetailView(LoginRequiredMixin, DetailView):
    model = Servizio
    template_name = "servizi/servizi/detail.html"
    context_object_name = "servizio"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["contratto_righe"] = (
            ContrattoRiga.objects.filter(servizio=self.object, contratto__stato="attivo")
            .select_related("contratto__cliente")
            .order_by("-contratto__created_at")
        )
        ctx["back_url"] = reverse("servizi:servizio_list")
        ctx["edit_url"] = reverse("servizi:servizio_update", kwargs={"pk": self.object.pk})
        ctx["content_type_id"] = ContentType.objects.get_for_model(Servizio).pk
        ctx["object_id"] = self.object.pk
        return ctx


class ServizioCreateView(LoginRequiredMixin, CreateView):
    model = Servizio
    form_class = ServizioForm
    template_name = "servizi/servizi/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = "Nuovo Servizio"
        ctx["back_url"] = reverse("servizi:servizio_list")
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"Servizio «{form.instance.nome}» creato.")
        return super().form_valid(form)


class ServizioUpdateView(LoginRequiredMixin, UpdateView):
    model = Servizio
    form_class = ServizioForm
    template_name = "servizi/servizi/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = f"Modifica: {self.object.nome}"
        ctx["back_url"] = self.object.get_absolute_url()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"Servizio «{form.instance.nome}» aggiornato.")
        return super().form_valid(form)


class ServizioDeleteView(LoginRequiredMixin, DeleteView):
    model = Servizio
    template_name = "servizi/servizi/confirm_delete.html"
    success_url = reverse_lazy("servizi:servizio_list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Solo gli amministratori possono eliminare i servizi.")
            return redirect("servizi:servizio_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Servizio «{self.object.nome}» eliminato.")
        return super().form_valid(form)


# ── Contratti ─────────────────────────────────────────────────────────────────

class ContrattoListView(LoginRequiredMixin, ListView):
    model = Contratto
    template_name = "servizi/contratti/list.html"
    context_object_name = "contratti"
    paginate_by = 25

    def get_queryset(self):
        qs = Contratto.objects.select_related("cliente").prefetch_related("righe__servizio").order_by("-created_at")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(cliente__ragione_sociale__icontains=q) | Q(righe__servizio__nome__icontains=q)
            ).distinct()
        stato = self.request.GET.get("stato", "attivo")
        if stato:
            qs = qs.filter(stato=stato)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stato_choices"] = Contratto.Stato.choices
        ctx["stato_sel"] = self.request.GET.get("stato", "attivo")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class ContrattoDetailView(LoginRequiredMixin, DetailView):
    model = Contratto
    template_name = "servizi/contratti/detail.html"
    context_object_name = "contratto"

    def get_queryset(self):
        return Contratto.objects.select_related(
            "cliente", "created_by"
        ).prefetch_related("righe__servizio", "filiali_contratto__filiale")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["back_url"] = reverse("servizi:contratto_list")
        ctx["edit_url"] = reverse("servizi:contratto_update", kwargs={"pk": self.object.pk})
        ctx["content_type_id"] = ContentType.objects.get_for_model(Contratto).pk
        ctx["object_id"] = self.object.pk
        ctx["righe"] = self.object.righe.select_related("servizio")
        ctx["filiali"] = self.object.filiali_contratto.select_related("filiale").order_by("filiale__nome")
        return ctx


class ContrattoCreateView(LoginRequiredMixin, CreateView):
    model = Contratto
    form_class = ContrattoForm
    template_name = "servizi/contratti/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = "Nuovo Contratto"
        ctx["back_url"] = reverse("servizi:contratto_list")
        if "righe_fs" not in ctx:
            ctx["righe_fs"] = ContrattoRigaFormSet(prefix="righe")
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        righe_fs = ContrattoRigaFormSet(request.POST, prefix="righe")
        if form.is_valid() and righe_fs.is_valid():
            form.instance.created_by = request.user
            self.object = form.save()
            righe_fs.instance = self.object
            righe_fs.save()
            filiali = self.object.cliente.filiali.filter(attivo=True)
            for f in filiali:
                ContrattoFiliale.objects.get_or_create(contratto=self.object, filiale=f)
            n = filiali.count()
            messages.success(request, f"Contratto creato e applicato a {n} sede{'i' if n != 1 else ''}.")
            return redirect(self.object.get_absolute_url())
        ctx = self.get_context_data(form=form, righe_fs=righe_fs)
        return self.render_to_response(ctx)


class ContrattoUpdateView(LoginRequiredMixin, UpdateView):
    model = Contratto
    form_class = ContrattoForm
    template_name = "servizi/contratti/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = f"Modifica contratto — {self.object}"
        ctx["back_url"] = self.object.get_absolute_url()
        if "righe_fs" not in ctx:
            ctx["righe_fs"] = ContrattoRigaFormSet(instance=self.object, prefix="righe")
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        righe_fs = ContrattoRigaFormSet(request.POST, instance=self.object, prefix="righe")
        if form.is_valid() and righe_fs.is_valid():
            self.object = form.save()
            righe_fs.save()
            messages.success(request, "Contratto aggiornato.")
            return redirect(self.object.get_absolute_url())
        ctx = self.get_context_data(form=form, righe_fs=righe_fs)
        return self.render_to_response(ctx)


class ContrattoDeleteView(LoginRequiredMixin, DeleteView):
    model = Contratto
    template_name = "servizi/contratti/confirm_delete.html"
    success_url = reverse_lazy("servizi:contratto_list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Solo gli amministratori possono eliminare i contratti.")
            return redirect("servizi:contratto_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Contratto eliminato.")
        return super().form_valid(form)


@login_required
def api_prezzo_contratto(request):
    """
    GET ?filiale=<pk>&servizio=<pk>
    Restituisce il prezzo dalla riga di contratto attiva per filiale+servizio, o null.
    """
    filiale_id = request.GET.get("filiale")
    servizio_id = request.GET.get("servizio")
    if not filiale_id or not servizio_id:
        return JsonResponse({"prezzo": None, "contratto_filiale_id": None})
    # Prima cerca override specifico per la sede
    sede_riga = (
        ContrattoFilialeRiga.objects.filter(
            servizio_id=servizio_id,
            contratto_filiale__filiale_id=filiale_id,
            contratto_filiale__contratto__stato="attivo",
        )
        .select_related("contratto_filiale__contratto")
        .order_by("-contratto_filiale__contratto__created_at")
        .first()
    )
    if sede_riga:
        cf = sede_riga.contratto_filiale
        return JsonResponse({"prezzo": str(sede_riga.prezzo), "contratto_filiale_id": cf.pk})

    # Fallback: prezzo base dal contratto
    riga = (
        ContrattoRiga.objects.filter(
            servizio_id=servizio_id,
            contratto__stato="attivo",
            contratto__filiali_contratto__filiale_id=filiale_id,
        )
        .select_related("contratto")
        .order_by("-contratto__created_at")
        .first()
    )
    if riga:
        cf = ContrattoFiliale.objects.filter(
            contratto=riga.contratto, filiale_id=filiale_id
        ).first()
        return JsonResponse({"prezzo": str(riga.prezzo), "contratto_filiale_id": cf.pk if cf else None})
    return JsonResponse({"prezzo": None, "contratto_filiale_id": None})


@login_required
def contratto_filiale_gestisci(request, cf_pk):
    """Gestisce prezzi override e servizi extra per una singola sede del contratto."""
    cf = get_object_or_404(ContrattoFiliale.objects.select_related("contratto__cliente", "filiale"), pk=cf_pk)
    contratto = cf.contratto
    righe_base = contratto.righe.select_related("servizio")
    servizi_base_ids = set(righe_base.values_list("servizio_id", flat=True))

    if request.method == "POST":
        fs = ContrattoFilialeRigaFormSet(request.POST, instance=cf, prefix="sede")
        if fs.is_valid():
            fs.save()
            messages.success(request, f"Prezzi per «{cf.filiale.nome}» aggiornati.")
            return redirect(contratto.get_absolute_url())
    else:
        fs = ContrattoFilialeRigaFormSet(instance=cf, prefix="sede")

    ctx = {
        "cf": cf,
        "contratto": contratto,
        "fs": fs,
        "righe_base": righe_base,
        "servizi_base_ids": servizi_base_ids,
        "righe_sede": cf.righe_sede.select_related("servizio"),
    }
    return render(request, "servizi/contratti/filiale_gestisci.html", ctx)


def contratto_pdf(request, pk):
    """Genera il PDF del contratto. View pubblica: necessario per l'invio via Green API."""
    from django.template.loader import render_to_string
    from django.utils import timezone
    from core.pdf_generator import generate_pdf_from_html, PDFConfig

    contratto = get_object_or_404(
        Contratto.objects.select_related("cliente").prefetch_related("righe__servizio"),
        pk=pk,
    )
    filiali = ContrattoFiliale.objects.filter(contratto=contratto).select_related("filiale")
    ctx = {
        "contratto": contratto,
        "righe": contratto.righe.select_related("servizio"),
        "filiali": filiali,
        "oggi": timezone.now().date(),
    }
    html = render_to_string("servizi/contratti/pdf.html", ctx, request=request)
    cliente_slug = contratto.cliente.ragione_sociale[:20].replace(" ", "_")
    return generate_pdf_from_html(
        html,
        PDFConfig(filename=f"contratto_{cliente_slug}_{contratto.pk}.pdf"),
        output_type="response",
    )


# ── ODS ───────────────────────────────────────────────────────────────────────

class ODSListView(LoginRequiredMixin, ListView):
    model = ODS
    template_name = "servizi/ods/list.html"
    context_object_name = "ods_list"
    paginate_by = 25

    def get_queryset(self):
        qs = ODS.objects.select_related(
            "filiale__cliente", "privato", "tecnico"
        ).prefetch_related("righe__servizio").order_by("-data_servizio", "-created_at")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(numero__icontains=q) |
                Q(filiale__cliente__ragione_sociale__icontains=q) |
                Q(filiale__nome__icontains=q) |
                Q(privato__cognome__icontains=q) |
                Q(privato__nome__icontains=q) |
                Q(righe__servizio__nome__icontains=q)
            ).distinct()
        stato = self.request.GET.get("stato", "")
        if stato:
            qs = qs.filter(stato=stato)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stato_choices"] = ODS.Stato.choices
        ctx["stato_sel"] = self.request.GET.get("stato", "")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class ODSDetailView(LoginRequiredMixin, DetailView):
    model = ODS
    template_name = "servizi/ods/detail.html"
    context_object_name = "ods"

    def get_queryset(self):
        return ODS.objects.select_related(
            "filiale__cliente", "privato", "tecnico", "assistente", "created_by", "distinta",
        ).prefetch_related(
            "righe__servizio", "righe__contratto_filiale__contratto",
            "righe__consumi__prodotto",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["back_url"] = reverse("servizi:ods_list")
        ctx["edit_url"] = reverse("servizi:ods_update", kwargs={"pk": self.object.pk})
        ctx["stato_choices"] = ODS.Stato.choices
        ctx["content_type_id"] = ContentType.objects.get_for_model(ODS).pk
        ctx["object_id"] = self.object.pk
        from django.contrib.auth import get_user_model
        ctx["utenti"] = get_user_model().objects.filter(is_active=True).order_by("last_name", "first_name")
        return ctx


def _salva_prodotti_previsti(request, formset):
    """
    Legge i prodotti previsti per ogni riga ODSRiga dal POST e aggiorna ConsumoMateriale
    con confermato=False (non scala stock).
    Prefix per riga N: cp-righe-N-TOTAL_FORMS, cp-righe-N-{i}-prodotto, cp-righe-N-{i}-quantita
    """
    from decimal import Decimal, InvalidOperation
    for form in formset.forms:
        if not form.instance.pk:
            continue
        if form.cleaned_data.get("DELETE"):
            continue
        riga = form.instance
        prefix = f"cp-{form.prefix}"
        total_str = request.POST.get(f"{prefix}-TOTAL_FORMS", "0")
        try:
            total = int(total_str)
        except ValueError:
            total = 0
        # Rimuove prodotti previsti esistenti
        riga.consumi.filter(confermato=False).delete()
        for i in range(total):
            if request.POST.get(f"{prefix}-{i}-DELETE"):
                continue
            prodotto_id = request.POST.get(f"{prefix}-{i}-prodotto")
            qty_str = request.POST.get(f"{prefix}-{i}-quantita", "1")
            if not prodotto_id:
                continue
            try:
                qty = Decimal(qty_str)
            except InvalidOperation:
                qty = Decimal("1")
            ConsumoMateriale.objects.create(
                riga=riga,
                prodotto_id=prodotto_id,
                quantita=qty,
                confermato=False,
            )


class ODSCreateView(LoginRequiredMixin, CreateView):
    model = ODS
    form_class = ODSForm
    template_name = "servizi/ods/form.html"

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("filiale"):
            initial["filiale"] = self.request.GET["filiale"]
        if self.request.GET.get("privato"):
            initial["privato"] = self.request.GET["privato"]
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = "Nuovo Ordine di Servizio"
        ctx["back_url"] = reverse("servizi:ods_list")
        ctx["api_prezzo_url"] = reverse("servizi:api_prezzo_contratto")
        if "formset" not in ctx:
            ctx["formset"] = ODSRigaFormSet(prefix="righe")
        from magazzino.models import Prodotto
        ctx["prodotti"] = Prodotto.objects.filter(attivo=True).order_by("nome_prodotto")
        ctx["formset_data"] = [(f, []) for f in ctx["formset"]]
        ctx["prodotto_form_vuoto"] = ProdottoPrevitoForm(prefix="__cp_prefix__")
        return ctx

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        formset = ODSRigaFormSet(self.request.POST, instance=form.instance, prefix="righe")
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            _salva_prodotti_previsti(self.request, formset)
            messages.success(self.request, f"ODS {self.object.numero} creato.")
            return redirect(self.object.get_absolute_url())
        return self.render_to_response(self.get_context_data(form=form, formset=formset))


class ODSUpdateView(LoginRequiredMixin, UpdateView):
    model = ODS
    form_class = ODSForm
    template_name = "servizi/ods/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = f"Modifica {self.object.numero}"
        ctx["back_url"] = self.object.get_absolute_url()
        ctx["api_prezzo_url"] = reverse("servizi:api_prezzo_contratto")
        if "formset" not in ctx:
            ctx["formset"] = ODSRigaFormSet(instance=self.object, prefix="righe")
        from magazzino.models import Prodotto
        ctx["prodotti"] = Prodotto.objects.filter(attivo=True).order_by("nome_prodotto")
        riga_previsti = {}
        for riga in self.object.righe.prefetch_related("consumi"):
            riga_previsti[riga.pk] = list(riga.consumi.filter(confermato=False))
        ctx["formset_data"] = [
            (f, riga_previsti.get(f.instance.pk, []))
            for f in ctx["formset"]
        ]
        ctx["prodotto_form_vuoto"] = ProdottoPrevitoForm(prefix="__cp_prefix__")
        return ctx

    def form_valid(self, form):
        formset = ODSRigaFormSet(self.request.POST, instance=self.object, prefix="righe")
        if formset.is_valid():
            self.object = form.save()
            formset.save()
            _salva_prodotti_previsti(self.request, formset)
            messages.success(self.request, f"ODS {self.object.numero} aggiornato.")
            return redirect(self.object.get_absolute_url())
        return self.render_to_response(self.get_context_data(form=form, formset=formset))


@login_required
def ods_cambia_personale(request, pk):
    """Aggiorna tecnico e assistente di un ODS senza cambiare stato."""
    ods = get_object_or_404(ODS, pk=pk)
    if request.method == "POST":
        from django.contrib.auth import get_user_model
        User = get_user_model()
        tecnico_id   = request.POST.get("tecnico") or None
        assistente_id = request.POST.get("assistente") or None
        if not tecnico_id:
            messages.error(request, "Il tecnico è obbligatorio.")
        else:
            try:
                ods.tecnico    = User.objects.get(pk=tecnico_id)
                ods.assistente = User.objects.get(pk=assistente_id) if assistente_id else None
                ods.save(update_fields=["tecnico", "assistente"])
                messages.success(request, "Tecnico e assistente aggiornati.")
            except User.DoesNotExist:
                messages.error(request, "Utente non trovato.")
    return redirect("servizi:ods_detail", pk=pk)


@login_required
def organizzazione_giri(request):
    """
    Tabella organizzazione giri: ODS + CondominioODS da_espletare.
    Sezione inferiore: giri già confermati raggruppati per tecnico.
    """
    from django.contrib.auth import get_user_model
    from itertools import groupby

    User = get_user_model()
    utenti = User.objects.filter(is_active=True).order_by("last_name", "first_name")

    # ── ODS da organizzare ────────────────────────────────────────────────────
    da_organizzare_qs = (
        ODS.objects
        .filter(stato="da_espletare")
        .select_related("filiale__cliente", "filiale", "privato", "tecnico")
        .prefetch_related("righe__servizio")
        .order_by("data_servizio", "ora_inizio")
    )
    da_organizzare_sorted = sorted(
        da_organizzare_qs,
        key=lambda o: (o.zona or "\xff", o.data_servizio.isoformat(), o.ora_inizio.isoformat() if o.ora_inizio else ""),
    )
    gruppi_da_organizzare = []
    for (zona, data), items in groupby(
        da_organizzare_sorted,
        key=lambda o: (o.zona or "—", o.data_servizio),
    ):
        gruppi_da_organizzare.append({"zona": zona, "data": data, "ods": list(items)})

    # ── Condomini da organizzare (senza tecnico) ──────────────────────────────
    condomini_da_organizzare = list(
        CondominioODS.objects
        .filter(stato=CondominioODS.Stato.DA_ESPLETARE, tecnico__isnull=True)
        .order_by("data", "ora")
    )

    # ── Giri confermati (ODS programmati + CondominioODS con tecnico) ─────────
    confermati_qs = list(
        ODS.objects
        .filter(stato="programmato")
        .select_related("filiale__cliente", "filiale", "privato", "tecnico", "assistente")
        .prefetch_related("righe__servizio")
        .order_by("data_servizio", "ora_inizio")
    )
    condomini_confermati = list(
        CondominioODS.objects
        .filter(stato=CondominioODS.Stato.DA_ESPLETARE, tecnico__isnull=False)
        .select_related("tecnico", "assistente")
        .order_by("data", "ora")
    )

    # Merge per tecnico
    tecnici_ids = set()
    for o in confermati_qs:
        if o.tecnico_id:
            tecnici_ids.add(o.tecnico_id)
    for c in condomini_confermati:
        tecnici_ids.add(c.tecnico_id)

    tecnici_map = {u.pk: u for u in User.objects.filter(pk__in=tecnici_ids).order_by("last_name", "first_name")}
    giri_confermati = []
    for tid, tecnico in tecnici_map.items():
        ods_list  = [o for o in confermati_qs    if o.tecnico_id == tid]
        cond_list = [c for c in condomini_confermati if c.tecnico_id == tid]
        senza_distinta = (
            sum(1 for o in ods_list  if not o.distinta_id) +
            sum(1 for c in cond_list if not c.distinta_id)
        )
        giri_confermati.append({
            "tecnico": tecnico,
            "ods": ods_list,
            "condomini": cond_list,
            "senza_distinta": senza_distinta,
        })

    from cespiti.models import Automezzo
    automezzi = Automezzo.objects.filter(attivo=True).order_by("targa")

    return render(request, "servizi/ods/organizzazione_giri.html", {
        "gruppi_da_organizzare": gruppi_da_organizzare,
        "condomini_da_organizzare": condomini_da_organizzare,
        "giri_confermati": giri_confermati,
        "utenti": utenti,
        "automezzi": automezzi,
        "today": timezone.localdate().isoformat(),
    })


@login_required
def condominio_assegna_tecnico(request, pk):
    """Assegna tecnico+assistente a un CondominioODS dalla pagina organizzazione giri."""
    condominio = get_object_or_404(CondominioODS, pk=pk)
    if request.method == "POST":
        tecnico_id    = request.POST.get("tecnico")
        assistente_id = request.POST.get("assistente") or None
        if tecnico_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                condominio.tecnico    = User.objects.get(pk=tecnico_id)
                condominio.assistente = User.objects.get(pk=assistente_id) if assistente_id else None
                condominio.save(update_fields=["tecnico", "assistente"])
                messages.success(request, f"{condominio.numero} assegnato a {condominio.tecnico.get_full_name()}.")
            except User.DoesNotExist:
                messages.error(request, "Utente non trovato.")
        else:
            messages.error(request, "Il tecnico è obbligatorio.")
    return redirect("servizi:organizzazione_giri")


@login_required
def ods_assegna_tecnico(request, pk):
    """Assegna tecnico+assistente a un ODS e lo porta in stato 'programmato'."""
    ods = get_object_or_404(ODS, pk=pk)
    if request.method == "POST":
        tecnico_id = request.POST.get("tecnico")
        assistente_id = request.POST.get("assistente") or None
        if tecnico_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                ods.tecnico = User.objects.get(pk=tecnico_id)
                ods.assistente = User.objects.get(pk=assistente_id) if assistente_id else None
                ods.stato = "programmato"
                ods.save(update_fields=["tecnico", "assistente", "stato"])
                messages.success(request, f"{ods.numero} assegnato a {ods.tecnico.get_full_name()}.")
            except User.DoesNotExist:
                messages.error(request, "Utente non trovato.")
        else:
            messages.error(request, "Il tecnico è obbligatorio.")
    return redirect("servizi:organizzazione_giri")


@login_required
def ods_da_incassare(request):
    """Tabella di tutti gli ODS con incasso_al_servizio=True non ancora incassati."""
    qs = ODS.objects.filter(
        incasso_al_servizio=True,
        incassato=False,
    ).select_related("filiale__cliente", "privato", "tecnico").prefetch_related(
        "righe__servizio"
    ).order_by("stato", "data_servizio")
    ods_list = list(qs)
    from decimal import Decimal
    return render(request, "servizi/ods/da_incassare.html", {
        "ods_list": ods_list,
        "totale_stimato": sum(o.prezzo_totale or Decimal("0") for o in ods_list) or None,
    })


@login_required
def ods_segna_incassato(request, pk):
    """Segna un ODS come incassato (POST)."""
    ods = get_object_or_404(ODS, pk=pk)
    if request.method == "POST":
        from decimal import Decimal, InvalidOperation
        importo_raw = request.POST.get("importo_incassato", "").strip()
        try:
            ods.importo_incassato = Decimal(importo_raw) if importo_raw else ods.prezzo_totale
        except InvalidOperation:
            ods.importo_incassato = ods.prezzo_totale
        ods.incassato = True
        ods.data_incasso = timezone.localdate()
        ods.save(update_fields=["incassato", "data_incasso", "importo_incassato"])
        messages.success(request, f"ODS {ods.numero} segnato come incassato.")
    next_url = request.POST.get("next") or reverse("servizi:ods_da_incassare")
    return redirect(next_url)


@login_required
@require_POST
def ods_set_importo(request, pk):
    """AJAX: salva l'importo da incassare su un ODS (può essere vuoto)."""
    from django.http import JsonResponse
    from decimal import Decimal, InvalidOperation
    ods = get_object_or_404(ODS, pk=pk)
    importo_str = request.POST.get("importo", "").strip()
    try:
        ods.importo_incassato = Decimal(importo_str) if importo_str else None
        ods.save(update_fields=["importo_incassato"])
        return JsonResponse({"success": True})
    except InvalidOperation:
        return JsonResponse({"success": False, "error": "Importo non valido"}, status=400)


@login_required
def ods_set_stato(request, pk):
    ods = get_object_or_404(ODS, pk=pk)
    if request.method == "POST":
        nuovo_stato = request.POST.get("stato")
        if nuovo_stato in [s[0] for s in ODS.Stato.choices]:
            ods.stato = nuovo_stato
            ods.save(update_fields=["stato"])
            messages.success(request, f"Stato aggiornato: {ods.get_stato_display()}")
    return redirect("servizi:ods_detail", pk=pk)


# ── Distinte ──────────────────────────────────────────────────────────────────

class DistintaListView(LoginRequiredMixin, ListView):
    model = Distinta
    template_name = "servizi/distinte/list.html"
    context_object_name = "distinte"

    def get_queryset(self):
        from django.db.models import Count
        return Distinta.objects.select_related("tecnico", "creata_da", "mezzo").annotate(
            n_ods=Count("ods_set"),
        ).order_by("-data", "-creata_il")


class DistintaDetailView(LoginRequiredMixin, DetailView):
    model = Distinta
    template_name = "servizi/distinte/detail.html"
    context_object_name = "distinta"

    def get_queryset(self):
        return Distinta.objects.select_related("tecnico", "creata_da", "mezzo")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.db.models import Sum
        ods_qs = self.object.ods_set.select_related(
            "filiale__cliente", "privato"
        ).prefetch_related(
            "righe__servizio",
            "righe__consumi__prodotto",
        ).annotate(
            prezzo_sum=Sum("righe__prezzo"),
        ).order_by("data_servizio", "pk")
        ctx["ods_list"] = ods_qs
        ctx["condomini_list"] = self.object.condomini_set.select_related(
            "tecnico", "assistente"
        ).prefetch_related("unita", "prodotti__prodotto").order_by("data", "ora")

        mezzo = self.object.mezzo
        ctx["mezzo"] = mezzo
        ctx["chiudi_form"] = ChiudiServizioForm()
        ctx["consumo_form"] = ConsumoMaterialeForm(mezzo=mezzo)
        ctx["chiudi_choices"] = ChiudiServizioForm().fields["modalita_pagamento"].choices
        return ctx


@login_required
def crea_distinta(request, tecnico_pk):
    """Crea una Distinta per un tecnico con tutti i suoi ODS programmati senza distinta."""
    if request.method != "POST":
        return redirect("servizi:organizzazione_giri")
    from django.contrib.auth import get_user_model
    from datetime import date as date_cls
    User = get_user_model()
    tecnico = get_object_or_404(User, pk=tecnico_pk)

    data_str = request.POST.get("data", "")
    try:
        from datetime import date as _date
        data = _date.fromisoformat(data_str)
    except ValueError:
        data = timezone.localdate()

    ods_da_includere = ODS.objects.filter(
        tecnico=tecnico, stato="programmato", distinta__isnull=True
    )
    condomini_da_includere = CondominioODS.objects.filter(
        tecnico=tecnico, stato=CondominioODS.Stato.DA_ESPLETARE, distinta__isnull=True
    )
    if not ods_da_includere.exists() and not condomini_da_includere.exists():
        messages.warning(request, f"Nessun servizio da includere per {tecnico.get_full_name() or tecnico.username}.")
        return redirect("servizi:organizzazione_giri")

    mezzo_id = request.POST.get("mezzo") or None
    distinta = Distinta.objects.create(
        data=data,
        tecnico=tecnico,
        mezzo_id=mezzo_id,
        creata_da=request.user,
    )
    n_ods  = ods_da_includere.update(distinta=distinta)
    n_cond = condomini_da_includere.update(distinta=distinta)
    n = n_ods + n_cond

    from comunicazioni.models import Promemoria
    Promemoria.objects.create(
        user=request.user,
        assegnato_a=tecnico,
        titolo=f"Distinta servizi {data.strftime('%d/%m/%Y')}",
        descrizione=(
            f"Hai {n} servizio{'i' if n != 1 else ''} assegnato{'i' if n != 1 else ''} "
            f"per il {data.strftime('%d/%m/%Y')}.\n"
            f"Accedi alla distinta per gestire i servizi."
        ),
        priorita="alta",
    )
    messages.success(request, f"Distinta creata con {n_ods} ODS e {n_cond} condomini. Promemoria inviato a {tecnico.get_full_name() or tecnico.username}.")
    return redirect(distinta.get_absolute_url())


@login_required
def chiudi_servizio_distinta(request, ods_pk):
    """Chiude un singolo ODS dalla distinta del tecnico."""
    ods = get_object_or_404(ODS.objects.select_related("distinta"), pk=ods_pk)
    if request.method != "POST":
        return redirect(ods.distinta.get_absolute_url() if ods.distinta else reverse("servizi:distinta_list"))

    form = ChiudiServizioForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        ods.stato = "completato"
        fields = ["stato"]
        if ods.incasso_al_servizio:
            modalita = cd.get("modalita_pagamento") or "contanti"
            ods.modalita_pagamento = modalita
            fields.append("modalita_pagamento")
            if modalita != "non_incassato":
                ods.incassato = True
                ods.data_incasso = timezone.localdate()
                importo = cd.get("importo_incassato")
                ods.importo_incassato = importo if importo else ods.prezzo_totale
                fields += ["incassato", "data_incasso", "importo_incassato"]
        note = cd.get("note_intervento", "").strip()
        if note:
            ods.note_intervento = note
            fields.append("note_intervento")
        ods.save(update_fields=fields)

        from decimal import Decimal, InvalidOperation

        # Conferma prodotti previsti (confermato=False → True se spuntati)
        for riga in ods.righe.all():
            for c in ConsumoMateriale.objects.filter(riga=riga, confermato=False):
                qty_str = request.POST.get(f"prod-quantita-{c.pk}", "").strip()
                confirmed = f"prod-confermato-{c.pk}" in request.POST
                try:
                    qty = Decimal(qty_str) if qty_str else c.quantita
                except InvalidOperation:
                    qty = c.quantita
                if confirmed or qty != c.quantita:
                    c.confermato = confirmed
                    c.quantita = qty
                    c.save()

        # Prodotti aggiuntivi non previsti (aggiunti sul campo)
        extra_total = int(request.POST.get("extra-TOTAL_FORMS", 0) or 0)
        if extra_total > 0:
            prima_riga = ods.righe.first()
            if prima_riga:
                for i in range(extra_total):
                    prod_id = request.POST.get(f"extra-{i}-prodotto", "").strip()
                    qty_str = request.POST.get(f"extra-{i}-quantita", "1").strip()
                    if not prod_id:
                        continue
                    try:
                        qty = Decimal(qty_str)
                    except InvalidOperation:
                        qty = Decimal("1")
                    ConsumoMateriale.objects.create(
                        riga=prima_riga,
                        prodotto_id=prod_id,
                        quantita=qty,
                        confermato=True,
                    )

        messages.success(request, f"ODS {ods.numero} chiuso.")

    back = ods.distinta.get_absolute_url() if ods.distinta else reverse("servizi:distinta_list")
    return redirect(back)


@login_required
def aggiungi_consumo(request, ods_pk):
    """Aggiunge un ConsumoMateriale a un ODS (prima riga) e scala ScortaMezzo."""
    ods = get_object_or_404(
        ODS.objects.prefetch_related("righe"), pk=ods_pk
    )
    if request.method != "POST":
        return redirect(ods.distinta.get_absolute_url() if ods.distinta else "servizi:distinta_list")

    from cespiti.models import Automezzo
    mezzo = Automezzo.objects.filter(
        assegnato_a=ods.tecnico, attivo=True
    ).first() if ods.tecnico else None

    form = ConsumoMaterialeForm(request.POST, mezzo=mezzo)
    if form.is_valid():
        riga = ods.righe.first()
        if riga:
            c = form.save(commit=False)
            c.riga = riga
            c.confermato = True  # aggiunto dalla distinta = uso reale, scala stock
            c.save()
            messages.success(request, f"Consumo registrato: {c.prodotto} ×{c.quantita}.")
        else:
            messages.error(request, "ODS senza righe servizio.")
    else:
        messages.error(request, "Dati non validi.")

    back = ods.distinta.get_absolute_url() if ods.distinta else reverse("servizi:distinta_list")
    return redirect(back)


@login_required
def elimina_consumo(request, consumo_pk):
    """Elimina un ConsumoMateriale e ripristina la ScortaMezzo."""
    consumo = get_object_or_404(
        ConsumoMateriale.objects.select_related("riga__ods__tecnico"), pk=consumo_pk
    )
    back = (
        consumo.riga.ods.distinta.get_absolute_url()
        if consumo.riga.ods.distinta
        else reverse("servizi:distinta_list")
    )
    if request.method == "POST":
        consumo.delete()
        messages.success(request, "Consumo eliminato.")
    return redirect(back)


@login_required
def distinta_chiudi(request, pk):
    """Chiusura rapida (legacy). Preferire chiudi_distinta_ufficio."""
    distinta = get_object_or_404(Distinta, pk=pk)
    if request.method == "POST":
        distinta.stato = "chiusa"
        distinta.save(update_fields=["stato"])
        messages.success(request, "Distinta chiusa.")
    return redirect(distinta.get_absolute_url())


@login_required
def chiudi_distinta_ufficio(request, pk):
    """
    Chiusura distinta da parte dell'ufficio: riconcilia incassi,
    permette di riaprire singoli ODS e invia promemoria al tecnico.
    """
    from decimal import Decimal, InvalidOperation
    from django.db.models import Sum, Q

    distinta = get_object_or_404(
        Distinta.objects.select_related("tecnico", "mezzo"), pk=pk
    )
    if distinta.stato == "chiusa":
        messages.info(request, "Questa distinta è già chiusa.")
        return redirect(distinta.get_absolute_url())

    ods_qs = (
        distinta.ods_set
        .select_related("filiale__cliente", "privato")
        .prefetch_related("righe__servizio")
        .order_by("data_servizio", "pk")
    )
    ods_list = list(ods_qs)

    condomini_qs = (
        distinta.condomini_set
        .prefetch_related("unita")
        .order_by("data", "pk")
    )
    condomini_list = list(condomini_qs)

    totale_previsto = (
        sum((o.importo_incassato or Decimal("0")) for o in ods_list if o.incassato) +
        sum(c.totale_incassato for c in condomini_list)
    )

    if request.method == "POST":
        # Riapertura ODS selezionati
        riaperti = 0
        for o in ods_list:
            if request.POST.get(f"riapri_{o.pk}"):
                fields = ["stato", "distinta"]
                o.stato = "da_espletare"
                o.distinta = None
                if o.incassato:
                    o.incassato = False
                    o.importo_incassato = None
                    o.data_incasso = None
                    fields += ["incassato", "importo_incassato", "data_incasso"]
                o.save(update_fields=fields)
                riaperti += 1

        # Riapertura CondominioODS selezionati
        for c in condomini_list:
            if request.POST.get(f"riapri_c_{c.pk}"):
                # Ripristina stock furgone per i prodotti già confermati
                for riga in c.prodotti.all():
                    if riga.confermato:
                        riga.confermato = False
                        riga.save(update_fields=["confermato"])
                c.stato = "da_espletare"
                c.distinta = None
                c.save(update_fields=["stato", "distinta"])
                riaperti += 1

        # Ricalcola totale dopo eventuali riaperture
        totale_effettivo = (
            sum(
                (o.importo_incassato or Decimal("0"))
                for o in ods_list
                if o.incassato and not request.POST.get(f"riapri_{o.pk}")
            ) +
            sum(
                c.totale_incassato
                for c in condomini_list
                if not request.POST.get(f"riapri_c_{c.pk}")
            )
        )

        importo_str = request.POST.get("importo_ricevuto", "").strip()
        try:
            importo_ricevuto = Decimal(importo_str) if importo_str else totale_effettivo
        except InvalidOperation:
            importo_ricevuto = totale_effettivo

        distinta.stato = "chiusa"
        distinta.importo_ricevuto = importo_ricevuto
        distinta.chiusa_da = request.user
        distinta.chiusa_il = timezone.now()
        distinta.save(update_fields=["stato", "importo_ricevuto", "chiusa_da", "chiusa_il"])

        # Promemoria al tecnico
        differenza = importo_ricevuto - totale_effettivo
        nome_ufficio = request.user.get_full_name() or request.user.username
        righe_msg = (
            f"Incasso previsto:  € {totale_effettivo}\n"
            f"Importo ricevuto:  € {importo_ricevuto}\n"
        )
        if differenza < 0:
            righe_msg += f"Differenza:        € {abs(differenza)} MANCANTI"
            priorita = "alta"
        elif differenza > 0:
            righe_msg += f"Differenza:        € {differenza} in eccesso"
            priorita = "normale"
        else:
            righe_msg += "Tutto corrisponde."
            priorita = "normale"
        if riaperti:
            righe_msg += f"\n\n{riaperti} servizio/i riportato/i a 'da espletare'."

        from comunicazioni.models import Promemoria
        Promemoria.objects.create(
            user=request.user,
            assegnato_a=distinta.tecnico,
            titolo=(
                f"Chiusura distinta {distinta.data.strftime('%d/%m/%Y')} "
                f"— Incasso € {importo_ricevuto}"
            ),
            descrizione=(
                f"Distinta del {distinta.data.strftime('%d/%m/%Y')} "
                f"chiusa da {nome_ufficio}.\n\n{righe_msg}"
            ),
            priorita=priorita,
        )

        nome_tec = distinta.tecnico.get_full_name() or distinta.tecnico.username
        messages.success(
            request,
            f"Distinta chiusa. Promemoria inviato a {nome_tec}."
            + (f" ({riaperti} ODS riaperti)" if riaperti else ""),
        )
        return redirect(distinta.get_absolute_url())

    return render(request, "servizi/distinte/chiudi_ufficio.html", {
        "distinta": distinta,
        "ods_list": ods_list,
        "condomini_list": condomini_list,
        "totale_previsto": totale_previsto,
    })


@login_required
def situazione_incassi(request):
    """Panoramica degli incassi per tecnico: distintas chiuse con riconciliazione."""
    from django.contrib.auth import get_user_model
    from django.db.models import Sum, Q
    from decimal import Decimal

    User = get_user_model()
    utenti = User.objects.filter(is_active=True).order_by("last_name", "first_name")

    tecnico_id = request.GET.get("tecnico") or None
    tecnico_sel = None

    from django.db.models import Count
    qs = (
        Distinta.objects
        .select_related("tecnico", "mezzo", "chiusa_da")
        .annotate(
            n_ods=Count("ods_set", distinct=True),
            totale_calcolato=Sum(
                "ods_set__importo_incassato",
                filter=Q(ods_set__incassato=True),
            ),
        )
        .order_by("-data")
    )

    if tecnico_id:
        try:
            tecnico_sel = User.objects.get(pk=tecnico_id)
            qs = qs.filter(tecnico=tecnico_sel)
        except User.DoesNotExist:
            pass

    distinte = []
    grand_previsto = Decimal("0")
    grand_ricevuto = Decimal("0")
    for d in qs:
        previsto = d.totale_calcolato or Decimal("0")
        ricevuto = d.importo_ricevuto or Decimal("0")
        grand_previsto += previsto
        grand_ricevuto += ricevuto
        diff = ricevuto - previsto
        distinte.append({
            "obj": d,
            "previsto": previsto,
            "ricevuto": ricevuto,
            "diff": diff,
            "diff_abs": abs(diff),
        })

    grand_diff = grand_ricevuto - grand_previsto
    return render(request, "servizi/distinte/situazione_incassi.html", {
        "distinte": distinte,
        "utenti": utenti,
        "tecnico_sel": tecnico_sel,
        "grand_previsto": grand_previsto,
        "grand_ricevuto": grand_ricevuto,
        "grand_diff": grand_diff,
        "grand_diff_abs": abs(grand_diff),
    })


# ── CONDOMINI ODS ─────────────────────────────────────────────────────────────

@login_required
def condominio_list(request):
    q = request.GET.get("q", "")
    qs = CondominioODS.objects.select_related("tecnico", "assistente").order_by("-data", "-created_at")
    if q:
        qs = qs.filter(Q(titolo__icontains=q) | Q(indirizzo__icontains=q) | Q(numero__icontains=q))
    return render(request, "servizi/condomini/list.html", {"condomini": qs, "q": q})


@login_required
def condominio_create(request):
    if request.method == "POST":
        form = CondominioODSForm(request.POST)
        fs_unita = RigaUnitaAbitativaFormSet(request.POST, prefix="unita")
        fs_prodotti = RigaProdottoCondominioFormSet(request.POST, prefix="prodotti")
        if form.is_valid() and fs_unita.is_valid() and fs_prodotti.is_valid():
            condominio = form.save(commit=False)
            condominio.created_by = request.user
            condominio.save()
            fs_unita.instance = condominio
            fs_unita.save()
            fs_prodotti.instance = condominio
            fs_prodotti.save()
            messages.success(request, f"Condominio ODS {condominio.numero} creato.")
            return redirect("servizi:condominio_detail", pk=condominio.pk)
    else:
        form = CondominioODSForm()
        fs_unita = RigaUnitaAbitativaFormSet(prefix="unita")
        fs_prodotti = RigaProdottoCondominioFormSet(prefix="prodotti")
    return render(request, "servizi/condomini/form.html", {
        "form": form,
        "fs_unita": fs_unita,
        "fs_prodotti": fs_prodotti,
        "titolo": "Nuovo Condominio ODS",
        "back_url": reverse("servizi:condominio_list"),
    })


@login_required
def condominio_detail(request, pk):
    condominio = get_object_or_404(
        CondominioODS.objects.select_related("tecnico", "assistente", "created_by", "distinta")
        .prefetch_related("unita", "prodotti__prodotto"),
        pk=pk,
    )
    unita = list(condominio.unita.all())
    return render(request, "servizi/condomini/detail.html", {
        "condominio": condominio,
        "unita": unita,
        "n_servizi": sum(1 for u in unita if u.servizio_effettuato),
        "n_incassi": sum(1 for u in unita if u.incasso_effettuato),
    })


def condominio_pdf(request, pk):
    from django.template.loader import render_to_string
    from django.utils import timezone
    from core.pdf_generator import generate_pdf_from_html, PDFConfig
    condominio = get_object_or_404(
        CondominioODS.objects.select_related("tecnico", "assistente").prefetch_related("unita"),
        pk=pk,
    )
    unita = list(condominio.unita.all())
    ctx = {"condominio": condominio, "unita": unita, "oggi": timezone.now().date()}
    html = render_to_string("servizi/condomini/pdf.html", ctx, request=request)
    return generate_pdf_from_html(
        html,
        PDFConfig(filename=f"{condominio.numero}.pdf"),
        output_type="response",
    )


@login_required
def condominio_update(request, pk):
    condominio = get_object_or_404(CondominioODS, pk=pk)
    if request.method == "POST":
        form = CondominioODSForm(request.POST, instance=condominio)
        fs_unita = RigaUnitaAbitativaFormSet(request.POST, instance=condominio, prefix="unita")
        fs_prodotti = RigaProdottoCondominioFormSet(request.POST, instance=condominio, prefix="prodotti")
        if form.is_valid() and fs_unita.is_valid() and fs_prodotti.is_valid():
            form.save()
            fs_unita.save()
            fs_prodotti.save()
            messages.success(request, "Condominio ODS aggiornato.")
            return redirect("servizi:condominio_detail", pk=condominio.pk)
    else:
        form = CondominioODSForm(instance=condominio)
        fs_unita = RigaUnitaAbitativaFormSet(instance=condominio, prefix="unita")
        fs_prodotti = RigaProdottoCondominioFormSet(instance=condominio, prefix="prodotti")
    return render(request, "servizi/condomini/form.html", {
        "form": form,
        "fs_unita": fs_unita,
        "fs_prodotti": fs_prodotti,
        "titolo": f"Modifica {condominio.numero}",
        "back_url": reverse("servizi:condominio_detail", kwargs={"pk": pk}),
        "condominio": condominio,
    })


@login_required
def condominio_esegui(request, pk):
    condominio = get_object_or_404(
        CondominioODS.objects.select_related("tecnico", "assistente", "distinta__mezzo")
        .prefetch_related("unita", "prodotti__prodotto"),
        pk=pk,
    )
    if request.method == "POST":
        action = request.POST.get("action", "salva")
        fs_unita = RigaUnitaAbitativaEseguiFormSet(request.POST, instance=condominio, prefix="unita")
        fs_prodotti = RigaProdottoCondominioEseguiFormSet(request.POST, instance=condominio, prefix="prodotti")
        if fs_unita.is_valid() and fs_prodotti.is_valid():
            fs_unita.save()
            fs_prodotti.save()
        if action == "chiudi":
            # Scala ScortaMezzo per tutti i prodotti non ancora confermati
            for riga in condominio.prodotti.all():
                if not riga.confermato:
                    riga.confermato = True
                    riga.save(update_fields=["confermato"])
            condominio.stato = CondominioODS.Stato.COMPLETATO
            condominio.save(update_fields=["stato"])
            messages.success(request, f"{condominio.numero} chiuso. Carico furgone aggiornato.")
            return redirect("servizi:condominio_detail", pk=pk)
        elif action == "torna":
            messages.success(request, "Progresso salvato.")
            return redirect("servizi:condominio_detail", pk=pk)
        elif fs_unita.is_valid():
            messages.success(request, "Progresso salvato.")
            return redirect("servizi:condominio_esegui", pk=pk)
    else:
        fs_unita = RigaUnitaAbitativaEseguiFormSet(instance=condominio, prefix="unita")
        fs_prodotti = RigaProdottoCondominioEseguiFormSet(instance=condominio, prefix="prodotti")

    # Stock furgone per ogni prodotto
    mezzo = None
    if condominio.distinta and condominio.distinta.mezzo_id:
        mezzo = condominio.distinta.mezzo
    elif condominio.tecnico_id:
        try:
            from cespiti.models import Automezzo
            mezzo = Automezzo.objects.filter(
                assegnato_a_id=condominio.tecnico_id, attivo=True
            ).first()
        except Exception:
            mezzo = None

    import json as _json
    scorte_mezzo = {}
    if mezzo:
        from magazzino.models import ScortaMezzo
        for sm in ScortaMezzo.objects.filter(mezzo=mezzo).select_related("prodotto"):
            scorte_mezzo[sm.prodotto_id] = sm.quantita

    importi = {
        str(u.pk): float(u.importo_da_incassare or condominio.prezzo_base)
        for u in condominio.unita.all()
    }
    return render(request, "servizi/condomini/esegui.html", {
        "condominio": condominio,
        "fs_unita": fs_unita,
        "fs_prodotti": fs_prodotti,
        "importi_json": importi,
        "mezzo": mezzo,
        "scorte_json": _json.dumps({str(k): float(v) for k, v in scorte_mezzo.items()}),
    })


@login_required
@require_POST
def condominio_salva_riga(request, pk):
    """AJAX: salva una singola RigaUnitaAbitativa senza ricaricare la pagina."""
    from django.http import JsonResponse
    import json
    from decimal import Decimal, InvalidOperation

    condominio = get_object_or_404(CondominioODS, pk=pk)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"success": False, "error": "Dati non validi"}, status=400)

    riga_id = data.get("riga_id")
    if not riga_id:
        return JsonResponse({"success": False, "error": "riga_id mancante"}, status=400)

    try:
        riga = RigaUnitaAbitativa.objects.get(pk=riga_id, condominio=condominio)
    except RigaUnitaAbitativa.DoesNotExist:
        return JsonResponse({"success": False, "error": "Riga non trovata"}, status=404)

    riga.servizio_effettuato = bool(data.get("servizio_effettuato", False))
    riga.incasso_effettuato  = bool(data.get("incasso_effettuato", False))
    importo_raw = data.get("importo_da_incassare")
    if importo_raw is not None and str(importo_raw).strip() != "":
        try:
            riga.importo_da_incassare = Decimal(str(importo_raw))
        except InvalidOperation:
            riga.importo_da_incassare = None
    else:
        riga.importo_da_incassare = None
    riga.save(update_fields=["servizio_effettuato", "incasso_effettuato", "importo_da_incassare"])
    return JsonResponse({"success": True})
