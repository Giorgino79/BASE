"""
Registro sorgenti contatti per il broadcast WhatsApp.

'anagrafica' varia per prodotto (Cliente/Fornitore in em26, Azienda/Filiale/
Privato/Fornitore in rattus26) — whatsapp è un'app CORE e non deve mai
importare direttamente un modello anagrafica specifico. Ogni app
anagrafica-like si registra una volta in apps.py::ready() con una funzione
che ritorna [(numero, nome), ...]. Stesso principio già usato da
core/sidebar.py, core/search.py, core/calendario_registry.py.
"""

_SOURCES = {}


def register_source(codice: str, label: str, funzione) -> None:
    """codice: es. 'clienti', 'fornitori', 'aziende'. funzione: callable() -> list[(numero, nome)]."""
    _SOURCES[codice] = {"label": label, "funzione": funzione}


def get_sources() -> dict:
    return dict(_SOURCES)


def contatti_per(codice: str) -> list:
    sorgente = _SOURCES.get(codice)
    if not sorgente:
        return []
    try:
        return list(sorgente["funzione"]())
    except Exception:
        import logging
        logging.getLogger(__name__).exception(f"Errore sorgente contatti whatsapp '{codice}'")
        return []
