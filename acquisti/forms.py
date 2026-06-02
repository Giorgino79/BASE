from django import forms
from django.forms import inlineformset_factory
from .models import OrdineAcquisto, RigaOrdine, FatturaPassiva

_BS_CLASS = {
    forms.TextInput: "form-control",
    forms.NumberInput: "form-control",
    forms.EmailInput: "form-control",
    forms.Textarea: "form-control",
    forms.DateInput: "form-control",
    forms.Select: "form-select",
    forms.SelectMultiple: "form-select",
    forms.ClearableFileInput: "form-control",
    forms.FileInput: "form-control",
    forms.CheckboxInput: "form-check-input",
}


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            cls = _BS_CLASS.get(type(field.widget))
            if cls:
                existing = field.widget.attrs.get("class", "")
                if cls not in existing:
                    field.widget.attrs["class"] = (existing + " " + cls).strip()


class OrdineAcquistoForm(BootstrapMixin, forms.ModelForm):
    fornitore = forms.ModelChoiceField(queryset=None, label="Fornitore")

    class Meta:
        model = OrdineAcquisto
        fields = ["fornitore", "data_ordine", "data_consegna_richiesta", "stato", "note"]
        widgets = {
            "data_ordine": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "data_consegna_richiesta": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from anagrafica_r2.models import Fornitore
        self.fields["fornitore"].queryset = Fornitore.objects.order_by("ragione_sociale")
        self.fields["data_consegna_richiesta"].required = False
        self.fields["note"].required = False
        self.fields["stato"].required = False


class RigaOrdineForm(BootstrapMixin, forms.ModelForm):
    prodotto = forms.ModelChoiceField(queryset=None, required=False, label="Prodotto")

    class Meta:
        model = RigaOrdine
        fields = ["prodotto", "descrizione", "unita_misura", "quantita_ordinata", "prezzo_unitario", "aliquota_iva", "note"]
        widgets = {
            "descrizione": forms.TextInput(attrs={"placeholder": "Articolo non a catalogo"}),
            "note": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from magazzino.models import Prodotto
            self.fields["prodotto"].queryset = Prodotto.objects.filter(attivo=True).order_by("nome_prodotto")
        except Exception:
            self.fields["prodotto"].queryset = RigaOrdine.objects.none()
        self.fields["descrizione"].required = False
        self.fields["unita_misura"].required = False
        self.fields["note"].required = False

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("prodotto") and not cleaned.get("descrizione"):
            raise forms.ValidationError("Seleziona un prodotto o inserisci una descrizione.")
        return cleaned


RigaOrdineFormSet = inlineformset_factory(
    OrdineAcquisto,
    RigaOrdine,
    form=RigaOrdineForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class FatturaPassivaForm(BootstrapMixin, forms.ModelForm):
    fornitore = forms.ModelChoiceField(queryset=None, label="Fornitore")
    ordini = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        label="Ordini collegati",
        widget=forms.CheckboxSelectMultiple(),
    )

    class Meta:
        model = FatturaPassiva
        fields = [
            "fornitore", "ordini", "numero_fattura", "data_fattura",
            "data_scadenza", "imponibile", "aliquota_iva",
            "file_fattura", "stato_pagamento", "data_pagamento", "note",
        ]
        widgets = {
            "data_fattura": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "data_scadenza": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "data_pagamento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from anagrafica_r2.models import Fornitore
        self.fields["fornitore"].queryset = Fornitore.objects.order_by("ragione_sociale")
        self.fields["ordini"].queryset = OrdineAcquisto.objects.select_related("fornitore").order_by("-data_ordine")
        for f in ["data_scadenza", "data_pagamento", "note", "file_fattura"]:
            self.fields[f].required = False
