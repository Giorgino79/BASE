"""
Geocoding — trasforma un indirizzo testuale in coordinate geografiche via Google Geocoding API.

Prerequisito: impostare GOOGLE_MAPS_GEOCODING_API_KEY nelle variabili d'ambiente
(chiave separata da quella "browser", ristretta solo a Geocoding API, mai esposta
nei template).

Usato come rete di sicurezza in save() dei modelli con indirizzo (Filiale, Privato,
CondominioODS) quando l'autocomplete lato client non ha valorizzato le coordinate.
"""

import logging
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GEOCODING_BASE = "https://maps.googleapis.com/maps/api/geocode/json"


def is_configured() -> bool:
    return bool(getattr(settings, "GOOGLE_MAPS_GEOCODING_API_KEY", ""))


def geocode(indirizzo: str) -> tuple[Decimal, Decimal] | None:
    """Ritorna (latitudine, longitudine) per l'indirizzo dato, o None se non trovato
    o in caso di qualunque errore. Non solleva mai eccezioni: un indirizzo mal scritto
    o l'API non disponibile non devono mai bloccare il salvataggio del record."""
    indirizzo = (indirizzo or "").strip()
    if not indirizzo or not is_configured():
        return None
    try:
        resp = requests.get(
            GEOCODING_BASE,
            params={
                "address": indirizzo,
                "region": "it",
                "key": settings.GOOGLE_MAPS_GEOCODING_API_KEY,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK" or not data.get("results"):
            return None
        location = data["results"][0]["geometry"]["location"]
        return Decimal(str(location["lat"])), Decimal(str(location["lng"]))
    except Exception:
        logger.warning("Geocoding fallito per indirizzo %r", indirizzo, exc_info=True)
        return None
