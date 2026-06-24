from django import forms
from django.forms import inlineformset_factory

from .models import Installazione, Postazione, InterventoInstallazione, RiscontroPostazione
from servizi.models import Servizio


class InstallazioneForm(forms.ModelForm):

    class Meta:
        model = Installazione
        fields = [
            "filiale", "privato", "servizio",
            "prodotto_principale", "data_installazione", "attiva", "note",
        ]
        widgets = {
            "data_installazione": forms.DateInput(attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["servizio"].queryset = Servizio.objects.filter(
            richiede_installazione=True, attivo=True
        )
        self.fields["filiale"].required = False
        self.fields["privato"].required = False
        self.fields["prodotto_principale"].required = False


class PostazioneForm(forms.ModelForm):

    class Meta:
        model = Postazione
        fields = ["descrizione_luogo", "ha_cartello", "numero_cartello", "prodotto", "quantita", "note"]
        widgets = {
            "descrizione_luogo": forms.Textarea(attrs={"rows": 3}),
            "note": forms.Textarea(attrs={"rows": 2}),
            "quantita": forms.NumberInput(attrs={"step": "0.001"}),
        }

    def __init__(self, *args, **kwargs):
        prodotto_default = kwargs.pop("prodotto_default", None)
        super().__init__(*args, **kwargs)
        self.fields["prodotto"].required = False
        self.fields["quantita"].required = False
        if prodotto_default and not self.instance.pk:
            self.fields["prodotto"].initial = prodotto_default


class InterventoInstallazioneForm(forms.ModelForm):

    class Meta:
        model = InterventoInstallazione
        fields = [
            "data_intervento", "tecnico", "prodotto",
            "quantita_prodotto", "note", "ods",
        ]
        widgets = {
            "data_intervento": forms.DateInput(attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tecnico"].required = False
        self.fields["prodotto"].required = False
        self.fields["quantita_prodotto"].required = False
        self.fields["ods"].required = False


class RiscontroPostazioneForm(forms.ModelForm):

    class Meta:
        model = RiscontroPostazione
        fields = ["esito", "note"]
        widgets = {
            "note": forms.TextInput(attrs={"placeholder": "Note aggiuntive…"}),
        }


RiscontroPostazioneFormSet = inlineformset_factory(
    InterventoInstallazione,
    RiscontroPostazione,
    form=RiscontroPostazioneForm,
    extra=0,
    can_delete=False,
)
