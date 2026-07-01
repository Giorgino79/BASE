import json
import calendar
from datetime import date

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, DetailView

PALETTE = [
    "#fd7e14", "#0d6efd", "#198754", "#dc3545",
    "#6f42c1", "#20c997", "#d63384", "#ffc107",
    "#0dcaf0", "#6c757d",
]


def _colore_filiale(filiale_id: int) -> str:
    return PALETTE[filiale_id % len(PALETTE)]


def _genera_date(data_inizio: date, frequenza: str, anno: int) -> list:
    step_mesi = {
        "mensile": 1, "bimestrale": 2, "trimestrale": 3,
        "semestrale": 6, "annuale": 12,
    }
    step = step_mesi.get(frequenza, 1)
    dates = []
    anno_c = data_inizio.year
    mese_c = data_inizio.month
    giorno = data_inizio.day

    while anno_c == anno:
        max_day = calendar.monthrange(anno_c, mese_c)[1]
        d = date(anno_c, mese_c, min(giorno, max_day))
        dates.append(d)
        mese_c += step
        while mese_c > 12:
            mese_c -= 12
            anno_c += 1

    return dates


class PianificazioneView(LoginRequiredMixin, TemplateView):
    template_name = "servizi/pianificazione.html"

    def get_context_data(self, **kwargs):
        from anagrafica_r2.models import Azienda
        ctx = super().get_context_data(**kwargs)
        ctx["clienti"] = Azienda.objects.filter(attivo=True).order_by("ragione_sociale")
        ctx["anno_corrente"] = date.today().year
        return ctx


class PianoDetailView(LoginRequiredMixin, DetailView):
    template_name = "servizi/piano_detail.html"
    context_object_name = "piano"

    def get_queryset(self):
        from .models import PianoServizio
        return PianoServizio.objects.select_related("cliente", "filiale", "servizio")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        piano = self.object
        ctx["ods_list"] = piano.ods_set.select_related("filiale", "tecnico").order_by("data_servizio")
        ctx["color"] = _colore_filiale(piano.filiale_id or 0)
        return ctx


@login_required
def pianificazione_eventi_api(request):
    from .models import ODS
    from django.db.models import F

    cliente_id = request.GET.get("cliente_id")
    start = request.GET.get("start", "")[:10]
    end = request.GET.get("end", "")[:10]

    qs = (
        ODS.objects
        .select_related("filiale__cliente", "tecnico")
        .prefetch_related("righe__servizio")
        .filter(filiale__isnull=False)
        .exclude(stato="annullato")
    )

    if cliente_id:
        qs = qs.filter(filiale__cliente_id=cliente_id)
    if start:
        qs = qs.filter(data_servizio__gte=start)
    if end:
        qs = qs.filter(data_servizio__lte=end)

    from django.urls import reverse
    eventi = []
    for ods in qs.order_by("data_servizio", F("ora_inizio").asc(nulls_last=True))[:600]:
        color = _colore_filiale(ods.filiale_id)
        servizio = ods.servizio_principale
        dimmed = ods.stato in ("completato", "fatturato")
        title = ods.filiale.nome if ods.filiale else "—"
        if servizio:
            title += f" · {servizio}"

        eventi.append({
            "id": f"ods-{ods.pk}",
            "title": title,
            "start": ods.data_servizio.isoformat(),
            "allDay": True,
            "color": color,
            "url": ods.get_absolute_url(),
            "extendedProps": {
                "ods_id": ods.pk,
                "filiale_id": ods.filiale_id,
                "filiale_nome": ods.filiale.nome if ods.filiale else "",
                "stato": ods.stato,
                "stato_display": ods.get_stato_display(),
                "numero": ods.numero,
                "servizio": str(servizio) if servizio else "",
                "piano_id": ods.piano_id,
                "dimmed": dimmed,
            },
        })

    return JsonResponse(eventi, safe=False)


@login_required
def pianificazione_filiali_api(request):
    from anagrafica_r2.models import Filiale

    cliente_id = request.GET.get("cliente_id")
    if not cliente_id:
        return JsonResponse([], safe=False)

    filiali = Filiale.objects.filter(cliente_id=cliente_id, attivo=True).order_by("nome")
    return JsonResponse([
        {
            "id": f.pk,
            "nome": f.nome,
            "indirizzo": f.indirizzo,
            "citta": f.citta,
            "color": _colore_filiale(f.pk),
        }
        for f in filiali
    ], safe=False)


@login_required
def pianificazione_servizi_api(request):
    """Servizi disponibili per un cliente (da contratti attivi, fallback tutti)."""
    from .models import Servizio, Contratto, ContrattoRiga, ContrattoFilialeRiga

    cliente_id = request.GET.get("cliente_id")
    if cliente_id:
        contratti_ids = list(
            Contratto.objects.filter(cliente_id=cliente_id, stato="attivo")
            .values_list("id", flat=True)
        )
        if contratti_ids:
            ids = set(
                ContrattoRiga.objects.filter(contratto_id__in=contratti_ids)
                .values_list("servizio_id", flat=True)
            )
            ids |= set(
                ContrattoFilialeRiga.objects.filter(
                    contratto_filiale__contratto_id__in=contratti_ids
                ).values_list("servizio_id", flat=True)
            )
            if ids:
                return JsonResponse([
                    {"id": s.pk, "nome": s.nome}
                    for s in Servizio.objects.filter(pk__in=ids, attivo=True).order_by("nome")
                ], safe=False)

    return JsonResponse([
        {"id": s.pk, "nome": s.nome}
        for s in Servizio.objects.filter(attivo=True).order_by("nome")
    ], safe=False)


