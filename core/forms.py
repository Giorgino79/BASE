from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Div, HTML
from .models_legacy import Allegato


# ============================================================================
# WIDGET PERSONALIZZATO PER UPLOAD MULTIPLO (Django 6.0+)
# ============================================================================


class MultipleFileInput(forms.FileInput):
    """
    Widget per upload multiplo di file compatibile con Django 6.0+.
    Sovrascrive __init__ per evitare il controllo su 'multiple'.
    """
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        # Bypassa il controllo del parent che blocca 'multiple'
        super(forms.FileInput, self).__init__(attrs)

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return files.get(name)

    def value_omitted_from_data(self, data, files, name):
        return name not in files


# ============================================================================
# PROCUREMENT MIXIN (per compatibilità con acquisti)
# ============================================================================


class ProcurementTargetFormMixin:
    """
    Mixin per form collegati a target di procurement.
    Placeholder per compatibilità con l'app acquisti.
    """
    pass


# ============================================================================
# FORM ALLEGATI
# ============================================================================


class AllegatoForm(forms.ModelForm):
    """
    Form per caricare allegati.
    Usa crispy_forms con Bootstrap 5 come da regole di sviluppo.
    """

    class Meta:
        model = Allegato
        fields = ["file", "descrizione"]
        widgets = {
            "descrizione": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"
        self.helper.layout = Layout(
            Div(
                Field("file", css_class="form-control"),
                css_class="mb-3",
            ),
            Div(
                Field(
                    "descrizione",
                    css_class="form-control",
                    placeholder="Descrizione opzionale",
                ),
                css_class="mb-3",
            ),
            Div(
                Submit("submit", "Carica Allegato", css_class="btn btn-primary"),
                css_class="d-grid gap-2",
            ),
        )


class MultipleAllegatoForm(forms.Form):
    """
    Form per caricare multipli allegati contemporaneamente.
    """

    files = forms.FileField(
        widget=MultipleFileInput(attrs={"multiple": True, "class": "form-control"}),
        label="File",
        help_text="Puoi selezionare più file contemporaneamente",
    )
    descrizione = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="Descrizione",
        help_text="Descrizione applicata a tutti i file caricati",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"
        self.helper.layout = Layout(
            Div(
                Field("files", css_class="form-control"),
                HTML(
                    '<small class="form-text text-muted">'
                    "Puoi selezionare più file contemporaneamente"
                    "</small>"
                ),
                css_class="mb-3",
            ),
            Div(
                Field(
                    "descrizione",
                    css_class="form-control",
                    placeholder="Descrizione opzionale",
                ),
                css_class="mb-3",
            ),
            Div(
                Submit("submit", "Carica File", css_class="btn btn-primary"),
                css_class="d-grid gap-2",
            ),
        )


# ============================================================================
# FORM EXPORT
# ============================================================================


class ExportForm(forms.Form):
    """
    Form generico per scegliere il formato di export.
    """

    FORMATO_CHOICES = [
        ("pdf", "PDF"),
        ("excel", "Excel (XLSX)"),
        ("csv", "CSV"),
    ]

    formato = forms.ChoiceField(
        choices=FORMATO_CHOICES,
        widget=forms.RadioSelect,
        label="Formato Export",
        initial="pdf",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Div(
                Field("formato"),
                css_class="mb-3",
            ),
            Div(
                Submit("export", "Esporta", css_class="btn btn-success"),
                css_class="d-grid gap-2",
            ),
        )


class DateRangeExportForm(forms.Form):
    """
    Form per export con filtro data.
    """

    FORMATO_CHOICES = [
        ("pdf", "PDF"),
        ("excel", "Excel (XLSX)"),
        ("csv", "CSV"),
    ]

    data_inizio = forms.DateField(
        label="Data Inizio",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    data_fine = forms.DateField(
        label="Data Fine",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    formato = forms.ChoiceField(
        choices=FORMATO_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Formato",
        initial="pdf",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Div(
                Div(Field("data_inizio"), css_class="col-md-6"),
                Div(Field("data_fine"), css_class="col-md-6"),
                css_class="row mb-3",
            ),
            Div(
                Field("formato"),
                css_class="mb-3",
            ),
            Div(
                Submit("export", "Genera Report", css_class="btn btn-success"),
                css_class="d-grid gap-2",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        data_inizio = cleaned_data.get("data_inizio")
        data_fine = cleaned_data.get("data_fine")

        if data_inizio and data_fine:
            if data_inizio > data_fine:
                raise forms.ValidationError(
                    "La data inizio non può essere successiva alla data fine"
                )

        return cleaned_data
