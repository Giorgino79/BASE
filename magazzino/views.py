from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from decimal import Decimal

from .models import Categoria, Prodotto, Ricezione, RigaRicezione, ScortaStabilimento, CaricoMezzo, RigaCaricoMezzo, ScortaMezzo
from .forms import CategoriaForm, ProdottoForm, RicezioneForm, RigaRicezioneForm, RigaRicezioneFormSet, CaricoMezzoForm, RigaCaricoMezzoFormSet


@login_required
def dashboard(request):
    from django.db.models import Sum, Q, F
    scorte_basse = (
        Prodotto.objects
        .filter(attivo=True, scorta_minima__isnull=False)
        .annotate(
            totale_scorta=Sum(
                "scorte_stabilimenti__quantita",
                filter=Q(scorte_stabilimenti__quantita__gt=0),
            )
        )
        .filter(Q(totale_scorta__lt=F("scorta_minima")) | Q(totale_scorta__isnull=True))
        .select_related("categoria")
        .order_by("nome_prodotto")
    )
    ctx = {"scorte_basse": scorte_basse}
    return render(request, "magazzino/dashboard.html", ctx)


# ── CATEGORIE ─────────────────────────────────────────────────

class CategoriaListView(LoginRequiredMixin, ListView):
    model = Categoria
    template_name = "magazzino/categorie/list.html"
    context_object_name = "categorie"

    def get_queryset(self):
        return Categoria.objects.order_by("nome")


