"""
Servizio WhatsApp — invia messaggi via Green API (green-api.com).

Standardizzato su Green API il 26/08/2026 (era un microservizio Node basato su
whatsapp-web.js — non ufficiale, rischio di ban del numero, vedi
docs/piani_azione/03_whatsapp_api_ufficiale.md). Stesso motore usato da
rattus26: è l'unica implementazione WhatsApp del catalogo (vedi Libro Mastro,
Capitolo 1).

Prerequisito: creare un'istanza su green-api.com, scansionare il QR (mostrato
in whatsapp:impostazioni) e configurare GREENAPI_INSTANCE_ID/GREENAPI_TOKEN
nelle variabili d'ambiente.
"""

import os
import re
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GREENAPI_BASE = "https://api.green-api.com"


def _credentials():
    """Ritorna (instance_id, token) oppure (None, None) se non configurati."""
    iid = getattr(settings, "GREENAPI_INSTANCE_ID", "")
    token = getattr(settings, "GREENAPI_TOKEN", "")
    if iid and token:
        return iid, token
    return None, None


def is_configured() -> bool:
    iid, token = _credentials()
    return bool(iid and token)


def _url(endpoint: str) -> str:
    iid, token = _credentials()
    return f"{GREENAPI_BASE}/waInstance{iid}/{endpoint}/{token}"


def normalize_phone(phone: str) -> str:
    """Normalizza in formato Green API chatId: 393331234567@c.us."""
    phone = re.sub(r"[\s\-\.\(\)+]", "", phone or "")
    if phone.startswith("0039"):
        phone = phone[2:]
    elif not phone.startswith("39"):
        phone = "39" + phone
    return f"{phone}@c.us"


def check_authorized() -> tuple[bool, str]:
    """Controlla se l'istanza Green API è autorizzata (QR scansionato).
    Ritorna (True, "") oppure (False, messaggio_errore)."""
    if not is_configured():
        return False, "Green API non configurata"
    try:
        r = requests.get(_url("getStateInstance"), timeout=10)
        r.raise_for_status()
        state = r.json().get("stateInstance", "")
        if state == "authorized":
            return True, ""
        return False, f"Istanza non autorizzata (stato: {state}) — scansiona il QR da whatsapp:impostazioni"
    except Exception as exc:
        return False, f"Impossibile verificare lo stato Green API: {exc}"


def get_status():
    """Ritorna lo stato della sessione e il QR code (data URI) se non autenticato."""
    if not is_configured():
        return {"connected": False, "error": "Green API non configurata (GREENAPI_INSTANCE_ID / GREENAPI_TOKEN mancanti)", "qr": None}

    ok, err = check_authorized()
    if ok:
        return {"connected": True, "error": None, "qr": None}

    qr = None
    try:
        rq = requests.get(_url("qr"), timeout=10)
        rq.raise_for_status()
        data = rq.json()
        if data.get("type") == "qrCode" and data.get("message"):
            qr = f"data:image/png;base64,{data['message']}"
    except Exception as exc:
        logger.warning(f"Errore recupero QR Green API: {exc}")

    return {"connected": False, "error": err, "qr": qr}


def send_message(numero, testo):
    """Invia un messaggio singolo. Ritorna dict {success, error}."""
    if not is_configured():
        return {"success": False, "error": "Green API non configurata"}
    try:
        r = requests.post(
            _url("sendMessage"),
            json={"chatId": normalize_phone(numero), "message": testo},
            timeout=30,
        )
        r.raise_for_status()
        return {"success": True}
    except Exception as e:
        logger.error(f"Errore invio WA a {numero}: {e}")
        return {"success": False, "error": str(e)}


def send_file(numero, file_path, caption=""):
    """Invia un file (es. PDF) con didascalia opzionale. Ritorna dict {success, error}."""
    if not is_configured():
        return {"success": False, "error": "Green API non configurata"}
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File non trovato: {file_path}"}
    try:
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            r = requests.post(
                _url("sendFileByUpload"),
                data={"chatId": normalize_phone(numero), "caption": caption},
                files={"file": (filename, f)},
                timeout=60,
            )
        r.raise_for_status()
        return {"success": True}
    except Exception as e:
        logger.error(f"Errore invio file WA a {numero}: {e}")
        return {"success": False, "error": str(e)}


def send_file_by_url(numero, url, filename="documento.pdf", caption=""):
    """Invia un file tramite URL pubblica — più efficiente dell'upload per un PDF già servito da Django."""
    if not is_configured():
        return {"success": False, "error": "Green API non configurata"}
    try:
        r = requests.post(
            _url("sendFileByUrl"),
            json={
                "chatId": normalize_phone(numero),
                "urlFile": url,
                "fileName": filename,
                "caption": caption,
            },
            timeout=30,
        )
        r.raise_for_status()
        return {"success": True}
    except Exception as e:
        logger.error(f"Errore invio file-url WA a {numero}: {e}")
        return {"success": False, "error": str(e)}


def set_profile_picture(image_path):
    """Imposta la foto profilo dell'istanza (JPEG). Ritorna dict {success, error}."""
    if not is_configured():
        return {"success": False, "error": "Green API non configurata"}
    try:
        with open(image_path, "rb") as f:
            r = requests.post(_url("setProfilePicture"), files={"file": f}, timeout=30)
        r.raise_for_status()
        data = r.json()
        return {"success": bool(data.get("setProfilePicture")), "error": data.get("reason")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_status_text(testo):
    """Green API non espone un endpoint pubblico per il testo 'Informazioni' del profilo
    (verificato sulla documentazione ufficiale il 26/08/2026) — a differenza del vecchio
    microservizio whatsapp-web.js custom. No-op intenzionale, non un bug."""
    return {"success": False, "error": "Non supportato da Green API"}


def disconnect():
    """Disconnette (logout) l'istanza. Ritorna dict {success, error}."""
    if not is_configured():
        return {"success": False, "error": "Green API non configurata"}
    try:
        r = requests.get(_url("logout"), timeout=15)
        r.raise_for_status()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
