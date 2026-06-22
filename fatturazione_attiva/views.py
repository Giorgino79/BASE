from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings as django_settings
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin

from core.excel_generator import generate_excel_response
from core.pdf_generator import generate_pdf_from_html, PDFConfig
from servizi.models import ODS, CondominioODS, ODSRiga
from .forms import RicercaFatturazioneForm, RicercaFattureForm
from .models import Fattura, RigaFattura, NotaCredito


# ── Dashboard fatturazione ────────────────────────────────────────────────────

class FatturazioneDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "fatturazione_attiva/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        anno = timezone.localdate().year

        fatture_anno = Fattura.objects.filter(anno=anno).exclude(stato=Fattura.Stato.ANNULLATA)
        da_incassare = Fattura.objects.filter(stato=Fattura.Stato.EMESSA)

        ctx["anno"] = anno
        ctx["n_fatture_anno"]        = fatture_anno.count()
        ctx["totale_fatturato_anno"] = fatture_anno.aggregate(t=Sum("totale"))["t"] or Decimal("0.00")
        ctx["n_da_incassare"]        = da_incassare.count()
        ctx["totale_da_incassare"]   = da_incassare.aggregate(t=Sum("totale"))["t"] or Decimal("0.00")
        ctx["ultime_fatture"]        = Fattura.objects.order_by("-anno", "-progressivo")[:6]
        return ctx


# ── Fatture da incassare ──────────────────────────────────────────────────────

class FattureDaIncassareView(LoginRequiredMixin, TemplateView):
    template_name = "fatturazione_attiva/da_incassare.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        oggi = timezone.localdate()

        fatture = list(
            Fattura.objects
            .filter(stato=Fattura.Stato.EMESSA)
            .prefetch_related("righe")
            .order_by("data_emissione")
        )
        totale = sum((f.totale for f in fatture), Decimal("0.00"))
        ctx["fatture"] = fatture
        ctx["totale"]  = totale
        ctx["n"]       = len(fatture)
        return ctx


# ── Sollecito pagamento (JSON) ─────────────────────────────────────────────────

def _email_cliente(fattura):
    """Restituisce (email_principale, email_secondaria) dal cliente collegato alla fattura."""
    ods = fattura.ods.select_related(
        "filiale__cliente", "privato"
    ).first()
    if not ods:
        return fattura.dest_pec or "", ""
    if ods.filiale and ods.filiale.cliente:
        c = ods.filiale.cliente
        prima    = c.email_amministrazione or ""
        seconda  = c.email_operativo if prima else ""
        if not prima:
            prima = c.email_operativo or ""
        return prima, seconda
    if ods.privato:
        return ods.privato.email or "", ""
    return fattura.dest_pec or "", ""


@login_required
def fattura_sollecito(request, pk):
    fattura = get_object_or_404(Fattura, pk=pk)
    if request.method == "POST":
        # Segna sollecito inviato (data)
        fattura.data_ultimo_sollecito = timezone.localdate()
        fattura.save(update_fields=["data_ultimo_sollecito", "updated_at"])
        return JsonResponse({"ok": True})
    # GET — restituisce testo sollecito + email di default
    email_a, email_cc = _email_cliente(fattura)
    data = fattura.get_sollecito()
    data["email_a"]  = email_a
    data["email_cc"] = email_cc
    return JsonResponse(data)


@login_required
@require_POST
def invia_sollecito(request, pk):
    """Invia il sollecito via email e segna la data."""
    from django.core.mail import EmailMessage as DjangoEmail
    from django.conf import settings as cfg

    fattura   = get_object_or_404(Fattura, pk=pk)
    email_a   = request.POST.get("email_a", "").strip()
    email_cc  = [e.strip() for e in request.POST.get("email_cc", "").split(",") if e.strip()]
    oggetto   = request.POST.get("oggetto", fattura.get_sollecito()["soggetto"]).strip()
    corpo     = request.POST.get("corpo", fattura.get_sollecito()["corpo"]).strip()

    if not email_a:
        return JsonResponse({"ok": False, "error": "Indirizzo email obbligatorio."})

    try:
        msg = DjangoEmail(
            subject=oggetto,
            body=corpo,
            from_email=cfg.DEFAULT_FROM_EMAIL,
            to=[email_a],
            cc=email_cc,
        )
        msg.send()
        fattura.data_ultimo_sollecito = timezone.localdate()
        fattura.save(update_fields=["data_ultimo_sollecito", "updated_at"])
        return JsonResponse({"ok": True})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)})


