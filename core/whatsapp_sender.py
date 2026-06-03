"""
WhatsApp Sender — invia messaggi via Green API (green-api.com).

Prerequisito: creare un'istanza su green-api.com, scansionare il QR con il numero
mittente e configurare GREENAPI_INSTANCE_ID e GREENAPI_TOKEN nelle variabili d'ambiente.

Il numero mittente è quello che ha scansionato il QR — può essere personale o aziendale.
"""

import os
import re
import requests

from django.conf import settings as django_settings

GREENAPI_BASE = "https://api.green-api.com"


def _credentials():
    """Restituisce (instance_id, token) oppure (None, None) se non configurati."""
    iid   = getattr(django_settings, "GREENAPI_INSTANCE_ID", "")
    token = getattr(django_settings, "GREENAPI_TOKEN", "")
    if iid and token:
        return iid, token
    return None, None


def is_configured() -> bool:
    iid, token = _credentials()
    return bool(iid and token)


def normalize_phone(phone: str) -> str:
    """
    Normalizza il numero in formato Green API chatId: 393331234567@c.us
    Accetta: 3331234567, 393331234567, +393331234567, 0039...
    """
    phone = re.sub(r"[\s\-\.\(\)+]", "", phone)
    if phone.startswith("0039"):
        phone = phone[2:]
    elif not phone.startswith("39"):
        phone = "39" + phone
    return f"{phone}@c.us"


class WhatsAppSender:

    @classmethod
    def _url(cls, endpoint: str) -> str:
        iid, token = _credentials()
        return f"{GREENAPI_BASE}/waInstance{iid}/{endpoint}/{token}"

    @classmethod
    def send_message(cls, phone: str, message: str, log_entry=None) -> bool:
        if not is_configured():
            _fail(log_entry, "Green API non configurata (GREENAPI_INSTANCE_ID / GREENAPI_TOKEN mancanti)")
            return False
        try:
            resp = requests.post(
                cls._url("sendMessage"),
                json={"chatId": normalize_phone(phone), "message": message},
                timeout=30,
            )
            resp.raise_for_status()
            _ok(log_entry)
            return True
        except Exception as exc:
            _fail(log_entry, str(exc))
            return False

    @classmethod
    def send_pdf(cls, phone: str, pdf_path: str, caption: str = "", log_entry=None) -> bool:
        if not is_configured():
            _fail(log_entry, "Green API non configurata")
            return False
        if not os.path.exists(pdf_path):
            _fail(log_entry, f"File non trovato: {pdf_path}")
            return False
        try:
            filename = os.path.basename(pdf_path)
            with open(pdf_path, "rb") as f:
                resp = requests.post(
                    cls._url("sendFileByUpload"),
                    data={"chatId": normalize_phone(phone), "caption": caption},
                    files={"file": (filename, f, "application/pdf")},
                    timeout=60,
                )
            resp.raise_for_status()
            _ok(log_entry)
            return True
        except Exception as exc:
            _fail(log_entry, str(exc))
            return False

    @classmethod
    def send_pdf_by_url(cls, phone: str, url: str, filename: str = "documento.pdf", caption: str = "", log_entry=None) -> bool:
        """Invia un PDF tramite URL pubblica (più efficiente di upload)."""
        if not is_configured():
            _fail(log_entry, "Green API non configurata")
            return False
        try:
            resp = requests.post(
                cls._url("sendFileByUrl"),
                json={
                    "chatId": normalize_phone(phone),
                    "urlFile": url,
                    "fileName": filename,
                    "caption": caption,
                },
                timeout=30,
            )
            resp.raise_for_status()
            _ok(log_entry)
            return True
        except Exception as exc:
            _fail(log_entry, str(exc))
            return False

    @classmethod
    def resolve_local_path(cls, pdf_url: str):
        """Converte URL relativa Django in percorso assoluto. Ritorna None se non riesce."""
        if not pdf_url:
            return None
        if pdf_url.startswith("/media/"):
            return os.path.join(str(django_settings.MEDIA_ROOT), pdf_url[7:])
        if pdf_url.startswith("/"):
            return os.path.join(str(django_settings.BASE_DIR), pdf_url.lstrip("/"))
        return None


def _ok(log_entry) -> None:
    if log_entry:
        log_entry.stato = "inviato"
        log_entry.save(update_fields=["stato", "updated_at"])


def _fail(log_entry, detail: str) -> None:
    if log_entry:
        log_entry.stato = "errore"
        log_entry.errore_dettaglio = detail
        log_entry.save(update_fields=["stato", "errore_dettaglio", "updated_at"])
