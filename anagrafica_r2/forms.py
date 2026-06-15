from django import forms
from .models import Azienda, Filiale, Fornitore, Privato

W_TEXT = {'class': 'form-control'}
W_EMAIL = {'class': 'form-control'}
W_AREA = {'class': 'form-control', 'rows': 3}
W_SEL = {'class': 'form-select'}
W_CHK = {'class': 'form-check-input'}


class AziendaForm(forms.ModelForm):

    class Meta:
        model = Azienda
        fields = [
            'ragione_sociale', 'marchio', 'indirizzo', 'citta', 'zona', 'cap', 'provincia',
            'partita_iva', 'codice_fiscale', 'codice_univoco', 'pec',
            'referente', 'telefono',
            'email_direzione', 'email_amministrazione', 'email_operativo', 'email_operativo_2',
            'tipo_pagamento',
            'sede_unica',
            'utente_riferimento',
            'installato', 'attivo', 'note',
        ]
        widgets = {
            'ragione_sociale':      forms.TextInput(attrs=W_TEXT),
            'marchio':              forms.TextInput(attrs={**W_TEXT, 'placeholder': 'es: McDonald\'s (se diverso dalla ragione sociale)'}),
            'indirizzo':            forms.TextInput(attrs=W_TEXT),
            'citta':                forms.TextInput(attrs=W_TEXT),
            'cap':                  forms.TextInput(attrs={**W_TEXT, 'maxlength': '5', 'pattern': '[0-9]{5}'}),
            'zona':                 forms.TextInput(attrs=W_TEXT),
            'provincia':            forms.TextInput(attrs={**W_TEXT, 'maxlength': '5', 'placeholder': 'es: MI'}),
            'partita_iva':          forms.TextInput(attrs={**W_TEXT, 'placeholder': 'IT12345678901'}),
            'codice_fiscale':       forms.TextInput(attrs=W_TEXT),
            'codice_univoco':       forms.TextInput(attrs={**W_TEXT, 'maxlength': '7', 'placeholder': '7 caratteri'}),
            'pec':                  forms.EmailInput(attrs={**W_EMAIL, 'placeholder': 'cliente@pec.it'}),
            'referente':            forms.TextInput(attrs=W_TEXT),
            'telefono':             forms.TextInput(attrs=W_TEXT),
            'email_direzione':      forms.EmailInput(attrs=W_EMAIL),
            'email_amministrazione': forms.EmailInput(attrs=W_EMAIL),
            'email_operativo':      forms.EmailInput(attrs=W_EMAIL),
            'email_operativo_2':    forms.EmailInput(attrs=W_EMAIL),
            'tipo_pagamento':       forms.Select(attrs=W_SEL),
            'utente_riferimento':   forms.Select(attrs=W_SEL),
            'sede_unica':           forms.CheckboxInput(attrs=W_CHK),
            'installato':           forms.CheckboxInput(attrs=W_CHK),
            'attivo':               forms.CheckboxInput(attrs=W_CHK),
            'note':                 forms.Textarea(attrs=W_AREA),
        }

    def clean_ragione_sociale(self):
        rs = self.cleaned_data.get('ragione_sociale', '').strip()
        qs = Azienda.objects.filter(ragione_sociale__iexact=rs)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Questa ragione sociale esiste già.')
        return rs


class FilialeForm(forms.ModelForm):

    class Meta:
        model = Filiale
        fields = [
            'nome', 'tipo_sede',
            'indirizzo', 'citta', 'zona', 'cap', 'provincia',
            'telefono', 'email',
            'referente_nome', 'referente_tel', 'referente_email',
            'orario_apertura', 'giorno_chiusura', 'note_accesso',
            'installato', 'attivo', 'note',
        ]
        widgets = {
            'nome':             forms.TextInput(attrs=W_TEXT),
            'tipo_sede':        forms.Select(attrs=W_SEL),
            'indirizzo':        forms.TextInput(attrs=W_TEXT),
            'citta':            forms.TextInput(attrs=W_TEXT),
            'cap':              forms.TextInput(attrs={**W_TEXT, 'maxlength': '5', 'pattern': '[0-9]{5}'}),
            'zona':             forms.TextInput(attrs=W_TEXT),
            'provincia':        forms.TextInput(attrs={**W_TEXT, 'maxlength': '5', 'placeholder': 'es: MI'}),
            'telefono':         forms.TextInput(attrs=W_TEXT),
            'email':            forms.EmailInput(attrs=W_EMAIL),
            'referente_nome':   forms.TextInput(attrs=W_TEXT),
            'referente_tel':    forms.TextInput(attrs=W_TEXT),
            'referente_email':  forms.EmailInput(attrs=W_EMAIL),
            'orario_apertura':  forms.TextInput(attrs={**W_TEXT, 'placeholder': 'es: 08:00-20:00 / Lun-Sab'}),
            'giorno_chiusura':  forms.Select(attrs=W_SEL),
            'note_accesso':     forms.Textarea(attrs=W_AREA),
            'installato':       forms.CheckboxInput(attrs=W_CHK),
            'attivo':           forms.CheckboxInput(attrs=W_CHK),
            'note':             forms.Textarea(attrs=W_AREA),
        }


