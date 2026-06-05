from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse

from anagrafica.models import Cliente


@login_required
def api_contatti_search(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    qs = (
        Cliente.objects.filter(
            Q(ragione_sociale__icontains=q)
            | Q(telefono__icontains=q)
            | Q(email__icontains=q),
            attivo=True,
        )
        .values("id", "ragione_sociale", "telefono", "email")
        .order_by("ragione_sociale")[:25]
    )
    results = [
        {
            "id": c["id"],
            "text": c["ragione_sociale"],
            "telefono": c["telefono"],
            "email": c["email"],
        }
        for c in qs
    ]
    return JsonResponse({"results": results})