class CategoriaCreateView(LoginRequiredMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "magazzino/categorie/form.html"
    success_url = reverse_lazy("magazzino:categoria_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = "Nuova Categoria"
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Categoria creata.")
        return super().form_valid(form)


class CategoriaUpdateView(LoginRequiredMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "magazzino/categorie/form.html"
    success_url = reverse_lazy("magazzino:categoria_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = f"Modifica {self.object.nome}"
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Categoria aggiornata.")
        return super().form_valid(form)


# ── PRODOTTI ──────────────────────────────────────────────────

class ProdottoListView(LoginRequiredMixin, ListView):
    model = Prodotto
    template_name = "magazzino/prodotti/list.html"
    context_object_name = "prodotti"
    paginate_by = 20

    def get_queryset(self):
        qs = Prodotto.objects.select_related("categoria", "fornitore_principale").order_by("nome_prodotto")
        q = self.request.GET.get("q")
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(nome_prodotto__icontains=q)
                | Q(codice_interno__icontains=q)
                | Q(codice_fornitore__icontains=q)
            )
        cat = self.request.GET.get("categoria")
        if cat:
            qs = qs.filter(categoria_id=cat)
        solo_attivi = self.request.GET.get("attivi", "1")
        if solo_attivi == "1":
            qs = qs.filter(attivo=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categorie"] = Categoria.objects.filter(attiva=True).order_by("nome")
        ctx["cat_sel"] = self.request.GET.get("categoria", "")
        return ctx


class ProdottoDetailView(LoginRequiredMixin, DetailView):
    model = Prodotto
    template_name = "magazzino/prodotti/dettaglio.html"
    context_object_name = "prodotto"

    def get_queryset(self):
        return Prodotto.objects.select_related("categoria", "fornitore_principale")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["back_url"] = reverse("magazzino:prodotto_list")
        ctx["edit_url"] = reverse("magazzino:prodotto_update", kwargs={"pk": self.object.pk})
        from django.contrib.contenttypes.models import ContentType
        ctx["content_type_id"] = ContentType.objects.get_for_model(self.model).pk
        ctx["object_id"] = self.object.pk
        ctx["scorte_stabilimenti"] = (
            ScortaStabilimento.objects.filter(prodotto=self.object)
            .select_related("stabilimento")
            .order_by("stabilimento__nome")
        )
        ctx["scorte_mezzi"] = (
            ScortaMezzo.objects.filter(prodotto=self.object, quantita__gt=0)
            .select_related("mezzo", "mezzo__assegnato_a")
            .order_by("mezzo__targa")
        )
        return ctx


class ProdottoCreateView(LoginRequiredMixin, CreateView):
    model = Prodotto
    form_class = ProdottoForm
    template_name = "magazzino/prodotti/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = "Nuovo Prodotto"
        ctx["back_url"] = reverse("magazzino:prodotto_list")
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Prodotto creato.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("magazzino:prodotto_detail", kwargs={"pk": self.object.pk})


class ProdottoUpdateView(LoginRequiredMixin, UpdateView):
    model = Prodotto
    form_class = ProdottoForm
    template_name = "magazzino/prodotti/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = f"Modifica {self.object.nome_prodotto}"
        ctx["back_url"] = reverse("magazzino:prodotto_detail", kwargs={"pk": self.object.pk})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Prodotto aggiornato.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("magazzino:prodotto_detail", kwargs={"pk": self.object.pk})


class ProdottoDeleteView(LoginRequiredMixin, DeleteView):
    model = Prodotto
    template_name = "magazzino/prodotti/confirm_delete.html"
    success_url = reverse_lazy("magazzino:prodotto_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Prodotto eliminato.")
        return super().delete(request, *args, **kwargs)


# ── RICEZIONI ─────────────────────────────────────────────────

@login_required
def ricezione_list(request):
    from django.db.models import Q
    from acquisti.models import OrdineAcquisto

    q       = request.GET.get("q", "").strip()
    data_da = request.GET.get("data_da", "").strip()
    data_a  = request.GET.get("data_a", "").strip()
    filtro_attivo = bool(q or data_da or data_a)

    qs = Ricezione.objects.select_related("fornitore", "ordine").prefetch_related("righe__prodotto").order_by("-data_ricezione", "-created_at")

    if q:
        qs = qs.filter(Q(numero_ddt__icontains=q) | Q(fornitore__ragione_sociale__icontains=q))
    if data_da:
        qs = qs.filter(data_ricezione__gte=data_da)
    if data_a:
        qs = qs.filter(data_ricezione__lte=data_a)

    if not filtro_attivo:
        qs = qs[:10]

    da_ricevere = (
        OrdineAcquisto.objects
        .exclude(stato="ricevuto")
        .select_related("fornitore")
        .prefetch_related("righe__prodotto")
        .order_by("data_ordine")
    )

    return render(request, "magazzino/ricezioni/list.html", {
        "ricezioni":      qs,
        "q":              q,
        "data_da":        data_da,
        "data_a":         data_a,
        "filtro_attivo":  filtro_attivo,
        "da_ricevere":    da_ricevere,
    })


class RicezioneDetailView(LoginRequiredMixin, DetailView):
    model = Ricezione
    template_name = "magazzino/ricezioni/dettaglio.html"
    context_object_name = "ricezione"

    def get_queryset(self):
        return Ricezione.objects.select_related("fornitore", "ordine", "created_by").prefetch_related(
            "righe__prodotto", "righe__riga_ordine"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["back_url"] = reverse("magazzino:ricezione_list")
        ctx["edit_url"] = reverse("magazzino:ricezione_update", kwargs={"pk": self.object.pk})
        from django.contrib.contenttypes.models import ContentType
        ctx["content_type_id"] = ContentType.objects.get_for_model(self.model).pk
        ctx["object_id"] = self.object.pk
        return ctx


class RicezioneCreateView(LoginRequiredMixin, CreateView):
    model = Ricezione
    form_class = RicezioneForm
    template_name = "magazzino/ricezioni/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = RigaRicezioneFormSet(self.request.POST)
        else:
            ctx["formset"] = RigaRicezioneFormSet()
        ctx["titolo"] = "Nuova Ricezione"
        ctx["back_url"] = reverse("magazzino:ricezione_list")
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        if formset.is_valid():
            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            self.object.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "Ricezione registrata.")
            return redirect("magazzino:ricezione_detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form))


class RicezioneUpdateView(LoginRequiredMixin, UpdateView):
    model = Ricezione
    form_class = RicezioneForm
    template_name = "magazzino/ricezioni/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = RigaRicezioneFormSet(self.request.POST, instance=self.object)
        else:
            ctx["formset"] = RigaRicezioneFormSet(instance=self.object)
        ctx["titolo"] = f"Modifica ricezione del {self.object.data_ricezione:%d/%m/%Y}"
        ctx["back_url"] = reverse("magazzino:ricezione_detail", kwargs={"pk": self.object.pk})
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "Ricezione aggiornata.")
            return redirect("magazzino:ricezione_detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form))


class RicezioneDeleteView(LoginRequiredMixin, DeleteView):
    model = Ricezione
    template_name = "magazzino/ricezioni/confirm_delete.html"
    success_url = reverse_lazy("magazzino:ricezione_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Ricezione eliminata.")
        return super().delete(request, *args, **kwargs)


@login_required
def api_oda_righe(request, oda_pk):
    from acquisti.models import OrdineAcquisto
    from django.http import JsonResponse
    ordine = get_object_or_404(
        OrdineAcquisto.objects.prefetch_related("righe__prodotto"), pk=oda_pk
    )
    righe_mancanti = [
        r.descrizione or f"Riga #{r.pk}"
        for r in ordine.righe.all()
        if not r.prodotto_id
    ]
    if righe_mancanti:
        return JsonResponse({"ok": False, "righe_mancanti": righe_mancanti})
    riga_ids = list(ordine.righe.values_list("pk", flat=True))
    return JsonResponse({"ok": True, "riga_ids": riga_ids})


def _invia_email_conferma_ricezione(ricezione, ordine, rettifiche):
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings as dj_settings
    from django.template.loader import render_to_string
    from core.pdf_generator import generate_pdf_from_html, PDFConfig
    import os

    fornitore = ricezione.fornitore
    destinatario = getattr(fornitore, "email", None) or getattr(fornitore, "referente_email", None)
    if not destinatario:
        return

    righe_ricevute = list(ricezione.righe.select_related("prodotto").all())

    corpo_lines = [
        f"Gentile {fornitore.ragione_sociale},",
        "",
        f"Vi confermiamo di aver ricevuto in data {ricezione.data_ricezione:%d/%m/%Y} "
        f"il materiale relativo all'ordine {ordine.numero_ordine}.",
    ]
    if ricezione.numero_ddt:
        corpo_lines.append(f"DDT di riferimento: {ricezione.numero_ddt}.")
    if rettifiche:
        corpo_lines += [
            "",
            "Si segnalano le seguenti differenze rispetto a quanto ordinato:",
        ]
        for r in rettifiche:
            corpo_lines.append(
                f"- {r['nome']}: ordinati {r['qty_ord']} {r['um']}, ricevuti {r['qty_ric']} {r['um']}."
            )
        corpo_lines += ["", "La presente comunicazione vale come rettifica dell'ordine."]
    corpo_lines += ["", "Distinti saluti.", "Ufficio amministrazione."]
    corpo = "\n".join(corpo_lines)

    subject = f"Conferma ricezione {ordine.numero_ordine} del {ricezione.data_ricezione:%d/%m/%Y}"
    if rettifiche:
        subject += " — con rettifiche"

    msg = EmailMultiAlternatives(
        subject=subject,
        body=corpo,
        from_email=dj_settings.DEFAULT_FROM_EMAIL,
        to=[destinatario],
    )

    # Allega PDF della ricezione
    pdf_html = render_to_string("magazzino/pdf/ricezione.html", {
        "ricezione": ricezione,
        "ordine": ordine,
        "righe": righe_ricevute,
        "rettifiche": rettifiche,
    })
    filename_pdf = f"ricezione_{ordine.numero_ordine}_{ricezione.data_ricezione:%Y%m%d}.pdf"
    pdf_buffer = generate_pdf_from_html(pdf_html, PDFConfig(filename=filename_pdf), output_type="buffer")
    if pdf_buffer:
        msg.attach(filename_pdf, pdf_buffer.read(), "application/pdf")

    # Allega bolla firmata se presente
    if ricezione.bolla_firmata:
        try:
            bolla_name = os.path.basename(ricezione.bolla_firmata.name)
            msg.attach(bolla_name, ricezione.bolla_firmata.read(), "application/octet-stream")
        except Exception:
            pass

    try:
        msg.send(fail_silently=False)
    except Exception:
        pass


@login_required
def ricezione_da_ordine(request, oda_pk):
    from acquisti.models import OrdineAcquisto
    from django.forms import inlineformset_factory
    from datetime import date

    ordine = get_object_or_404(
        OrdineAcquisto.objects.select_related("fornitore").prefetch_related("righe__prodotto"),
        pk=oda_pk,
    )

    stati_chiusi = (
        OrdineAcquisto.Stato.RICEVUTO,
        OrdineAcquisto.Stato.FATTURATO,
        OrdineAcquisto.Stato.PAGATO,
        OrdineAcquisto.Stato.ANNULLATO,
    )
    if ordine.stato in stati_chiusi:
        messages.error(request, f"L'ODA {ordine.numero_ordine} è già stato ricevuto e non può essere ricevuto nuovamente.")
        return redirect("acquisti:ordine_detail", pk=oda_pk)

    righe_mancanti = [
        r.descrizione or f"Riga #{r.pk}"
        for r in ordine.righe.all()
        if not r.prodotto_id
    ]
    if righe_mancanti:
        return render(request, "magazzino/ricezioni/form.html", {
            "righe_mancanti": righe_mancanti,
            "ordine": ordine,
            "back_url": reverse("acquisti:ordine_detail", kwargs={"pk": oda_pk}),
            "titolo": f"Ricevi ODA {ordine.numero_ordine}",
        })

    if request.method == "POST":
        form = RicezioneForm(request.POST, request.FILES)
        formset = RigaRicezioneFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            # Cattura le quantità originali prima della rettifica automatica
            oda_righe_originali = {
                r.pk: {
                    "nome": r.prodotto.nome_prodotto if r.prodotto else r.descrizione,
                    "um": (r.prodotto.unita_misura if r.prodotto else r.unita_misura) or "",
                    "qty_ord": r.quantita_ordinata,
                }
                for r in ordine.righe.all()
            }
            ricezione = form.save(commit=False)
            ricezione.created_by = request.user
            ricezione.save()
            formset.instance = ricezione
            formset.save()
            # Raccoglie le rettifiche (qty ricevuta ≠ qty originalmente ordinata)
            rettifiche = []
            for riga_ric in ricezione.righe.select_related("prodotto").all():
                if riga_ric.riga_ordine_id and riga_ric.riga_ordine_id in oda_righe_originali:
                    orig = oda_righe_originali[riga_ric.riga_ordine_id]
                    if riga_ric.quantita_ricevuta != orig["qty_ord"]:
                        rettifiche.append({
                            "nome": orig["nome"],
                            "um": orig["um"],
                            "qty_ord": orig["qty_ord"],
                            "qty_ric": riga_ric.quantita_ricevuta,
                        })
            _invia_email_conferma_ricezione(ricezione, ordine, rettifiche)
            messages.success(request, "Ricezione registrata.")
            return redirect("magazzino:ricezione_detail", pk=ricezione.pk)
    else:
        righe_residue = [r for r in ordine.righe.all() if r.prodotto_id and r.da_ricevere > 0]
        initial_righe = [
            {
                "riga_ordine": r.pk,
                "prodotto": r.prodotto_id,
                "quantita_ricevuta": r.da_ricevere,
                "prezzo_unitario": r.prezzo_unitario,
            }
            for r in righe_residue
        ]
        form = RicezioneForm(initial={
            "fornitore": ordine.fornitore_id,
            "ordine": ordine.pk,
            "data_ricezione": date.today(),
        })
        n = max(len(initial_righe), 1)
        DynFormSet = inlineformset_factory(
            Ricezione, RigaRicezione, form=RigaRicezioneForm,
            extra=n, can_delete=True, min_num=1, validate_min=True,
        )
        formset = DynFormSet(initial=initial_righe)

    return render(request, "magazzino/ricezioni/form.html", {
        "form": form,
        "formset": formset,
        "titolo": f"Ricevi ODA {ordine.numero_ordine}",
        "back_url": reverse("acquisti:ordine_detail", kwargs={"pk": oda_pk}),
        "ordine": ordine,
    })


@login_required
def api_scorta_prodotto(request, pk):
    from django.http import JsonResponse
    stabilimento_id = request.GET.get("stabilimento")
    try:
        prodotto = Prodotto.objects.get(pk=pk)
    except Prodotto.DoesNotExist:
        return JsonResponse({"ok": False})
    if stabilimento_id:
        scorta = ScortaStabilimento.objects.filter(
            prodotto_id=pk, stabilimento_id=stabilimento_id
        ).first()
        quantita = scorta.quantita if scorta else Decimal("0")
    else:
        from django.db.models import Sum
        quantita = ScortaStabilimento.objects.filter(prodotto_id=pk).aggregate(
            tot=Sum("quantita")
        )["tot"] or Decimal("0")
    return JsonResponse({"ok": True, "quantita": str(quantita), "um": prodotto.get_unita_misura_display()})


@login_required
def scorte_dashboard(request):
    from cespiti.models import Automezzo, Stabilimento
    stabilimenti = Stabilimento.objects.attivi().order_by("nome")
    mezzi = Automezzo.objects.filter(attivo=True).select_related("assegnato_a").order_by("targa")
    return render(request, "magazzino/scorte/dashboard.html", {
        "stabilimenti": stabilimenti,
        "mezzi": mezzi,
        "back_url": reverse("magazzino:dashboard"),
    })


@login_required
def scorte_stabilimento(request, pk):
    from cespiti.models import Stabilimento
    stabilimento = get_object_or_404(Stabilimento, pk=pk)
    scorte = (
        ScortaStabilimento.objects
        .filter(stabilimento=stabilimento)
        .select_related("prodotto__categoria")
        .order_by("prodotto__nome_prodotto")
    )
    return render(request, "magazzino/scorte/stabilimento.html", {
        "stabilimento": stabilimento,
        "scorte": scorte,
        "back_url": reverse("magazzino:scorte_dashboard"),
    })


@login_required
def rettifica_scorta(request, pk):
    from django import forms as dj_forms
    scorta = get_object_or_404(
        ScortaStabilimento.objects.select_related("prodotto", "stabilimento"), pk=pk
    )

    class RettificaForm(dj_forms.Form):
        nuova_quantita = dj_forms.DecimalField(
            label="Nuova giacenza",
            max_digits=12, decimal_places=3, min_value=0,
            widget=dj_forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
        )
        motivo = dj_forms.CharField(
            label="Motivo della rettifica",
            widget=dj_forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            min_length=5,
            error_messages={"min_length": "Inserire almeno 5 caratteri."},
        )

    if request.method == "POST":
        form = RettificaForm(request.POST)
        if form.is_valid():
            vecchia = scorta.quantita
            nuova = form.cleaned_data["nuova_quantita"]
            scorta.quantita = nuova
            scorta.save(update_fields=["quantita", "updated_at"])
            delta_str = f"+{nuova - vecchia}" if nuova >= vecchia else str(nuova - vecchia)
            messages.success(
                request,
                f"Rettifica '{scorta.prodotto}': {vecchia} → {nuova} ({delta_str}). "
                f"Motivo: {form.cleaned_data['motivo']}",
            )
        else:
            for field_errors in form.errors.values():
                for e in field_errors:
                    messages.error(request, e)
    return redirect("magazzino:scorte_stabilimento", pk=scorta.stabilimento_id)


@login_required
def scorte_mezzo(request, pk):
    from cespiti.models import Automezzo
    mezzo = get_object_or_404(Automezzo, pk=pk)
    from django.db.models import Subquery, OuterRef
    ultimo_mov_qs = (
        RigaCaricoMezzo.objects
        .filter(carico__mezzo=mezzo, prodotto=OuterRef("prodotto"))
        .order_by("-carico__data", "-carico__created_at")
        .values("carico__data")[:1]
    )
    scorte = (
        ScortaMezzo.objects
        .filter(mezzo=mezzo)
        .select_related("prodotto__categoria")
        .annotate(ultimo_movimento=Subquery(ultimo_mov_qs))
        .order_by("prodotto__nome_prodotto")
    )
    prodotto_ids = [s.prodotto_id for s in scorte]
    from django.db.models import Sum
    disp_per_prodotto = {
        entry["prodotto_id"]: entry["tot"]
        for entry in ScortaStabilimento.objects.filter(
            prodotto_id__in=prodotto_ids
        ).values("prodotto_id").annotate(tot=Sum("quantita"))
    }
    scorte_con_disp = [(s, disp_per_prodotto.get(s.prodotto_id, Decimal("0"))) for s in scorte]
    from cespiti.models import Stabilimento
    stabilimenti = Stabilimento.objects.attivi().order_by("nome")
    ctx = {
        "mezzo": mezzo,
        "scorte_con_disp": scorte_con_disp,
        "stabilimenti": stabilimenti,
        "back_url": reverse("magazzino:scorte_dashboard"),
    }
    return render(request, "magazzino/scorte/mezzo.html", ctx)


@login_required
def mezzo_operazione_rapida(request, mezzo_pk):
    """Carico o scarico rapido di un singolo prodotto su un mezzo."""
    from cespiti.models import Automezzo
    from django.db.models import F
    if request.method != "POST":
        return redirect("magazzino:scorte_mezzo", pk=mezzo_pk)

    from cespiti.models import Stabilimento
    mezzo = get_object_or_404(Automezzo, pk=mezzo_pk)
    prodotto = get_object_or_404(Prodotto, pk=request.POST.get("prodotto_id", 0))
    tipo = request.POST.get("tipo", "")
    stabilimento = get_object_or_404(Stabilimento, pk=request.POST.get("stabilimento_id", 0))
    try:
        quantita = Decimal(request.POST.get("quantita", "0"))
    except Exception:
        quantita = Decimal("0")

    if quantita <= 0:
        messages.error(request, "La quantità deve essere maggiore di zero.")
        return redirect("magazzino:scorte_mezzo", pk=mezzo_pk)

    if tipo == CaricoMezzo.Tipo.CARICO:
        scorta_stab = ScortaStabilimento.objects.filter(prodotto=prodotto, stabilimento=stabilimento).first()
        disp = scorta_stab.quantita if scorta_stab else Decimal("0")
        if disp < quantita:
            messages.error(request, f"Scorte '{stabilimento}' insufficienti per '{prodotto}': disponibili {disp}.")
            return redirect("magazzino:scorte_mezzo", pk=mezzo_pk)
    elif tipo == CaricoMezzo.Tipo.SCARICO:
        scorta_mezzo = ScortaMezzo.objects.filter(mezzo=mezzo, prodotto=prodotto).first()
        disp = scorta_mezzo.quantita if scorta_mezzo else Decimal("0")
        if disp < quantita:
            messages.error(request, f"Scorte mezzo insufficienti per '{prodotto}': disponibili {disp}.")
            return redirect("magazzino:scorte_mezzo", pk=mezzo_pk)
    else:
        messages.error(request, "Tipo operazione non valido.")
        return redirect("magazzino:scorte_mezzo", pk=mezzo_pk)

    carico = CaricoMezzo.objects.create(mezzo=mezzo, stabilimento=stabilimento, tipo=tipo, operatore=request.user)
    RigaCaricoMezzo.objects.create(carico=carico, prodotto=prodotto, quantita=quantita)

    if tipo == CaricoMezzo.Tipo.CARICO:
        ScortaStabilimento.aggiungi(prodotto.pk, stabilimento.pk, -quantita)
        sm, _ = ScortaMezzo.objects.get_or_create(mezzo=mezzo, prodotto=prodotto, defaults={"quantita": 0})
        ScortaMezzo.objects.filter(pk=sm.pk).update(quantita=F("quantita") + quantita)
        messages.success(request, f"Caricati {quantita} {prodotto.get_unita_misura_display()} di '{prodotto}' dal {stabilimento}.")
    else:
        ScortaStabilimento.aggiungi(prodotto.pk, stabilimento.pk, quantita)
        sm, _ = ScortaMezzo.objects.get_or_create(mezzo=mezzo, prodotto=prodotto, defaults={"quantita": 0})
        ScortaMezzo.objects.filter(pk=sm.pk).update(quantita=F("quantita") - quantita)
        messages.success(request, f"Scaricati {quantita} {prodotto.get_unita_misura_display()} di '{prodotto}' al {stabilimento}.")

    return redirect("magazzino:scorte_mezzo", pk=mezzo_pk)


@login_required
def carico_mezzo_list(request):
    from cespiti.models import Automezzo
    from servizi.models import ConsumoMateriale

    automezzi = Automezzo.objects.filter(attivo=True).order_by("targa")

    mezzo_pk = request.GET.get("mezzo", "").strip()
    data_da  = request.GET.get("data_da", "").strip()
    data_a   = request.GET.get("data_a", "").strip()
    filtro_attivo = bool(mezzo_pk)

    carichi      = CaricoMezzo.objects.none()
    uscite       = ConsumoMateriale.objects.none()

    if filtro_attivo:
        carichi = (
            CaricoMezzo.objects
            .filter(mezzo_id=mezzo_pk)
            .select_related("mezzo", "operatore", "stabilimento")
            .prefetch_related("righe__prodotto")
            .order_by("-data", "-created_at")
        )
        uscite = (
            ConsumoMateriale.objects
            .filter(riga__ods__distinta__mezzo_id=mezzo_pk, confermato=True)
            .select_related(
                "prodotto",
                "riga__ods__distinta",
                "riga__ods__filiale__cliente",
                "riga__ods__privato",
                "riga__servizio",
            )
            .order_by("-riga__ods__data_servizio")
        )
        if data_da:
            carichi = carichi.filter(data__gte=data_da)
            uscite  = uscite.filter(riga__ods__data_servizio__gte=data_da)
        if data_a:
            carichi = carichi.filter(data__lte=data_a)
            uscite  = uscite.filter(riga__ods__data_servizio__lte=data_a)

    return render(request, "magazzino/scorte/carico_list.html", {
        "automezzi":     automezzi,
        "mezzo_pk":      mezzo_pk,
        "data_da":       data_da,
        "data_a":        data_a,
        "filtro_attivo": filtro_attivo,
        "carichi":       carichi,
        "uscite":        uscite,
        "back_url":      reverse("magazzino:scorte_dashboard"),
    })


class CaricoMezzoDetailView(LoginRequiredMixin, DetailView):
    model = CaricoMezzo
    template_name = "magazzino/scorte/carico_detail.html"
    context_object_name = "carico"

    def get_queryset(self):
        return CaricoMezzo.objects.select_related("mezzo", "operatore").prefetch_related("righe__prodotto")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["back_url"] = reverse("magazzino:carico_mezzo_list")
        from django.contrib.contenttypes.models import ContentType
        ctx["content_type_id"] = ContentType.objects.get_for_model(self.model).pk
        ctx["object_id"] = self.object.pk
        return ctx


class CaricoMezzoUpdateView(LoginRequiredMixin, UpdateView):
    model = CaricoMezzo
    fields = ["note"]
    template_name = "magazzino/scorte/carico_update.html"
    context_object_name = "carico"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["note"].widget.attrs.update({"class": "form-control", "rows": 4})
        form.fields["note"].required = False
        return form

    def form_valid(self, form):
        messages.success(self.request, "Note aggiornate.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("magazzino:carico_mezzo_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["back_url"] = reverse("magazzino:carico_mezzo_detail", kwargs={"pk": self.object.pk})
        return ctx


@login_required
def carico_mezzo_delete(request, pk):
    from django import forms as dj_forms
    carico = get_object_or_404(CaricoMezzo.objects.prefetch_related("righe"), pk=pk)

    class MotivoForm(dj_forms.Form):
        motivo = dj_forms.CharField(
            label="Motivo dell'eliminazione",
            widget=dj_forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            min_length=10,
            error_messages={"min_length": "Il motivo deve essere di almeno 10 caratteri."},
        )

    if request.method == "POST":
        form = MotivoForm(request.POST)
        if form.is_valid():
            # Annulla i movimenti di scorta
            from django.db.models import F
            stab_id = carico.stabilimento_id
            for riga in carico.righe.all():
                if carico.tipo == CaricoMezzo.Tipo.CARICO:
                    # era uscito dallo stabilimento → lo rimettiamo
                    ScortaStabilimento.aggiungi(riga.prodotto_id, stab_id, riga.quantita)
                    sm = ScortaMezzo.objects.filter(mezzo=carico.mezzo, prodotto=riga.prodotto).first()
                    if sm:
                        ScortaMezzo.objects.filter(pk=sm.pk).update(quantita=F("quantita") - riga.quantita)
                else:
                    # era rientrato allo stabilimento → lo sottraiamo
                    ScortaStabilimento.aggiungi(riga.prodotto_id, stab_id, -riga.quantita)
                    sm, _ = ScortaMezzo.objects.get_or_create(
                        mezzo=carico.mezzo, prodotto=riga.prodotto, defaults={"quantita": 0}
                    )
                    ScortaMezzo.objects.filter(pk=sm.pk).update(quantita=F("quantita") + riga.quantita)
            carico.delete()
            messages.success(
                request,
                f"Movimento eliminato. Motivo: {form.cleaned_data['motivo']}",
            )
            return redirect("magazzino:carico_mezzo_list")
    else:
        form = MotivoForm()

    return render(request, "magazzino/scorte/carico_confirm_delete.html", {
        "carico": carico,
        "form": form,
        "back_url": reverse("magazzino:carico_mezzo_detail", kwargs={"pk": pk}),
    })


class CaricoMezzoCreateView(LoginRequiredMixin, CreateView):
    model = CaricoMezzo
    form_class = CaricoMezzoForm
    template_name = "magazzino/scorte/carico_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = RigaCaricoMezzoFormSet(self.request.POST)
        else:
            ctx["formset"] = RigaCaricoMezzoFormSet()
        ctx["titolo"] = "Nuovo Carico/Scarico Mezzo"
        ctx["back_url"] = reverse("magazzino:carico_mezzo_list")
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        tipo = form.cleaned_data["tipo"]
        righe_valide = [f for f in formset if f.cleaned_data and not f.cleaned_data.get("DELETE")]

        stabilimento = form.cleaned_data.get("stabilimento")
        stab_id = stabilimento.pk if stabilimento else None

        # Verifica disponibilità scorte prima di salvare
        for riga_form in righe_valide:
            prodotto = riga_form.cleaned_data["prodotto"]
            qty = riga_form.cleaned_data["quantita"]
            if tipo == CaricoMezzo.Tipo.CARICO:
                scorta = ScortaStabilimento.objects.filter(prodotto=prodotto, stabilimento=stabilimento).first() if stabilimento else None
                disponibile = scorta.quantita if scorta else Decimal("0")
                if disponibile < qty:
                    form.add_error(None, f"Scorte '{stabilimento}' insufficienti per '{prodotto}': disponibili {disponibile}, richiesti {qty}.")
                    return self.render_to_response(self.get_context_data(form=form))
            else:
                scorta = ScortaMezzo.objects.filter(mezzo=form.cleaned_data["mezzo"], prodotto=prodotto).first()
                disponibile = scorta.quantita if scorta else Decimal("0")
                if disponibile < qty:
                    form.add_error(None, f"Scorte mezzo insufficienti per '{prodotto}': disponibili {disponibile}, richiesti {qty}.")
                    return self.render_to_response(self.get_context_data(form=form))

        self.object = form.save(commit=False)
        self.object.operatore = self.request.user
        self.object.save()
        formset.instance = self.object
        formset.save()

        # Aggiorna scorte
        mezzo = self.object.mezzo
        from django.db.models import F
        for riga in self.object.righe.all():
            if tipo == CaricoMezzo.Tipo.CARICO:
                ScortaStabilimento.aggiungi(riga.prodotto_id, stab_id, -riga.quantita)
                sm, _ = ScortaMezzo.objects.get_or_create(mezzo=mezzo, prodotto=riga.prodotto, defaults={"quantita": 0})
                ScortaMezzo.objects.filter(pk=sm.pk).update(quantita=F("quantita") + riga.quantita)
            else:
                ScortaStabilimento.aggiungi(riga.prodotto_id, stab_id, riga.quantita)
                sm, _ = ScortaMezzo.objects.get_or_create(mezzo=mezzo, prodotto=riga.prodotto, defaults={"quantita": 0})
                ScortaMezzo.objects.filter(pk=sm.pk).update(quantita=F("quantita") - riga.quantita)

        messages.success(self.request, f"{self.object.get_tipo_display()} registrato.")
        return redirect("magazzino:carico_mezzo_detail", pk=self.object.pk)


@login_required
def prodotto_invia_scheda(request, pk):
    prodotto = get_object_or_404(Prodotto, pk=pk)
    if request.method == "POST":
        destinatario = request.POST.get("destinatario", "").strip()
        oggetto = request.POST.get("oggetto", "").strip()
        body = request.POST.get("body", "").strip()
        if not destinatario:
            messages.error(request, "Inserisci un destinatario.")
            return redirect("magazzino:prodotto_detail", pk=pk)
        from django.core.mail import EmailMessage
        from django.conf import settings
        msg = EmailMessage(
            subject=oggetto or f"Scheda tecnica: {prodotto.nome_prodotto}",
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        if prodotto.scheda_tecnica:
            msg.attach_file(prodotto.scheda_tecnica.path)
        try:
            msg.send(fail_silently=False)
            messages.success(request, f"Email inviata a {destinatario}.")
        except Exception as e:
            messages.error(request, f"Errore invio email: {e}")
    return redirect("magazzino:prodotto_detail", pk=pk)
