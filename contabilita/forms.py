import json
from decimal import Decimal, InvalidOperation

from django import forms

from fatturazione_attiva.models import Fattura

from .documenti import fatture_da_incassare, fatture_da_pagare
from .models import (
    REGOLE_DARE_AVERE, ContoContabile, MovimentoPrimaNota, valida_dare_avere,
)

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

    Incassi e pagamenti non si registrano da qui: hanno un flusso guidato che
    aggiorna anche lo stato della fattura, cosa che questo form non fa. Se
    fossero selezionabili, un movimento con i conti giusti lascerebbe comunque
    la fattura aperta e il saldo del cliente sfalsato.
    """

    #: Tipi che hanno un flusso dedicato e vanno registrati solo da lì.
    TIPI_GUIDATI = {
        MovimentoPrimaNota.Tipo.INCASSO:   ('contabilita:incasso_create',   'Registra incasso'),
        MovimentoPrimaNota.Tipo.PAGAMENTO: ('contabilita:pagamento_create', 'Registra pagamento'),
    }

    #: Tipi generati dai signal all'emissione/registrazione della fattura:
    #: registrarli a mano creerebbe un doppione della scrittura automatica.
    TIPI_AUTOMATICI = {
        MovimentoPrimaNota.Tipo.FATTURA_CLIENTE,
        MovimentoPrimaNota.Tipo.FATTURA_FORNITORE,
    }

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

        esclusi = set(self.TIPI_GUIDATI) | self.TIPI_AUTOMATICI
        self.fields['tipo'].choices = [
            ('', '---------'),
            *[(v, l) for v, l in MovimentoPrimaNota.Tipo.choices if v not in esclusi],
        ]

    def regole_json(self):
        """
        Matrice tipo → tipi di conto ammessi, in JSON: il template la usa per
        filtrare le due tendine appena si sceglie il tipo, così l'errore non
        arriva nemmeno a essere digitabile. Il vincolo vero resta comunque
        server-side, nel model.
        """
        regole = {
            tipo: {'dare': sorted(dare), 'avere': sorted(avere)}
            for tipo, (dare, avere) in REGOLE_DARE_AVERE.items()
            if tipo not in (set(self.TIPI_GUIDATI) | self.TIPI_AUTOMATICI)
        }
        return json.dumps(regole)

    def conti_json(self):
        """pk → tipo di ogni conto selezionabile, per il filtro lato client."""
        return json.dumps({
            str(c.pk): c.tipo
            for c in self.fields['conto_dare'].queryset
        })

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

        # Stessa regola del model, applicata qui per legare il messaggio ai due
        # campi invece che al form intero.
        errore = valida_dare_avere(
            cleaned.get('tipo'), cleaned.get('conto_dare'), cleaned.get('conto_avere'),
        )
        if errore:
            self.add_error('conto_dare', errore)

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


class RegistrazioneQuoteForm(BootstrapMixin, forms.Form):
    """
    Base dei due flussi guidati: un movimento monetario che chiude una o più
    fatture, con l'importo ripartito fra i documenti selezionati.

    Incasso e pagamento sono lo stesso problema visto dai due lati: cambiano il
    modello delle fatture, il verso della scrittura e le etichette, non la
    logica di ripartizione. Le sottoclassi dichiarano solo le differenze.
    """

    #: Prefisso dei campi quota generati dal template (`incasso_<pk>`).
    prefisso_quota = 'quota'
    #: Nome del documento nei messaggi d'errore ('incasso' / 'pagamento').
    verbo = 'importo'

    data = forms.DateField(
        label='Data movimento',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    conto = forms.ModelChoiceField(
        label='Conto banca / cassa',
        queryset=ContoContabile.objects.none(),
        empty_label='Scegli il conto…',
    )
    # La controparte si sceglie per prima e restringe le fatture. È un
    # CharField e non un ModelChoiceField perché i due flussi la identificano
    # in modo diverso (il cliente con `dest_nome`, il fornitore con la pk) e
    # perché le opzioni arrivano via AJAX: renderizzarle tutte nella pagina è
    # esattamente quello che questo campo serve a evitare.
    controparte = forms.CharField(label='Cliente')
    importo = forms.DecimalField(
        label='Importo (€)', max_digits=12, decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0,00'}),
    )
    fatture = forms.ModelMultipleChoiceField(
        label='Fatture',
        queryset=Fattura.objects.none(),
        # Il widget non renderizza opzioni: le carica il template dopo aver
        # scelto la controparte. Il queryset resta quello completo e continua
        # a validare le pk che arrivano col POST.
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
        self.fields['fatture'].queryset = self.get_fatture_queryset()
        # Le quote arrivano come campi dinamici: qui si tiene la ripartizione
        # risolta, così la view non deve rileggere il POST.
        self.ripartizione = {}

    # ── Da specializzare ─────────────────────────────────────────────────────

    def get_fatture_queryset(self):
        raise NotImplementedError

    def numero_fattura(self, fattura):
        raise NotImplementedError

    def controparte_di(self, fattura):
        """Identificativo della controparte di una fattura, come stringa."""
        raise NotImplementedError

    def nome_controparte(self, valore):
        """Etichetta leggibile della controparte, per ripopolare il campo."""
        raise NotImplementedError

    # ── Controparte ──────────────────────────────────────────────────────────

    def controparte_scelta(self):
        """
        Controparte già selezionata, in JSON per il template: dopo un errore di
        validazione il select2 va ripopolato, e le sue opzioni non stanno
        nella pagina.
        """
        valore = (self['controparte'].value() or '').strip()
        if not valore:
            return json.dumps(None)
        return json.dumps({'id': valore, 'nome': self.nome_controparte(valore)})

    def fatture_scelte(self):
        """
        Fatture già selezionate, coi dati che servono alla ripartizione. Stesso
        motivo: il template non le ha, gliele passiamo noi.
        """
        from .documenti import righe_fatture

        pks = [p for p in (self.data.getlist('fatture') if self.is_bound else []) if p]
        if not pks:
            return json.dumps([])
        qs = self.get_fatture_queryset().filter(pk__in=pks)
        return json.dumps(righe_fatture(qs, self.numero_fattura))

    # ── Ripartizione ─────────────────────────────────────────────────────────

    def quote_inviate(self):
        """
        Quote per fattura arrivate col POST, in JSON per il template: dopo un
        errore di validazione la ripartizione digitata va ripopolata.
        """
        prefisso = f'{self.prefisso_quota}_'
        quote = {
            chiave.removeprefix(prefisso): valore
            for chiave, valore in (self.data or {}).items()
            if chiave.startswith(prefisso) and valore
        }
        return json.dumps(quote)

    def clean(self):
        cleaned = super().clean()
        fatture = cleaned.get('fatture')
        importo = cleaned.get('importo')
        controparte = (cleaned.get('controparte') or '').strip()

        # Le fatture arrivano da una chiamata AJAX filtrata per controparte, ma
        # le pk viaggiano nel POST: senza questo controllo si potrebbe pagare
        # la fattura di un cliente movimentando il conto di un altro.
        if fatture and controparte:
            estranee = [self.numero_fattura(f) for f in fatture
                        if self.controparte_di(f) != controparte]
            if estranee:
                self.add_error('fatture', (
                    f'{"Queste fatture non appartengono" if len(estranee) > 1 else "Questa fattura non appartiene"} '
                    f'alla controparte selezionata: {", ".join(estranee)}.'
                ))
                return cleaned

        if not fatture or importo is None:
            return cleaned

        totale_quote = Decimal('0.00')
        ripartizione = {}

        for fattura in fatture:
            numero = self.numero_fattura(fattura)
            grezzo = (self.data.get(f'{self.prefisso_quota}_{fattura.pk}') or '').strip()
            if not grezzo:
                # Nessuna quota indicata: si assume il saldo del residuo.
                quota = fattura.residuo
            else:
                try:
                    quota = Decimal(grezzo.replace(',', '.'))
                except (InvalidOperation, AttributeError):
                    self.add_error(None, f'Importo non valido per la fattura {numero}.')
                    continue

            if quota <= 0:
                self.add_error(None, f'L\'{self.verbo} della fattura {numero} deve essere maggiore di zero.')
                continue
            if quota > fattura.residuo:
                self.add_error(None, (
                    f'La fattura {numero} ha un residuo di € {fattura.residuo}: '
                    f'non puoi registrarne € {quota}.'
                ))
                continue

            ripartizione[fattura] = quota
            totale_quote += quota

        if self.errors:
            return cleaned

        if totale_quote != importo:
            self.add_error(None, (
                f'La ripartizione fra le fatture (€ {totale_quote}) non corrisponde '
                f'all\'importo del movimento (€ {importo}). Correggi le quote o l\'importo.'
            ))
            return cleaned

        self.ripartizione = ripartizione
        return cleaned


class RegistrazioneIncassoForm(RegistrazioneQuoteForm):
    """
    Registra un movimento bancario che incassa una o più fatture attive.

    Dare il conto banca/cassa, Avere il conto del cliente: il verso non è
    scelto dall'utente, quindi non può essere invertito.
    """

    prefisso_quota = 'incasso'
    verbo = 'incasso'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conto'].label = 'Conto banca / cassa'
        self.fields['conto'].empty_label = 'Scegli il conto su cui è arrivato il denaro…'
        self.fields['importo'].label = 'Importo ricevuto (€)'
        self.fields['fatture'].label = 'Fatture incassate'
        self.fields['controparte'].label = 'Cliente che ha pagato'
        self.fields['controparte'].error_messages['required'] = (
            'Scegli prima il cliente: le sue fatture aperte compariranno qui sotto.'
        )

    def get_fatture_queryset(self):
        return fatture_da_incassare()

    def numero_fattura(self, fattura):
        return fattura.numero

    def controparte_di(self, fattura):
        return fattura.dest_nome

    def nome_controparte(self, valore):
        # Il cliente *è* il suo nome: non c'è niente da risolvere.
        return valore


class RegistrazionePagamentoForm(RegistrazioneQuoteForm):
    """
    Registra il pagamento di una o più fatture passive.

    Dare il conto del fornitore, Avere il conto banca/cassa: speculare
    all'incasso, e come quello non lascia scegliere il verso.
    """

    prefisso_quota = 'pagamento'
    verbo = 'pagamento'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conto'].label = 'Conto banca / cassa'
        self.fields['conto'].empty_label = 'Scegli il conto da cui è uscito il denaro…'
        self.fields['importo'].label = 'Importo pagato (€)'
        self.fields['fatture'].label = 'Fatture pagate'
        self.fields['controparte'].label = 'Fornitore pagato'
        self.fields['controparte'].error_messages['required'] = (
            'Scegli prima il fornitore: le sue fatture aperte compariranno qui sotto.'
        )

    def get_fatture_queryset(self):
        return fatture_da_pagare()

    def numero_fattura(self, fattura):
        return fattura.numero_fattura

    def controparte_di(self, fattura):
        return str(fattura.fornitore_id)

    def nome_controparte(self, valore):
        from anagrafica_r2.models import Fornitore

        try:
            return Fornitore.objects.get(pk=valore).ragione_sociale
        except (Fornitore.DoesNotExist, ValueError):
            return ''
