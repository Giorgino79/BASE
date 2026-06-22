from django import forms
from django.utils import timezone
from anagrafica_r2.models import Azienda, Privato
from servizi.models import CondominioStabile, ODS

W = {"class": "form-control form-control-sm"}
W_SEL = {"class": "form-select form-select-sm"}
W_DATE = {"class": "form-control form-control-sm", "type": "date"}


TIPO_CHOICES = [
    ("azienda",    "Cliente aziendale"),
    ("privato",    "Cliente privato"),
    ("condominio", "Condominio / Stabile"),
]


class RicercaFatturazioneForm(forms.Form):
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        initial="azienda",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label="Tipo cliente",
    )
    azienda = forms.ModelChoiceField(
        queryset=Azienda.objects.filter(attivo=True).order_by("ragione_sociale"),
        required=False,
        empty_label="— Seleziona cliente —",
        label="Cliente aziendale",
        widget=forms.Select(attrs=W_SEL),
    )
    privato = forms.ModelChoiceField(
        queryset=Privato.objects.filter(attivo=True).order_by("cognome", "nome"),
        required=False,
        empty_label="— Seleziona privato —",
        label="Cliente privato",
        widget=forms.Select(attrs=W_SEL),
    )
    stabile = forms.ModelChoiceField(
        queryset=CondominioStabile.objects.order_by("nome"),
        required=False,
        empty_label="— Seleziona stabile —",
        label="Stabile / Condominio",
        widget=forms.Select(attrs=W_SEL),
    )
    data_da = forms.DateField(
        required=False,
        label="Data dal",
        widget=forms.DateInput(attrs=W_DATE),
    )
    data_a = forms.DateField(
        required=False,
        label="Data al",
        widget=forms.DateInput(attrs=W_DATE),
    )
    solo_completati = forms.BooleanField(
        required=False,
        initial=True,
        label="Solo completati",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean(self):
        cd = super().clean()
        tipo = cd.get("tipo")
        if tipo == "azienda" and not cd.get("azienda"):
            self.add_error("azienda", "Seleziona un cliente aziendale.")
        if tipo == "privato" and not cd.get("privato"):
            self.add_error("privato", "Seleziona un cliente privato.")
        if tipo == "condominio" and not cd.get("stabile"):
            self.add_error("stabile", "Seleziona uno stabile.")
        da = cd.get("data_da")
        a = cd.get("data_a")
        if da and a and da > a:
            self.add_error("data_a", "La data di fine deve essere successiva alla data di inizio.")
        return cd


INCASSO_CHOICES = [
    ("tutti",        "Tutte le fatture"),
    ("da_incassare", "Da incassare"),
    ("incassate",    "Incassate"),
]

TIPO_CLIENTE_CHOICES = [
    ("",       "— Tutti i tipi —"),
    ("azienda", "Cliente aziendale"),
    ("privato", "Cliente privato"),
]


class RicercaFattureForm(forms.Form):
    tipo_cliente = forms.ChoiceField(
        choices=TIPO_CLIENTE_CHOICES,
        required=False,
        label="Tipo cliente",
        widget=forms.Select(attrs=W_SEL),
    )
    azienda = forms.ModelChoiceField(
        queryset=Azienda.objects.filter(attivo=True).order_by("ragione_sociale"),
        required=False,
        empty_label="— Seleziona cliente —",
        label="Cliente aziendale",
        widget=forms.Select(attrs=W_SEL),
    )
    privato = forms.ModelChoiceField(
        queryset=Privato.objects.filter(attivo=True).order_by("cognome", "nome"),
        required=False,
        empty_label="— Seleziona privato —",
        label="Cliente privato",
        widget=forms.Select(attrs=W_SEL),
    )
    data_da = forms.DateField(
        required=False,
        label="Data servizio dal",
        widget=forms.DateInput(attrs=W_DATE),
    )
    data_a = forms.DateField(
        required=False,
        label="Data servizio al",
        widget=forms.DateInput(attrs=W_DATE),
    )
    incasso = forms.ChoiceField(
        choices=INCASSO_CHOICES,
        initial="tutti",
        required=False,
        label="Stato incasso",
        widget=forms.Select(attrs=W_SEL),
    )

    def clean(self):
        cd = super().clean()
        da = cd.get("data_da")
        a  = cd.get("data_a")
        if da and a and da > a:
            self.add_error("data_a", "La data di fine deve essere successiva alla data di inizio.")
        return cd


TIPO_CLIENTE_LIBERA = [
    ("azienda", "Cliente aziendale"),
    ("privato", "Cliente privato"),
]


class FatturaLiberaForm(forms.Form):
    tipo_cliente = forms.ChoiceField(
        choices=TIPO_CLIENTE_LIBERA,
        initial="azienda",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label="Tipo cliente",
    )
    azienda = forms.ModelChoiceField(
        queryset=Azienda.objects.filter(attivo=True).order_by("ragione_sociale"),
        required=False,
        empty_label="— Seleziona cliente —",
        label="Cliente aziendale",
        widget=forms.Select(attrs=W_SEL),
    )
    privato = forms.ModelChoiceField(
        queryset=Privato.objects.filter(attivo=True).order_by("cognome", "nome"),
        required=False,
        empty_label="— Seleziona privato —",
        label="Cliente privato",
        widget=forms.Select(attrs=W_SEL),
    )
    data_emissione = forms.DateField(
        initial=timezone.localdate,
        label="Data emissione",
        widget=forms.DateInput(attrs=W_DATE),
    )
    note_pagamento = forms.CharField(
        required=False,
        label="Condizioni di pagamento",
        widget=forms.TextInput(attrs=W),
    )
    note = forms.CharField(
        required=False,
        label="Note generali",
        widget=forms.Textarea(attrs={**W, "rows": "2"}),
    )

    def clean(self):
        cd = super().clean()
        tipo = cd.get("tipo_cliente")
        if tipo == "azienda" and not cd.get("azienda"):
            self.add_error("azienda", "Seleziona un cliente aziendale.")
        if tipo == "privato" and not cd.get("privato"):
            self.add_error("privato", "Seleziona un cliente privato.")
        return cd


TIPO_NC_CHOICES = [
    ("",         "— Tutti i tipi —"),
    ("totale",   "Totale"),
    ("parziale", "Parziale"),
]


class RicercaNoteCreditoForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Cerca",
        widget=forms.TextInput(attrs={**W, "placeholder": "N° NC, n° fattura, destinatario…"}),
    )
    tipo = forms.ChoiceField(
        choices=TIPO_NC_CHOICES,
        required=False,
        label="Tipo",
        widget=forms.Select(attrs=W_SEL),
    )
    data_da = forms.DateField(
        required=False,
        label="Data emissione dal",
        widget=forms.DateInput(attrs=W_DATE),
    )
    data_a = forms.DateField(
        required=False,
        label="Data emissione al",
        widget=forms.DateInput(attrs=W_DATE),
    )

    def clean(self):
        cd = super().clean()
        da = cd.get("data_da")
        a  = cd.get("data_a")
        if da and a and da > a:
            self.add_error("data_a", "La data di fine deve essere successiva alla data di inizio.")
        return cd
