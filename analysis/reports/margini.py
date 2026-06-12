from decimal import Decimal
from datetime import date
from django.db.models import Sum
from django.db.models.functions import Coalesce
from .base import BaseReport


class MarginiReport(BaseReport):
    slug = "margini"
    nome = "Ricavi vs Costi"
    descrizione = "Confronto ricavi, costi e margine nel periodo"
    chart_type = "line"
    icon = "bi-activity"

    def get_data(self, data_da, data_a, group_by="month"):
        from servizi.models import ODS, CondominioODS
        from acquisti.models import FatturaPassiva
        from payroll.models import BustaPaga

        Trunc = self.get_trunc(group_by)

        # ── Ricavi ──────────────────────────────────────────────────────────
        ods_map = self.build_map(
            ODS.objects.filter(stato="completato", data_servizio__range=(data_da, data_a))
            .annotate(periodo=Trunc("data_servizio")).values("periodo")
            .annotate(totale=Coalesce(Sum("righe__prezzo"), Decimal("0"))).order_by("periodo"),
            group_by,
        )
        con_map = self.build_map(
            CondominioODS.objects.filter(stato="completato", data__range=(data_da, data_a))
            .annotate(periodo=Trunc("data")).values("periodo")
            .annotate(totale=Coalesce(Sum("prezzo_base"), Decimal("0"))).order_by("periodo"),
            group_by,
        )
        ricavi_map = {p: ods_map.get(p, 0) + con_map.get(p, 0)
                      for p in set(ods_map) | set(con_map)}

        # ── Costi ───────────────────────────────────────────────────────────
        acq_map = self.build_map(
            FatturaPassiva.objects.filter(data_fattura__range=(data_da, data_a))
            .annotate(periodo=Trunc("data_fattura")).values("periodo")
            .annotate(totale=Coalesce(Sum("imponibile"), Decimal("0"))).order_by("periodo"),
            group_by,
        )
        payroll_map = {}
        for bp in BustaPaga.objects.filter(
            anno__gte=data_da.year, anno__lte=data_a.year
        ).values("anno", "mese", "netto_busta"):
            d = date(bp["anno"], bp["mese"], 1)
            if data_da <= d <= data_a:
                payroll_map[d] = payroll_map.get(d, 0.0) + float(bp["netto_busta"] or 0)

        costi_map = {p: acq_map.get(p, 0) + payroll_map.get(p, 0)
                     for p in set(acq_map) | set(payroll_map)}

        # ── Merge ───────────────────────────────────────────────────────────
        all_periods = sorted(set(ricavi_map) | set(costi_map))
        labels = [self.fmt_period(p, group_by) for p in all_periods]
        r_data = [ricavi_map.get(p, 0) for p in all_periods]
        c_data = [costi_map.get(p, 0) for p in all_periods]
        m_data = [r - c for r, c in zip(r_data, c_data)]

        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Ricavi",
                    "data": r_data,
                    "borderColor": "#28a745",
                    "backgroundColor": "rgba(40,167,69,0.08)",
                    "fill": True,
                    "tension": 0.3,
                    "pointRadius": 4,
                },
                {
                    "label": "Costi",
                    "data": c_data,
                    "borderColor": "#dc3545",
                    "backgroundColor": "rgba(220,53,69,0.08)",
                    "fill": True,
                    "tension": 0.3,
                    "pointRadius": 4,
                },
                {
                    "label": "Margine",
                    "data": m_data,
                    "borderColor": "#5585b5",
                    "backgroundColor": "rgba(85,133,181,0.08)",
                    "fill": True,
                    "tension": 0.3,
                    "pointRadius": 4,
                    "borderDash": [5, 3],
                },
            ],
            "totale_ricavi": sum(r_data),
            "totale_costi": sum(c_data),
            "margine": sum(m_data),
        }
