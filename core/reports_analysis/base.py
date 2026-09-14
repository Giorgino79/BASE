from datetime import date

MESI_IT = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
           "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]


class BaseReport:
    slug = ""
    nome = ""
    descrizione = ""
    chart_type = "bar"
    icon = "bi-bar-chart"

    def get_data(self, data_da: date, data_a: date, group_by: str = "month") -> dict:
        raise NotImplementedError

    @staticmethod
    def get_trunc(group_by):
        from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
        return {"month": TruncMonth, "week": TruncWeek, "day": TruncDay}.get(group_by, TruncMonth)

    @staticmethod
    def to_date(val):
        if val is None:
            return None
        return val.date() if hasattr(val, "date") else val

    @classmethod
    def fmt_period(cls, d, group_by):
        if group_by == "month":
            return f"{MESI_IT[d.month - 1]} {d.year}"
        if group_by == "week":
            iso = d.isocalendar()
            return f"Sett {iso[1]:02d}/{iso[0]}"
        return d.strftime("%d/%m/%Y")

    @classmethod
    def build_map(cls, qs, group_by):
        """Queryset rows must have 'periodo' and 'totale'. Returns {date: float}."""
        result = {}
        for row in qs:
            d = cls.to_date(row["periodo"])
            if d:
                result[d] = result.get(d, 0.0) + float(row["totale"] or 0)
        return result
