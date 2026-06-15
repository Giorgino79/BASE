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

        totale_ods = sum(
            (o.prezzo_totale for o in ods_qs if o.prezzo_totale), Decimal("0.00")
        )
        totale_condomini = sum(
            (c.totale_da_incassare for c in condomini_qs), Decimal("0.00")
        )

        return {
            "ods_list": ods_qs,
            "condomini_list": condomini_qs,
            "totale_ods": totale_ods,
            "totale_condomini": totale_condomini,
            "totale_generale": totale_ods + totale_condomini,
            "ricerca_eseguita": True,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("ods_list", [])
        ctx.setdefault("condomini_list", [])
        ctx.setdefault("ricerca_eseguita", False)
        return ctx
