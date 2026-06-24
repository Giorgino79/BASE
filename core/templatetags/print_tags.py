"""
Template tags per il sistema di stampa.
"""

from django import template

register = template.Library()


@register.filter(name='get_field_value')
def get_field_value(obj, field_name):
    """
    Recupera il valore di un campo su un oggetto Django.

    Prova in ordine:
    1. get_FIELD_display() — per campi con choices
    2. attributo diretto
    3. metodo senza argomenti

    Uso: {{ obj|get_field_value:field_name }}
    """
    display_method = f'get_{field_name}_display'
    if hasattr(obj, display_method):
        val = getattr(obj, display_method)()
    else:
        val = getattr(obj, field_name, None)

    if callable(val):
        try:
            val = val()
        except TypeError:
            val = None

    if val is None or val == '':
        return '—'
    if isinstance(val, bool):
        return 'Sì' if val else 'No'
    return val
