from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field

from .models import Corrispondenza, TipoCorrispondenza


class CorrispondenzaForm(forms.ModelForm):
    class Meta:
        model = Corrispondenza
        fields = [
            'oggetto', 'contenuto', 'tipo_destinatario',
            'destinatario_utente',
            'destinatario_nome', 'destinatario_indirizzo',
            'destinatario_cap', 'destinatario_citta', 'destinatario_provincia',
            'destinatario_email', 'destinatario_telefono',
            'tipo_corrispondenza', 'priorita', 'data_invio',
            'note_interne', 'allegato',
        ]
        widgets = {
            'contenuto': forms.Textarea(attrs={'rows': 10}),
            'note_interne': forms.Textarea(attrs={'rows': 3}),
            'destinatario_indirizzo': forms.TextInput(),
            'data_invio': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        optional = [
            'destinatario_utente', 'destinatario_nome', 'destinatario_indirizzo',
            'destinatario_cap', 'destinatario_citta', 'destinatario_provincia',
            'destinatario_email', 'destinatario_telefono',
            'tipo_corrispondenza', 'data_invio', 'allegato', 'note_interne',
        ]
        for f in optional:
            self.fields[f].required = False

        from users.models import User
        self.fields['destinatario_utente'].queryset = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        self.fields['tipo_corrispondenza'].queryset = TipoCorrispondenza.objects.filter(attivo=True)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('oggetto'),
            Row(Column('tipo_corrispondenza', css_class='col-md-6'), Column('priorita', css_class='col-md-6')),
            Row(Column('tipo_destinatario', css_class='col-md-6'), Column('data_invio', css_class='col-md-6')),
            Field('destinatario_utente'),
            Row(Column('destinatario_nome', css_class='col-md-8'), Column('destinatario_telefono', css_class='col-md-4')),
            Row(Column('destinatario_email', css_class='col-md-6'), Column('destinatario_indirizzo', css_class='col-md-6')),
            Row(Column('destinatario_cap', css_class='col-md-3'), Column('destinatario_citta', css_class='col-md-6'), Column('destinatario_provincia', css_class='col-md-3')),
            Field('contenuto'),
            Field('note_interne'),
            Field('allegato'),
        )

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo_destinatario')
        if tipo == Corrispondenza.TipoDestinatario.INTERNO and not cleaned.get('destinatario_utente'):
            self.add_error('destinatario_utente', 'Seleziona un utente interno.')
        elif tipo == Corrispondenza.TipoDestinatario.ESTERNO and not cleaned.get('destinatario_nome'):
            self.add_error('destinatario_nome', 'Il nome è obbligatorio per destinatario esterno.')
        return cleaned


class CorrispondenzaSearchForm(forms.Form):
    q = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Cerca oggetto, protocollo, destinatario…'}),
    )
    stato = forms.ChoiceField(
        choices=[('', 'Tutti gli stati')] + list(Corrispondenza.Stato.choices),
        required=False,
    )
    priorita = forms.ChoiceField(
        choices=[('', 'Tutte le priorità')] + list(Corrispondenza.Priorita.choices),
        required=False,
    )
    data_da = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    data_a = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
