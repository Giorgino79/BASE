"""
Gating runtime dei moduli: quali app sono attive per QUESTA installazione.

Sorgente di verità: core.models_legacy.ModuloRegistry (tabella già esistente
e migrata, prima orfana — nessun codice la leggeva a runtime). Se la tabella
non ha righe (nessuna sync mai lanciata, es. un'installazione storica prima
di questa modifica), get_active_modules() ritorna None: significa
"nessun filtro, tutte le app sono considerate attive" — è il default di
sicurezza che garantisce zero cambi di comportamento finché qualcuno non
popola/cura deliberatamente il registry per un cliente specifico.

Pattern di cache identico a multi_company.models.MultiCompanySettings.is_enabled()
(nella versione em26 di questo progetto — vedi la sorella em26 di questo file).
"""

from django.core.cache import cache

CACHE_KEY = "module_gating_active_modules"
CACHE_TTL = 300  # 5 minuti

_UNSET = object()


def get_active_modules():
    """
    None => nessun filtro (tutte le app attive).
    set[str] => solo questi app_name sono attivi.
    """
    cached = cache.get(CACHE_KEY, _UNSET)
    if cached is not _UNSET:
        return cached

    from core.models_legacy import ModuloRegistry

    try:
        if not ModuloRegistry.objects.exists():
            result = None
        else:
            result = set(
                ModuloRegistry.objects.filter(attivo=True).values_list(
                    "app_name", flat=True
                )
            )
    except Exception:
        # Tabella non ancora migrata/DB non raggiungibile: fail-open, mai bloccare.
        result = None

    cache.set(CACHE_KEY, result, CACHE_TTL)
    return result


def is_module_active(app_name):
    """True se app_name è attivo, o se non è impostato alcun filtro."""
    active = get_active_modules()
    return active is None or app_name in active


def invalidate_cache(*args, **kwargs):
    """Da collegare a post_save/post_delete di ModuloRegistry."""
    cache.delete(CACHE_KEY)
