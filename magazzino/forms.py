from django import forms
from django.forms import inlineformset_factory
from .models import Categoria, Prodotto, Ricezione, RigaRicezione, CaricoMezzo, RigaCaricoMezzo

_BS_CLASS = {
    forms.TextInput: "form-control",
    forms.NumberInput: "form-control",
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


class CategoriaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nome", "descrizione", "attiva"]
        widgets = {"descrizione": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["descrizione"].required = False


class ProdottoForm(BootstrapMixin, forms.ModelForm):
    fornitore_principale = forms.ModelChoiceField(
        queryset=None, required=False, label="Fornitore principale"
    )

    class Meta:
        model = Prodotto
        fields = [
            "categoria", "fornitore_principale", "nome_prodotto",
            "codice_interno", "codice_fornitore", "descrizione",
            "unita_misura", "quantita_per_confezione", "formato_confezione",
            "is_biocida", "principio_attivo", "numero_registrazione",
            "attivo", "scorta_minima", "note_interne", "immagine", "scheda_tecnica",
        ]
        widgets = {
            "descrizione": forms.Textarea(attrs={"rows": 3}),
            "note_interne": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from anagrafica_r2.models import Fornitore
        self.fields["fornitore_principale"].queryset = Fornitore.objects.order_by("ragione_sociale")
        for f in [
            "codice_interno", "codice_fornitore", "descrizione",
            "quantita_per_confezione", "formato_confezione",
            "principio_attivo", "numero_registrazione", "scorta_minima", "note_interne", "immagine", "scheda_tecnica",
        ]:
            self.fields[f].required = False


class RicezioneForm(BootstrapMixin, forms.ModelForm):
    class _OrdineField(forms.ModelChoiceField):
        def label_from_instance(self, obj):
            prima_riga = obj.righe.all()[0] if obj.righe.all() else None
            prodotto_str = f" — {prima_riga.prodotto.nome_prodotto}" if prima_riga else ""
            return f"{obj.numero_ordine} | {obj.fornitore}{prodotto_str}"

    fornitore    = forms.ModelChoiceField(queryset=None, label="Fornitore")
    ordine       = _OrdineField(queryset=None, required=False, label="ODA di riferimento")
    stabilimento = forms.ModelChoiceField(queryset=None, required=False, label="Stabilimento destinatario")
    mezzo        = forms.ModelChoiceField(queryset=None, required=False, label="Mezzo destinatario")

    class Meta:
        model = Ricezione
        fields = ["numero_ddt", "data_ricezione", "fornitore", "ordine", "stabilimento", "mezzo", "bolla_firmata", "note"]
        widgets = {
            "data_ricezione": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from anagrafica_r2.models import Fornitore
        from acquisti.models import OrdineAcquisto
        from cespiti.models import Stabilimento, Automezzo
        self.fields["fornitore"].queryset = Fornitore.objects.order_by("ragione_sociale")
        self.fields["ordine"].queryset = OrdineAcquisto.objects.exclude(
            stato__in=["annullato", "pagato", "ricevuto"]
        ).select_related("fornitore").prefetch_related("righe__prodotto").order_by("-data_ordine")
        self.fields["stabilimento"].queryset = Stabilimento.objects.attivi().order_by("nome")
        self.fields["mezzo"].queryset = Automezzo.objects.filter(attivo=True).order_by("targa")
        self.fields["numero_ddt"].required = False
        self.fields["bolla_firmata"].required = False
        self.fields["note"].required = False

    def clean(self):
        cleaned = super().clean()
        stab  = cleaned.get("stabilimento")
        mezzo = cleaned.get("mezzo")
        if stab and mezzo:
            raise forms.ValidationError("Seleziona stabilimento oppure mezzo, non entrambi.")
        if not stab and not mezzo:
            raise forms.ValidationError("Seleziona un destinatario: stabilimento o mezzo.")
        return cleaned


class RigaRicezioneForm(BootstrapMixin, forms.ModelForm):
    riga_ordine = forms.ModelChoiceField(queryset=None, required=False, label="Riga ODA")
    prodotto = forms.ModelChoiceField(queryset=None, label="Prodotto")

    class Meta:
        model = RigaRicezione
        fields = [
            "riga_ordine", "prodotto", "nr_colli", "quantita_ricevuta",
            "prezzo_unitario", "numero_lotto", "data_scadenza_lotto", "note",
        ]
        widgets = {
            "data_scadenza_lotto": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "note": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from acquisti.models import RigaOrdine
        self.fields["prodotto"].queryset = Prodotto.objects.filter(attivo=True).order_by("nome_prodotto")
        self.fields["riga_ordine"].queryset = RigaOrdine.objects.select_related("ordine").order_by("-ordine__data_ordine")
        self.fields["nr_colli"].required = False
        self.fields["prezzo_unitario"].required = False
        self.fields["numero_lotto"].required = False
        self.fields["data_scadenza_lotto"].required = False
        self.fields["note"].required = False


RigaRicezioneFormSet = inlineformset_factory(
    Ricezione,
    RigaRicezione,
    form=RigaRicezioneForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class CaricoMezzoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = CaricoMezzo
        fields = ["mezzo", "stabilimento", "tipo", "note"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from cespiti.models import Automezzo, Stabilimento
        self.fields["mezzo"].queryset = Automezzo.objects.filter(attivo=True).order_by("targa")
        self.fields["stabilimento"].queryset = Stabilimento.objects.attivi().order_by("nome")
        self.fields["note"].required = False


class RigaCaricoMezzoForm(BootstrapMixin, forms.ModelForm):
    prodotto = forms.ModelChoiceField(queryset=None, label="Prodotto")

    class Meta:
        model = RigaCaricoMezzo
        fields = ["prodotto", "quantita"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["prodotto"].queryset = Prodotto.objects.filter(attivo=True).order_by("nome_prodotto")


RigaCaricoMezzoFormSet = inlineformset_factory(
    CaricoMezzo,
    RigaCaricoMezzo,
    form=RigaCaricoMezzoForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
