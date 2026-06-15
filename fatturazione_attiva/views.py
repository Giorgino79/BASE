from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from servizi.models import ODS, CondominioODS
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
        data_a = cd.get("data_a")
        solo_completati = cd.get("solo_completati", True)

        ods_qs = ODS.objects.none()
        condomini_qs = CondominioODS.objects.none()

        if tipo in ("azienda", "privato"):
            ods_qs = ODS.objects.select_related(
                "filiale__cliente", "privato", "tecnico"
            ).prefetch_related("righe__servizio")

            if tipo == "azienda":
                azienda = cd["azienda"]
                ods_qs = ods_qs.filter(filiale__cliente=azienda)
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
            stabile = cd["stabile"]
            condomini_qs = CondominioODS.objects.filter(stabile=stabile).prefetch_related("unita")
            if solo_completati:
                condomini_qs = condomini_qs.filter(stato=CondominioODS.Stato.COMPLETATO)
            if data_da:
                condomini_qs = condomini_qs.filter(data__gte=data_da)
            if data_a:
                condomini_qs = condomini_qs.filter(data__lte=data_a)
            condomini_qs = condomini_qs.order_by("data")

        # Appiattisce ODS → una entry per riga servizio (con rowspan per le celle ODS)
        ods_righe = []
        totale_ods = Decimal("0.00")
        for ods in ods_qs:
            righe = list(ods.righe.select_related("servizio").order_by("ordine", "pk"))
            if righe:
                for i, riga in enumerate(righe):
                    ods_righe.append({
                        "ods":      ods,
                        "riga":     riga,
                        "is_first": i == 0,
                        "rowspan":  len(righe) if i == 0 else 0,
                    })
                    if riga.prezzo:
                        totale_ods += riga.prezzo
            else:
                ods_righe.append({
                    "ods":      ods,
                    "riga":     None,
                    "is_first": True,
                    "rowspan":  1,
                })

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
