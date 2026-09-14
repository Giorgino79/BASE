from django import forms
from .models import WAConfig, WABroadcast


class WAConfigForm(forms.ModelForm):
    class Meta:
        model = WAConfig
        fields = [
            "numero_mittente", "foto_profilo", "stato_wa",
            "delay_min", "delay_max", "attivo",
        ]
        widgets = {
            "numero_mittente": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "es: 393331234567 (senza +)",
            }),
            "foto_profilo": forms.FileInput(attrs={"class": "form-control"}),
            "stato_wa": forms.TextInput(attrs={
                "class": "form-control",
                "maxlength": 139,
                "placeholder": "Es: Servizio clienti",
            }),
            "delay_min": forms.NumberInput(attrs={"class": "form-control", "min": 3}),
            "delay_max": forms.NumberInput(attrs={"class": "form-control", "min": 5}),
            "attivo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cd = super().clean()
        dmin = cd.get("delay_min", 0)
        dmax = cd.get("delay_max", 0)
        if dmin and dmax and dmin >= dmax:
            raise forms.ValidationError("Il delay minimo deve essere inferiore al delay massimo.")
        return cd


class InvioSingoloForm(forms.Form):
    numero = forms.CharField(
        max_length=20,
        label="Numero destinatario",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "es: 393331234567",
        }),
    )
    nome = forms.CharField(
        max_length=200, required=False,
        label="Nome (opzionale)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    testo = forms.CharField(
        label="Messaggio",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )


class WABroadcastForm(forms.ModelForm):
    class Meta:
        model = WABroadcast
        fields = ["titolo", "messaggio"]
        widgets = {
            "titolo": forms.TextInput(attrs={"class": "form-control"}),
            "messaggio": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }


class BroadcastDestinatariForm(forms.Form):
    """Form per selezionare i destinatari — le fonti (clienti/fornitori/...) non sono
    hardcoded: ogni app anagrafica-like si registra in contact_sources (vedi
    whatsapp/contact_sources.py), così whatsapp (CORE) non importa mai direttamente
    un modello anagrafica specifico, che varia per prodotto."""
    fonti = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=False,
        label="Fonti destinatari",
    )
    numeri_manuali = forms.CharField(
        required=False,
        label="Numeri manuali",
        help_text="Un numero per riga nel formato 393331234567",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .contact_sources import get_sources
        self.fields["fonti"].choices = [
            (codice, sorgente["label"]) for codice, sorgente in get_sources().items()
        ]

    def clean(self):
        cd = super().clean()
        if not cd.get("fonti") and not cd.get("numeri_manuali", "").strip():
            raise forms.ValidationError("Seleziona almeno una fonte o inserisci numeri manuali.")
        return cd
