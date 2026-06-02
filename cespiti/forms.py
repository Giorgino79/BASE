from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import date
from django.contrib.auth import get_user_model

from .models import (
    Automezzo, Manutenzione, AllegatoManutenzione,
    Rifornimento, EventoAutomezzo,
    Stabilimento, CostiStabilimento, DocStabilimento,
)

User = get_user_model()

DATE_WIDGET = {"type": "date"}

_BS_CLASS = {
    forms.TextInput:         "form-control",
    forms.NumberInput:       "form-control",
    forms.EmailInput:        "form-control",
    forms.URLInput:          "form-control",
    forms.PasswordInput:     "form-control",
    forms.Textarea:          "form-control",
    forms.DateInput:         "form-control",
    forms.DateTimeInput:     "form-control",
    forms.TimeInput:         "form-control",
    forms.Select:            "form-select",
    forms.SelectMultiple:    "form-select",
    forms.ClearableFileInput:"form-control",
    forms.FileInput:         "form-control",
    forms.CheckboxInput:     "form-check-input",
}


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            cls = _BS_CLASS.get(type(w))
            if cls:
                existing = w.attrs.get("class", "")
                if cls not in existing:
                    w.attrs["class"] = (existing + " " + cls).strip()
            if isinstance(w, forms.Select) and not field.required:
                w.attrs.setdefault("class", "form-select")


# ── AUTOMEZZI ────────────────────────────────────────────────

class AutomezzoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Automezzo
        fields = [
            "numero_mezzo", "targa", "marca", "modello", "anno_immatricolazione",
            "chilometri_attuali", "attivo", "disponibile", "bloccata", "motivo_blocco",
            "libretto_fronte", "libretto_retro", "assicurazione",
            "data_scadenza_assicurazione", "data_revisione", "assegnato_a",
        ]
        widgets = {
            "data_revisione": forms.DateInput(attrs=DATE_WIDGET),
            "data_scadenza_assicurazione": forms.DateInput(attrs=DATE_WIDGET),
            "motivo_blocco": forms.Textarea(attrs={"rows": 2}),
        }


class ManutenzioneCreateForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Manutenzione
        fields = ["automezzo", "data_prevista", "descrizione", "fornitore", "luogo", "responsabile", "allegati"]
        widgets = {
            "data_prevista": forms.DateInput(attrs=DATE_WIDGET),
            "descrizione": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ["fornitore", "luogo", "responsabile", "allegati"]:
            self.fields[f].required = False


class ManutenzioneUpdateForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Manutenzione
        fields = [
            "automezzo", "data_prevista", "descrizione", "stato",
            "fornitore", "luogo", "costo", "seguito_da", "responsabile", "allegati",
        ]
        widgets = {
            "data_prevista": forms.DateInput(attrs=DATE_WIDGET),
            "descrizione": forms.Textarea(attrs={"rows": 3}),
            "costo": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["costo"].required = False


class ManutenzioneResponsabileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Manutenzione
        fields = ["foglio_accettazione", "note_responsabile"]
        widgets = {"note_responsabile": forms.Textarea(attrs={"rows": 3})}


class ManutenzioneFinaleForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Manutenzione
        fields = ["costo", "note_finali", "fattura_fornitore"]
        widgets = {
            "costo": forms.NumberInput(attrs={"step": "0.01"}),
            "note_finali": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["costo"].required = True


class AllegatoManutenzioneForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = AllegatoManutenzione
        fields = ["nome", "file"]


class RifornimentoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Rifornimento
        fields = ["automezzo", "data", "litri", "costo_totale", "chilometri", "scontrino"]
        widgets = {"data": forms.DateInput(attrs=DATE_WIDGET)}


class EventoAutomezzoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = EventoAutomezzo
        fields = ["automezzo", "tipo", "data_evento", "descrizione", "costo", "dipendente_coinvolto", "file_allegato", "risolto"]
        widgets = {
            "data_evento": forms.DateInput(attrs=DATE_WIDGET),
            "descrizione": forms.Textarea(attrs={"rows": 2}),
        }


# ── STABILIMENTI ─────────────────────────────────────────────

class StabilimentoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Stabilimento
        fields = [
            "nome", "indirizzo", "cap", "citta", "provincia",
            "telefono", "email_filiale",
            "responsabile_operativo", "responsabile_amministrativo",
            "superficie_mq", "numero_piani", "anno_costruzione",
            "data_apertura", "note_generali",
        ]
        widgets = {
            "data_apertura": forms.DateInput(attrs=DATE_WIDGET),
            "note_generali": forms.Textarea(attrs={"rows": 3}),
            "provincia": forms.TextInput(attrs={"maxlength": "2", "style": "text-transform:uppercase"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        active_users = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        self.fields["responsabile_operativo"].queryset = active_users
        self.fields["responsabile_amministrativo"].queryset = active_users
        for f in ["responsabile_operativo", "responsabile_amministrativo", "telefono",
                  "email_filiale", "superficie_mq", "numero_piani", "anno_costruzione",
                  "data_apertura", "note_generali"]:
            self.fields[f].required = False

    def clean_provincia(self):
        p = self.cleaned_data.get("provincia", "")
        return p.upper()

    def clean_data_apertura(self):
        d = self.cleaned_data.get("data_apertura")
        if d and d > date.today():
            raise ValidationError("La data di apertura non può essere nel futuro")
        return d


class CostiStabilimentoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = CostiStabilimento
        fields = [
            "stabilimento", "fornitore", "causale", "stato",
            "titolo", "descrizione", "importo", "iva_percentuale",
            "data_richiesta", "data_inizio_lavori", "data_fine_lavori",
            "data_fattura", "data_scadenza_servizio",
            "fattura", "preventivo", "certificato", "note_interne",
        ]
        widgets = {
            "data_richiesta": forms.DateInput(attrs=DATE_WIDGET),
            "data_inizio_lavori": forms.DateInput(attrs=DATE_WIDGET),
            "data_fine_lavori": forms.DateInput(attrs=DATE_WIDGET),
            "data_fattura": forms.DateInput(attrs=DATE_WIDGET),
            "data_scadenza_servizio": forms.DateInput(attrs=DATE_WIDGET),
            "descrizione": forms.Textarea(attrs={"rows": 4}),
            "note_interne": forms.Textarea(attrs={"rows": 3}),
            "importo": forms.NumberInput(attrs={"step": "0.01"}),
            "iva_percentuale": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args, user=None, stabilimento=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["stabilimento"].queryset = Stabilimento.objects.attivi().order_by("nome")
        try:
            from anagrafica.models import Fornitore
            self.fields["fornitore"].queryset = Fornitore.objects.filter(attivo=True).order_by("ragione_sociale")
        except Exception:
            pass
        if stabilimento and not self.instance.pk:
            self.fields["stabilimento"].initial = stabilimento
        for f in ["data_inizio_lavori", "data_fine_lavori", "data_fattura",
                  "data_scadenza_servizio", "fattura", "preventivo", "certificato", "note_interne"]:
            self.fields[f].required = False

    def clean(self):
        cleaned = super().clean()
        d_inizio = cleaned.get("data_inizio_lavori")
        d_fine = cleaned.get("data_fine_lavori")
        if d_inizio and d_fine and d_inizio > d_fine:
            raise ValidationError("La data fine lavori non può essere precedente all'inizio")
        return cleaned


class UtenzaForm(CostiStabilimentoForm):
    class Meta(CostiStabilimentoForm.Meta):
        fields = CostiStabilimentoForm.Meta.fields + [
            "consumo_kwh", "consumo_mc",
            "periodo_fatturazione_da", "periodo_fatturazione_a", "codice_pdr_pod",
        ]
        widgets = {
            **CostiStabilimentoForm.Meta.widgets,
            "consumo_kwh": forms.NumberInput(attrs={"step": "0.01"}),
            "consumo_mc": forms.NumberInput(attrs={"step": "0.01"}),
            "periodo_fatturazione_da": forms.DateInput(attrs=DATE_WIDGET),
            "periodo_fatturazione_a": forms.DateInput(attrs=DATE_WIDGET),
        }

    UTENZE_CHOICES = [
        ("energia_elettrica", "Energia Elettrica"),
        ("gas_naturale", "Gas Naturale"),
        ("acqua", "Acqua e Scarichi"),
        ("telefonia", "Telefonia e Internet"),
        ("rifiuti", "Smaltimento Rifiuti"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["causale"].choices = [("", "---------")] + self.UTENZE_CHOICES
        for f in ["consumo_kwh", "consumo_mc", "periodo_fatturazione_da",
                  "periodo_fatturazione_a", "codice_pdr_pod",
                  "data_inizio_lavori", "data_fine_lavori"]:
            self.fields[f].required = False
        if not self.instance.pk:
            self.fields["stato"].initial = "fatturato"
            self.fields["causale"].initial = "energia_elettrica"


class DocStabilimentoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DocStabilimento
        fields = [
            "nome_documento", "tipo_documento", "versione",
            "descrizione", "file_documento", "data_documento", "data_scadenza", "note", "attivo",
        ]
        widgets = {
            "data_documento": forms.DateInput(attrs=DATE_WIDGET),
            "data_scadenza": forms.DateInput(attrs=DATE_WIDGET),
            "descrizione": forms.Textarea(attrs={"rows": 3}),
            "note": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, stabilimento=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for f in ["descrizione", "data_documento", "data_scadenza", "note", "versione"]:
            self.fields[f].required = False


# ── SEARCH FORMS ─────────────────────────────────────────────

class StabilimentiSearchForm(BootstrapMixin, forms.Form):
    q = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={"placeholder": "Cerca..."}))
    provincia = forms.CharField(max_length=2, required=False, widget=forms.TextInput(attrs={"maxlength": "2"}))
    attivo = forms.ChoiceField(
        choices=[("", "Tutti"), ("true", "Attivi"), ("false", "Inattivi")],
        required=False,
    )


class CostiSearchForm(BootstrapMixin, forms.Form):
    stabilimento = forms.ModelChoiceField(
        queryset=Stabilimento.objects.attivi().order_by("nome"),
        required=False, empty_label="Tutti gli stabilimenti",
    )
    causale = forms.ChoiceField(
        choices=[("", "Tutte le tipologie")] + list(CostiStabilimento.TipoCosto.choices),
        required=False,
    )
    stato = forms.ChoiceField(
        choices=[("", "Tutti gli stati")] + list(CostiStabilimento.StatoCosto.choices),
        required=False,
    )
    anno = forms.ChoiceField(required=False)
    scadenze_prossime = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        anno_corrente = timezone.now().year
        self.fields["anno"].choices = [("", "Tutti")] + [
            (str(a), str(a)) for a in range(anno_corrente, anno_corrente - 5, -1)
        ]
