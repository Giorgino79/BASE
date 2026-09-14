from decimal import Decimal
from datetime import date
from django.db.models import Sum
from django.db.models.functions import Coalesce
from .base import BaseReport


class CostiReport(BaseReport):
    slug = "costi"
    nome = "Costi"
    descrizione = "Fatture passive e costo personale nel periodo"
    chart_type = "bar"
    icon = "bi-receipt"

    def get_data(self, data_da, data_a, group_by="month"):
        from acquisti.models import FatturaPassiva
        from payroll.models import BustaPaga

        Trunc = self.get_trunc(group_by)

        acq_map = self.build_map(
            FatturaPassiva.objects.filter(data_fattura__range=(data_da, data_a))
            .annotate(periodo=Trunc("data_fattura"))
            .values("periodo")
            .annotate(totale=Coalesce(Sum("imponibile"), Decimal("0")))
            .order_by("periodo"),
            group_by,
        )

        # BustaPaga ha solo mese/anno interi → aggregazione sempre mensile
        payroll_map = {}
        for bp in BustaPaga.objects.filter(
            anno__gte=data_da.year, anno__lte=data_a.year
        ).values("anno", "mese", "netto_busta"):
            d = date(bp["anno"], bp["mese"], 1)
            if data_da <= d <= data_a:
                payroll_map[d] = payroll_map.get(d, 0.0) + float(bp["netto_busta"] or 0)

        all_periods = sorted(set(acq_map) | set(payroll_map))
        labels = [self.fmt_period(p, group_by) for p in all_periods]

        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Acquisti",
                    "data": [acq_map.get(p, 0) for p in all_periods],
                    "backgroundColor": "rgba(220,53,69,0.8)",
                    "borderColor": "#dc3545",
                    "borderWidth": 1,
                },
                {
                    "label": "Personale",
                    "data": [payroll_map.get(p, 0) for p in all_periods],
                    "backgroundColor": "rgba(255,165,0,0.8)",
                    "borderColor": "#e69500",
                    "borderWidth": 1,
                },
            ],
            "totale": sum(acq_map.values()) + sum(payroll_map.values()),
        }
