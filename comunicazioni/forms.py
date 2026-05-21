from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field

from .models import Promemoria


class PromemoriaForm(forms.ModelForm):
    class Meta:
        model = Promemoria
        fields = ['titolo', 'descrizione', 'priorita', 'stato', 'data_scadenza', 'assegnato_a']
        widgets = {
            'data_scadenza': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'descrizione': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_scadenza'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['data_scadenza'].required = False
        self.fields['assegnato_a'].required = False
        self.fields['descrizione'].required = False
        if user:
            from users.models import User
            self.fields['assegnato_a'].queryset = User.objects.filter(is_active=True).exclude(pk=user.pk)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('titolo'),
            Row(Column('priorita', css_class='col-md-6'), Column('stato', css_class='col-md-6')),
            Field('data_scadenza'),
            Field('assegnato_a'),
            Field('descrizione'),
        )


class NuovaConversazioneForm(forms.Form):
    TIPO_CHOICES = [('direct', 'Chat diretta'), ('group', 'Gruppo')]

    tipo = forms.ChoiceField(choices=TIPO_CHOICES, initial='direct', widget=forms.RadioSelect)
    titolo = forms.CharField(
        max_length=200, required=False, label='Titolo gruppo (opzionale)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Es. Team marketing…'}),
    )
    destinatari = forms.ModelMultipleChoiceField(
        queryset=None, label='Destinatari',
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from users.models import User
        self.fields['destinatari'].queryset = User.objects.filter(
            is_active=True
        ).exclude(pk=current_user.pk if current_user else None)

        self.helper = FormHelper()
        self.helper.form_tag = False
