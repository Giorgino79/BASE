"""
Forms per gestione Template Permessi.
"""

from django import forms
from django.contrib.auth.models import Permission
from .models_permissions import PermissionTemplate
from .permissions_registry import get_registry


class PermissionTemplateForm(forms.ModelForm):
    """
    Form per creare/modificare template di permessi.

    Include sia permessi CRUD sui modelli che permessi base operativi.
    """

    # Permessi base operativi (checkbox)
    PERMESSI_BASE_CHOICES = [
        # Timbrature
        ('users.add_timbratura', 'Timbrare (ingresso/uscita)'),
        ('users.view_timbratura', 'Visualizzare timbrature'),
        ('users.change_timbratura', 'Modificare timbrature'),
        ('users.delete_timbratura', 'Eliminare timbrature'),

        # Giornate lavorative
        ('users.view_giornatalavorativa', 'Visualizzare giornate lavorative'),

        # Ferie
        ('users.add_richiestaferie', 'Richiedere ferie'),
        ('users.view_richiestaferie', 'Visualizzare richieste ferie'),
        ('users.change_richiestaferie', 'Modificare richieste ferie'),
        ('users.approva_ferie', '✨ Approvare/Rifiutare ferie'),

        # Permessi
        ('users.add_richiestapermesso', 'Richiedere permessi'),
        ('users.view_richiestapermesso', 'Visualizzare richieste permessi'),
        ('users.change_richiestapermesso', 'Modificare richieste permessi'),
        ('users.approva_permessi', '✨ Approvare/Rifiutare permessi'),

        # Lettere richiamo
        ('users.view_letterarichiamo', 'Visualizzare lettere richiamo'),
        ('users.emetti_lettera_richiamo', '✨ Emettere lettere richiamo'),

        # Users
        ('users.view_user', 'Visualizzare utenti'),
        ('users.change_user', '✨ Modificare utenti'),
        ('users.add_user', '✨ Creare utenti'),
        ('users.gestione_completa_users', '✨ Gestione completa utenti'),

        # Dashboard
        ('users.visualizza_dashboard_admin', '✨ Dashboard amministratore'),
        ('users.visualizza_report_presenze', '✨ Report presenze'),

        # Corrispondenza
        ('corrispondenza.add_corrispondenza', 'Creare corrispondenza'),
        ('corrispondenza.view_corrispondenza', 'Visualizzare propria corrispondenza'),
        ('corrispondenza.change_corrispondenza', 'Modificare corrispondenza in bozza'),
        ('corrispondenza.delete_corrispondenza', 'Eliminare corrispondenza in bozza'),
        ('corrispondenza.can_view_all', '✨ Visualizzare tutta la corrispondenza'),
        ('corrispondenza.can_send', '✨ Inviare corrispondenza'),

        # Promemoria
        ('comunicazioni.add_promemoria', 'Creare promemoria'),
        ('comunicazioni.view_promemoria', 'Visualizzare promemoria'),
        ('comunicazioni.change_promemoria', 'Modificare promemoria'),
        ('comunicazioni.delete_promemoria', 'Eliminare promemoria'),

        # Chat
        ('comunicazioni.add_chatconversazione', 'Avviare conversazioni chat'),
        ('comunicazioni.view_chatconversazione', 'Visualizzare chat'),
    ]

    permessi_base_selezionati = forms.MultipleChoiceField(
        label="Permessi Base Operativi",
        choices=PERMESSI_BASE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text="Permessi operativi (timbrature, ferie, approvazioni, etc.)"
    )

    class Meta:
        model = PermissionTemplate
        fields = ['nome', 'descrizione', 'permessi_crud', 'attivo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Es. Responsabile HR'}),
            'descrizione': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrizione dei permessi inclusi...'}),
            'permessi_crud': forms.CheckboxSelectMultiple(),
            'attivo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtra solo permessi CRUD sui modelli registrati
        registry = get_registry()
        registered_models = registry.get_registered_models()

        # Ottieni codenames dei permessi registrati
        registered_codenames = []
        for model_info in registered_models.values():
            for perm in model_info['permissions']:
                registered_codenames.append(perm['codename'])

        # Limita queryset ai permessi registrati
        self.fields['permessi_crud'].queryset = Permission.objects.filter(
            codename__in=registered_codenames
        ).select_related('content_type').order_by('content_type__app_label', 'codename')

        # Pre-popola permessi base se modifica
        if self.instance.pk and self.instance.permessi_base:
            self.fields['permessi_base_selezionati'].initial = self.instance.permessi_base

    def save(self, commit=True):
        """Salva template con permessi base"""
        instance = super().save(commit=False)

        # Salva permessi base come lista JSON
        instance.permessi_base = self.cleaned_data.get('permessi_base_selezionati', [])

        if commit:
            instance.save()
            # Salva M2M (permessi_crud)
            self.save_m2m()

        return instance

    def get_permessi_by_category(self):
        """
        Raggruppa permessi CRUD per categoria per il template.

        Returns:
            dict: Struttura per rendering template
        """
        registry = get_registry()
        models_by_category = registry.get_models_by_category()

        categorized = {}

        for category, models in sorted(models_by_category.items()):
            categorized[category] = {'models': {}}

            for model_info in sorted(models, key=lambda x: x['display_name']):
                display_name = model_info['display_name']
                categorized[category]['models'][display_name] = {
                    'info': model_info,
                    'permissions': []
                }

                # Aggiungi permessi CRUD per questo modello
                for perm in model_info['permissions']:
                    # Crea field name compatibile con il form
                    field_name = f"{model_info['app_label']}_{model_info['model_name']}_{perm['action']}"

                    # Cerca il Permission object
                    try:
                        permission = Permission.objects.get(
                            content_type__app_label=model_info['app_label'],
                            codename=perm['codename']
                        )

                        # Arricchisci le info del permesso con badge_class e display_name
                        perm_info = perm.copy()

                        # Aggiungi badge_class in base all'action
                        badge_classes = {
                            'view': 'info',
                            'add': 'success',
                            'change': 'warning',
                            'delete': 'danger',
                        }
                        perm_info['badge_class'] = badge_classes.get(perm['action'], 'secondary')

                        # Aggiungi display_name leggibile
                        display_names = {
                            'view': 'Visualizza',
                            'add': 'Crea',
                            'change': 'Modifica',
                            'delete': 'Elimina',
                        }
                        perm_info['display_name'] = display_names.get(perm['action'], perm['label'])

                        categorized[category]['models'][display_name]['permissions'].append({
                            'permission': permission,
                            'info': perm_info,
                            'field_name': field_name
                        })
                    except Permission.DoesNotExist:
                        pass

        return categorized


class ApplicaTemplateForm(forms.Form):
    """
    Form per applicare un template a un utente.

    Usato nella gestione permessi utente.
    """

    template = forms.ModelChoiceField(
        label="Seleziona Template",
        queryset=PermissionTemplate.objects.filter(attivo=True).order_by('nome'),
        required=False,
        empty_label="-- Nessun template --",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Seleziona un template predefinito per applicare rapidamente i permessi"
    )

    sovrascrivi = forms.BooleanField(
        label="Rimuovi permessi esistenti prima di applicare",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Se selezionato, rimuove tutti i permessi attuali prima di applicare il template"
    )
