from django.apps import apps
from django.conf import settings
from django.urls import reverse, NoReverseMatch


def passaggio_cassa_modal(request):
    """
    Il modale di passaggio di cassa vive nel FAB "Strumenti", quindi deve
    poter comparire su qualunque pagina — non solo su quelle di contabilità,
    perché chi lo usa (un tecnico, un cassiere) spesso non ha accesso al
    modulo contabilità in sidebar. `contabilita` resta comunque un modulo
    opzionale (vedi CLAUDE.md): sulle installazioni dove non è installato
    questo processor non deve rompere ogni pagina del sito.
    """
    if not request.user.is_authenticated or not apps.is_installed('contabilita'):
        return {}

    from contabilita.forms import PassaggioCassaForm
    from contabilita.signals import conto_custodia_di

    conto = conto_custodia_di(request.user)
    return {
        'form_passaggio': PassaggioCassaForm(user=request.user),
        'passaggio_cassa_saldo': conto.saldo if conto else None,
    }


def google_maps(request):
    return {
        "google_maps_js_key": settings.GOOGLE_MAPS_JS_API_KEY,
        "map_default_lat": settings.MAP_DEFAULT_LAT,
        "map_default_lng": settings.MAP_DEFAULT_LNG,
    }


def sidebar_nav(request):
    if not request.user.is_authenticated:
        return {"sidebar_nav": []}

    from .sidebar import get_sections

    try:
        rm = request.resolver_match
        current_app = getattr(rm, "app_name", "") or ""
        current_url = getattr(rm, "url_name", "") or ""
    except Exception:
        current_app = current_url = ""

    sections = []
    for section in get_sections():
        visible_items = []
        for item in section["items"]:
            if item.get("staff_only") and not request.user.is_staff:
                continue
            perm = item.get("permission")
            if perm and not request.user.has_perm(perm):
                continue

            try:
                resolved = reverse(item["url"])
            except NoReverseMatch:
                continue

            # Active detection
            active_app = item.get("active_app")
            active_contains = item.get("active_url_contains")
            if isinstance(active_contains, str):
                active_contains = [active_contains]
            active_exact = item.get("active_url")

            if active_app and active_contains:
                is_active = current_app == active_app and any(
                    c in current_url for c in active_contains
                )
            elif active_app:
                is_active = current_app == active_app
            elif active_contains:
                is_active = any(c in current_url for c in active_contains)
            elif active_exact:
                is_active = current_url == active_exact
            else:
                is_active = request.path == resolved

            visible_items.append({**item, "resolved_url": resolved, "is_active": is_active})

        if visible_items:
            sections.append({**section, "items": visible_items})

    return {"sidebar_nav": sections}
