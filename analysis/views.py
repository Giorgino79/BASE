import json
from datetime import date, datetime
from decimal import Decimal
from django.contrib.auth.decorators import login_required
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
