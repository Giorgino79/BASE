"""
WhatsApp Sender — core utility per invio messaggi e PDF via WhatsApp Web.

Usa pywhatkit che apre WhatsApp Web nel browser della macchina locale.
Prerequisito: account WhatsApp loggato su WhatsApp Web nel browser di default.

Rate limiting: minimo WHATSAPP_MIN_DELAY secondi tra invii consecutivi (default 20+jitter)
per ridurre il rischio di blocco dell'account senza Business API.
"""

import os
import re
import time
import random
import threading
import tempfile
import urllib.request
from typing import Optional

from django.conf import settings as django_settings

MIN_DELAY: int = getattr(django_settings, "WHATSAPP_MIN_DELAY", 20)
WAIT_TIME: int = getattr(django_settings, "WHATSAPP_WAIT_TIME", 12)


def _get_pywhatkit():
    """Import lazy: evita crash al caricamento del modulo se il display X non è disponibile."""
    try:
        import pywhatkit
        return pywhatkit
    except (ImportError, Exception):
        return None


PYWHATKIT_AVAILABLE: bool = True  # verificato a runtime in _get_pywhatkit()


def normalize_phone(phone: str) -> str:
    """
    Normalizza il numero in formato pywhatkit: +39XXXXXXXXXX
    Accetta: 3331234567, 393331234567, +393331234567, 0039...
    """
    phone = re.sub(r"[\s\-\.\(\)]", "", phone)
    if phone.startswith("0039"):
        phone = "+" + phone[2:]
    elif phone.startswith("39") and not phone.startswith("+"):
        phone = "+" + phone
    elif not phone.startswith("+"):
        phone = "+39" + phone
    return phone


class WhatsAppSender:
    """
    Invia messaggi e file PDF via WhatsApp Web (pywhatkit).
    Thread-safe: applica rate limiting globale tra invii consecutivi.
    """

    _lock = threading.Lock()
    _last_send_time: float = 0.0

    @classmethod
    def _apply_rate_limit(cls) -> None:
        with cls._lock:
            now = time.time()
            elapsed = now - cls._last_send_time
            jitter = random.uniform(0, 5)
            gap = MIN_DELAY + jitter
            if elapsed < gap:
                time.sleep(gap - elapsed)
            cls._last_send_time = time.time()

    @classmethod
    def send_message(cls, phone: str, message: str, log_entry=None) -> bool:
        pw = _get_pywhatkit()
        if pw is None:
            _fail(log_entry, "pywhatkit non disponibile (pip install pywhatkit o display X mancante)")
            return False
        try:
            cls._apply_rate_limit()
            pw.sendwhatmsg_instantly(
                phone_no=normalize_phone(phone),
                message=message,
                wait_time=WAIT_TIME,
                tab_close=True,
                close_time=3,
            )
            _ok(log_entry)
            return True
        except Exception as exc:
            _fail(log_entry, str(exc))
            return False

    @classmethod
    def send_pdf(cls, phone: str, pdf_path: str, caption: str = "", log_entry=None) -> bool:
        pw = _get_pywhatkit()
        if pw is None:
            _fail(log_entry, "pywhatkit non disponibile (pip install pywhatkit o display X mancante)")
            return False
        if not os.path.exists(pdf_path):
            _fail(log_entry, f"File non trovato: {pdf_path}")
            return False
        try:
            cls._apply_rate_limit()
            pw.sendwhats_image(
                receiver=normalize_phone(phone),
                img_location=pdf_path,
                caption=caption,
                wait_time=WAIT_TIME,
                tab_close=True,
                close_time=3,
            )
            _ok(log_entry)
            return True
        except Exception as exc:
            _fail(log_entry, str(exc))
            return False

    @classmethod
    def resolve_local_path(cls, pdf_url: str) -> Optional[str]:
        """
        Converte una URL relativa Django in percorso assoluto sul filesystem.
        Se l'URL è esterna, scarica in un file temporaneo e restituisce il path.
        Restituisce None se non riesce.
        """
        if not pdf_url:
            return None
        if pdf_url.startswith("/media/"):
            return os.path.join(str(django_settings.MEDIA_ROOT), pdf_url[7:])
        if pdf_url.startswith("/"):
            return os.path.join(str(django_settings.BASE_DIR), pdf_url.lstrip("/"))
        # URL esterna — scarica in temp
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            urllib.request.urlretrieve(pdf_url, tmp.name)
            return tmp.name
        except Exception:
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
