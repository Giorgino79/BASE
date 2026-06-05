from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse

from anagrafica_r2.models import Azienda, Privato, Fornitore

User = get_user_model()


@login_required
def api_contatti_search(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    results = []

    # Utenti del sistema (tecnici, assistenti, ecc.)
    for u in User.objects.filter(
        Q(first_name__icontains=q)
        | Q(last_name__icontains=q)
        | Q(email__icontains=q)
        | Q(telefono__icontains=q),
        is_active=True,
    ).exclude(first_name="", last_name="").values(
        "id", "first_name", "last_name", "email", "telefono"
    )[:10]:
        nome = f"{u['first_name']} {u['last_name']}".strip()
        results.append({
            "id": f"u_{u['id']}",
            "text": nome,
            "tipo": "Utente",
            "telefono": u["telefono"],
            "email": u["email"],
        })

    # Aziende / clienti
    for a in Azienda.objects.filter(
        Q(ragione_sociale__icontains=q)
        | Q(telefono__icontains=q)
        | Q(email_operativo__icontains=q),
    ).values("id", "ragione_sociale", "telefono", "email_operativo")[:10]:
        results.append({
            "id": f"a_{a['id']}",
            "text": a["ragione_sociale"],
            "tipo": "Azienda",
            "telefono": a["telefono"],
            "email": a["email_operativo"],
        })

    # Privati
    for p in Privato.objects.filter(
        Q(nome__icontains=q)
        | Q(cognome__icontains=q)
        | Q(telefono__icontains=q),
    ).values("id", "nome", "cognome", "telefono", "email")[:10]:
        results.append({
            "id": f"p_{p['id']}",
            "text": f"{p['cognome']} {p['nome']}".strip(),
            "tipo": "Privato",
            "telefono": p["telefono"],
            "email": p["email"],
        })

    # Fornitori
    for f in Fornitore.objects.filter(
        Q(ragione_sociale__icontains=q)
        | Q(telefono__icontains=q)
        | Q(email__icontains=q),
    ).values("id", "ragione_sociale", "telefono", "email")[:5]:
        results.append({
            "id": f"f_{f['id']}",
            "text": f["ragione_sociale"],
            "tipo": "Fornitore",
            "telefono": f["telefono"],
            "email": f["email"],
        })

    results.sort(key=lambda x: x["text"].lower())
    return JsonResponse({"results": results[:30]})
