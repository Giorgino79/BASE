"""
Forms per l'app users.
"""

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
    UserChangeForm,
)
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import User, Timbratura, RichiestaFerie, RichiestaPermesso, LetteraRichiamo, EventoPersonale
from datetime import datetime, date, time


class LoginForm(AuthenticationForm):
    """
    Form di login personalizzato.

    Supporta:
    - Username o email
    - Remember me (30 giorni)
    - Validazioni custom
    """

    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username",
                "autofocus": True,
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        ),
    )

    remember_me = forms.BooleanField(
        label="Ricordami (30 giorni)",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    error_messages = {
        "invalid_login": (
            "Username o password non corretti. "
            "Nota che entrambi i campi potrebbero essere case-sensitive."
        ),
        "inactive": "Questo account è stato disattivato.",
    }

    def clean_username(self):
        """Pulisce e valida username"""
        username = self.cleaned_data.get("username")
        if username:
            username = username.strip()
        return username


# ============================================================================
# FORMS GESTIONE USERS
# ============================================================================


class UserCreateForm(UserCreationForm):
    """
    Form creazione nuovo user.

    Features:
    - Genera automaticamente codice_dipendente
    - Gestione permessi granulari
    - Template permessi predefiniti
    """

    # Template permessi predefiniti
    TEMPLATE_PERMESSI = [
        ("dipendente_base", "Dipendente Base (solo timbrature e richieste)"),
        ("responsabile", "Responsabile (gestione ferie/permessi del reparto)"),
        ("amministratore", "Amministratore (gestione completa users)"),
        ("custom", "Personalizzato (seleziona manualmente)"),
    ]

    template_permessi = forms.ChoiceField(
        label="Template Permessi",
        choices=TEMPLATE_PERMESSI,
        initial="dipendente_base",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # Permessi custom (visibili solo se template='custom')
    permessi_custom = forms.ModelMultipleChoiceField(
        label="Permessi Personalizzati",
        queryset=Permission.objects.filter(
            content_type__app_label__in=["users", "core", "auth"]
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email.lower() if email else email

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password1",
            "password2",
            "first_name",
            "last_name",
            "qualifica",
            "reparto",
            "stato",
            "data_nascita",
            "luogo_nascita",
            "codice_fiscale",
            "carta_d_identita",
            "data_scadenza_ci",
            "patente_di_guida",
            "data_scadenza_patente",
            "categorie_patente",
            "posizione_inail",
            "posizione_inps",
            "telefono",
            "telefono_emergenza",
            "indirizzo",
            "citta",
            "cap",
            "provincia",
            "data_assunzione",
            "giorni_ferie_anno",
            "ore_permesso_residue",
            "foto_profilo",
            "foto_carta_identita",
            "foto_codice_fiscale",
            "foto_patente",
            "note",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "qualifica": forms.TextInput(attrs={"class": "form-control"}),
            "reparto": forms.TextInput(attrs={"class": "form-control"}),
            "stato": forms.Select(attrs={"class": "form-select"}),
            "data_nascita": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "luogo_nascita": forms.TextInput(attrs={"class": "form-control"}),
            "codice_fiscale": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "16"}
            ),
            "carta_d_identita": forms.TextInput(attrs={"class": "form-control"}),
            "data_scadenza_ci": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "patente_di_guida": forms.TextInput(attrs={"class": "form-control"}),
            "data_scadenza_patente": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "categorie_patente": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Es. B, C, D"}
            ),
            "posizione_inail": forms.TextInput(attrs={"class": "form-control"}),
            "posizione_inps": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "telefono_emergenza": forms.TextInput(attrs={"class": "form-control"}),
            "indirizzo": forms.TextInput(attrs={"class": "form-control"}),
            "citta": forms.TextInput(attrs={"class": "form-control"}),
            "cap": forms.TextInput(attrs={"class": "form-control", "maxlength": "5"}),
            "provincia": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "2"}
            ),
            "data_assunzione": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "giorni_ferie_anno": forms.NumberInput(attrs={"class": "form-control"}),
            "ore_permesso_residue": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.25"}
            ),
            "foto_profilo": forms.FileInput(attrs={"class": "form-control"}),
            "foto_carta_identita": forms.FileInput(attrs={"class": "form-control"}),
            "foto_codice_fiscale": forms.FileInput(attrs={"class": "form-control"}),
            "foto_patente": forms.FileInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def save(self, commit=True):
        """
        Salva user con permessi e codice auto-generato.
        """
        user = super().save(commit=False)

        # Genera codice_dipendente automatico
        if not user.codice_dipendente:
            ultimo_codice = User.objects.order_by("-codice_dipendente").first()
            if ultimo_codice and ultimo_codice.codice_dipendente:
                try:
                    nuovo_numero = int(ultimo_codice.codice_dipendente) + 1
                    user.codice_dipendente = f"{nuovo_numero:03d}"
                except ValueError:
                    user.codice_dipendente = "001"
            else:
                user.codice_dipendente = "001"

        if commit:
            user.save()

            # Applica template permessi
            template = self.cleaned_data.get("template_permessi")
            if template == "dipendente_base":
                self._applica_permessi_dipendente(user)
            elif template == "responsabile":
                self._applica_permessi_responsabile(user)
            elif template == "amministratore":
                self._applica_permessi_amministratore(user)
            elif template == "custom":
                permessi = self.cleaned_data.get("permessi_custom", [])
                user.user_permissions.set(permessi)

        return user

    def _applica_permessi_dipendente(self, user):
        """Permessi base: timbrature e richieste"""
        permessi = [
            "users.add_timbratura",
            "users.view_timbratura",
            "users.add_richiestaferie",
            "users.view_richiestaferie",
            "users.add_richiestapermesso",
            "users.view_richiestapermesso",
            "users.change_user",  # Solo per sé stesso (verificato in view)
            "users.view_user",
        ]
        self._assegna_permessi(user, permessi)

    def _applica_permessi_responsabile(self, user):
        """Permessi responsabile: gestione ferie/permessi"""
        self._applica_permessi_dipendente(user)
        permessi_extra = [
            "users.approva_ferie",
            "users.approva_permessi",
            "users.view_giornatalavorativa",
        ]
        self._assegna_permessi(user, permessi_extra)

    def _applica_permessi_amministratore(self, user):
        """Permessi admin: gestione completa"""
        permessi = [
            "users.gestione_completa_users",
            "users.add_user",
            "users.change_user",
            "users.view_user",
            "users.approva_ferie",
            "users.approva_permessi",
            "users.emetti_lettera_richiamo",
        ]
        self._assegna_permessi(user, permessi)

    def _assegna_permessi(self, user, permessi_codename):
        """Helper per assegnare permessi da lista codename"""
        for codename in permessi_codename:
            app_label, perm = codename.split(".")
            try:
                permission = Permission.objects.get(
                    codename=perm, content_type__app_label=app_label
                )
                user.user_permissions.add(permission)
            except Permission.DoesNotExist:
                pass


