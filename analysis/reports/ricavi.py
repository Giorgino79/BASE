from decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import Coalesce
from .base import BaseReport


class RicaviReport(BaseReport):
    slug = "ricavi"
    nome = "Ricavi"
    descrizione = "ODS e Condomini completati nel periodo"
    chart_type = "bar"
    icon = "bi-graph-up-arrow"

    def get_data(self, data_da, data_a, group_by="month"):
        from servizi.models import ODS, CondominioODS

        Trunc = self.get_trunc(group_by)

        ods_map = self.build_map(
            ODS.objects.filter(stato="completato", data_servizio__range=(data_da, data_a))
            .annotate(periodo=Trunc("data_servizio"))
            .values("periodo")
            .annotate(totale=Coalesce(Sum("righe__prezzo"), Decimal("0")))
            .order_by("periodo"),
            group_by,
        )

        con_map = self.build_map(
            CondominioODS.objects.filter(stato="completato", data__range=(data_da, data_a))
            .annotate(periodo=Trunc("data"))
            .values("periodo")
            .annotate(totale=Coalesce(Sum("prezzo_base"), Decimal("0")))
            .order_by("periodo"),
            group_by,
        )

        all_periods = sorted(set(ods_map) | set(con_map))
        labels = [self.fmt_period(p, group_by) for p in all_periods]

        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "ODS",
                    "data": [ods_map.get(p, 0) for p in all_periods],
                    "backgroundColor": "rgba(85,133,181,0.8)",
                    "borderColor": "#5585b5",
                    "borderWidth": 1,
                },
                {
                    "label": "Condomini",
                    "data": [con_map.get(p, 0) for p in all_periods],
                    "backgroundColor": "rgba(40,167,69,0.8)",
                    "borderColor": "#28a745",
                    "borderWidth": 1,
                },
            ],
            "totale": sum(ods_map.values()) + sum(con_map.values()),
        }


class RicaviPerTipoReport(BaseReport):
    """Doughnut: ripartizione ODS vs Condomini (totale nel periodo)."""

    slug = "ricavi-tipo"
    nome = "Ripartizione ricavi"
    descrizione = "ODS vs Condomini"
    chart_type = "doughnut"
    icon = "bi-pie-chart"

    def get_data(self, data_da, data_a, group_by="month"):
        from servizi.models import ODS, CondominioODS
        from django.db.models import Sum
        from django.db.models.functions import Coalesce

        tot_ods = float(
            ODS.objects.filter(stato="completato", data_servizio__range=(data_da, data_a))
            .aggregate(t=Coalesce(Sum("righe__prezzo"), Decimal("0")))["t"]
        )
        tot_con = float(
            CondominioODS.objects.filter(stato="completato", data__range=(data_da, data_a))
            .aggregate(t=Coalesce(Sum("prezzo_base"), Decimal("0")))["t"]
        )

        return {
            "labels": ["ODS", "Condomini"],
            "datasets": [
                {
                    "data": [tot_ods, tot_con],
                    "backgroundColor": ["rgba(85,133,181,0.85)", "rgba(40,167,69,0.85)"],
                    "borderWidth": 2,
                }
            ],
            "totale": tot_ods + tot_con,
        }
