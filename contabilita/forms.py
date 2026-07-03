from django import forms
from .models import ContoContabile, MovimentoPrimaNota


class ContoContabileForm(forms.ModelForm):
    class Meta:
        model  = ContoContabile
        fields = ['nome', 'tipo', 'descrizione', 'attivo']
        widgets = {
            'descrizione': forms.Textarea(attrs={'rows': 3}),
        }


class MovimentoPrimaNotaForm(forms.ModelForm):
    class Meta:
        model  = MovimentoPrimaNota
        fields = [
            'data', 'tipo', 'causale', 'importo',
            'conto_dare', 'conto_avere',
            'numero_documento', 'fattura_passiva', 'note',
        ]
        widgets = {
            'data':  forms.DateInput(attrs={'type': 'date'}),
            'note':  forms.Textarea(attrs={'rows': 2}),
            'causale': forms.TextInput(attrs={'placeholder': 'Es: Ft 2026/42 — Rossi SRL'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo conti attivi
        self.fields['conto_dare'].queryset  = ContoContabile.objects.filter(attivo=True).order_by('tipo', 'nome')
        self.fields['conto_avere'].queryset = ContoContabile.objects.filter(attivo=True).order_by('tipo', 'nome')
        self.fields['fattura_passiva'].required = False
        self.fields['fattura_passiva'].help_text = 'Opzionale — collega questo movimento a una fattura fornitore esistente.'

    def clean(self):
        cleaned = super().clean()
        dare  = cleaned.get('conto_dare')
        avere = cleaned.get('conto_avere')
        if dare and avere and dare == avere:
            raise forms.ValidationError('Il conto Dare e il conto Avere non possono essere lo stesso conto.')
        return cleaned
