"""
Views AJAX per la gestione degli allegati.
Sistema completo con permessi granulari.
"""

from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from .models_legacy import Allegato
import json
import os


# ============================================================================
# CONSTANTS
# ============================================================================

# Estensioni file permesse per upload
ALLOWED_FILE_EXTENSIONS = {
    '.pdf',   # PDF
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',  # Immagini
    '.doc', '.docx',  # Word
    '.xls', '.xlsx',  # Excel
    '.odt', '.ods',   # OpenOffice
    '.txt', '.csv',   # Text
    '.zip', '.rar',   # Archivi compressi
}

# Dimensione massima file: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB in bytes

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def validate_file_upload(file):
    """
    Valida un file caricato dall'utente.

    Controlla:
    - Estensione file permessa
    - Dimensione file entro limiti

    Args:
        file: UploadedFile object

    Returns:
        tuple: (is_valid, error_message)

    Example:
        is_valid, error = validate_file_upload(request.FILES['file'])
        if not is_valid:
            return JsonResponse({"error": error}, status=400)
    """
    # Controlla estensione
    file_ext = os.path.splitext(file.name)[1].lower()

    if file_ext not in ALLOWED_FILE_EXTENSIONS:
        allowed_list = ', '.join(sorted(ALLOWED_FILE_EXTENSIONS))
        return False, f"Tipo file non consentito. Formati permessi: {allowed_list}"

    # Controlla dimensione
    if file.size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        actual_mb = file.size / (1024 * 1024)
        return False, f"File troppo grande ({actual_mb:.1f}MB). Dimensione massima: {max_mb:.0f}MB"

    return True, None


