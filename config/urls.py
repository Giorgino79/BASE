from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users import views as users_views

urlpatterns = [
    path("select2/", include("django_select2.urls")),
    path("admin/", admin.site.urls),
    path("dashboard/", users_views.dashboard_view, name="dashboard"),
    path("", include("users.urls")),
    path("core/", include("core.urls")),
    path("comunicazioni/", include("comunicazioni.urls")),
    path("corrispondenza/", include("corrispondenza.urls")),
    path("payroll/", include("payroll.urls")),
    path("anagrafica/", include("anagrafica_r2.urls")),
    path("cespiti/", include("cespiti.urls")),
    path("acquisti/", include("acquisti.urls")),
    path("magazzino/", include("magazzino.urls")),
    path("servizi/", include("servizi.urls")),
    path("installazioni/", include("installazioni.urls")),
    path("analysis/", include("analysis.urls")),
    path("cliente/", include("portale.urls")),
    path("fatturazione/attiva/", include("fatturazione_attiva.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
