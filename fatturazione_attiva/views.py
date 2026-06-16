from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings as django_settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from core.excel_generator import generate_excel_response
from core.pdf_generator import generate_pdf_from_html, PDFConfig
from servizi.models import ODS, CondominioODS, ODSRiga
from .forms import RicercaFatturazioneForm, RicercaFattureForm


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
                      .exclude(stato=ODS.Stato.FATTURATO))   # mai mostrare già fatturati

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

    if action in ("pdf", "fattura"):
        is_fattura = action == "fattura"
        nome_file  = f"{'fattura' if is_fattura else 'controllo'}_{timezone.localdate()}"

        # flag is_new_ods per separatori visivi
        prev = None
        for r in righe_rows:
            r["is_new_ods"] = r["ods"].pk != prev
            prev = r["ods"].pk

        ctx = _build_pdf_ctx(righe_rows, is_fattura)
        html = render_to_string("fatturazione_attiva/pdf_fattura.html", ctx)
        buf  = generate_pdf_from_html(html, PDFConfig(filename=f"{nome_file}.pdf"), output_type="buffer")

        if action == "fattura":
            ods_ids = {r["ods"].pk for r in righe_rows}
            ODS.objects.filter(pk__in=ods_ids).update(stato=ODS.Stato.FATTURATO)

        if buf:
            resp = HttpResponse(buf.read(), content_type="application/pdf")
            resp["Content-Disposition"] = f'inline; filename="{nome_file}.pdf"'
            return resp

    return redirect(request.META.get("HTTP_REFERER", "fatturazione_attiva:ricerca"))


# ── helpers ───────────────────────────────────────────────────────────────────

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


def _build_pdf_ctx(rows, is_fattura):
    fat_cfg     = django_settings.FATTURAZIONE
    aliquota    = Decimal(str(fat_cfg.get("ALIQUOTA_IVA", 22)))
    imponibile  = sum(
        r["riga"].prezzo for r in rows if r["riga"] and r["riga"].prezzo
    )
    importo_iva    = (imponibile * aliquota / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    totale_fattura = imponibile + importo_iva

    # numero documento progressivo basato sul conteggio ODS fatturati oggi
    oggi    = timezone.localdate()
    n_oggi  = ODS.objects.filter(stato=ODS.Stato.FATTURATO,
                                  updated_at__date=oggi).count() + 1
    numero  = f"FA-{oggi.year}-{n_oggi:04d}"

    return {
        "righe":           rows,
        "azienda":         fat_cfg,
        "destinatario":    _build_destinatario(rows),
        "is_fattura":      is_fattura,
        "numero_documento": numero,
        "data_documento":  oggi,
        "aliquota_iva":    aliquota,
        "imponibile":      imponibile,
        "importo_iva":     importo_iva,
        "totale_fattura":  totale_fattura,
    }


def _build_destinatario(rows):
    ods = rows[0]["ods"]
    if ods.filiale:
        c = ods.filiale.cliente       # Azienda
        return {
            "nome":          c.ragione_sociale,
            "indirizzo":     c.indirizzo,
            "cap":           c.cap,
            "citta":         c.citta,
            "provincia":     getattr(c, "provincia", ""),
            "partita_iva":   c.partita_iva,
            "codice_fiscale": getattr(c, "codice_fiscale", ""),
            "pec":           getattr(c, "pec", ""),
        }
    if ods.privato:
        p = ods.privato
        return {
            "nome":          str(p),
            "indirizzo":     p.indirizzo,
            "cap":           p.cap,
            "citta":         p.citta,
            "provincia":     getattr(p, "provincia", ""),
            "partita_iva":   "",
            "codice_fiscale": p.codice_fiscale,
            "pec":           "",
        }
    return {"nome": "—", "indirizzo": "", "cap": "", "citta": "", "provincia": "",
            "partita_iva": "", "codice_fiscale": "", "pec": ""}


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


def _cliente_label(rows):
    ods = rows[0]["ods"]
    return str(ods.filiale.cliente) if ods.filiale else str(ods.privato) if ods.privato else "—"


# ── RICERCA FATTURE ───────────────────────────────────────────────────────────

class FattureListView(LoginRequiredMixin, TemplateView):
    template_name = "fatturazione_attiva/fatture_list.html"

    def get(self, request, *args, **kwargs):
        form = RicercaFattureForm(request.GET or None)
        ctx  = self.get_context_data(form=form)
        if request.GET and form.is_valid():
            ctx.update(self._cerca(form.cleaned_data))
        return self.render_to_response(ctx)

    def _cerca(self, cd):
        qs = (ODS.objects
              .filter(stato=ODS.Stato.FATTURATO)
              .select_related("filiale__cliente", "privato")
              .prefetch_related("righe__servizio"))

        tipo = cd.get("tipo_cliente")
        if tipo == "azienda" and cd.get("azienda"):
            qs = qs.filter(filiale__cliente=cd["azienda"])
        elif tipo == "privato" and cd.get("privato"):
            qs = qs.filter(privato=cd["privato"])
        elif cd.get("azienda"):
            qs = qs.filter(filiale__cliente=cd["azienda"])
        elif cd.get("privato"):
            qs = qs.filter(privato=cd["privato"])

        if cd.get("data_da"):
            qs = qs.filter(data_servizio__gte=cd["data_da"])
        if cd.get("data_a"):
            qs = qs.filter(data_servizio__lte=cd["data_a"])

        incasso = cd.get("incasso", "tutti")
        if incasso == "da_incassare":
            qs = qs.filter(incassato=False)
        elif incasso == "incassate":
            qs = qs.filter(incassato=True)

        qs = qs.order_by("-data_servizio")

        totale_imponibile = Decimal("0.00")
        totale_incassato  = Decimal("0.00")
        n_da_incassare    = 0

        fatture = list(qs)
        for ods in fatture:
            pt = ods.prezzo_totale
            if pt:
                totale_imponibile += pt
            if ods.incassato:
                totale_incassato += (ods.importo_incassato or ods.prezzo_totale or Decimal("0"))
            else:
                n_da_incassare += 1

        return {
            "fatture":           fatture,
            "totale_imponibile": totale_imponibile,
            "totale_incassato":  totale_incassato,
            "n_da_incassare":    n_da_incassare,
            "ricerca_eseguita":  True,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("fatture", [])
        ctx.setdefault("ricerca_eseguita", False)
        return ctx