@login_required
@require_POST
def pianificazione_salva_piano(request):
    """Crea in bulk tutti gli ODS dalla bozza confermata dall'utente."""
    try:
        payload     = json.loads(request.body)
        servizio_id = int(payload["servizio_id"])
        programma   = payload["programma"]   # [{filiale_id, data}, ...]

        from anagrafica_r2.models import Filiale
        from .models import ODS, ODSRiga, Servizio, ContrattoFiliale
        from django.urls import reverse

        servizio = get_object_or_404(Servizio, pk=servizio_id)

        # prezzo per filiale (cache per evitare N query)
        prezzi = {}
        def _prezzo(filiale):
            if filiale.pk not in prezzi:
                p = servizio.tariffa_cartello
                cf = ContrattoFiliale.objects.filter(
                    filiale=filiale, contratto__stato="attivo"
                ).first()
                if cf:
                    riga = cf.righe_sede.filter(servizio=servizio).first()
                    if riga:
                        p = riga.prezzo
                prezzi[filiale.pk] = p
            return prezzi[filiale.pk]

        creati = []
        filiali_cache = {}
        for item in programma:
            fid = int(item["filiale_id"])
            if fid not in filiali_cache:
                filiali_cache[fid] = get_object_or_404(Filiale, pk=fid)
            filiale   = filiali_cache[fid]
            data_serv = date.fromisoformat(item["data"])

            ods = ODS.objects.create(
                filiale=filiale,
                data_servizio=data_serv,
                stato=ODS.Stato.PROGRAMMATO,
                created_by=request.user,
            )
            ODSRiga.objects.create(ods=ods, servizio=servizio, prezzo=_prezzo(filiale))
            creati.append({
                "ods_id":        ods.pk,
                "numero":        ods.numero,
                "url":           reverse("servizi:ods_detail", kwargs={"pk": ods.pk}),
                "filiale_id":    fid,
                "filiale_nome":  filiale.nome,
                "data":          data_serv.isoformat(),
                "color":         _colore_filiale(fid),
                "stato":         ods.stato,
                "stato_display": ods.get_stato_display(),
            })

        return JsonResponse({"ok": True, "n": len(creati), "ods": creati})

    except Exception as e:
        return JsonResponse({"ok": False, "errore": str(e)}, status=400)


@login_required
@require_POST
def pianificazione_genera(request):
    try:
        data = json.loads(request.body)
        filiale_id = int(data["filiale_id"])
        servizio_id = int(data["servizio_id"])
        anno = int(data["anno"])
        frequenza = data["frequenza"]
        data_inizio = date.fromisoformat(data["data_inizio"])
        note = data.get("note", "")

        from anagrafica_r2.models import Filiale
        from .models import PianoServizio, ODS, ODSRiga, Servizio, ContrattoFiliale
        from decimal import Decimal

        filiale = get_object_or_404(Filiale, pk=filiale_id)
        servizio = get_object_or_404(Servizio, pk=servizio_id)

        # Prezzo: cerca in ContrattoFiliale attivo, fallback tariffa cartello
        prezzo = servizio.tariffa_cartello
        cf = ContrattoFiliale.objects.filter(
            filiale=filiale, contratto__stato="attivo"
        ).first()
        if cf:
            riga_cf = cf.righe_sede.filter(servizio=servizio).first()
            if riga_cf:
                prezzo = riga_cf.prezzo

        piano = PianoServizio.objects.create(
            cliente=filiale.cliente,
            filiale=filiale,
            servizio=servizio,
            anno=anno,
            frequenza=frequenza,
            note=note,
            created_by=request.user,
        )

        dates = _genera_date(data_inizio, frequenza, anno)

        for d in dates:
            ods = ODS.objects.create(
                filiale=filiale,
                data_servizio=d,
                stato=ODS.Stato.PROGRAMMATO,
                piano=piano,
                created_by=request.user,
            )
            ODSRiga.objects.create(ods=ods, servizio=servizio, prezzo=prezzo)

        return JsonResponse({
            "ok": True,
            "piano_id": piano.pk,
            "n_ods": len(dates),
            "date": [d.isoformat() for d in dates],
            "color": _colore_filiale(filiale.pk),
        })

    except Exception as e:
        return JsonResponse({"ok": False, "errore": str(e)}, status=400)


@login_required
@require_POST
def pianificazione_sposta_ods(request, ods_pk):
    try:
        data = json.loads(request.body)
        nuova_data = date.fromisoformat(data["data"][:10])

        from .models import ODS
        ods = get_object_or_404(ODS, pk=ods_pk)

        if ods.stato in ("completato", "fatturato"):
            return JsonResponse(
                {"ok": False, "errore": "Non puoi spostare un ODS già completato o fatturato."},
                status=400,
            )

        ods.data_servizio = nuova_data
        ods.save(update_fields=["data_servizio", "updated_at"])

        return JsonResponse({"ok": True, "numero": ods.numero, "data": nuova_data.isoformat()})

    except Exception as e:
        return JsonResponse({"ok": False, "errore": str(e)}, status=400)
