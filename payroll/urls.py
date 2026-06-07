"""
URL patterns per il modulo Payroll
"""

from django.urls import path
from . import views

app_name = "payroll"

urlpatterns = [
    path("dipendenti/", views.dipendenti_payroll_list, name="dipendenti_payroll_list"),
    path("dati-payroll/<int:user_pk>/", views.dati_payroll_detail, name="dati_payroll_detail"),
    path("dati-payroll/<int:user_pk>/form/", views.dati_payroll_form, name="dati_payroll_form"),
    path("buste-paga/<int:user_pk>/", views.busta_paga_list, name="busta_paga_list"),
    path("busta-paga/<int:pk>/", views.busta_paga_detail, name="busta_paga_detail"),
    path("busta-paga/<int:user_pk>/elabora/", views.busta_paga_elabora, name="busta_paga_elabora"),
    path("ferie-permessi/<int:user_pk>/", views.ferie_permessi_list, name="ferie_permessi_list"),
    path("manuale/", views.manuale_payroll, name="manuale_payroll"),
    path("manuale/edit/", views.manuale_payroll_edit, name="manuale_payroll_edit"),
]
