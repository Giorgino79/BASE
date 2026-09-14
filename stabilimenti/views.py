from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import models as db_models
from django.utils import timezone
from datetime import timedelta

from .models import Stabilimento, CostiStabilimento, DocStabilimento
from .forms import (
    StabilimentoForm, CostiStabilimentoForm, UtenzaForm,
    DocStabilimentoForm, StabilimentiSearchForm, CostiSearchForm,
)


# ============================================================
# DASHBOARD
# ============================================================

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "stabilimenti/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        ctx["stabilimenti_count"] = Stabilimento.objects.count()
        ctx["stabilimenti_attivi"] = Stabilimento.objects.filter(attivo=True).count()
        ctx["scadenze_urgenti"] = CostiStabilimento.objects.filter(
            data_scadenza_servizio__gte=today,
            data_scadenza_servizio__lte=today + timedelta(days=7),
        ).count()
        return ctx


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
    return render(request, "stabilimenti/stabilimenti/list.html", {"form": form, "page_obj": page_obj, "stats": stats})


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
            return redirect("stabilimenti:stabilimento_detail", pk=stab.pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = StabilimentoForm(user=request.user)
    return render(request, "stabilimenti/stabilimenti/form.html", {"form": form, "action": "Nuovo Stabilimento"})


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
    return render(request, "stabilimenti/stabilimenti/dettaglio.html", {
        "stabilimento": stab,
        "object": stab,
        "costi_recenti": costi_recenti,
        "documenti_recenti": documenti_recenti,
        "scadenze_prossime": scadenze_prossime,
        "costi_anno": costi_anno,
        "edit_url": reverse("stabilimenti:stabilimento_update", kwargs={"pk": pk}),
        "back_url": reverse("stabilimenti:stabilimento_list"),
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
            return redirect("stabilimenti:stabilimento_detail", pk=pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = StabilimentoForm(instance=stab, user=request.user)
    return render(request, "stabilimenti/stabilimenti/form.html", {
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
    return render(request, "stabilimenti/costi/list.html", {"form": form, "page_obj": page_obj})


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
            return redirect("stabilimenti:stabilimento_detail", pk=stab.pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = CostiStabilimentoForm(user=request.user, stabilimento=stab)
    return render(request, "stabilimenti/costi/form.html", {"form": form, "stabilimento": stab, "action": "Nuovo Costo"})


@login_required
def costo_detail(request, pk):
    costo = get_object_or_404(
        CostiStabilimento.objects.select_related("stabilimento", "fornitore", "incaricato"),
        pk=pk,
    )
    from django.contrib.contenttypes.models import ContentType
    return render(request, "stabilimenti/costi/dettaglio.html", {
        "costo": costo,
        "object": costo,
        "edit_url": reverse("stabilimenti:costo_update", kwargs={"pk": pk}) if costo.can_be_modified() else None,
        "back_url": reverse("stabilimenti:costo_list"),
        "content_type_id": ContentType.objects.get_for_model(CostiStabilimento).pk,
        "object_id": costo.pk,
    })


@login_required
def costo_update(request, pk):
    costo = get_object_or_404(CostiStabilimento, pk=pk)
    if not costo.can_be_modified():
        messages.error(request, "Non è possibile modificare un costo già pagato")
        return redirect("stabilimenti:costo_detail", pk=pk)
    if request.method == "POST":
        form = CostiStabilimentoForm(request.POST, request.FILES, instance=costo, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Costo "{costo.titolo}" modificato.')
            return redirect("stabilimenti:costo_detail", pk=pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = CostiStabilimentoForm(instance=costo, user=request.user)
    return render(request, "stabilimenti/costi/form.html", {"form": form, "costo": costo, "action": f"Modifica {costo.numero_pratica}"})


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
            return redirect("stabilimenti:stabilimento_detail", pk=stab.pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = UtenzaForm(user=request.user, stabilimento=stab)
    return render(request, "stabilimenti/costi/utenza_form.html", {"form": form, "stabilimento": stab})


@login_required
def utenza_update(request, pk):
    utenza = get_object_or_404(CostiStabilimento, pk=pk)
    if utenza.causale not in UTENZE_TYPES:
        messages.error(request, "Questo costo non è un'utenza")
        return redirect("stabilimenti:costo_detail", pk=pk)
    if not utenza.can_be_modified():
        messages.error(request, "Non è possibile modificare un'utenza già pagata")
        return redirect("stabilimenti:costo_detail", pk=pk)
    if request.method == "POST":
        form = UtenzaForm(request.POST, request.FILES, instance=utenza, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Utenza modificata.")
            return redirect("stabilimenti:costo_detail", pk=pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = UtenzaForm(instance=utenza, user=request.user)
    return render(request, "stabilimenti/costi/utenza_form.html", {"form": form, "utenza": utenza, "stabilimento": utenza.stabilimento})


# ============================================================
# DOCUMENTI
# ============================================================

@login_required
def documento_list(request, stabilimento_pk):
    stab = get_object_or_404(Stabilimento, pk=stabilimento_pk)
    documenti = stab.documenti.order_by("-data_inserimento")
    paginator = Paginator(documenti, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "stabilimenti/documenti/list.html", {"stabilimento": stab, "page_obj": page_obj})


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
            return redirect("stabilimenti:documento_list", stabilimento_pk=stab.pk)
        messages.error(request, "Correggi gli errori nel form")
    else:
        form = DocStabilimentoForm(user=request.user, stabilimento=stab)
    return render(request, "stabilimenti/documenti/form.html", {"form": form, "stabilimento": stab})


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
    return render(request, "stabilimenti/scadenze.html", {
        "scadute": scadute,
        "questa_settimana": questa_settimana,
        "prossimi_30": prossimi_30,
        "scadenze_costi_urgenti": scadenze_costi_urgenti,
        "oggi": oggi,
    })
