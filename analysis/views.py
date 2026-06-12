import json
from datetime import date, datetime
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import render

from .reports.ricavi import RicaviReport, RicaviPerTipoReport
from .reports.costi import CostiReport
from .reports.margini import MarginiReport

REPORTS = {
    r.slug: r
    for r in [RicaviReport(), RicaviPerTipoReport(), CostiReport(), MarginiReport()]
}


def _parse_date(s, fallback):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return fallback


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


@login_required
def dashboard(request):
    today = date.today()
    data_da = _parse_date(request.GET.get("data_da"), date(today.year, 1, 1))
    data_a  = _parse_date(request.GET.get("data_a"),  date(today.year, 12, 31))
    group_by = request.GET.get("group_by", "month")
    if group_by not in ("month", "week", "day"):
        group_by = "month"

    ricavi  = RicaviReport().get_data(data_da, data_a, group_by)
    tipo    = RicaviPerTipoReport().get_data(data_da, data_a, group_by)
    costi   = CostiReport().get_data(data_da, data_a, group_by)
    margini = MarginiReport().get_data(data_da, data_a, group_by)

    # KPI
    kpi = {
        "ricavi":   ricavi["totale"],
        "costi":    costi["totale"],
        "margine":  margini["margine"],
        "margine_pct": (
            round(margini["margine"] / ricavi["totale"] * 100, 1)
            if ricavi["totale"] else 0
        ),
    }

    ctx = {
        "data_da":  data_da.strftime("%Y-%m-%d"),
        "data_a":   data_a.strftime("%Y-%m-%d"),
        "group_by": group_by,
        "kpi":      kpi,
        "ricavi_json":  json.dumps(ricavi,  cls=_DecimalEncoder),
        "tipo_json":    json.dumps(tipo,    cls=_DecimalEncoder),
        "costi_json":   json.dumps(costi,   cls=_DecimalEncoder),
        "margini_json": json.dumps(margini, cls=_DecimalEncoder),
    }
    return render(request, "analysis/dashboard.html", ctx)


@login_required
def costi_servizi(request):
    today = date.today()
    data_da = _parse_date(request.GET.get("data_da"), date(today.year, today.month, 1))
    data_a  = _parse_date(request.GET.get("data_a"),  today)

    from servizi.models import ODS, CondominioODS, ConsumoMateriale, RigaProdottoCondominio
    from magazzino.models import RigaRicezione, Prodotto

    # ── Query ODS ────────────────────────────────────────────────────────────
    ods_qs = (
        ODS.objects
        .filter(data_servizio__range=(data_da, data_a))
        .select_related("tecnico", "filiale__cliente", "privato")
        .prefetch_related("righe", "righe__consumi__prodotto")
        .order_by("-data_servizio", "numero")
    )

    # ── Query CondominioODS ───────────────────────────────────────────────────
    con_qs = (
        CondominioODS.objects
        .filter(data__range=(data_da, data_a))
        .select_related("tecnico")
        .prefetch_related("prodotti__prodotto")
        .order_by("-data", "numero")
    )

    # ── Raccogli tutti i prodotti usati ───────────────────────────────────────
    product_ids = set()
    for ods in ods_qs:
        for riga in ods.righe.all():
            for cm in riga.consumi.all():
                product_ids.add(cm.prodotto_id)
    for con in con_qs:
        for rp in con.prodotti.all():
            product_ids.add(rp.prodotto_id)

    # ── Ultimo prezzo di acquisto per prodotto ────────────────────────────────
    prices = {}
    if product_ids:
        last_price_sq = (
            RigaRicezione.objects
            .filter(prodotto_id=OuterRef("pk"))
            .order_by("-ricezione__data_ricezione", "-pk")
            .values("prezzo_unitario")[:1]
        )
        prices = dict(
            Prodotto.objects.filter(pk__in=product_ids)
            .annotate(ultimo_prezzo=Subquery(last_price_sq))
            .values_list("pk", "ultimo_prezzo")
        )

    # ── Costruisci righe ──────────────────────────────────────────────────────
    rows = []

    for ods in ods_qs:
        ricavo = float(sum((r.prezzo or 0) for r in ods.righe.all()))
        items, costo = _build_consumo_items(
            [(cm.prodotto, cm.quantita)
             for riga in ods.righe.all()
             for cm in riga.consumi.all()],
            prices,
        )
        rows.append({
            "tipo":          "ODS",
            "data":          ods.data_servizio,
            "numero":        ods.numero,
            "display":       ods.cliente_display,
            "tecnico":       ods.tecnico,
            "stato":         ods.stato,
            "stato_display": ods.get_stato_display(),
            "url":           ods.get_absolute_url(),
            "ricavo":        ricavo,
            "items":         items,
            "costo":         costo,
            "margine":       ricavo - costo,
        })

    for con in con_qs:
        ricavo = float(con.prezzo_base or 0)
        items, costo = _build_consumo_items(
            [(rp.prodotto, rp.quantita) for rp in con.prodotti.all()],
            prices,
        )
        rows.append({
            "tipo":          "Cond.",
            "data":          con.data,
            "numero":        con.numero,
            "display":       con.titolo,
            "tecnico":       con.tecnico,
            "stato":         con.stato,
            "stato_display": con.get_stato_display(),
            "url":           con.get_absolute_url(),
            "ricavo":        ricavo,
            "items":         items,
            "costo":         costo,
            "margine":       ricavo - costo,
        })

    rows.sort(key=lambda r: (r["data"], r["numero"]), reverse=True)

    totali = {
        "ricavo":  sum(r["ricavo"]  for r in rows),
        "costo":   sum(r["costo"]   for r in rows),
        "margine": sum(r["margine"] for r in rows),
    }

    return render(request, "analysis/costi_servizi.html", {
        "rows":    rows,
        "totali":  totali,
        "data_da": data_da.strftime("%Y-%m-%d"),
        "data_a":  data_a.strftime("%Y-%m-%d"),
    })


def _build_consumo_items(prodotto_qty_pairs, prices):
    """Ritorna (lista_items, costo_totale)."""
    items = []
    totale = 0.0
    for prodotto, quantita in prodotto_qty_pairs:
        price = float(prices.get(prodotto.pk) or 0)
        cost  = float(quantita) * price
        totale += cost
        items.append({
            "nome":    prodotto.nome_prodotto,
            "qty":     float(quantita),
            "um":      prodotto.get_unita_misura_display(),
            "prezzo":  price,
            "costo":   cost,
        })
    return items, totale


@login_required
def api_report(request, slug):
    report = REPORTS.get(slug)
    if not report:
        return JsonResponse({"error": "report non trovato"}, status=404)

    today = date.today()
    data_da  = _parse_date(request.GET.get("data_da"), date(today.year, 1, 1))
    data_a   = _parse_date(request.GET.get("data_a"),  date(today.year, 12, 31))
    group_by = request.GET.get("group_by", "month")
    if group_by not in ("month", "week", "day"):
        group_by = "month"

    data = report.get_data(data_da, data_a, group_by)
    return JsonResponse(data, encoder=_DecimalEncoder)
