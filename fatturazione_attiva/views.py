from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from core.excel_generator import generate_excel_response
from core.pdf_generator import generate_pdf_from_html, PDFConfig
from servizi.models import ODS, CondominioODS, ODSRiga
from .forms import RicercaFatturazioneForm


class RicercaFatturazioneView(LoginRequiredMixin, TemplateView):
    template_name = "fatturazione_attiva/ricerca.html"

    def get(self, request, *args, **kwargs):
        form = RicercaFatturazioneForm(request.GET or None)
        ctx = self.get_context_data(form=form)
        if request.GET and form.is_valid():
            ctx.update(self._cerca(form.cleaned_data))
        return self.render_to_response(ctx)

    def _cerca(self, cd):
        tipo = cd["tipo"]
        data_da = cd.get("data_da")
        data_a  = cd.get("data_a")
        solo_completati = cd.get("solo_completati", True)

        ods_qs       = ODS.objects.none()
        condomini_qs = CondominioODS.objects.none()

        if tipo in ("azienda", "privato"):
            ods_qs = ODS.objects.select_related(
                "filiale__cliente", "privato", "tecnico"
            )
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
            condomini_qs = CondominioODS.objects.filter(
                stabile=cd["stabile"]
            ).prefetch_related("unita")
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


@login_required
@require_POST
def azione_fatturazione(request):
    """
    Gestisce PDF preview, Excel e Elabora Fattura sulle righe selezionate.
    Valori sel[]: "r-{riga_pk}" per ODSRiga, "o-{ods_pk}" per ODS senza righe.
    """
    action  = request.POST.get("action", "pdf")
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

    if action in ("pdf", "fattura"):
        cliente_label = _cliente_label(righe_rows)
        totale = sum(
            r["riga"].prezzo for r in righe_rows
            if r["riga"] and r["riga"].prezzo
        )
        # Aggiunge flag is_new_ods per separatori visivi nel PDF
        prev_ods_pk = None
        for r in righe_rows:
            r["is_new_ods"] = r["ods"].pk != prev_ods_pk
            prev_ods_pk = r["ods"].pk

        ctx = {
            "righe":         righe_rows,
            "cliente_label": cliente_label,
            "totale":        totale,
            "data_oggi":     timezone.localdate(),
            "is_fattura":    action == "fattura",
        }
        html = render_to_string("fatturazione_attiva/pdf_fattura.html", ctx)
        nome_file = f"{'fattura' if action == 'fattura' else 'preventivo'}_{timezone.localdate()}.pdf"
        pdf = generate_pdf_from_html(html, PDFConfig(filename=nome_file), output_type="buffer")

        if action == "fattura":
            ods_ids = {r["ods"].pk for r in righe_rows}
            ODS.objects.filter(pk__in=ods_ids).update(stato=ODS.Stato.FATTURATO)

        if pdf:
            resp = HttpResponse(pdf.read(), content_type="application/pdf")
            resp["Content-Disposition"] = f'inline; filename="{nome_file}"'
            return resp

    return redirect(request.META.get("HTTP_REFERER", "fatturazione_attiva:ricerca"))


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_ods_righe(ods_qs):
    """Restituisce (flat_list, totale) con una entry per riga servizio."""
    rows = []
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
    """Carica righe/ODS dai valori sel[] e restituisce flat_list uniformata."""
    riga_ids = []
    ods_ids  = []
    for v in selezione:
        if v.startswith("r-"):
            try:
                riga_ids.append(int(v[2:]))
            except ValueError:
                pass
        elif v.startswith("o-"):
            try:
                ods_ids.append(int(v[2:]))
            except ValueError:
                pass

    rows = []
    if riga_ids:
        righe = (ODSRiga.objects
                 .filter(pk__in=riga_ids)
                 .select_related("ods__filiale__cliente", "ods__privato", "servizio")
                 .order_by("ods__data_servizio", "ods__pk", "ordine"))
        for riga in righe:
            rows.append({"ods": riga.ods, "riga": riga})

    if ods_ids:
        ods_list = (ODS.objects
                    .filter(pk__in=ods_ids)
                    .select_related("filiale__cliente", "privato")
                    .order_by("data_servizio"))
        for ods in ods_list:
            rows.append({"ods": ods, "riga": None})

    return rows


def _export_excel(rows):
    data = []
    for r in rows:
        ods  = r["ods"]
        riga = r["riga"]
        data.append({
            "N° ODS":          ods.numero,
            "Data servizio":   ods.data_servizio,
            "Cliente":         ods.cliente_display,
            "Stato":           ods.get_stato_display(),
            "Tipo servizio":   riga.servizio.nome if riga else "—",
            "Note servizio":   riga.note if riga else "",
            "Importo (€)":     float(riga.prezzo) if riga and riga.prezzo else "",
        })
    return generate_excel_response(
        data,
        filename=f"fatturazione_{timezone.localdate()}",
        sheet_name="Fatturazione",
    )


def _cliente_label(rows):
    ods = rows[0]["ods"]
    if ods.filiale:
        return str(ods.filiale.cliente)
    if ods.privato:
        return str(ods.privato)
    return "—"