class FornitoreForm(forms.ModelForm):

    class Meta:
        model = Fornitore
        fields = [
            'ragione_sociale', 'indirizzo', 'citta', 'cap', 'provincia', 'regione',
            'telefono', 'email',
            'partita_iva', 'codice_fiscale', 'pec', 'codice_destinatario', 'iban',
            'categoria', 'tipo_pagamento', 'priorita_pagamento',
            'referente_nome', 'referente_telefono', 'referente_email',
            'attivo', 'note',
        ]
        widgets = {
            'ragione_sociale':     forms.TextInput(attrs=W_TEXT),
            'indirizzo':           forms.TextInput(attrs=W_TEXT),
            'citta':               forms.TextInput(attrs=W_TEXT),
            'cap':                 forms.TextInput(attrs={**W_TEXT, 'maxlength': '5', 'pattern': '[0-9]{5}'}),
            'provincia':           forms.TextInput(attrs={**W_TEXT, 'maxlength': '5', 'placeholder': 'es: MI'}),
            'regione':             forms.TextInput(attrs={**W_TEXT, 'placeholder': 'es: Lombardia'}),
            'telefono':            forms.TextInput(attrs=W_TEXT),
            'email':               forms.EmailInput(attrs=W_EMAIL),
            'partita_iva':         forms.TextInput(attrs={**W_TEXT, 'placeholder': 'IT12345678901'}),
            'codice_fiscale':      forms.TextInput(attrs=W_TEXT),
            'pec':                 forms.EmailInput(attrs={**W_EMAIL, 'placeholder': 'fornitore@pec.it'}),
            'codice_destinatario': forms.TextInput(attrs={**W_TEXT, 'maxlength': '7', 'placeholder': '7 caratteri'}),
            'iban':                forms.TextInput(attrs={**W_TEXT, 'placeholder': 'IT60X0542811101000000123456'}),
            'categoria':           forms.Select(attrs=W_SEL),
            'tipo_pagamento':      forms.Select(attrs=W_SEL),
            'priorita_pagamento':  forms.Select(attrs=W_SEL),
            'referente_nome':      forms.TextInput(attrs=W_TEXT),
            'referente_telefono':  forms.TextInput(attrs=W_TEXT),
            'referente_email':     forms.EmailInput(attrs=W_EMAIL),
            'attivo':              forms.CheckboxInput(attrs=W_CHK),
            'note':                forms.Textarea(attrs=W_AREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['iban'].help_text = 'IBAN per bonifici (IT + 25 caratteri)'
        self.fields['codice_destinatario'].help_text = 'Codice SDI a 7 caratteri per fatturazione elettronica'

    def clean_iban(self):
        iban = self.cleaned_data.get('iban', '')
        if not iban:
            return iban
        iban = iban.replace(' ', '').upper()
        if not iban.startswith('IT') or len(iban) != 27:
            raise forms.ValidationError('IBAN non valido (formato: IT + 25 caratteri)')
        return iban


class PrivatoForm(forms.ModelForm):

    class Meta:
        model = Privato
        fields = [
            'nome', 'cognome', 'telefono',
            'indirizzo', 'citta', 'zona', 'cap', 'provincia',
            'codice_fiscale', 'email',
            'attivo', 'note',
        ]
        widgets = {
            'nome':            forms.TextInput(attrs=W_TEXT),
            'cognome':         forms.TextInput(attrs=W_TEXT),
            'telefono':        forms.TextInput(attrs=W_TEXT),
            'indirizzo':       forms.TextInput(attrs=W_TEXT),
            'citta':           forms.TextInput(attrs=W_TEXT),
            'zona':            forms.TextInput(attrs=W_TEXT),
            'cap':             forms.TextInput(attrs={**W_TEXT, 'maxlength': '5', 'pattern': '[0-9]{5}'}),
            'provincia':       forms.TextInput(attrs={**W_TEXT, 'maxlength': '5', 'placeholder': 'es: MI'}),
            'codice_fiscale':  forms.TextInput(attrs={**W_TEXT, 'placeholder': 'RSSMRA80A01H501U'}),
            'email':           forms.EmailInput(attrs=W_EMAIL),
            'attivo':          forms.CheckboxInput(attrs=W_CHK),
            'note':            forms.Textarea(attrs=W_AREA),
        }
