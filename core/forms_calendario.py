from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, Submit

from .models.evento_calendario import EventoCalendario


class EventoCalendarioForm(forms.ModelForm):
    class Meta:
        model = EventoCalendario
        fields = ["titolo", "descrizione", "data_inizio", "data_fine", "tutto_il_giorno", "colore", "visibilita"]
        widgets = {
            "data_inizio": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "data_fine": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "descrizione": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_inizio"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["data_fine"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["data_fine"].required = False
        self.fields["descrizione"].required = False

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("titolo"),
            Field("descrizione"),
            Row(
                Column("data_inizio", css_class="col-md-6"),
                Column("data_fine", css_class="col-md-6"),
            ),
            Field("tutto_il_giorno"),
            Row(
                Column("colore", css_class="col-md-6"),
                Column("visibilita", css_class="col-md-6"),
            ),
        )
