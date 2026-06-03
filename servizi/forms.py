from django import forms
from django.forms import inlineformset_factory
from .models import Servizio, Contratto, ContrattoFiliale, ContrattoRiga, ODS, ODSRiga, ConsumoMateriale, CondominioODS, RigaUnitaAbitativa, RigaProdottoCondominio

_BS = {"class": "form-control"}
_SEL = {"class": "form-select"}
_CHK = {"class": "form-check-input"}
_AREA = {"class": "form-control", "rows": 3}
_DATE = {"class": "form-control", "type": "date"}
_TIME = {"class": "form-control", "type": "time"}


class ServizioForm(forms.ModelForm):
    class Meta:
        model = Servizio
        fields = ["nome", "descrizione", "tariffa_cartello", "attivo"]
        widgets = {
            "nome":             forms.TextInput(attrs=_BS),
            "descrizione":      forms.Textarea(attrs=_AREA),
            "tariffa_cartello": forms.NumberInput(attrs={**_BS, "step": "0.01"}),
            "attivo":           forms.CheckboxInput(attrs=_CHK),
        }


class ContrattoForm(forms.ModelForm):
    class Meta:
        model = Contratto
        fields = [
            "cliente", "periodicita",
            "data_inizio", "data_fine", "stato", "note",
        ]
        widgets = {
            "cliente":     forms.Select(attrs=_SEL),
            "periodicita": forms.Select(attrs=_SEL),
            "data_inizio": forms.DateInput(attrs=_DATE, format="%Y-%m-%d"),
            "data_fine":   forms.DateInput(attrs=_DATE, format="%Y-%m-%d"),
            "stato":       forms.Select(attrs=_SEL),
            "note":        forms.Textarea(attrs=_AREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from anagrafica_r2.models import Azienda
        self.fields["cliente"].queryset = Azienda.objects.filter(attivo=True).order_by("ragione_sociale")
        self.fields["data_fine"].required = False
        self.fields["note"].required = False


class ContrattoRigaForm(forms.ModelForm):
    class Meta:
        model = ContrattoRiga
        fields = ["servizio", "prezzo"]
        widgets = {
            "servizio": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "prezzo":   forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01", "placeholder": "0.00"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["servizio"].queryset = Servizio.objects.filter(attivo=True).order_by("nome")


ContrattoRigaFormSet = inlineformset_factory(
    Contratto, ContrattoRiga,
    form=ContrattoRigaForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class ODSForm(forms.ModelForm):
    class Meta:
        model = ODS
        fields = [
            "filiale", "privato",
            "data_servizio", "ora_inizio", "ora_fine",
            "stato", "incasso_al_servizio", "note_intervento",
        ]
        widgets = {
            "filiale":             forms.Select(attrs=_SEL),
            "privato":             forms.Select(attrs=_SEL),
            "data_servizio":       forms.DateInput(attrs=_DATE, format="%Y-%m-%d"),
            "ora_inizio":          forms.TimeInput(attrs=_TIME),
            "ora_fine":            forms.TimeInput(attrs=_TIME),
            "stato":               forms.Select(attrs=_SEL),
            "incasso_al_servizio": forms.CheckboxInput(attrs=_CHK),
            "note_intervento":     forms.Textarea(attrs=_AREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from anagrafica_r2.models import Filiale, Privato
        self.fields["filiale"].queryset = (
            Filiale.objects.filter(attivo=True)
            .select_related("cliente")
            .order_by("cliente__ragione_sociale", "nome")
        )
        self.fields["filiale"].required = False
        self.fields["privato"].queryset = Privato.objects.filter(attivo=True).order_by("cognome", "nome")
        self.fields["privato"].required = False
        self.fields["ora_inizio"].required = False
        self.fields["ora_fine"].required = False
        self.fields["note_intervento"].required = False


class ODSRigaForm(forms.ModelForm):
    class Meta:
        model = ODSRiga
        fields = ["servizio", "prezzo", "contratto_filiale", "note"]
        widgets = {
            "servizio":            forms.Select(attrs={**_SEL, "class": "form-select form-select-sm riga-servizio"}),
            "prezzo":              forms.NumberInput(attrs={"class": "form-control form-control-sm riga-prezzo", "step": "0.01", "placeholder": "—"}),
            "contratto_filiale":   forms.HiddenInput(attrs={"class": "riga-contratto-filiale"}),
            "note":                forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Note riga"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["servizio"].queryset = Servizio.objects.filter(attivo=True).order_by("nome")
        self.fields["prezzo"].required = False
        self.fields["contratto_filiale"].required = False
        self.fields["note"].required = False


ODSRigaFormSet = inlineformset_factory(
    ODS, ODSRiga,
    form=ODSRigaForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class ProdottoPrevitoForm(forms.Form):
    """Riga prodotto previsto da inserire nell'ODS (non scala stock)."""
    prodotto = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={"class": "form-select form-select-sm prodotto-sel"}),
        empty_label="— Prodotto —",
    )
    quantita = forms.DecimalField(
        max_digits=10, decimal_places=3, initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.001", "min": "0.001"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from magazzino.models import Prodotto
        self.fields["prodotto"].queryset = Prodotto.objects.filter(attivo=True).order_by("nome_prodotto")


class ConsumoMaterialeForm(forms.ModelForm):
    class Meta:
        model = ConsumoMateriale
        fields = ["prodotto", "quantita", "note"]
        widgets = {
            "prodotto":  forms.Select(attrs=_SEL),
            "quantita":  forms.NumberInput(attrs={**_BS, "step": "0.001", "min": "0.001"}),
            "note":      forms.TextInput(attrs={**_BS, "placeholder": "Note (opzionale)"}),
        }

    def __init__(self, *args, mezzo=None, **kwargs):
        super().__init__(*args, **kwargs)
        from magazzino.models import Prodotto, ScortaMezzo
        if mezzo:
            ids = ScortaMezzo.objects.filter(
                mezzo=mezzo, quantita__gt=0
            ).values_list("prodotto_id", flat=True)
            self.fields["prodotto"].queryset = Prodotto.objects.filter(pk__in=ids, attivo=True).order_by("nome_prodotto")
        else:
            self.fields["prodotto"].queryset = Prodotto.objects.filter(attivo=True).order_by("nome_prodotto")
        self.fields["note"].required = False


class ChiudiServizioForm(forms.Form):
    modalita_pagamento = forms.ChoiceField(
        choices=[
            ("contanti",      "Contanti"),
            ("carta",         "Carta"),
            ("paypal",        "PayPal"),
            ("non_incassato", "Non incassato"),
        ],
        initial="contanti",
        widget=forms.Select(attrs=_SEL),
        required=False,
    )
    importo_incassato = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={**_BS, "step": "0.01", "placeholder": "Importo"}),
    )
    note_intervento = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={**_AREA, "placeholder": "Note intervento"}),
    )


class CondominioODSForm(forms.ModelForm):
    class Meta:
        model = CondominioODS
        fields = ["titolo", "indirizzo", "data", "ora", "prezzo_base", "distinta", "tecnico", "assistente", "note"]
        widgets = {
            "titolo":      forms.TextInput(attrs=_BS),
            "indirizzo":   forms.TextInput(attrs=_BS),
            "data":        forms.DateInput(attrs=_DATE),
            "ora":         forms.TimeInput(attrs=_TIME),
            "prezzo_base": forms.NumberInput(attrs={**_BS, "step": "0.01"}),
            "tecnico":     forms.Select(attrs=_SEL),
            "assistente":  forms.Select(attrs=_SEL),
            "note":        forms.Textarea(attrs=_AREA),
        }


class RigaUnitaAbitativaForm(forms.ModelForm):
    class Meta:
        model = RigaUnitaAbitativa
        fields = ["nome", "servizio_effettuato", "incasso_effettuato", "importo_da_incassare"]
        widgets = {
            "nome":                 forms.TextInput(attrs={**_BS, "placeholder": "Es. Rossi Mario — Int. 3"}),
            "servizio_effettuato":  forms.CheckboxInput(attrs=_CHK),
            "incasso_effettuato":   forms.CheckboxInput(attrs=_CHK),
            "importo_da_incassare": forms.NumberInput(attrs={**_BS, "step": "0.01", "placeholder": "Lascia vuoto per prezzo base"}),
        }


RigaUnitaAbitativaFormSet = inlineformset_factory(
    CondominioODS, RigaUnitaAbitativa,
    form=RigaUnitaAbitativaForm,
    extra=5, can_delete=True, min_num=1, validate_min=True,
)


class RigaProdottoCondominioForm(forms.ModelForm):
    class Meta:
        model = RigaProdottoCondominio
        fields = ["prodotto", "quantita"]
        widgets = {
            "prodotto": forms.Select(attrs=_SEL),
            "quantita": forms.NumberInput(attrs={**_BS, "step": "0.001"}),
        }


RigaProdottoCondominioFormSet = inlineformset_factory(
    CondominioODS, RigaProdottoCondominio,
    form=RigaProdottoCondominioForm,
    extra=2, can_delete=True, min_num=0, validate_min=False,
)


# Formset usato dal tecnico durante l'esecuzione (no extra rows, aggiunte via JS)
RigaUnitaAbitativaEseguiFormSet = inlineformset_factory(
    CondominioODS, RigaUnitaAbitativa,
    form=RigaUnitaAbitativaForm,
    extra=0, can_delete=False,
)

RigaProdottoCondominioEseguiFormSet = inlineformset_factory(
    CondominioODS, RigaProdottoCondominio,
    form=RigaProdottoCondominioForm,
    extra=0, can_delete=False,
)
