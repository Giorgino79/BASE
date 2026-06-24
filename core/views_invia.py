"""
View AJAX per il bottone INVIA — invia documenti (testo o PDF) via WhatsApp e/o email.
Risponde in JSON; l'invio WhatsApp avviene in un thread separato per non bloccare la risposta.
"""

import json
import os
import tempfile
import threading

from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings as django_settings

from .whatsapp_sender import WhatsAppSender, is_configured, check_authorized, normalize_phone
from .models.invia_log import InvioLog


def _fetch_pdf_with_session(abs_url: str, session_id: str) -> str | None:
    """
    Scarica un PDF da una URL Django protetta da login usando il session cookie.
    Salva in un file temporaneo e restituisce il percorso, oppure None in caso di errore.
    """
    import requests as _req
    try:
        resp = _req.get(
            abs_url,
            cookies={"sessionid": session_id},
            timeout=30,
            allow_redirects=False,
        )
        if resp.status_code == 200 and "pdf" in resp.headers.get("content-type", ""):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(resp.content)
            tmp.close()
            return tmp.name
    except Exception:
        pass
    return None


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
    link_url = data.get("link_url", "").strip()
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

    # Costruisce URL assoluta
    if pdf_url and not pdf_url.startswith("http"):
        abs_pdf_url = request.build_absolute_uri(pdf_url)
    else:
        abs_pdf_url = pdf_url

    if link_url and not link_url.startswith("http"):
        abs_link_url = request.build_absolute_uri(link_url)
    else:
        abs_link_url = link_url

    # Se la pdf_url punta a una view Django (non a un file statico/media),
    # la scarica subito con il session cookie dell'utente, prima del thread.
    # Questo risolve il problema dei PDF protetti da @login_required.
    pre_downloaded_path = None
    session_id = request.COOKIES.get("sessionid", "")
    if abs_pdf_url and session_id and not pdf_local_path:
        is_static = any(abs_pdf_url.split("?")[0].endswith(ext)
                        for ext in (".pdf", ".png", ".jpg", ".jpeg"))
        if not is_static:
            pre_downloaded_path = _fetch_pdf_with_session(abs_pdf_url, session_id)

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
        tmp_to_delete = pre_downloaded_path
        local_path = pre_downloaded_path or pdf_local_path or None

        # Testo finale: messaggio + link (se presente)
        testo_extra = messaggio
        if abs_link_url:
            testo_extra = f"{messaggio}\n\n{abs_link_url}".strip() if messaggio else abs_link_url

        try:
            caption = testo_extra or oggetto

            # --- WhatsApp ---
            if canale in ("whatsapp", "entrambi"):
                wa_log = log if canale == "whatsapp" else None
                if local_path and os.path.exists(local_path):
                    # Upload diretto: funziona anche con URL protette da login
                    WhatsAppSender.send_pdf(telefono, local_path, caption=caption, log_entry=wa_log)
                elif abs_pdf_url and abs_pdf_url.startswith("http"):
                    # Fallback URL pubblica (es. file su S3/media)
                    filename = os.path.basename(pdf_url.split("?")[0]) or "documento.pdf"
                    if not filename.endswith(".pdf"):
                        filename += ".pdf"
                    WhatsAppSender.send_pdf_by_url(telefono, abs_pdf_url, filename=filename, caption=caption, log_entry=wa_log)
                else:
                    testo = f"{oggetto}\n\n{testo_extra}".strip() if testo_extra else oggetto
                    if not testo:
                        testo = "Messaggio da Rattus26"
                    WhatsAppSender.send_message(telefono, testo, log_entry=wa_log)

            # --- Email ---
            if canale in ("email", "entrambi"):
                _send_email(email_dest, oggetto, testo_extra or messaggio, local_path)
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
            if tmp_to_delete and os.path.exists(tmp_to_delete):
                os.unlink(tmp_to_delete)

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
