from decimal import Decimal
from datetime import date
from django.db.models import Sum, ExpressionWrapper, F, Value, Subquery, OuterRef
from django.db.models import DecimalField as DBDecimalField
from django.db.models.functions import Coalesce
from .base import BaseReport
from .ricavi import _con_ricavo_qs


def _last_price_subquery():
    from magazzino.models import RigaRicezione
    return (
        RigaRicezione.objects
        .filter(prodotto_id=OuterRef("prodotto_id"))
        .order_by("-ricezione__data_ricezione", "-pk")
        .values("prezzo_unitario")[:1]
    )


def _consumo_map(qs_class, date_path, data_da, data_a, Trunc):
    """
    Aggregate product consumption costs for a queryset that has prodotto_id and quantita.
    date_path is the ORM path to the date field (e.g. 'riga__ods__data_servizio').
    """
    last_price_sq = _last_price_subquery()
    qs = (
        qs_class.objects
        .filter(**{f"{date_path}__range": (data_da, data_a)})
        .annotate(
            periodo=Trunc(date_path),
            ultimo_prezzo=Coalesce(
                Subquery(last_price_sq, output_field=DBDecimalField(max_digits=10, decimal_places=4)),
                Value(Decimal("0")),
            ),
            costo_item=ExpressionWrapper(
                F("quantita") * F("ultimo_prezzo"),
                output_field=DBDecimalField(max_digits=10, decimal_places=2),
            ),
        )
        .values("periodo")
        .annotate(totale=Coalesce(Sum("costo_item"), Decimal("0")))
        .order_by("periodo")
    )
    result = {}
    for row in qs:
        from .base import BaseReport
        d = BaseReport.to_date(row["periodo"])
        if d:
            result[d] = result.get(d, 0.0) + float(row["totale"] or 0)
    return result


class MarginiReport(BaseReport):
    slug = "margini"
    nome = "Ricavi vs Costi"
    descrizione = "Confronto ricavi, costi e margine nel periodo"
    chart_type = "bar"
    icon = "bi-activity"

    def get_data(self, data_da, data_a, group_by="month"):
        from servizi.models import ODS, CondominioODS, ConsumoMateriale, RigaProdottoCondominio
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
            _con_ricavo_qs(
                CondominioODS.objects.filter(stato="completato", data__range=(data_da, data_a))
                .annotate(periodo=Trunc("data"))
            )
            .values("periodo")
            .annotate(totale=Coalesce(Sum("ricavo"), Decimal("0")))
            .order_by("periodo"),
            group_by,
        )
        ricavi_map = {p: ods_map.get(p, 0) + con_map.get(p, 0)
                      for p in set(ods_map) | set(con_map)}

        # ── Costi (fatture + paghe) ──────────────────────────────────────────
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

        # ── Costo prodotti consumati ─────────────────────────────────────────
        ods_cp = _consumo_map(ConsumoMateriale, "riga__ods__data_servizio", data_da, data_a, Trunc)
        con_cp = _consumo_map(RigaProdottoCondominio, "condominio__data", data_da, data_a, Trunc)
        consumo_map = {p: ods_cp.get(p, 0) + con_cp.get(p, 0)
                       for p in set(ods_cp) | set(con_cp)}

        # ── Merge ───────────────────────────────────────────────────────────
        all_periods = sorted(set(ricavi_map) | set(costi_map) | set(consumo_map))
        labels = [self.fmt_period(p, group_by) for p in all_periods]
        r_data  = [ricavi_map.get(p, 0) for p in all_periods]
        c_data  = [costi_map.get(p, 0) for p in all_periods]
        cp_data = [consumo_map.get(p, 0) for p in all_periods]
        m_data  = [r - cp for r, cp in zip(r_data, cp_data)]

        return {
            "labels": labels,
            "datasets": [
                {
                    "type": "bar",
                    "label": "Ricavi",
                    "data": r_data,
                    "backgroundColor": "rgba(40,167,69,0.6)",
                    "borderColor": "#28a745",
                    "borderWidth": 1,
                    "order": 2,
                },
                {
                    "type": "line",
                    "label": "Costo prodotti",
                    "data": cp_data,
                    "borderColor": "#fd7e14",
                    "backgroundColor": "transparent",
                    "fill": False,
                    "tension": 0.3,
                    "pointRadius": 3,
                    "borderWidth": 2,
                    "order": 1,
                },
                {
                    "type": "line",
                    "label": "Costi (fatture+paghe)",
                    "data": c_data,
                    "borderColor": "#dc3545",
                    "backgroundColor": "rgba(220,53,69,0.08)",
                    "fill": True,
                    "tension": 0.3,
                    "pointRadius": 3,
                    "borderWidth": 1.5,
                    "order": 1,
                },
                {
                    "type": "line",
                    "label": "Margine",
                    "data": m_data,
                    "borderColor": "#5585b5",
                    "backgroundColor": "rgba(85,133,181,0.08)",
                    "fill": True,
                    "tension": 0.3,
                    "pointRadius": 3,
                    "borderDash": [5, 3],
                    "borderWidth": 1.5,
                    "order": 1,
                },
            ],
            "totale_ricavi": sum(r_data),
            "totale_costi": sum(c_data),
            "totale_costo_prodotti": sum(cp_data),
            "margine": sum(m_data),
        }
