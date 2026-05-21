"""
Sidebar navigation registry.

Usage in AppConfig.ready():

    from core.sidebar import register_nav

    register_nav(
        section_key   = 'persone',
        section_label = 'Persone',
        items = [
            {
                'label': 'Dipendenti',
                'url':   'users:user_list',   # URL name to reverse()
                'icon':  'bi-people',
                # active detection (all optional):
                'active_app':          'users',  # request.resolver_match.app_name
                'active_url_contains': 'user',   # substring in url_name (str or list)
                # permission gates (optional):
                'staff_only':  False,
                'permission':  None,  # e.g. 'users.view_user'
            },
        ],
        order = 20,   # lower = higher in sidebar
    )

Multiple calls with the same section_key merge their items.
"""

_registry: dict = {}


def register_nav(section_key: str, section_label: str, items: list, order: int = 100):
    if section_key not in _registry:
        _registry[section_key] = {"label": section_label, "items": [], "order": order}
    _registry[section_key]["items"].extend(items)


def get_sections() -> list:
    return sorted(_registry.values(), key=lambda s: s["order"])
