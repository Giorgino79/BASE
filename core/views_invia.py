"""
View AJAX per il bottone INVIA — invia documenti (testo o PDF) via WhatsApp e/o email.
Risponde in JSON; l'invio WhatsApp avviene in un thread separato per non bloccare la risposta.
"""

import json
import os
import threading

from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings as django_settings

from .whatsapp_sender import WhatsAppSender, is_configured, check_authorized, normalize_phone
from .models.invia_log import InvioLog


@login_required
@require_POST
def invia_documento(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = request.POST

    canale = data.get("canale", "whatsapp").strip()
    telefono = data.get("telefono", "").strip()
    email_dest = data.get("email", "").strip()
    oggetto = data.get("oggetto", "Documento").strip()
    messaggio = data.get("messaggio", "").strip()
    pdf_url = data.get("pdf_url", "").strip()
    pdf_local_path = data.get("pdf_path", "").strip()
    destinatario_nome = data.get("destinatario_nome", "").strip()

    # Validazione
    if canale in ("whatsapp", "entrambi") and not telefono:
        return JsonResponse({"success": False, "error": "Numero WhatsApp obbligatorio"})
    if canale in ("email", "entrambi") and not email_dest:
        return JsonResponse({"success": False, "error": "Email destinatario obbligatoria"})
    if canale in ("whatsapp", "entrambi") and not is_configured():
        return JsonResponse({"success": False, "error": "WhatsApp non configurato — imposta GREENAPI_INSTANCE_ID e GREENAPI_TOKEN"})
    if canale in ("whatsapp", "entrambi"):
        ok, err = check_authorized()
        if not ok:
            return JsonResponse({"success": False, "error": err})

    # Costruisce subito l'URL assoluta dal request (garantisce l'host corretto su qualsiasi server)
    if pdf_url and not pdf_url.startswith("http"):
        abs_pdf_url = request.build_absolute_uri(pdf_url)
    else:
        abs_pdf_url = pdf_url

    log = InvioLog.objects.create(
        utente=request.user,
        canale=canale,
        destinatario_nome=destinatario_nome,
        telefono=normalize_phone(telefono) if telefono else "",
        email=email_dest,
        oggetto=oggetto,
        messaggio=messaggio,
        ha_pdf=bool(pdf_url or pdf_local_path),
        stato="pending",
    )

    def _send():
        tmp_created = False
        local_path = pdf_local_path or None

        try:
            # --- WhatsApp ---
            if canale in ("whatsapp", "entrambi"):
                wa_log = log if canale == "whatsapp" else None
                caption = messaggio or oggetto
                if abs_pdf_url and abs_pdf_url.startswith("http"):
                    filename = os.path.basename(pdf_url.split("?")[0]) or "documento.pdf"
                    if not filename.endswith(".pdf"):
                        filename += ".pdf"
                    WhatsAppSender.send_pdf_by_url(telefono, abs_pdf_url, filename=filename, caption=caption, log_entry=wa_log)
                elif local_path and os.path.exists(local_path):
                    WhatsAppSender.send_pdf(telefono, local_path, caption=caption, log_entry=wa_log)
                else:
                    testo = f"{oggetto}\n\n{messaggio}".strip() if messaggio else oggetto
                    WhatsAppSender.send_message(telefono, testo, log_entry=wa_log)

            # --- Email ---
            if canale in ("email", "entrambi"):
                # Per email con PDF remoto: scarica prima in locale
                if abs_pdf_url and abs_pdf_url.startswith("http") and not local_path:
                    local_path = WhatsAppSender.resolve_local_path(pdf_url)
                _send_email(email_dest, oggetto, messaggio, local_path)
                if canale == "email":
                    log.stato = "inviato"
                    log.save(update_fields=["stato", "updated_at"])

            if canale == "entrambi":
                log.stato = "inviato"
                log.save(update_fields=["stato", "updated_at"])

        except Exception as exc:
            log.stato = "errore"
            log.errore_dettaglio = str(exc)
            log.save(update_fields=["stato", "errore_dettaglio", "updated_at"])

        finally:
            if tmp_created and local_path and os.path.exists(local_path):
                os.unlink(local_path)

    threading.Thread(target=_send, daemon=True).start()

    label = {
        "whatsapp": "Messaggio WhatsApp inviato — controlla il telefono",
        "email": "Email in invio…",
        "entrambi": "WhatsApp + Email inviati",
    }.get(canale, "Invio in corso…")

    return JsonResponse({"success": True, "message": label, "log_id": log.pk})


def _send_email(to: str, subject: str, body: str, pdf_path: str | None) -> None:
    email = EmailMessage(
        subject=subject or "Documento",
        body=body or subject or "In allegato il documento richiesto.",
        from_email=django_settings.DEFAULT_FROM_EMAIL,
        to=[to],
    )
    if pdf_path and os.path.exists(pdf_path):
        email.attach_file(pdf_path)
    email.send()
