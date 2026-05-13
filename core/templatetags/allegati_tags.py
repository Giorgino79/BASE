"""
Template tags per la gestione degli allegati.
Fornisce funzionalità automatiche per integrare il sistema allegati
in qualsiasi template detail.
"""

from django import template
from django.contrib.contenttypes.models import ContentType

register = template.Library()


@register.simple_tag
def get_content_type_id(obj):
    """
    Restituisce il ContentType ID di un oggetto.

    Uso: {% get_content_type_id object as content_type_id %}
    """
    if obj:
        return ContentType.objects.get_for_model(obj.__class__).pk
    return None


@register.filter
def has_allegati_mixin(obj):
    """
    Verifica se un oggetto ha AllegatiMixin.

    Uso: {% if object|has_allegati_mixin %}
    """
    return hasattr(obj, "allegati") and hasattr(obj, "conta_allegati")


@register.inclusion_tag("commons_templates/components/allegati_count_badge.html")
def allegati_badge(obj):
    """
    Mostra badge con conteggio allegati.

    Uso: {% allegati_badge object %}
    """
    count = obj.conta_allegati() if hasattr(obj, "conta_allegati") else 0
    return {"count": count, "has_allegati": count > 0}


@register.filter
def file_icon_class(allegato):
    """
    Restituisce la classe Bootstrap Icon appropriata per il tipo di file.

    Uso: {{ allegato|file_icon_class }}
    """
    if hasattr(allegato, "is_pdf") and allegato.is_pdf():
        return "bi-file-earmark-pdf-fill text-danger"
    elif hasattr(allegato, "is_image") and allegato.is_image():
        return "bi-file-earmark-image-fill text-primary"
    elif allegato.nome_originale.endswith((".doc", ".docx")):
        return "bi-file-earmark-word-fill text-info"
    elif allegato.nome_originale.endswith((".xls", ".xlsx")):
        return "bi-file-earmark-excel-fill text-success"
    elif allegato.nome_originale.endswith(".zip"):
        return "bi-file-earmark-zip-fill text-warning"
    else:
        return "bi-file-earmark-fill text-secondary"


@register.filter
def can_delete_allegato(allegato, user):
    """
    Verifica se l'utente può eliminare l'allegato.

    Logica permessi:
    - Admin: può eliminare tutto
    - Creatore: può eliminare solo i propri
    - Altri: non possono eliminare

    Uso: {% if allegato|can_delete_allegato:request.user %}
    """
    if not user or not user.is_authenticated:
        return False

    # Admin può tutto
    if user.is_staff or user.is_superuser:
        return True

    # Il creatore può eliminare i propri allegati
    if hasattr(allegato, "uploaded_by") and allegato.uploaded_by == user:
        return True

    return False


@register.filter
def can_modify_allegato(allegato, user):
    """
    Verifica se l'utente può modificare l'allegato.
    Stesse regole di can_delete_allegato.

    Uso: {% if allegato|can_modify_allegato:request.user %}
    """
    return can_delete_allegato(allegato, user)
