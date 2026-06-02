"""
Views per la gestione dei QR Code.
Sistema completo per generare, visualizzare e scaricare QR Code collegati a qualsiasi oggetto.
"""

from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.urls import reverse
from .models_legacy import QRCode
import qrcode
from io import BytesIO


# ============================================================================
# QR CODE VIEWS
# ============================================================================


@login_required
@require_http_methods(["POST"])
def qrcode_generate(request):
    """
    Genera o recupera un QR Code per un oggetto specifico.

    POST parameters:
        - content_type: ID del ContentType
        - object_id: ID dell'oggetto

    Returns:
        JSON con dati del QR Code creato/esistente
    """
    try:
        content_type_id = request.POST.get("content_type")
        object_id = request.POST.get("object_id")

        if not content_type_id or not object_id:
            return JsonResponse({"error": "Parametri mancanti"}, status=400)

        # Recupera ContentType
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
        except ContentType.DoesNotExist:
            return JsonResponse({"error": "Tipo contenuto non valido"}, status=400)

        # Verifica se esiste già un QR Code per questo oggetto
        qr_obj, created = QRCode.objects.get_or_create(
            content_type=content_type,
            object_id=object_id,
            defaults={"created_by": request.user}
        )

        # Verifica se l'immagine esiste
        has_image = bool(qr_obj.qr_image) and qr_obj.qr_image.name

        # Se è appena stato creato o manca l'immagine, genera l'immagine QR
        if created or not has_image:
            # Recupera l'oggetto reale per costruire l'URL
            obj = content_type.get_object_for_this_type(pk=object_id)

            # Costruisce URL assoluto all'oggetto
            # Prova a usare get_absolute_url() se esiste, altrimenti usa admin URL
            if hasattr(obj, 'get_absolute_url'):
                obj_url = obj.get_absolute_url()
            else:
                # Fallback: URL admin
                obj_url = reverse(
                    f'admin:{content_type.app_label}_{content_type.model}_change',
                    args=[object_id]
                )

            # URL assoluto completo
            full_url = request.build_absolute_uri(obj_url)
            qr_obj.url = full_url

            # Genera QR Code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(full_url)
            qr.make(fit=True)

            # Crea immagine
            img = qr.make_image(fill_color="black", back_color="white")

            # Salva in BytesIO
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            # Salva nel modello
            filename = f"qr_{content_type.model}_{object_id}.png"
            qr_obj.qr_image.save(filename, ContentFile(buffer.read()), save=False)
            qr_obj.save()

        # Label leggibile dell'oggetto (es. "TRS-2026-002 - Titolo")
        try:
            linked_obj = content_type.get_object_for_this_type(pk=object_id)
            object_label = str(linked_obj)
        except Exception:
            object_label = f"{content_type.model}_{object_id}"

        # Restituisci dati QR Code
        return JsonResponse({
            "success": True,
            "qrcode": {
                "id": qr_obj.pk,
                "url": qr_obj.url,
                "image_url": qr_obj.qr_image.url,
                "created_at": qr_obj.created_at.strftime("%d/%m/%Y %H:%M"),
                "created": created,
                "object_label": object_label,
            }
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def qrcode_download(request, qrcode_id):
    """
    Download dell'immagine QR Code.

    URL: /core/qrcode/<id>/download/
    """
    try:
        qr_obj = QRCode.objects.get(pk=qrcode_id)

        # Costruisce filename dal label dell'oggetto (es. "TRS-2026-002.png")
        try:
            linked_obj = qr_obj.content_type.get_object_for_this_type(pk=qr_obj.object_id)
            raw_label = str(linked_obj).split(' - ')[0].strip()  # prende solo il codice/numero
            import re
            safe_label = re.sub(r'[^\w\-]', '_', raw_label)
            download_filename = f"{safe_label}.png"
        except Exception:
            download_filename = f"qrcode_{qr_obj.pk}.png"

        # FileResponse gestisce automaticamente il download
        response = FileResponse(
            qr_obj.qr_image.open("rb"),
            as_attachment=True,
            filename=download_filename,
        )

        return response

    except QRCode.DoesNotExist:
        raise Http404("QR Code non trovato")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["DELETE", "POST"])  # POST per compatibilità browser
def qrcode_delete(request, qrcode_id):
    """
    Elimina un QR Code.

    URL: /core/qrcode/<id>/delete/
    """
    try:
        qr_obj = QRCode.objects.get(pk=qrcode_id)

        # Elimina (il file immagine viene eliminato automaticamente tramite override delete())
        qr_obj.delete()

        return JsonResponse({
            "success": True,
            "message": "QR Code eliminato con successo"
        })

    except QRCode.DoesNotExist:
        return JsonResponse({"error": "QR Code non trovato"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def qrcode_stampa(request, content_type_id, object_id):
    """
    Pagina di stampa etichetta QR Code.
    Genera automaticamente il QR se non esiste ancora, poi mostra la pagina di stampa.

    URL: /core/qrcode/<content_type_id>/<object_id>/stampa/
    """
    try:
        content_type = ContentType.objects.get(pk=content_type_id)
    except ContentType.DoesNotExist:
        raise Http404("Tipo contenuto non valido")

    try:
        linked_obj = content_type.get_object_for_this_type(pk=object_id)
    except Exception:
        raise Http404("Oggetto non trovato")

    qr_obj, created = QRCode.objects.get_or_create(
        content_type=content_type,
        object_id=object_id,
        defaults={"created_by": request.user}
    )

    has_image = bool(qr_obj.qr_image) and qr_obj.qr_image.name

    if created or not has_image:
        if hasattr(linked_obj, 'get_absolute_url'):
            obj_url = linked_obj.get_absolute_url()
        else:
            obj_url = reverse(
                f'admin:{content_type.app_label}_{content_type.model}_change',
                args=[object_id]
            )

        full_url = request.build_absolute_uri(obj_url)
        qr_obj.url = full_url

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(full_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f"qr_{content_type.model}_{object_id}.png"
        qr_obj.qr_image.save(filename, ContentFile(buffer.read()), save=False)
        qr_obj.save()

    from django.shortcuts import render
    return render(request, 'core/qrcode_stampa.html', {
        'qr_obj': qr_obj,
        'linked_obj': linked_obj,
        'object_label': str(linked_obj),
        'content_type': content_type,
    })


@login_required
@require_http_methods(["GET"])
def qrcode_check(request):
    """
    Verifica se esiste un QR Code per un oggetto specifico.

    GET parameters:
        - content_type: ID del ContentType
        - object_id: ID dell'oggetto

    Returns:
        JSON con informazioni sul QR Code se esiste
    """
    try:
        content_type_id = request.GET.get("content_type")
        object_id = request.GET.get("object_id")

        if not content_type_id or not object_id:
            return JsonResponse({"error": "Parametri mancanti"}, status=400)

        # Cerca QR Code esistente
        try:
            qr_obj = QRCode.objects.get(
                content_type_id=content_type_id,
                object_id=object_id
            )

            # Verifica se l'immagine esiste
            has_image = bool(qr_obj.qr_image) and qr_obj.qr_image.name
            if not has_image:
                # QR esiste ma immagine mancante, trattalo come non esistente
                return JsonResponse({
                    "success": True,
                    "exists": False
                })

            try:
                linked_obj = qr_obj.content_type.get_object_for_this_type(pk=qr_obj.object_id)
                object_label = str(linked_obj)
            except Exception:
                object_label = f"{qr_obj.content_type.model}_{qr_obj.object_id}"

            return JsonResponse({
                "success": True,
                "exists": True,
                "qrcode": {
                    "id": qr_obj.pk,
                    "url": qr_obj.url,
                    "image_url": qr_obj.qr_image.url,
                    "created_at": qr_obj.created_at.strftime("%d/%m/%Y %H:%M"),
                    "object_label": object_label,
                }
            })
        except QRCode.DoesNotExist:
            return JsonResponse({
                "success": True,
                "exists": False
            })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
