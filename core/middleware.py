"""
Middleware per il gating runtime dei moduli venduti/attivi per installazione.

Attiva solo se settings.MODULE_GATING_ENABLED è True (env var MODULE_GATING_ENABLED,
default 'False'): finché non viene abilitata esplicitamente per un'istanza cliente,
questa middleware è presente in MIDDLEWARE ma non fa nulla — nessun cambio di
comportamento per l'installazione esistente.
"""

from django.conf import settings
from django.http import Http404
from django.urls import Resolver404, resolve

from core.module_gating import is_module_active
from core.module_manager import CORE_MODULES

# Prefissi sempre esenti dal gating: admin, viste senza namespace, ecc.
_ALWAYS_ALLOWED_APP_NAMES = set(CORE_MODULES) | {
    None,  # viste senza namespace (es. root/login, healthcheck)
    "admin",
}

# anagrafica_r2/urls.py dichiara `app_name = 'anagrafica'` (namespace URL
# storico, usato in centinaia di {% url 'anagrafica:...' %} nei template —
# non rinominabile senza un refactor enorme), diverso dal vero app label
# Django `anagrafica_r2` (usato in INSTALLED_APPS/module_manager.py). Senza
# questo alias, il gating vedrebbe le URL di anagrafica_r2 con app_name
# 'anagrafica', non lo troverebbe tra i CORE_MODULES ('anagrafica_r2') e le
# bloccherebbe appena il gating venisse attivato — anche se e' un modulo core.
_URL_NAMESPACE_ALIASES = {
    "anagrafica": "anagrafica_r2",
}


class ModuleGatingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "MODULE_GATING_ENABLED", False):
            return self.get_response(request)

        try:
            match = resolve(request.path_info)
        except Resolver404:
            return self.get_response(request)

        app_name = match.app_name or (
            match.func.__module__.split(".")[0] if match.func else None
        )
        app_name = _URL_NAMESPACE_ALIASES.get(app_name, app_name)

        if app_name in _ALWAYS_ALLOWED_APP_NAMES:
            return self.get_response(request)

        if not is_module_active(app_name):
            raise Http404("Modulo non attivo per questa installazione")

        return self.get_response(request)
