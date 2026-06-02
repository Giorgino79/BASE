from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse

from .models import OrdineAcquisto, RigaOrdine, FatturaPassiva
from .forms import OrdineAcquistoForm, RigaOrdineFormSet, FatturaPassivaForm
from .mailer import invia_oda


def _prodotti_um_json():
    import json
    try:
        from magazzino.models import Prodotto
        data = {p.pk: p.get_unita_misura_display() for p in Prodotto.objects.filter(attivo=True).only("pk", "unita_misura")}
    except Exception:
        data = {}
    return json.dumps(data)


@login_required
def dashboard(request):
    from django.utils import timezone
    today = timezone.localdate()
    stati_aperti = ["bozza", "inviato", "ricevuto_parz"]
    ctx = {
        "oda_da_ricevere": OrdineAcquisto.objects.filter(stato__in=stati_aperti).count(),
        "oda_in_ritardo": OrdineAcquisto.objects.filter(
            stato__in=stati_aperti,
            data_consegna_richiesta__isnull=False,
            data_consegna_richiesta__lt=today,
        ).count(),
        "fatture_da_ricevere": OrdineAcquisto.objects.filter(
            stato="ricevuto", fatture__isnull=True
        ).count(),
        "fatture_da_pagare": FatturaPassiva.objects.filter(stato_pagamento="da_pagare").count(),
        "ultimi_ordini": OrdineAcquisto.objects.select_related("fornitore").order_by("-created_at")[:5],
        "ultime_fatture": FatturaPassiva.objects.select_related("fornitore").order_by("-data_fattura")[:5],
    }
    return render(request, "acquisti/dashboard.html", ctx)


# ── ODA ────────────────────────────────────────────────────────