def can_user_delete_allegato(allegato, user):
    """
    Verifica se l'utente può eliminare l'allegato.

    Regole:
    - Admin/Staff: può eliminare tutto
    - Creatore: può eliminare solo i propri
    - Altri: non possono eliminare
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    if allegato.uploaded_by == user:
        return True

    return False


def can_user_modify_allegato(allegato, user):
    """
    Verifica se l'utente può modificare l'allegato.
    Stesse regole di can_user_delete_allegato.
    """
    return can_user_delete_allegato(allegato, user)


# ============================================================================
# AJAX VIEWS
# ============================================================================


@login_required
@require_http_methods(["POST"])
def allegato_upload(request):
    """
    Upload di un nuovo allegato via AJAX.

    POST parameters:
        - file: file da caricare
        - content_type: ID del ContentType
        - object_id: ID dell'oggetto
        - descrizione: descrizione opzionale

    Returns:
        JSON con dati allegato creato o errore
    """
    try:
        # Validazione dati
        if "file" not in request.FILES:
            return JsonResponse({"error": "Nessun file fornito"}, status=400)

        # SECURITY: Valida file prima di salvarlo
        uploaded_file = request.FILES["file"]
        is_valid, error_message = validate_file_upload(uploaded_file)

        if not is_valid:
            return JsonResponse({"error": error_message}, status=400)

        content_type_id = request.POST.get("content_type")
        object_id = request.POST.get("object_id")

        if not content_type_id or not object_id:
            return JsonResponse({"error": "Parametri mancanti"}, status=400)

        # Recupera ContentType
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
        except ContentType.DoesNotExist:
            return JsonResponse({"error": "Tipo contenuto non valido"}, status=400)

        # Crea allegato (file già validato)
        allegato = Allegato.objects.create(
            content_type=content_type,
            object_id=object_id,
            file=uploaded_file,
            descrizione=request.POST.get("descrizione", ""),
            uploaded_by=request.user,
        )

        # Restituisci dati allegato
        return JsonResponse(
            {
                "success": True,
                "allegato": {
                    "id": allegato.pk,
                    "nome": allegato.nome_originale,
                    "dimensione": allegato.get_size_display(),
                    "data": allegato.created_at.strftime("%d/%m/%Y %H:%M"),
                    "uploaded_by": allegato.uploaded_by.get_full_name()
                    or allegato.uploaded_by.username,
                    "url": allegato.file.url,
                    "is_pdf": allegato.is_pdf(),
                    "is_image": allegato.is_image(),
                },
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def allegati_list(request):
    """
    Restituisce lista allegati di un oggetto via AJAX.

    GET parameters:
        - content_type: ID del ContentType
        - object_id: ID dell'oggetto

    Returns:
        JSON con lista allegati
    """
    try:
        content_type_id = request.GET.get("content_type")
        object_id = request.GET.get("object_id")

        if not content_type_id or not object_id:
            return JsonResponse({"error": "Parametri mancanti"}, status=400)

        # Recupera allegati
        allegati = (
            Allegato.objects.filter(
                content_type_id=content_type_id, object_id=object_id
            )
            .select_related("uploaded_by")
            .order_by("-created_at")
        )

        # Prepara dati con permessi
        allegati_data = []
        for allegato in allegati:
            allegati_data.append(
                {
                    "id": allegato.pk,
                    "nome": allegato.nome_originale,
                    "descrizione": allegato.descrizione,
                    "dimensione": allegato.get_size_display(),
                    "data": allegato.created_at.strftime("%d/%m/%Y %H:%M"),
                    "uploaded_by": (
                        allegato.uploaded_by.get_full_name()
                        or allegato.uploaded_by.username
                        if allegato.uploaded_by
                        else "Anonimo"
                    ),
                    "url": allegato.file.url,
                    "is_pdf": allegato.is_pdf(),
                    "is_image": allegato.is_image(),
                    "can_delete": can_user_delete_allegato(allegato, request.user),
                    "can_modify": can_user_modify_allegato(allegato, request.user),
                }
            )

        return JsonResponse(
            {"success": True, "allegati": allegati_data, "count": len(allegati_data)}
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["DELETE", "POST"])  # POST per compatibilità browser
def allegato_delete(request, allegato_id):
    """
    Elimina un allegato.

    URL: /core/allegati/<id>/delete/

    Permessi:
    - Admin: può eliminare tutto
    - Creatore: può eliminare solo i propri
    """
    try:
        allegato = Allegato.objects.get(pk=allegato_id)

        # Verifica permessi
        if not can_user_delete_allegato(allegato, request.user):
            raise PermissionDenied("Non hai i permessi per eliminare questo allegato")

        # Elimina (il file fisico viene eliminato automaticamente tramite override delete())
        allegato.delete()

        return JsonResponse(
            {"success": True, "message": "Allegato eliminato con successo"}
        )

    except Allegato.DoesNotExist:
        return JsonResponse({"error": "Allegato non trovato"}, status=404)
    except PermissionDenied as e:
        return JsonResponse({"error": str(e)}, status=403)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def allegato_download(request, allegato_id):
    """
    Download di un allegato.

    URL: /core/allegati/<id>/download/

    Tutti gli utenti autenticati possono scaricare gli allegati.
    """
    try:
        allegato = Allegato.objects.get(pk=allegato_id)

        # FileResponse gestisce automaticamente il download
        response = FileResponse(
            allegato.file.open("rb"),
            as_attachment=True,
            filename=allegato.nome_originale,
        )

        return response

    except Allegato.DoesNotExist:
        raise Http404("Allegato non trovato")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def allegato_preview(request, allegato_id):
    """
    Preview di un allegato (per PDF e immagini).

    URL: /core/allegati/<id>/preview/

    Restituisce il file inline (non come download).
    """
    try:
        allegato = Allegato.objects.get(pk=allegato_id)

        # Solo PDF e immagini hanno preview
        if not (allegato.is_pdf() or allegato.is_image()):
            return JsonResponse(
                {"error": "Preview non disponibile per questo tipo di file"}, status=400
            )

        # FileResponse inline (apre nel browser)
        response = FileResponse(
            allegato.file.open("rb"),
            content_type=allegato.tipo_file or "application/octet-stream",
        )

        return response

    except Allegato.DoesNotExist:
        raise Http404("Allegato non trovato")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ============================================================================
# RICERCA GLOBALE
# ============================================================================


@login_required
@require_http_methods(["GET"])
def global_search(request):
    """
    Ricerca globale in tutti i model registrati nel SearchRegistry.

    GET parameters:
        - q: query di ricerca

    Returns:
        JSON con risultati raggruppati per categoria
    """
    from .search import SearchRegistry

    try:
        query = request.GET.get("q", "").strip()

        if not query or len(query) < 2:
            return JsonResponse(
                {"success": False, "error": "Query troppo corta (minimo 2 caratteri)"},
                status=400,
            )

        # Esegue ricerca in tutti i model registrati
        results = SearchRegistry.search_all(query, max_results_per_model=5)

        return JsonResponse(
            {
                "success": True,
                "query": query,
                "results": results,
                "total_categories": len(results),
                "total_results": sum(len(cat["items"]) for cat in results),
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
