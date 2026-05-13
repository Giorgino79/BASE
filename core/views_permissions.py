"""
Views per gestione Template Permessi.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import transaction

from .models_permissions import PermissionTemplate
from .forms_permissions import PermissionTemplateForm


# ============================================================================
# TEMPLATE PERMESSI - LIST
# ============================================================================

@login_required
@permission_required('users.gestione_completa_users', raise_exception=True)
@require_http_methods(["GET"])
def permission_template_list_view(request):
    """
    Lista tutti i template di permessi.

    Permessi richiesti: users.gestione_completa_users

    Features:
    - Visualizza tutti i template con statistiche utilizzo
    - Filtro attivi/inattivi
    - Link a CRUD operations
    """
    templates = PermissionTemplate.objects.all().prefetch_related('permessi_crud')

    # Filtra per stato attivo se richiesto
    filtro_attivo = request.GET.get('attivo')
    if filtro_attivo == '1':
        templates = templates.filter(attivo=True)
    elif filtro_attivo == '0':
        templates = templates.filter(attivo=False)

    context = {
        'templates': templates,
        'filtro_attivo': filtro_attivo,
        'title': 'Template Permessi'
    }

    return render(request, 'core/permission_template_list.html', context)


# ============================================================================
# TEMPLATE PERMESSI - CREATE
# ============================================================================

@login_required
@permission_required('users.gestione_completa_users', raise_exception=True)
@require_http_methods(["GET", "POST"])
def permission_template_create_view(request):
    """
    Crea nuovo template di permessi.

    Permessi richiesti: users.gestione_completa_users

    Features:
    - Form con permessi CRUD raggruppati per categoria
    - Permessi base operativi (timbrature, ferie, etc.)
    - Preview permessi selezionati
    """
    if request.method == 'POST':
        form = PermissionTemplateForm(request.POST)

        if form.is_valid():
            try:
                template = form.save()
                messages.success(
                    request,
                    f"Template '{template.nome}' creato con successo! "
                    f"({template.get_permessi_count()} permessi)"
                )
                return redirect('core:permission_template_detail', pk=template.pk)
            except Exception as e:
                messages.error(request, f"Errore nella creazione template: {str(e)}")
        else:
            messages.error(request, "Errore nella validazione form. Verifica i campi.")
    else:
        form = PermissionTemplateForm()

    # Raggruppa permessi CRUD per categoria
    permessi_by_category = form.get_permessi_by_category()

    context = {
        'form': form,
        'permessi_by_category': permessi_by_category,
        'title': 'Nuovo Template Permessi'
    }

    return render(request, 'core/permission_template_form.html', context)


# ============================================================================
# TEMPLATE PERMESSI - DETAIL
# ============================================================================

@login_required
@permission_required('users.gestione_completa_users', raise_exception=True)
@require_http_methods(["GET"])
def permission_template_detail_view(request, pk):
    """
    Visualizza dettagli template permessi.

    Permessi richiesti: users.gestione_completa_users

    Features:
    - Visualizza tutti i permessi inclusi nel template
    - Statistiche utilizzo
    - Link a modifica/eliminazione
    """
    template = get_object_or_404(
        PermissionTemplate.objects.prefetch_related('permessi_crud'),
        pk=pk
    )

    # Raggruppa permessi CRUD per categoria
    from .permissions_registry import get_registry
    registry = get_registry()
    models_by_category = registry.get_models_by_category()

    permessi_crud_grouped = {}
    for category, models in sorted(models_by_category.items()):
        permessi_crud_grouped[category] = {'models': {}}

        for model_info in sorted(models, key=lambda x: x['display_name']):
            display_name = model_info['display_name']

            # Filtra permessi di questo modello presenti nel template
            model_permissions = template.permessi_crud.filter(
                content_type__app_label=model_info['app_label'],
                content_type__model=model_info['model_name']
            )

            if model_permissions.exists():
                permessi_crud_grouped[category]['models'][display_name] = {
                    'info': model_info,
                    'permissions': model_permissions
                }

    # Permessi base in formato leggibile
    permessi_base_display = template.get_permessi_base_display()

    context = {
        'template': template,
        'permessi_crud_grouped': permessi_crud_grouped,
        'permessi_base_display': permessi_base_display,
        'title': f'Template: {template.nome}'
    }

    return render(request, 'core/permission_template_detail.html', context)


# ============================================================================
# TEMPLATE PERMESSI - UPDATE
# ============================================================================

@login_required
@permission_required('users.gestione_completa_users', raise_exception=True)
@require_http_methods(["GET", "POST"])
def permission_template_update_view(request, pk):
    """
    Modifica template permessi esistente.

    Permessi richiesti: users.gestione_completa_users
    """
    template = get_object_or_404(PermissionTemplate, pk=pk)

    if request.method == 'POST':
        form = PermissionTemplateForm(request.POST, instance=template)

        if form.is_valid():
            try:
                template = form.save()
                messages.success(
                    request,
                    f"Template '{template.nome}' aggiornato con successo! "
                    f"({template.get_permessi_count()} permessi)"
                )
                return redirect('core:permission_template_detail', pk=template.pk)
            except Exception as e:
                messages.error(request, f"Errore nell'aggiornamento template: {str(e)}")
        else:
            messages.error(request, "Errore nella validazione form. Verifica i campi.")
    else:
        form = PermissionTemplateForm(instance=template)

    # Raggruppa permessi CRUD per categoria
    permessi_by_category = form.get_permessi_by_category()

    context = {
        'form': form,
        'template': template,
        'permessi_by_category': permessi_by_category,
        'title': f'Modifica Template: {template.nome}'
    }

    return render(request, 'core/permission_template_form.html', context)


# ============================================================================
# TEMPLATE PERMESSI - DELETE
# ============================================================================

@login_required
@permission_required('users.gestione_completa_users', raise_exception=True)
@require_http_methods(["POST"])
def permission_template_delete_view(request, pk):
    """
    Elimina template permessi.

    Permessi richiesti: users.gestione_completa_users

    Note:
    - Richiede conferma via POST
    - Non influenza gli utenti che hanno già ricevuto i permessi da questo template
    """
    template = get_object_or_404(PermissionTemplate, pk=pk)
    nome_template = template.nome

    try:
        with transaction.atomic():
            template.delete()

        messages.success(
            request,
            f"Template '{nome_template}' eliminato con successo. "
            f"Gli utenti che avevano ricevuto questi permessi mantengono i loro permessi attuali."
        )
    except Exception as e:
        messages.error(request, f"Errore nell'eliminazione template: {str(e)}")

    return redirect('core:permission_template_list')