class OrdineListView(LoginRequiredMixin, ListView):
    model = OrdineAcquisto
    template_name = "acquisti/ordini/list.html"
    context_object_name = "ordini"
    paginate_by = 20

    def get_queryset(self):
        qs = OrdineAcquisto.objects.select_related("fornitore").order_by("-data_ordine", "-created_at")
        stato = self.request.GET.get("stato")
        if stato:
            qs = qs.filter(stato=stato)
        q = self.request.GET.get("q")
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(numero_ordine__icontains=q) | Q(fornitore__ragione_sociale__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stato_choices"] = OrdineAcquisto.Stato.choices
        ctx["stato_sel"] = self.request.GET.get("stato", "")
        return ctx


class OrdineDetailView(LoginRequiredMixin, DetailView):
    model = OrdineAcquisto
    template_name = "acquisti/ordini/dettaglio.html"
    context_object_name = "ordine"

    def get_queryset(self):
        return OrdineAcquisto.objects.select_related("fornitore", "created_by").prefetch_related(
            "righe__prodotto", "fatture"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stato_choices"] = OrdineAcquisto.Stato.choices
        ctx["back_url"] = reverse("acquisti:ordine_list")
        ctx["edit_url"] = reverse("acquisti:ordine_update", kwargs={"pk": self.object.pk})
        from django.contrib.contenttypes.models import ContentType
        ctx["content_type_id"] = ContentType.objects.get_for_model(self.model).pk
        ctx["object_id"] = self.object.pk
        return ctx


class OrdineCreateView(LoginRequiredMixin, CreateView):
    model = OrdineAcquisto
    form_class = OrdineAcquistoForm
    template_name = "acquisti/ordini/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = RigaOrdineFormSet(self.request.POST)
        else:
            ctx["formset"] = RigaOrdineFormSet()
        ctx["titolo"] = "Nuovo Ordine di Acquisto"
        ctx["back_url"] = reverse("acquisti:ordine_list")
        ctx["prodotti_um_json"] = _prodotti_um_json()
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
            # Invio automatico al fornitore
            inviata, errore = invia_oda(self.object)
            if inviata:
                self.object.stato = OrdineAcquisto.Stato.INVIATO
                self.object.save(update_fields=["stato"])
                messages.success(self.request, f"Ordine {self.object.numero_ordine} creato e inviato al fornitore.")
            else:
                messages.success(self.request, f"Ordine {self.object.numero_ordine} creato.")
                messages.warning(self.request, f"Email non inviata: {errore}")
            return redirect("acquisti:ordine_detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form))


class OrdineUpdateView(LoginRequiredMixin, UpdateView):
    model = OrdineAcquisto
    form_class = OrdineAcquistoForm
    template_name = "acquisti/ordini/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = RigaOrdineFormSet(self.request.POST, instance=self.object)
        else:
            ctx["formset"] = RigaOrdineFormSet(instance=self.object)
        ctx["titolo"] = f"Modifica {self.object.numero_ordine}"
        ctx["back_url"] = reverse("acquisti:ordine_detail", kwargs={"pk": self.object.pk})
        ctx["prodotti_um_json"] = _prodotti_um_json()
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "Ordine aggiornato.")
            return redirect("acquisti:ordine_detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form))


class OrdineDeleteView(LoginRequiredMixin, DeleteView):
    model = OrdineAcquisto
    template_name = "acquisti/ordini/confirm_delete.html"
    success_url = reverse_lazy("acquisti:ordine_list")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f"Ordine {obj.numero_ordine} eliminato.")
        return super().delete(request, *args, **kwargs)


@login_required
def ordine_pdf(request, pk):
    ordine = get_object_or_404(OrdineAcquisto.objects.prefetch_related("righe__prodotto"), pk=pk)
    from django.template.loader import render_to_string
    from core.pdf_generator import generate_pdf_from_html, PDFConfig
    context = {
        "ordine": ordine,
        "righe": list(ordine.righe.select_related("prodotto").all()),
    }
    html = render_to_string("acquisti/pdf/oda.html", context)
    return generate_pdf_from_html(
        html,
        PDFConfig(filename=f"{ordine.numero_ordine}.pdf"),
        output_type="response",
    )


@login_required
def ordine_reinvia_mail(request, pk):
    ordine = get_object_or_404(OrdineAcquisto, pk=pk)
    if request.method == "POST":
        inviata, errore = invia_oda(ordine)
        if inviata:
            messages.success(request, f"Email reinviata al fornitore per {ordine.numero_ordine}.")
        else:
            messages.warning(request, f"Email non inviata: {errore}")
    return redirect("acquisti:ordine_detail", pk=pk)


@login_required
def ordine_set_stato(request, pk):
    ordine = get_object_or_404(OrdineAcquisto, pk=pk)
    if request.method == "POST":
        nuovo_stato = request.POST.get("stato")
        stati_validi = [s[0] for s in OrdineAcquisto.Stato.choices]
        if nuovo_stato in stati_validi:
            ordine.stato = nuovo_stato
            ordine.save(update_fields=["stato"])
            messages.success(request, f"Stato aggiornato: {ordine.get_stato_display()}")
    return redirect("acquisti:ordine_detail", pk=pk)


# ── FATTURE PASSIVE ────────────────────────────────────────────

class FatturaListView(LoginRequiredMixin, ListView):
    model = FatturaPassiva
    template_name = "acquisti/fatture/list.html"
    context_object_name = "fatture"
    paginate_by = 20

    def get_queryset(self):
        qs = FatturaPassiva.objects.select_related("fornitore").order_by("-data_fattura")
        stato = self.request.GET.get("stato")
        if stato:
            qs = qs.filter(stato_pagamento=stato)
        q = self.request.GET.get("q")
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(numero_fattura__icontains=q) | Q(fornitore__ragione_sociale__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stato_choices"] = FatturaPassiva.StatoPagamento.choices
        ctx["stato_sel"] = self.request.GET.get("stato", "")
        return ctx


class FatturaDetailView(LoginRequiredMixin, DetailView):
    model = FatturaPassiva
    template_name = "acquisti/fatture/dettaglio.html"
    context_object_name = "fattura"

    def get_queryset(self):
        return FatturaPassiva.objects.select_related("fornitore", "created_by").prefetch_related("ordini")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["back_url"] = reverse("acquisti:fattura_list")
        ctx["edit_url"] = reverse("acquisti:fattura_update", kwargs={"pk": self.object.pk})
        return ctx


class FatturaCreateView(LoginRequiredMixin, CreateView):
    model = FatturaPassiva
    form_class = FatturaPassivaForm
    template_name = "acquisti/fatture/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = "Nuova Fattura Passiva"
        ctx["back_url"] = reverse("acquisti:fattura_list")
        return ctx

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user
        self.object.save()
        form.save_m2m()
        messages.success(self.request, "Fattura registrata.")
        return redirect("acquisti:fattura_detail", pk=self.object.pk)


class FatturaUpdateView(LoginRequiredMixin, UpdateView):
    model = FatturaPassiva
    form_class = FatturaPassivaForm
    template_name = "acquisti/fatture/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titolo"] = f"Modifica Fattura {self.object.numero_fattura}"
        ctx["back_url"] = reverse("acquisti:fattura_detail", kwargs={"pk": self.object.pk})
        return ctx

    def get_success_url(self):
        return reverse("acquisti:fattura_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Fattura aggiornata.")
        return super().form_valid(form)


class FatturaDeleteView(LoginRequiredMixin, DeleteView):
    model = FatturaPassiva
    template_name = "acquisti/fatture/confirm_delete.html"
    success_url = reverse_lazy("acquisti:fattura_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Fattura eliminata.")
        return super().delete(request, *args, **kwargs)


# ── AUTOFATTURAZIONE ───────────────────────────────────────────

@login_required
def autofatturazione(request):
    from anagrafica_r2.models import Fornitore
    from core.excel_generator import generate_excel_response
    from core.pdf_generator import generate_pdf_from_html, PDFConfig
    from django.template.loader import render_to_string
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings

    fornitori = Fornitore.objects.order_by("ragione_sociale")
    fornitore_pk = request.POST.get("fornitore") or request.GET.get("fornitore", "")
    fornitore = Fornitore.objects.filter(pk=fornitore_pk).first() if fornitore_pk else None

    oda_qs = (
        OrdineAcquisto.objects
        .filter(fornitore=fornitore, stato="ricevuto", fatture__isnull=True)
        .prefetch_related("righe__prodotto")
        .order_by("data_ordine")
        if fornitore else OrdineAcquisto.objects.none()
    )

    action = request.POST.get("action", "")

    if request.method == "POST" and action in ("excel", "pdf", "invia"):
        pks = request.POST.getlist("oda_pks")
        ordini = (
            OrdineAcquisto.objects
            .filter(pk__in=pks, fornitore=fornitore)
            .prefetch_related("righe__prodotto")
            .order_by("data_ordine")
        )
        if not ordini:
            messages.warning(request, "Nessun ordine selezionato.")
            return redirect(f"{request.path}?fornitore={fornitore_pk}")

        if action == "excel":
            rows = []
            for oda in ordini:
                for r in oda.righe.all():
                    prodotto_nome = r.prodotto.nome_prodotto if r.prodotto else r.descrizione or "—"
                    um = r.prodotto.unita_misura if r.prodotto else r.unita_misura or "—"
                    rows.append({
                        "N° Ordine":      oda.numero_ordine,
                        "Data ordine":    oda.data_ordine,
                        "Fornitore":      str(oda.fornitore),
                        "Prodotto":       prodotto_nome,
                        "UM":             um,
                        "Qt. ordinata":   r.quantita_ordinata,
                        "Prezzo unit.":   r.prezzo_unitario,
                        "Totale riga":    r.imponibile,
                    })
            filename = f"autofatturazione_{fornitore.ragione_sociale}".replace(" ", "_")
            return generate_excel_response(rows, filename=filename, sheet_name="Autofatturazione")

        if action in ("pdf", "invia"):
            ctx = {
                "fornitore":  fornitore,
                "ordini":     [(oda, list(oda.righe.all())) for oda in ordini],
                "data_oggi":  __import__("django.utils.timezone", fromlist=["localdate"]).localdate(),
            }
            pdf_html = render_to_string("acquisti/pdf/autofatturazione.html", ctx)
            filename = f"autofatturazione_{fornitore.ragione_sociale}.pdf".replace(" ", "_")

            if action == "pdf":
                return generate_pdf_from_html(pdf_html, PDFConfig(filename=filename), output_type="response")

            # invia email
            destinatario = fornitore.email or fornitore.referente_email
            if not destinatario:
                messages.error(request, f"Nessun indirizzo email per il fornitore {fornitore}.")
                return redirect(f"{request.path}?fornitore={fornitore_pk}")

            corpo = (
                "Salve,\n\n"
                "in allegato l'autofatturazione degli acquisti effettuati presso la vs azienda "
                "per cui non abbiamo ancora ricevuto fattura.\n\n"
                "Distinti saluti.\n"
                "Ufficio amministrazione."
            )
            msg = EmailMultiAlternatives(
                subject=f"Autofatturazione ordini — {fornitore.ragione_sociale}",
                body=corpo,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[destinatario],
            )
            pdf_buffer = generate_pdf_from_html(pdf_html, PDFConfig(filename=filename), output_type="buffer")
            if pdf_buffer:
                msg.attach(filename, pdf_buffer.read(), "application/pdf")
            try:
                msg.send(fail_silently=False)
                messages.success(request, f"Email inviata a {destinatario}.")
            except Exception as e:
                messages.error(request, f"Errore invio email: {e}")
            return redirect(f"{request.path}?fornitore={fornitore_pk}")

    return render(request, "acquisti/autofatturazione.html", {
        "fornitori":    fornitori,
        "fornitore":    fornitore,
        "fornitore_pk": str(fornitore_pk),
        "oda_qs":       oda_qs,
    })