# ── Ricerca ODS da fatturare ──────────────────────────────────────────────────

class RicercaFatturazioneView(LoginRequiredMixin, TemplateView):
    template_name = "fatturazione_attiva/ricerca.html"

    def get(self, request, *args, **kwargs):
        form = RicercaFatturazioneForm(request.GET or None)
        ctx = self.get_context_data(form=form)
        if request.GET and form.is_valid():
            ctx.update(self._cerca(form.cleaned_data))
        return self.render_to_response(ctx)

    def _cerca(self, cd):
        tipo            = cd["tipo"]
        data_da         = cd.get("data_da")
        data_a          = cd.get("data_a")
        solo_completati = cd.get("solo_completati", True)

        ods_qs       = ODS.objects.none()
        condomini_qs = CondominioODS.objects.none()

        if tipo in ("azienda", "privato"):
            ods_qs = (ODS.objects
                      .select_related("filiale__cliente", "privato", "tecnico")
                      .exclude(stato=ODS.Stato.FATTURATO))

            if tipo == "azienda":
                ods_qs = ods_qs.filter(filiale__cliente=cd["azienda"])
            else:
                ods_qs = ods_qs.filter(privato=cd["privato"])

            if solo_completati:
                ods_qs = ods_qs.filter(stato=ODS.Stato.COMPLETATO)
            if data_da:
                ods_qs = ods_qs.filter(data_servizio__gte=data_da)
            if data_a:
                ods_qs = ods_qs.filter(data_servizio__lte=data_a)
            ods_qs = ods_qs.order_by("data_servizio")

        elif tipo == "condominio":
            condomini_qs = (CondominioODS.objects
                            .filter(stabile=cd["stabile"])
                            .prefetch_related("unita"))
            if solo_completati:
                condomini_qs = condomini_qs.filter(stato=CondominioODS.Stato.COMPLETATO)
            if data_da:
                condomini_qs = condomini_qs.filter(data__gte=data_da)
            if data_a:
                condomini_qs = condomini_qs.filter(data__lte=data_a)
            condomini_qs = condomini_qs.order_by("data")

        ods_righe, totale_ods = _build_ods_righe(ods_qs)
        totale_condomini = sum(
            (c.totale_da_incassare for c in condomini_qs), Decimal("0.00")
        )

        return {
            "ods_righe":        ods_righe,
            "condomini_list":   condomini_qs,
            "n_ods":            len({r["ods"].pk for r in ods_righe}),
            "totale_ods":       totale_ods,
            "totale_condomini": totale_condomini,
            "totale_generale":  totale_ods + totale_condomini,
            "ricerca_eseguita": True,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("ods_righe", [])
        ctx.setdefault("condomini_list", [])
        ctx.setdefault("n_ods", 0)
        ctx.setdefault("ricerca_eseguita", False)
        return ctx


# ── Azione fatturazione ───────────────────────────────────────────────────────

@login_required
@require_POST
def azione_fatturazione(request):
    """POST: action=pdf|excel|fattura, sel[]=lista di "r-{riga_pk}" o "o-{ods_pk}"."""
    action    = request.POST.get("action", "pdf")
    selezione = request.POST.getlist("sel")

    if not selezione:
        messages.warning(request, "Nessuna riga selezionata.")
        return redirect(request.META.get("HTTP_REFERER", "fatturazione_attiva:ricerca"))

    righe_rows = _load_selezione(selezione)
    if not righe_rows:
        messages.warning(request, "Nessun elemento valido nella selezione.")
        return redirect(request.META.get("HTTP_REFERER", "fatturazione_attiva:ricerca"))

    if action == "excel":
        return _export_excel(righe_rows)

    if action == "pdf":
        # Anteprima senza salvare
        ctx = _build_pdf_ctx_da_righe(righe_rows, is_fattura=False)
        html = render_to_string("fatturazione_attiva/pdf_fattura.html", ctx)
        buf = generate_pdf_from_html(html, PDFConfig(filename="controllo.pdf"), output_type="buffer")
        if buf:
            resp = HttpResponse(buf.read(), content_type="application/pdf")
            resp["Content-Disposition"] = 'inline; filename="controllo.pdf"'
            return resp

    if action == "fattura":
        # Crea la fattura nel DB e genera il PDF
        fattura = Fattura.crea(righe_rows, emessa_da=request.user)
        messages.success(request, f"Fattura {fattura.numero} emessa con successo.")
        return redirect("fatturazione_attiva:fattura_detail", pk=fattura.pk)

    return redirect(request.META.get("HTTP_REFERER", "fatturazione_attiva:ricerca"))


# ── Lista fatture emesse ──────────────────────────────────────────────────────

class FattureListView(LoginRequiredMixin, TemplateView):
    template_name = "fatturazione_attiva/fatture_list.html"

    def get(self, request, *args, **kwargs):
        form = RicercaFattureForm(request.GET or None)
        ctx  = self.get_context_data(form=form)
        if request.GET and form.is_valid():
            ctx.update(self._cerca(form.cleaned_data))
        return self.render_to_response(ctx)

    def _cerca(self, cd):
        qs = Fattura.objects.prefetch_related("righe")

        tipo = cd.get("tipo_cliente")
        if tipo == "azienda" and cd.get("azienda"):
            qs = qs.filter(
                ods__filiale__cliente=cd["azienda"]
            ).distinct()
        elif tipo == "privato" and cd.get("privato"):
            qs = qs.filter(ods__privato=cd["privato"]).distinct()

        if cd.get("data_da"):
            qs = qs.filter(data_emissione__gte=cd["data_da"])
        if cd.get("data_a"):
            qs = qs.filter(data_emissione__lte=cd["data_a"])

        incasso = cd.get("incasso", "tutti")
        if incasso == "da_incassare":
            qs = qs.filter(stato=Fattura.Stato.EMESSA)
        elif incasso == "incassate":
            qs = qs.filter(stato=Fattura.Stato.PAGATA)

        qs = qs.order_by("-anno", "-progressivo")
        fatture = list(qs)

        totale_emesso  = sum((f.totale for f in fatture if f.stato != Fattura.Stato.ANNULLATA), Decimal("0.00"))
        totale_pagato  = sum((f.totale for f in fatture if f.stato == Fattura.Stato.PAGATA), Decimal("0.00"))
        n_da_incassare = sum(1 for f in fatture if f.stato == Fattura.Stato.EMESSA)

        return {
            "fatture":          fatture,
            "totale_emesso":    totale_emesso,
            "totale_pagato":    totale_pagato,
            "n_da_incassare":   n_da_incassare,
            "ricerca_eseguita": True,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("fatture", [])
        ctx.setdefault("ricerca_eseguita", False)
        return ctx


# ── Dettaglio fattura (con download PDF) ─────────────────────────────────────

class FatturaDetailView(LoginRequiredMixin, DetailView):
    model = Fattura
    template_name = "fatturazione_attiva/fattura_detail.html"
    context_object_name = "fattura"


@login_required
def fattura_pdf(request, pk):
    """Rigenera il PDF di una fattura già emessa dai dati salvati nel DB."""
    fattura = get_object_or_404(Fattura, pk=pk)

    # Adatta le righe salvate al formato dict atteso dal template
    from types import SimpleNamespace
    righe = []
    prev_ods = None
    for r in fattura.righe.all():
        is_new = r.ods_numero != prev_ods
        ods_ns  = SimpleNamespace(numero=r.ods_numero, data_servizio=r.data_servizio, filiale=None)
        riga_ns = SimpleNamespace(
            servizio=SimpleNamespace(nome=r.descrizione),
            prezzo=r.importo,
            note=r.note,
        )
        righe.append({"ods": ods_ns, "riga": riga_ns, "is_new_ods": is_new})
        prev_ods = r.ods_numero

    ctx = {
        "righe": righe,
        "azienda": {
            "RAGIONE_SOCIALE": fattura.emit_ragione_sociale,
            "INDIRIZZO":       fattura.emit_indirizzo,
            "CAP_CITTA":       fattura.emit_cap_citta,
            "PARTITA_IVA":     fattura.emit_partita_iva,
            "CODICE_FISCALE":  fattura.emit_codice_fiscale,
            "TELEFONO":        fattura.emit_telefono,
            "EMAIL":           fattura.emit_email,
            "IBAN":            fattura.emit_iban,
            "NOTE_PAGAMENTO":  fattura.note_pagamento,
        },
        "destinatario": {
            "nome":            fattura.dest_nome,
            "indirizzo":       fattura.dest_indirizzo,
            "cap":             fattura.dest_cap,
            "citta":           fattura.dest_citta,
            "provincia":       fattura.dest_provincia,
            "partita_iva":     fattura.dest_partita_iva,
            "codice_fiscale":  fattura.dest_codice_fiscale,
            "pec":             fattura.dest_pec,
        },
        "is_fattura":       True,
        "numero_documento": fattura.numero,
        "data_documento":   fattura.data_emissione,
        "aliquota_iva":     fattura.aliquota_iva,
        "imponibile":       fattura.imponibile,
        "importo_iva":      fattura.importo_iva,
        "totale_fattura":   fattura.totale,
    }
    html = render_to_string("fatturazione_attiva/pdf_fattura.html", ctx, request=request)
    return generate_pdf_from_html(
        html,
        PDFConfig(filename=f"{fattura.numero}.pdf"),
        output_type="response",
    )


@login_required
@require_POST
def fattura_segna_pagata(request, pk):
    fattura = get_object_or_404(Fattura, pk=pk)
    if fattura.stato == Fattura.Stato.EMESSA:
        fattura.stato = Fattura.Stato.PAGATA
        fattura.data_pagamento = timezone.localdate()
        fattura.save(update_fields=["stato", "data_pagamento", "updated_at"])
        messages.success(request, f"Fattura {fattura.numero} segnata come pagata.")
    return redirect("fatturazione_attiva:fattura_detail", pk=pk)


# ── Nota di Credito ───────────────────────────────────────────────────────────

@login_required
@require_POST
def emetti_nota_credito(request, pk):
    fattura = get_object_or_404(Fattura, pk=pk)
    tipo    = request.POST.get("tipo", "totale")
    note    = request.POST.get("note", "").strip()

    if tipo == "totale":
        imponibile = fattura.imponibile
    else:
        raw = request.POST.get("imponibile", "").replace(",", ".")
        try:
            imponibile = Decimal(raw)
        except Exception:
            messages.error(request, "Importo non valido.")
            return redirect("fatturazione_attiva:fattura_detail", pk=pk)
        if imponibile <= 0 or imponibile > fattura.imponibile:
            messages.error(
                request,
                f"L'importo deve essere positivo e non superiore a € {fattura.imponibile}.",
            )
            return redirect("fatturazione_attiva:fattura_detail", pk=pk)

    nc = NotaCredito.crea(fattura=fattura, imponibile=imponibile, note=note, emessa_da=request.user)
    messages.success(request, f"Nota di credito {nc.numero} emessa con successo.")
    return redirect("fatturazione_attiva:nc_detail", pk=nc.pk)


class NotaCreditoDetailView(LoginRequiredMixin, DetailView):
    model = NotaCredito
    template_name = "fatturazione_attiva/nc_detail.html"
    context_object_name = "nc"


@login_required
def nc_pdf(request, pk):
    nc = get_object_or_404(NotaCredito, pk=pk)
    ctx = {
        "nc": nc,
        "azienda": {
            "RAGIONE_SOCIALE": nc.emit_ragione_sociale,
            "INDIRIZZO":       nc.emit_indirizzo,
            "CAP_CITTA":       nc.emit_cap_citta,
            "PARTITA_IVA":     nc.emit_partita_iva,
            "CODICE_FISCALE":  nc.emit_codice_fiscale,
            "TELEFONO":        nc.emit_telefono,
            "EMAIL":           nc.emit_email,
            "IBAN":            nc.emit_iban,
        },
        "destinatario": {
            "nome":            nc.dest_nome,
            "indirizzo":       nc.dest_indirizzo,
            "cap":             nc.dest_cap,
            "citta":           nc.dest_citta,
            "provincia":       nc.dest_provincia,
            "partita_iva":     nc.dest_partita_iva,
            "codice_fiscale":  nc.dest_codice_fiscale,
            "pec":             nc.dest_pec,
        },
    }
    html = render_to_string("fatturazione_attiva/pdf_nc.html", ctx, request=request)
    return generate_pdf_from_html(
        html,
        PDFConfig(filename=f"{nc.numero}.pdf"),
        output_type="response",
    )


@login_required
@require_POST
def fattura_annulla(request, pk):
    fattura = get_object_or_404(Fattura, pk=pk)
    if fattura.stato != Fattura.Stato.PAGATA:
        fattura.stato = Fattura.Stato.ANNULLATA
        fattura.save(update_fields=["stato", "updated_at"])
        # Rimetti gli ODS in stato completato
        fattura.ods.all().update(stato=ODS.Stato.COMPLETATO)
        messages.success(request, f"Fattura {fattura.numero} annullata. Gli ODS sono tornati in stato 'completato'.")
    return redirect("fatturazione_attiva:fatture_list")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_ods_righe(ods_qs):
    rows   = []
    totale = Decimal("0.00")
    for ods in ods_qs:
        righe = list(ods.righe.select_related("servizio").order_by("ordine", "pk"))
        if righe:
            for i, riga in enumerate(righe):
                rows.append({
                    "ods":      ods,
                    "riga":     riga,
                    "sel_val":  f"r-{riga.pk}",
                    "is_first": i == 0,
                    "rowspan":  len(righe) if i == 0 else 0,
                })
                if riga.prezzo:
                    totale += riga.prezzo
        else:
            rows.append({
                "ods":      ods,
                "riga":     None,
                "sel_val":  f"o-{ods.pk}",
                "is_first": True,
                "rowspan":  1,
            })
    return rows, totale


def _load_selezione(selezione):
    riga_ids, ods_ids = [], []
    for v in selezione:
        try:
            if v.startswith("r-"):
                riga_ids.append(int(v[2:]))
            elif v.startswith("o-"):
                ods_ids.append(int(v[2:]))
        except ValueError:
            pass

    rows = []
    if riga_ids:
        for riga in (ODSRiga.objects
                     .filter(pk__in=riga_ids)
                     .select_related("ods__filiale__cliente", "ods__privato", "servizio")
                     .order_by("ods__data_servizio", "ods__pk", "ordine")):
            rows.append({"ods": riga.ods, "riga": riga})
    if ods_ids:
        for ods in (ODS.objects
                    .filter(pk__in=ods_ids)
                    .select_related("filiale__cliente", "privato")
                    .order_by("data_servizio")):
            rows.append({"ods": ods, "riga": None})
    return rows


def _build_pdf_ctx_da_righe(rows, is_fattura):
    """Context per anteprima PDF (senza salvare nel DB)."""
    fat_cfg    = django_settings.FATTURAZIONE
    aliquota   = Decimal(str(fat_cfg.get("ALIQUOTA_IVA", 22)))
    imponibile = sum(
        (r["riga"].prezzo for r in rows if r["riga"] and r["riga"].prezzo),
        Decimal("0.00"),
    )
    importo_iva    = (imponibile * aliquota / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    totale_fattura = imponibile + importo_iva
    from .models import _build_destinatario
    return {
        "righe":             rows,
        "azienda":           fat_cfg,
        "destinatario":      _build_destinatario(rows),
        "is_fattura":        is_fattura,
        "numero_documento":  "BOZZA",
        "data_documento":    timezone.localdate(),
        "aliquota_iva":      aliquota,
        "imponibile":        imponibile,
        "importo_iva":       importo_iva,
        "totale_fattura":    totale_fattura,
    }


def _export_excel(rows):
    data = [
        {
            "N° ODS":        r["ods"].numero,
            "Data servizio": r["ods"].data_servizio,
            "Cliente":       r["ods"].cliente_display,
            "Stato":         r["ods"].get_stato_display(),
            "Tipo servizio": r["riga"].servizio.nome if r["riga"] else "—",
            "Note":          r["riga"].note if r["riga"] else "",
            "Importo (€)":   float(r["riga"].prezzo) if r["riga"] and r["riga"].prezzo else "",
        }
        for r in rows
    ]
    return generate_excel_response(
        data,
        filename=f"fatturazione_{timezone.localdate()}",
        sheet_name="Fatturazione",
    )