class UserUpdateForm(UserChangeForm):
    """
    Form modifica user esistente.

    Note:
    - Non consente eliminazione (solo modifica)
    - Admin può modificare tutti i campi
    - User può modificare solo foto profilo
    """

    password = None  # Rimuovi campo password (usa change password separato)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email.lower() if email else email

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "qualifica",
            "reparto",
            "stato",
            "data_nascita",
            "luogo_nascita",
            "codice_fiscale",
            "carta_d_identita",
            "data_scadenza_ci",
            "patente_di_guida",
            "data_scadenza_patente",
            "categorie_patente",
            "posizione_inail",
            "posizione_inps",
            "telefono",
            "telefono_emergenza",
            "indirizzo",
            "citta",
            "cap",
            "provincia",
            "data_assunzione",
            "data_cessazione",
            "giorni_ferie_anno",
            "giorni_ferie_residui",
            "ore_permesso_residue",
            "foto_profilo",
            "foto_carta_identita",
            "foto_codice_fiscale",
            "foto_patente",
            "note",
            "note_interne",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "qualifica": forms.TextInput(attrs={"class": "form-control"}),
            "reparto": forms.TextInput(attrs={"class": "form-control"}),
            "stato": forms.Select(attrs={"class": "form-select"}),
            "data_nascita": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "luogo_nascita": forms.TextInput(attrs={"class": "form-control"}),
            "codice_fiscale": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "16"}
            ),
            "carta_d_identita": forms.TextInput(attrs={"class": "form-control"}),
            "data_scadenza_ci": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "patente_di_guida": forms.TextInput(attrs={"class": "form-control"}),
            "data_scadenza_patente": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "categorie_patente": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Es. B, C, D"}
            ),
            "posizione_inail": forms.TextInput(attrs={"class": "form-control"}),
            "posizione_inps": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "telefono_emergenza": forms.TextInput(attrs={"class": "form-control"}),
            "indirizzo": forms.TextInput(attrs={"class": "form-control"}),
            "citta": forms.TextInput(attrs={"class": "form-control"}),
            "cap": forms.TextInput(attrs={"class": "form-control", "maxlength": "5"}),
            "provincia": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "2"}
            ),
            "data_assunzione": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "data_cessazione": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "giorni_ferie_anno": forms.NumberInput(attrs={"class": "form-control"}),
            "giorni_ferie_residui": forms.NumberInput(attrs={"class": "form-control"}),
            "ore_permesso_residue": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.25"}
            ),
            "foto_profilo": forms.FileInput(attrs={"class": "form-control"}),
            "foto_carta_identita": forms.FileInput(attrs={"class": "form-control"}),
            "foto_codice_fiscale": forms.FileInput(attrs={"class": "form-control"}),
            "foto_patente": forms.FileInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "note_interne": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class UserProfiloForm(forms.ModelForm):
    """
    Form per modifica profilo utente (solo foto).

    Usato quando user modifica sé stesso.
    """

    class Meta:
        model = User
        fields = ["foto_profilo"]
        widgets = {
            "foto_profilo": forms.FileInput(attrs={"class": "form-control"}),
        }


