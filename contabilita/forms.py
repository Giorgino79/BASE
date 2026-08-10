import json
from decimal import Decimal, InvalidOperation

from django import forms

from fatturazione_attiva.models import Fattura

from .documenti import fatture_da_incassare
from .models import ContoContabile, MovimentoPrimaNota

_BS_CLASS = {
    forms.TextInput:          "form-control",
    forms.NumberInput:        "form-control",
    forms.Textarea:           "form-control",
    forms.DateInput:          "form-control",
    forms.Select:             "form-select",
    forms.CheckboxInput:      "form-check-input",
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


class ContoContabileForm(BootstrapMixin, forms.ModelForm):
    # I conti cliente e fornitore nascono automaticamente dall'anagrafica
    # (vedi contabilita/signals.py): a mano si creano solo questi.
    TIPI_MANUALI = [
        ContoContabile.Tipo.CASSA,
        ContoContabile.Tipo.BANCA,
        ContoContabile.Tipo.GENERICO,
    ]

    class Meta:
        model  = ContoContabile
        fields = ['nome', 'tipo', 'iban', 'descrizione', 'attivo']
        widgets = {
            'iban': forms.TextInput(attrs={'placeholder': 'IT60 X054 2811 1010 0000 0123 456'}),
            'descrizione': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        campo = self.fields['tipo']
        if self.instance.pk and self.instance.tipo not in self.TIPI_MANUALI:
            # Conto automatico esistente: si modifica tutto tranne il tipo.
            campo.disabled = True
            campo.help_text = 'Conto generato dall\'anagrafica: il tipo non è modificabile.'
        else:
            campo.choices = [
                (v, l) for v, l in ContoContabile.Tipo.choices
                if v in self.TIPI_MANUALI
            ]
            campo.help_text = (
                'I conti cliente e fornitore vengono creati automaticamente '
                'dall\'anagrafica e non si inseriscono da qui.'
            )


class MovimentoPrimaNotaForm(BootstrapMixin, forms.ModelForm):
    """
    Un movimento registrato a mano deve sempre riferirsi a un documento
    specifico: una fattura attiva o una fattura passiva, esattamente una.
    Le due FK sono pilotate da un unico campo di ricerca nel template, quindi
    qui viaggiano come input nascosti.
    """

    class Meta:
        model  = MovimentoPrimaNota
        fields = [
            'data', 'tipo', 'causale', 'importo',
            'conto_dare', 'conto_avere',
            'numero_documento', 'fattura_attiva', 'fattura_passiva', 'note',
        ]
        widgets = {
            'data':  forms.DateInput(attrs={'type': 'date'}),
            'note':  forms.Textarea(attrs={'rows': 2}),
            'causale': forms.TextInput(attrs={'placeholder': 'Es: Ft 2026/42 — Rossi SRL'}),
            'fattura_attiva':  forms.HiddenInput(),
            'fattura_passiva': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo conti attivi
        self.fields['conto_dare'].queryset  = ContoContabile.objects.filter(attivo=True).order_by('tipo', 'nome')
        self.fields['conto_avere'].queryset = ContoContabile.objects.filter(attivo=True).order_by('tipo', 'nome')
        # La validazione "una delle due" sta in clean(): singolarmente opzionali.
        self.fields['fattura_attiva'].required  = False
        self.fields['fattura_passiva'].required = False

    def documento_selezionato(self):
        """
        Etichetta del documento già collegato, per ripopolare il campo di
        ricerca dopo un errore di validazione o su un form legato a istanza.
        """
        from . import documenti

        attiva = self.get_field_object('fattura_attiva')
        if attiva:
            return {'kind': documenti.ATTIVA, 'etichetta': documenti.descrivi_attiva(attiva)}
        passiva = self.get_field_object('fattura_passiva')
        if passiva:
            return {'kind': documenti.PASSIVA, 'etichetta': documenti.descrivi_passiva(passiva)}
        return None

    def get_field_object(self, nome):
        """Istanza collegata a una delle due FK, sia da POST che da instance."""
        raw = self[nome].value()
        if not raw:
            return None
        try:
            return self.fields[nome].queryset.get(pk=raw)
        except (self.fields[nome].queryset.model.DoesNotExist, TypeError, ValueError):
            return None

    def clean(self):
        cleaned = super().clean()

        dare  = cleaned.get('conto_dare')
        avere = cleaned.get('conto_avere')
        if dare and avere and dare == avere:
            raise forms.ValidationError('Il conto Dare e il conto Avere non possono essere lo stesso conto.')

        attiva  = cleaned.get('fattura_attiva')
        passiva = cleaned.get('fattura_passiva')
        if not attiva and not passiva:
            raise forms.ValidationError(
                'Collega il movimento a un documento: cerca una fattura attiva '
                'o una fattura passiva nel campo "Documento di riferimento".'
            )
        if attiva and passiva:
            raise forms.ValidationError(
                'Un movimento può riferirsi a una sola fattura: scegli o quella '
                'attiva o quella passiva.'
            )

        return cleaned


class RegistrazioneIncassoForm(BootstrapMixin, forms.Form):
    """
    Registra un movimento bancario che incassa una o più fatture attive.

    L'importo ricevuto va ripartito fra le fatture selezionate: la quota di
    ciascuna arriva come campo dinamico `incasso_<pk>`, generato dal template
    quando si scelgono le fatture nel select2. Ogni quota non può superare il
    residuo della fattura, e la somma delle quote deve fare esattamente
    l'importo del movimento.
    """

    data = forms.DateField(
        label='Data movimento',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    conto = forms.ModelChoiceField(
        label='Conto banca / cassa',
        queryset=ContoContabile.objects.none(),
        empty_label='Scegli il conto su cui è arrivato il denaro…',
    )
    importo = forms.DecimalField(
        label='Importo ricevuto (€)', max_digits=12, decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0,00'}),
    )
    fatture = forms.ModelMultipleChoiceField(
        label='Fatture incassate',
        queryset=Fattura.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'data-select2': '1'}),
    )
    note = forms.CharField(
        label='Note', required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conto'].queryset = (
            ContoContabile.objects
            .filter(attivo=True, tipo__in=[ContoContabile.Tipo.BANCA, ContoContabile.Tipo.CASSA])
            .order_by('tipo', 'nome')
        )
        self.fields['fatture'].queryset = fatture_da_incassare()
        # Le quote arrivano come campi dinamici: qui si tiene la ripartizione
        # risolta, così la view non deve rileggere il POST.
        self.ripartizione = {}

    def quote_inviate(self):
        """
        Quote per fattura arrivate col POST, in JSON per il template: dopo un
        errore di validazione la ripartizione digitata va ripopolata.
        """
        quote = {
            chiave.removeprefix('incasso_'): valore
            for chiave, valore in (self.data or {}).items()
            if chiave.startswith('incasso_') and valore
        }
        return json.dumps(quote)

    def clean(self):
        cleaned = super().clean()
        fatture = cleaned.get('fatture')
        importo = cleaned.get('importo')

        if not fatture or importo is None:
            return cleaned

        totale_quote = Decimal('0.00')
        ripartizione = {}

        for fattura in fatture:
            grezzo = (self.data.get(f'incasso_{fattura.pk}') or '').strip()
            if not grezzo:
                # Nessuna quota indicata: si assume il saldo del residuo.
                quota = fattura.residuo
            else:
                try:
                    quota = Decimal(grezzo.replace(',', '.'))
                except (InvalidOperation, AttributeError):
                    self.add_error(None, f'Importo non valido per la fattura {fattura.numero}.')
                    continue

            if quota <= 0:
                self.add_error(None, f'L\'incasso della fattura {fattura.numero} deve essere maggiore di zero.')
                continue
            if quota > fattura.residuo:
                self.add_error(None, (
                    f'La fattura {fattura.numero} ha un residuo di € {fattura.residuo}: '
                    f'non puoi incassarne € {quota}.'
                ))
                continue

            ripartizione[fattura] = quota
            totale_quote += quota

        if self.errors:
            return cleaned

        if totale_quote != importo:
            self.add_error(None, (
                f'La ripartizione fra le fatture (€ {totale_quote}) non corrisponde '
                f'all\'importo ricevuto (€ {importo}). Correggi le quote o l\'importo.'
            ))
            return cleaned

        self.ripartizione = ripartizione
        return cleaned
