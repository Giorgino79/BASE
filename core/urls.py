"""
URL Configuration per l'app Core

Include le API AJAX per la gestione allegati e gestione Template Permessi.
"""

from django.urls import path
from .views_allegati import (
    allegato_upload,
    allegati_list,
    allegato_delete,
    allegato_download,
    allegato_preview,
    global_search,
)
from .views import serve_qr_code, test_email_view
from .views_qrcode import (
    qrcode_generate,
    qrcode_download,
    qrcode_delete,
    qrcode_check,
    qrcode_stampa,
)
from .views_permissions import (
    permission_template_list_view,
    permission_template_create_view,
    permission_template_detail_view,
    permission_template_update_view,
    permission_template_delete_view,
)
from .admin_views import modules_dashboard, amministrazione_dashboard, hr_dashboard_view
from .views_invia import invia_documento
from .views_tools import calcolatrice_view
from .views_calendario import (
    CalendarioView,
    CalendarioPersonaleView,
    CalendarioEventiAPIView,
    CalendarioPersonaleEventiAPIView,
    evento_calendario_create,
    evento_calendario_edit,
    evento_calendario_delete,
)

app_name = "core"

urlpatterns = [
    # ========== API ALLEGATI (AJAX) ==========
    path("allegati/upload/", allegato_upload, name="allegato_upload"),
    path("allegati/list/", allegati_list, name="allegati_list"),
    path("allegati/<int:allegato_id>/delete/", allegato_delete, name="allegato_delete"),
    path(
        "allegati/<int:allegato_id>/download/",
        allegato_download,
        name="allegato_download",
    ),
    path(
        "allegati/<int:allegato_id>/preview/", allegato_preview, name="allegato_preview"
    ),
    # ========== RICERCA GLOBALE (AJAX) ==========
    path("search/", global_search, name="global_search"),
    # ========== API QR CODE (AJAX) ==========
    path("qrcode/generate/", qrcode_generate, name="qrcode_generate"),
    path("qrcode/check/", qrcode_check, name="qrcode_check"),
    path("qrcode/<int:qrcode_id>/download/", qrcode_download, name="qrcode_download"),
    path("qrcode/<int:qrcode_id>/delete/", qrcode_delete, name="qrcode_delete"),
    path("qrcode/<int:content_type_id>/<int:object_id>/stampa/", qrcode_stampa, name="qrcode_stampa"),
    # ========== UTILITY QR CODE (Legacy) ==========
    path("qrcode/", serve_qr_code, name="serve_qr_code"),
    # ========== TEMPLATE PERMESSI ==========
    path("permission-templates/", permission_template_list_view, name="template_permessi_list"),
    path("permission-templates/create/", permission_template_create_view, name="template_permessi_create"),
    path("permission-templates/<int:pk>/", permission_template_detail_view, name="template_permessi_detail"),
    path("permission-templates/<int:pk>/update/", permission_template_update_view, name="template_permessi_update"),
    path("permission-templates/<int:pk>/delete/", permission_template_delete_view, name="template_permessi_delete"),
    # ========== DASHBOARD MODULI ==========
    path("admin/modules/", modules_dashboard, name="modules_dashboard"),
    # ========== AMMINISTRAZIONE HUB ==========
    path("amministrazione/", amministrazione_dashboard, name="amministrazione_dashboard"),
    # ========== HR DASHBOARD ==========
    path("hr/", hr_dashboard_view, name="hr_dashboard"),
    # ========== TOOLS ==========
    path("calcolatrice/", calcolatrice_view, name="calcolatrice"),
    # ========== CALENDARIO AZIENDALE ==========
    path("calendario/", CalendarioView.as_view(), name="calendario_aziendale"),
    path("calendario/eventi/", CalendarioEventiAPIView.as_view(), name="calendario_eventi_api"),
    # ========== CALENDARIO PERSONALE ==========
    path("calendario-personale/", CalendarioPersonaleView.as_view(), name="calendario_personale"),
    path("calendario-personale/eventi/", CalendarioPersonaleEventiAPIView.as_view(), name="calendario_personale_eventi_api"),
    # ========== EVENTI MANUALI CRUD ==========
    path("calendario/evento/nuovo/", evento_calendario_create, name="evento_calendario_create"),
    path("calendario/evento/<int:pk>/modifica/", evento_calendario_edit, name="evento_calendario_update"),
    path("calendario/evento/<int:pk>/elimina/", evento_calendario_delete, name="evento_calendario_delete"),
    # ========== TEST EMAIL ==========
    path("test-mail/", test_email_view, name="test_email"),
    # ========== INVIA (WhatsApp / Email) ==========
    path("invia/", invia_documento, name="invia_documento"),
]
