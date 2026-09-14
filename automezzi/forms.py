from django import forms
from django.contrib.auth import get_user_model

from .models import (
    Automezzo, Manutenzione, AllegatoManutenzione,
    Rifornimento, EventoAutomezzo,
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
