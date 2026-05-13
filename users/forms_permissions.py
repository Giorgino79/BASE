"""
Form per gestione permissions utenti sui modelli.
Dinamicamente generato dal ModelPermissionRegistry.
"""

from django import forms
from django.contrib.auth.models import Permission
from core.permissions_registry import get_registry


class UserPermissionsForm(forms.Form):
    """
    Form dinamico per assegnare permissions CRUD agli utenti.

    Genera automaticamente i campi basandosi sui modelli registrati
    nel ModelPermissionRegistry.
    """

    def __init__(self, *args, **kwargs):
        self.user_obj = kwargs.pop("user_obj", None)
        super().__init__(*args, **kwargs)

        if not self.user_obj:
            return

        registry = get_registry()
        models_by_category = registry.get_models_by_category()

        # Genera campi dinamicamente per ogni modello
        for category, models in sorted(models_by_category.items()):
            for model_info in sorted(models, key=lambda x: x["display_name"]):
                self._add_model_fields(model_info)

        # Popola valori iniziali con permessi attuali utente
        self._set_initial_values()

    def _add_model_fields(self, model_info):
        """
        Aggiunge i campi CRUD per un singolo modello.

        Crea 4 BooleanField:
        - {app}_{model}_add
        - {app}_{model}_view
        - {app}_{model}_change
        - {app}_{model}_delete
        """
        app_label = model_info["app_label"]
        model_name = model_info["model_name"]
        display_name = model_info["display_name"]

        for perm in model_info["permissions"]:
            field_name = f"{app_label}_{model_name}_{perm['action']}"

            self.fields[field_name] = forms.BooleanField(
                required=False,
                label=f"{perm['label']} {display_name}",
                widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
            )

            # Salva metadati per il template
            self.fields[field_name].model_info = model_info
            self.fields[field_name].permission_info = perm

    def _set_initial_values(self):
        """Imposta valori iniziali basati sui permessi correnti dell'utente"""
        if not self.user_obj:
            return

        user_permissions = self.user_obj.user_permissions.values_list(
            "content_type__app_label", "codename"
        )

        # Crea set per lookup veloce
        user_perms_set = {f"{app}.{codename}" for app, codename in user_permissions}

        # Imposta initial per ogni field
        for field_name, field in self.fields.items():
            if hasattr(field, "permission_info"):
                perm_full_name = field.permission_info["full_name"]
                self.initial[field_name] = perm_full_name in user_perms_set

    def save(self):
        """
        Salva le permissions selezionate sull'utente.

        Rimuove tutti i permessi esistenti sui modelli registrati
        e ri-assegna solo quelli selezionati nel form.
        """
        if not self.user_obj:
            raise ValueError("user_obj not set")

        registry = get_registry()
        registered_models = registry.get_registered_models()

        # 1. Ottieni tutti i codenames dei modelli registrati
        registered_codenames = []
        for model_info in registered_models.values():
            for perm in model_info["permissions"]:
                registered_codenames.append(perm["codename"])

        # 2. Rimuovi permessi esistenti sui modelli registrati
        self.user_obj.user_permissions.filter(
            codename__in=registered_codenames
        ).delete()

        # 3. Aggiungi permessi selezionati
        permissions_to_add = []

        for field_name, is_checked in self.cleaned_data.items():
            if not is_checked:
                continue

            # Ottieni info dal field
            field = self.fields[field_name]
            if not hasattr(field, "permission_info"):
                continue

            perm_info = field.permission_info
            model_info = field.model_info

            # Trova il Permission object
            try:
                permission = Permission.objects.get(
                    content_type__app_label=model_info["app_label"],
                    codename=perm_info["codename"],
                )
                permissions_to_add.append(permission)
            except Permission.DoesNotExist:
                # Log warning ma continua
                print(
                    f"WARNING: Permission {perm_info['full_name']} non trovato nel database"
                )

        # 4. Assegna in batch
        if permissions_to_add:
            self.user_obj.user_permissions.add(*permissions_to_add)

        return self.user_obj

    def get_fields_by_category(self):
        """
        Raggruppa i campi per categoria per il template.

        Returns:
            dict: {
                'category_name': {
                    'models': {
                        'model_display_name': {
                            'info': model_info,
                            'fields': [field_name, ...]
                        }
                    }
                }
            }
        """
        categorized = {}

        for field_name, field in self.fields.items():
            if not hasattr(field, "model_info"):
                continue

            model_info = field.model_info
            category = model_info["category"]
            display_name = model_info["display_name"]

            # Inizializza struttura
            if category not in categorized:
                categorized[category] = {"models": {}}

            if display_name not in categorized[category]["models"]:
                categorized[category]["models"][display_name] = {
                    "info": model_info,
                    "fields": [],
                }

            # Aggiungi field (usa self[field_name] per ottenere il BoundField)
            categorized[category]["models"][display_name]["fields"].append(
                {
                    "name": field_name,
                    "field": self[field_name],  # BoundField invece di Field
                    "permission_info": field.permission_info,
                }
            )

        return categorized