# ============================================================================
# FORMS TIMBRATURE
# ============================================================================


class TimbraturaForm(forms.ModelForm):
    """
    Form per timbratura ingresso/uscita.

    Features:
    - Modal snello
    - 3 turni: mattina, pomeriggio, notte
    - Auto-popolamento data/ora (automatico con auto_now_add)
    """

    class Meta:
        model = Timbratura
        fields = ["tipo", "turno", "note"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "turno": forms.Select(attrs={"class": "form-select"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class TimbraturaQuickForm(forms.Form):
    """
    Form ultra-rapido per timbratura da dashboard.

    Solo 2 campi: tipo e turno (data/ora auto).
    """

    tipo = forms.ChoiceField(
        label="Tipo",
        choices=Timbratura.TIPO_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}),
    )

    turno = forms.ChoiceField(
        label="Turno",
        choices=Timbratura.TURNO_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}),
    )


# ============================================================================
# FORMS FERIE E PERMESSI
# ============================================================================


class RichiestaFerieForm(forms.ModelForm):
    """
    Form richiesta ferie.

    Features:
    - Calcolo automatico giorni
    - Validazione giorni disponibili
    - Validazione sovrapposizioni ferie
    - Upload allegati (certificati)
    """

    class Meta:
        model = RichiestaFerie
        fields = ["data_inizio", "data_fine", "motivo"]
        widgets = {
            "data_inizio": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "data_fine": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "motivo": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        """Valida range date, giorni disponibili e sovrapposizioni"""
        cleaned_data = super().clean()
        data_inizio = cleaned_data.get("data_inizio")
        data_fine = cleaned_data.get("data_fine")

        if data_inizio and data_fine:
            if data_fine < data_inizio:
                raise ValidationError(
                    "Data fine non può essere precedente a data inizio"
                )

            # Calcola giorni lavorativi
            delta = data_fine - data_inizio
            giorni = delta.days + 1

            # Rimuovi weekend (approssimato - TODO: calendario festività)
            giorni_lavorativi = giorni - (giorni // 7 * 2)
            cleaned_data["giorni_richiesti"] = giorni_lavorativi

        return cleaned_data

    def save(self, commit=True):
        """Salva con calcolo giorni e validazione model"""
        instance = super().save(commit=False)
        instance.giorni_richiesti = self.cleaned_data.get("giorni_richiesti", 0)

        if commit:
            # Chiama full_clean per eseguire le validazioni del model (inclusa la sovrapposizione)
            instance.full_clean()
            instance.save()

        return instance


class RichiestaFerieAdminForm(forms.ModelForm):
    """
    Form admin per creare richieste ferie per conto di un dipendente.
    Bypassa il controllo giorni residui (gestito dall'admin).
    """

    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('last_name', 'first_name'),
        label="Dipendente",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = RichiestaFerie
        fields = ["user", "data_inizio", "data_fine", "motivo"]
        widgets = {
            "data_inizio": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "data_fine": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "motivo": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        data_inizio = cleaned_data.get("data_inizio")
        data_fine = cleaned_data.get("data_fine")

        if data_inizio and data_fine:
            if data_fine < data_inizio:
                raise ValidationError(
                    "Data fine non può essere precedente a data inizio"
                )
            delta = data_fine - data_inizio
            giorni = delta.days + 1
            giorni_lavorativi = giorni - (giorni // 7 * 2)
            cleaned_data["giorni_richiesti"] = giorni_lavorativi

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.giorni_richiesti = self.cleaned_data.get("giorni_richiesti", 0)

        if commit:
            instance.full_clean()
            instance.save()

        return instance


class RichiestaPermessoForm(forms.ModelForm):
    """
    Form richiesta permesso orario.

    Features:
    - Calcolo automatico ore
    - Validazione ore disponibili
    """

    class Meta:
        model = RichiestaPermesso
        fields = ["data", "ora_inizio", "ora_fine", "motivo"]
        widgets = {
            "data": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "ora_inizio": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "ora_fine": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "motivo": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        """Valida range orario"""
        cleaned_data = super().clean()
        ora_inizio = cleaned_data.get("ora_inizio")
        ora_fine = cleaned_data.get("ora_fine")

        if ora_inizio and ora_fine:
            if ora_fine <= ora_inizio:
                raise ValidationError("Ora fine deve essere successiva a ora inizio")

            # Calcola ore
            delta = datetime.combine(date.today(), ora_fine) - datetime.combine(
                date.today(), ora_inizio
            )
            ore = delta.total_seconds() / 3600
            cleaned_data["ore_richieste"] = round(ore, 2)

        return cleaned_data

    def save(self, commit=True):
        """Salva con calcolo ore"""
        instance = super().save(commit=False)
        instance.ore_richieste = self.cleaned_data["ore_richieste"]

        if commit:
            instance.save()

        return instance


class ApprovaRifiutaForm(forms.Form):
    """
    Form per approvazione/rifiuto richieste.

    Usato da admin per ferie/permessi.
    """

    azione = forms.ChoiceField(
        label="Azione",
        choices=[("approva", "Approva"), ("rifiuta", "Rifiuta")],
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    motivazione_rifiuto = forms.CharField(
        label="Motivazione Rifiuto",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        help_text="Obbligatorio in caso di rifiuto",
    )

    def clean(self):
        """Valida motivazione obbligatoria per rifiuto"""
        cleaned_data = super().clean()
        azione = cleaned_data.get("azione")
        motivazione = cleaned_data.get("motivazione_rifiuto")

        if azione == "rifiuta" and not motivazione:
            raise ValidationError("Motivazione rifiuto è obbligatoria")

        return cleaned_data


# ============================================================================
# FORMS LETTERA RICHIAMO
# ============================================================================


class LetteraRichiamoForm(forms.ModelForm):
    """
    Form emissione lettera di richiamo.

    Features:
    - 3 tipi: verbale, scritta, disciplinare
    - Upload allegato PDF
    - Notifica automatica user
    """

    class Meta:
        model = LetteraRichiamo
        fields = ["user", "tipo", "motivo"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "motivo": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra solo users attivi
        self.fields["user"].queryset = User.objects.filter(stato="attivo")


# ============================================================================
# FORMS CALENDARIO PERSONALE
# ============================================================================


class EventoPersonaleForm(forms.ModelForm):
    """
    Form per creare/modificare eventi personali nel calendario.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from crispy_forms.helper import FormHelper
        from crispy_forms.layout import Layout, Row, Column, Field
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('titolo'),
            Row(Column('tipo', css_class='col-md-6'), Column('priorita', css_class='col-md-6')),
            Row(Column('data_inizio', css_class='col-md-6'), Column('data_fine', css_class='col-md-6')),
            Field('tutto_il_giorno'),
            Field('descrizione'),
            Row(Column('colore', css_class='col-md-4'), Column('notifica_email', css_class='col-md-8 pt-4')),
        )

    data_inizio = forms.DateTimeField(
        label='Data/Ora Inizio',
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'}
        ),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']
    )

    data_fine = forms.DateTimeField(
        label='Data/Ora Fine',
        required=False,
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'}
        ),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']
    )

    class Meta:
        model = EventoPersonale
        fields = [
            'titolo', 'descrizione', 'tipo', 'priorita',
            'data_inizio', 'data_fine', 'tutto_il_giorno',
            'colore', 'notifica_email',
        ]
        widgets = {
            'titolo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Es. Riunione, Compleanno, Scadenza...'}),
            'descrizione': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Aggiungi dettagli...'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'priorita': forms.Select(attrs={'class': 'form-select'}),
            'tutto_il_giorno': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'colore': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'notifica_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_data_inizio(self):
        from django.utils import timezone
        data_inizio = self.cleaned_data.get('data_inizio')
        if data_inizio and timezone.is_naive(data_inizio):
            return timezone.make_aware(data_inizio)
        return data_inizio

    def clean_data_fine(self):
        from django.utils import timezone
        data_fine = self.cleaned_data.get('data_fine')
        if data_fine and timezone.is_naive(data_fine):
            return timezone.make_aware(data_fine)
        return data_fine

    def clean(self):
        cleaned_data = super().clean()
        data_inizio = cleaned_data.get('data_inizio')
        data_fine = cleaned_data.get('data_fine')
        if data_fine and data_inizio and data_fine < data_inizio:
            raise ValidationError('La data di fine deve essere successiva alla data di inizio')
        return cleaned_data
