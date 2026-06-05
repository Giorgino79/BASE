from django.contrib.auth.decorators import login_required
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.http import JsonResponse

from anagrafica_r2.models import Azienda, Privato, Fornitore


@login_required
def api_contatti_search(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    results = []

    # Aziende
    for a in Azienda.objects.filter(
        Q(ragione_sociale__icontains=q) | Q(telefono__icontains=q) | Q(email_operativo__icontains=q)
    ).values("id", "ragione_sociale", "telefono", "email_operativo")[:10]:
        results.append({
            "id": f"a_{a['id']}",
            "text": a["ragione_sociale"],
            "telefono": a["telefono"],
            "email": a["email_operativo"],
        })

    # Privati
    for p in Privato.objects.filter(
        Q(nome__icontains=q) | Q(cognome__icontains=q) | Q(telefono__icontains=q)
    ).values("id", "nome", "cognome", "telefono", "email")[:10]:
        results.append({
            "id": f"p_{p['id']}",
            "text": f"{p['cognome']} {p['nome']}".strip(),
            "telefono": p["telefono"],
            "email": p["email"],
        })

    # Fornitori
    for f in Fornitore.objects.filter(
        Q(ragione_sociale__icontains=q) | Q(telefono__icontains=q) | Q(email__icontains=q)
    ).values("id", "ragione_sociale", "telefono", "email")[:5]:
        results.append({
            "id": f"f_{f['id']}",
            "text": f["ragione_sociale"],
            "telefono": f["telefono"],
            "email": f["email"],
        })

    results.sort(key=lambda x: x["text"].lower())
    return JsonResponse({"results": results[:25]})
