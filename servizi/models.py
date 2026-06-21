from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from core.mixins.model_mixins import AllegatiMixin


def _next_numero_distinta():
    anno = timezone.now().year
    prefix = f"DIS-{anno}-"
    ultimo = Distinta.objects.filter(numero__startswith=prefix).order_by("numero").last()
    if ultimo:
        try:
            n = int(ultimo.numero.split("-")[-1]) + 1
        except ValueError:
            n = 1
    else:
        n = 1
    return f"{prefix}{n:04d}"


def _next_numero_ods():
    anno = timezone.now().year
    prefix = f"ODS-{anno}-"
    ultimo = ODS.objects.filter(numero__startswith=prefix).order_by("numero").last()
    if ultimo:
        try:
            n = int(ultimo.numero.split("-")[-1]) + 1
        except ValueError:
            n = 1
    else:
        n = 1
    return f"{prefix}{n:04d}"


class Servizio(AllegatiMixin, models.Model):

    nome             = models.CharField(max_length=200, verbose_name="Nome servizio")
    descrizione      = models.TextField(blank=True, verbose_name="Descrizione")
    tariffa_cartello = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        verbose_name="Tariffa di cartello",
        help_text="Prezzo di riferimento se non specificato nel contratto o nell'ODS",
    )
    attivo           = models.BooleanField(default=True, verbose_name="Attivo")
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Servizio"
        verbose_name_plural = "Servizi"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return reverse("servizi:servizio_detail", kwargs={"pk": self.pk})


class Contratto(AllegatiMixin, models.Model):

    class Periodicita(models.TextChoices):
        MENSILE     = "mensile",     "Mensile"
        BIMESTRALE  = "bimestrale",  "Bimestrale"
        TRIMESTRALE = "trimestrale", "Trimestrale"
        SEMESTRALE  = "semestrale",  "Semestrale"
        ANNUALE     = "annuale",     "Annuale"
        A_CHIAMATA  = "a_chiamata",  "A chiamata"

    class Stato(models.TextChoices):
        ATTIVO    = "attivo",    "Attivo"
        SOSPESO   = "sospeso",   "Sospeso"
        SCADUTO   = "scaduto",   "Scaduto"
        ANNULLATO = "annullato", "Annullato"

    cliente        = models.ForeignKey(
        "anagrafica.Azienda", on_delete=models.PROTECT,
        related_name="contratti", verbose_name="Cliente",
    )
    periodicita    = models.CharField(
        max_length=20, choices=Periodicita.choices, default=Periodicita.MENSILE,
        verbose_name="Periodicità",
    )
    data_inizio    = models.DateField(verbose_name="Data inizio", default=timezone.localdate)
    data_fine      = models.DateField(null=True, blank=True, verbose_name="Data fine")
    stato          = models.CharField(
        max_length=20, choices=Stato.choices, default=Stato.ATTIVO,
        verbose_name="Stato",
    )
    note           = models.TextField(blank=True, verbose_name="Note")
    created_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="contratti_creati",
    )
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contratto"
        verbose_name_plural = "Contratti"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.cliente} — {self.get_periodicita_display()}"

    def get_absolute_url(self):
        return reverse("servizi:contratto_detail", kwargs={"pk": self.pk})


class ContrattoFiliale(models.Model):
    """Riga per singola sede — creata automaticamente al salvataggio del contratto."""

    contratto       = models.ForeignKey(
        Contratto, on_delete=models.CASCADE, related_name="filiali_contratto",
    )
    filiale         = models.ForeignKey(
        "anagrafica.Filiale", on_delete=models.CASCADE, related_name="contratti_filiale",
    )
    note            = models.CharField(max_length=300, blank=True, verbose_name="Note sede")

    class Meta:
        unique_together = [("contratto", "filiale")]
        verbose_name = "Sede contratto"
        verbose_name_plural = "Sedi contratto"

    def __str__(self):
        return f"{self.contratto} / {self.filiale.nome}"


class ContrattoFilialeRiga(models.Model):
    """
    Prezzo specifico per sede: override di un servizio del contratto padre
    o servizio aggiuntivo valido solo per questa filiale.
    """
    contratto_filiale = models.ForeignKey(
        ContrattoFiliale, on_delete=models.CASCADE, related_name="righe_sede",
    )
    servizio  = models.ForeignKey(
        Servizio, on_delete=models.PROTECT, related_name="righe_filiale_contratto",
    )
    prezzo    = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Prezzo",
    )

    class Meta:
        unique_together = [("contratto_filiale", "servizio")]
        verbose_name = "Riga sede contratto"
        verbose_name_plural = "Righe sede contratto"
        ordering = ["servizio__nome"]

    def __str__(self):
        return f"{self.servizio} — € {self.prezzo}"


class ContrattoRiga(models.Model):
    """Un servizio con il relativo prezzo all'interno di un contratto."""

    contratto = models.ForeignKey(
        Contratto, on_delete=models.CASCADE, related_name="righe",
    )
    servizio  = models.ForeignKey(
        Servizio, on_delete=models.PROTECT, related_name="righe_contratto",
    )
    prezzo    = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Prezzo",
    )

    class Meta:
        unique_together = [("contratto", "servizio")]
        verbose_name = "Riga contratto"
        verbose_name_plural = "Righe contratto"
        ordering = ["servizio__nome"]

    def __str__(self):
        return f"{self.servizio} — € {self.prezzo}"


class ODS(AllegatiMixin, models.Model):

    class Stato(models.TextChoices):
        DA_ESPLETARE = "da_espletare", "Da espletare"
        PROGRAMMATO  = "programmato",  "Programmato"
        COMPLETATO   = "completato",   "Completato"
        FATTURATO    = "fatturato",    "Fatturato"
        ANNULLATO    = "annullato",    "Annullato"

    numero            = models.CharField(max_length=30, unique=True, blank=True)

    filiale           = models.ForeignKey(
        "anagrafica.Filiale", on_delete=models.PROTECT,
        null=True, blank=True, related_name="ods", verbose_name="Sede cliente",
    )
    privato           = models.ForeignKey(
        "anagrafica.Privato", on_delete=models.PROTECT,
        null=True, blank=True, related_name="ods", verbose_name="Cliente privato",
    )
    data_servizio     = models.DateField(verbose_name="Data servizio", default=timezone.localdate)
    ora_inizio        = models.TimeField(null=True, blank=True, verbose_name="Ora inizio")
    ora_fine          = models.TimeField(null=True, blank=True, verbose_name="Ora fine")
    stato             = models.CharField(
        max_length=20, choices=Stato.choices, default=Stato.DA_ESPLETARE,
        verbose_name="Stato",
    )
    tecnico           = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="ods_assegnati", verbose_name="Tecnico",
    )
    assistente        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="ods_assistiti", verbose_name="Assistente",
    )
    distinta  = models.ForeignKey(
        "Distinta", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="ods_set", verbose_name="Distinta",
    )
    modalita_pagamento = models.CharField(
        max_length=20,
        choices=[
            ("contanti",      "Contanti"),
            ("carta",         "Carta"),
            ("paypal",        "PayPal"),
            ("non_incassato", "Non incassato"),
        ],
        null=True, blank=True, verbose_name="Modalità pagamento",
    )
    incasso_al_servizio = models.BooleanField(
        default=False, verbose_name="Incasso al servizio",
        help_text="Il pagamento va riscosso al momento del servizio (non fatturato)",
    )
    incassato           = models.BooleanField(default=False, verbose_name="Incassato")
    data_incasso        = models.DateField(null=True, blank=True, verbose_name="Data incasso")
    importo_incassato   = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Importo incassato",
    )
    note_intervento   = models.TextField(blank=True, verbose_name="Note intervento")
    created_by        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="ods_creati",
    )
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ordine di Servizio"
        verbose_name_plural = "Ordini di Servizio"
        ordering = ["-data_servizio", "-created_at"]

    def __str__(self):
        return self.numero

    def get_absolute_url(self):
        return reverse("servizi:ods_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = _next_numero_ods()
        super().save(*args, **kwargs)

    def clean(self):
        if not self.filiale and not self.privato:
            raise ValidationError("Seleziona una sede cliente o un cliente privato.")
        if self.filiale and self.privato:
            raise ValidationError("Seleziona solo una sede oppure un privato, non entrambi.")

    @property
    def zona(self):
        if self.filiale_id:
            return self.filiale.zona
        if self.privato_id:
            return self.privato.zona
        return ""

    @property
    def cliente_display(self):
        if self.filiale:
            return f"{self.filiale.cliente} — {self.filiale.nome}"
        return str(self.privato)

    @property
    def is_privato(self):
        return self.privato_id is not None

    @property
    def indirizzo_servizio(self):
        if self.filiale_id:
            return self.filiale.indirizzo
        if self.privato_id:
            return self.privato.indirizzo
        return ""

    @property
    def citta_servizio(self):
        if self.filiale_id:
            return self.filiale.citta
        if self.privato_id:
            return self.privato.citta
        return ""

    @property
    def servizio_principale(self):
        try:
            return self.righe.all()[0].servizio
        except IndexError:
            return None

    @property
    def prezzo_totale(self):
        total = sum((r.prezzo for r in self.righe.all() if r.prezzo), Decimal("0.00"))
        return total if total else None


class ODSRiga(models.Model):

    ods               = models.ForeignKey(
        ODS, on_delete=models.CASCADE, related_name="righe", verbose_name="ODS",
    )
    ordine            = models.PositiveSmallIntegerField(default=0, verbose_name="Ordine")
    servizio          = models.ForeignKey(
        Servizio, on_delete=models.PROTECT, related_name="righe_ods", verbose_name="Servizio",
    )
    prezzo            = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Prezzo",
    )
    contratto_filiale = models.ForeignKey(
        ContrattoFiliale, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="righe_ods", verbose_name="Contratto applicato",
    )
    note              = models.CharField(max_length=300, blank=True, verbose_name="Note")

    class Meta:
        verbose_name = "Riga ODS"
        verbose_name_plural = "Righe ODS"
        ordering = ["ordine", "pk"]

    def __str__(self):
        return f"{self.ods.numero} — {self.servizio}"


class Distinta(models.Model):

    class Stato(models.TextChoices):
        APERTA = "aperta", "Aperta"
        CHIUSA  = "chiusa",  "Chiusa"

    numero    = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Numero")
    data      = models.DateField(verbose_name="Data servizi")
    tecnico   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="distinte", verbose_name="Tecnico",
    )
    assistente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="distinte_assistente",
        verbose_name="Assistente",
    )
    mezzo     = models.ForeignKey(
        "cespiti.Automezzo", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="distinte_mezzo",
        verbose_name="Mezzo",
    )
    stato     = models.CharField(
        max_length=10, choices=Stato.choices, default=Stato.APERTA, verbose_name="Stato",
    )
    nota             = models.TextField(blank=True, verbose_name="Note")
    importo_ricevuto = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Importo ricevuto",
        help_text="Contante/pagamenti effettivamente ricevuti dal tecnico all'ufficio",
    )
    chiusa_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="distinte_chiuse",
        verbose_name="Chiusa da",
    )
    chiusa_il = models.DateTimeField(null=True, blank=True, verbose_name="Chiusa il")
    creata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="distinte_create",
    )
    creata_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Distinta"
        verbose_name_plural = "Distinte"
        ordering = ["-data", "-creata_il"]

    def __str__(self):
        nome = self.tecnico.get_full_name() or self.tecnico.username
        return f"{self.numero} — {self.data:%d/%m/%Y} — {nome}"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = _next_numero_distinta()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("servizi:distinta_detail", kwargs={"pk": self.pk})

    @property
    def n_completati(self):
        return (
            self.ods_set.filter(stato="completato").count() +
            self.condomini_set.filter(stato="completato").count()
        )

    @property
    def n_totale(self):
        return self.ods_set.count() + self.condomini_set.count()


class ConsumoMateriale(models.Model):

    riga     = models.ForeignKey(
        ODSRiga, on_delete=models.CASCADE, related_name="consumi", verbose_name="Riga ODS",
    )
    prodotto = models.ForeignKey(
        "magazzino.Prodotto", on_delete=models.PROTECT,
        related_name="consumi_servizi", verbose_name="Prodotto",
    )
    quantita   = models.DecimalField(
        max_digits=10, decimal_places=3, default=1, verbose_name="Quantità",
    )
    confermato = models.BooleanField(
        default=False, verbose_name="Confermato",
        help_text="False = quantità prevista (non scala stock); True = effettivo (scala ScortaMezzo)",
    )
    note       = models.CharField(max_length=300, blank=True, verbose_name="Note")

    class Meta:
        verbose_name = "Consumo materiale"
        verbose_name_plural = "Consumi materiali"

    def __str__(self):
        return f"{self.prodotto} ×{self.quantita}"

    def _mezzo_tecnico(self):
        from cespiti.models import Automezzo
        ods = self.riga.ods
        # Priorità: mezzo agganciato alla distinta (scelta esplicita al momento della creazione)
        if ods.distinta_id:
            row = Distinta.objects.filter(pk=ods.distinta_id).values("mezzo_id").first()
            if row and row["mezzo_id"]:
                return Automezzo.objects.filter(pk=row["mezzo_id"]).first()
        # Fallback: mezzo assegnato al tecnico in anagrafica
        if ods.tecnico_id:
            return Automezzo.objects.filter(assegnato_a_id=ods.tecnico_id, attivo=True).first()
        return None

    def save(self, *args, **kwargs):
        # Scala ScortaMezzo solo sui consumi confermati
        old_qty = Decimal("0")
        old_confermato = False
        if self.pk:
            old = ConsumoMateriale.objects.filter(pk=self.pk).values_list(
                "quantita", "confermato"
            ).first()
            if old:
                old_qty, old_confermato = old
                old_qty = old_qty or Decimal("0")
        super().save(*args, **kwargs)
        # Calcola delta effettivo sullo stock
        qty_confermata_prima = old_qty if old_confermato else Decimal("0")
        qty_confermata_dopo  = self.quantita if self.confermato else Decimal("0")
        delta = qty_confermata_dopo - qty_confermata_prima
        if delta:
            mezzo = self._mezzo_tecnico()
            if mezzo:
                from magazzino.models import ScortaMezzo
                from django.db.models import F
                sm, _ = ScortaMezzo.objects.get_or_create(
                    mezzo=mezzo, prodotto_id=self.prodotto_id,
                    defaults={"quantita": Decimal("0")},
                )
                ScortaMezzo.objects.filter(pk=sm.pk).update(
                    quantita=F("quantita") - delta
                )

    def delete(self, *args, **kwargs):
        mezzo = self._mezzo_tecnico() if self.confermato else None
        qty = self.quantita if self.confermato else Decimal("0")
        prodotto_id = self.prodotto_id
        super().delete(*args, **kwargs)
        if mezzo and qty:
            from magazzino.models import ScortaMezzo
            from django.db.models import F
            sm = ScortaMezzo.objects.filter(
                mezzo=mezzo, prodotto_id=prodotto_id
            ).first()
            if sm:
                ScortaMezzo.objects.filter(pk=sm.pk).update(
                    quantita=F("quantita") + qty
                )


# ── CONDOMINI ODS ─────────────────────────────────────────────

def _next_numero_condominio():
    anno = timezone.now().year
    prefix = f"CON-{anno}-"
    ultimo = CondominioODS.objects.filter(numero__startswith=prefix).order_by("numero").last()
    if ultimo:
        try:
            n = int(ultimo.numero.split("-")[-1]) + 1
        except ValueError:
            n = 1
    else:
        n = 1
    return f"{prefix}{n:04d}"


class CondominioStabile(models.Model):
    """Anagrafica stabile condominiale con unità abitative ricorrenti."""
    nome       = models.CharField(max_length=200, verbose_name="Nome stabile")
    indirizzo  = models.CharField(max_length=300, verbose_name="Indirizzo")
    prezzo_base = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Prezzo base per unità",
        help_text="Prezzo predefinito quando si crea un ODS da questo stabile",
    )
    note = models.TextField(blank=True)

    class Meta:
        verbose_name = "Stabile"
        verbose_name_plural = "Stabili"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} — {self.indirizzo}"

    def get_absolute_url(self):
        return reverse("servizi:stabile_detail", kwargs={"pk": self.pk})


class UnitaAbitativaBase(models.Model):
    """Unità abitativa fissa di uno stabile (template per gli ODS)."""
    stabile  = models.ForeignKey(
        CondominioStabile, on_delete=models.CASCADE, related_name="unita",
    )
    nome     = models.CharField(max_length=200, verbose_name="Nome / Intestatario")
    importo_override = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Importo specifico",
        help_text="Lascia vuoto per usare il prezzo base dello stabile",
    )

    class Meta:
        verbose_name = "Unità abitativa base"
        verbose_name_plural = "Unità abitative base"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class CondominioODS(models.Model):

    class Stato(models.TextChoices):
        DA_ESPLETARE = "da_espletare", "Da espletare"
        COMPLETATO   = "completato",   "Completato"
        ANNULLATO    = "annullato",    "Annullato"

    stabile    = models.ForeignKey(
        CondominioStabile, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="ods_set", verbose_name="Stabile",
    )
    numero     = models.CharField(max_length=30, unique=True, blank=True)
    titolo     = models.CharField(max_length=200, verbose_name="Titolo servizio")
    indirizzo  = models.CharField(max_length=300, verbose_name="Indirizzo")
    data       = models.DateField(verbose_name="Data servizio")
    ora        = models.TimeField(null=True, blank=True, verbose_name="Ora")
    prezzo_base = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Prezzo base per unità",
    )
    stato      = models.CharField(
        max_length=20, choices=Stato.choices, default=Stato.DA_ESPLETARE, verbose_name="Stato",
    )
    distinta   = models.ForeignKey(
        "Distinta", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="condomini_set", verbose_name="Distinta",
    )
    tecnico    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="condomini_tecnico", verbose_name="Tecnico",
    )
    assistente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="condomini_assistente", verbose_name="Assistente",
    )
    note       = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="condomini_creati",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Condominio ODS"
        verbose_name_plural = "Condomini ODS"
        ordering = ["-data", "-created_at"]

    def __str__(self):
        return f"{self.numero} — {self.titolo}"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = _next_numero_condominio()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("servizi:condominio_detail", kwargs={"pk": self.pk})

    @property
    def totale_da_incassare(self):
        return sum(
            u.importo_effettivo for u in self.unita.all() if u.servizio_effettuato
        )

    @property
    def totale_incassato(self):
        return sum(
            u.importo_effettivo for u in self.unita.all() if u.incasso_effettuato
        )


class RigaUnitaAbitativa(models.Model):
    condominio          = models.ForeignKey(
        CondominioODS, on_delete=models.CASCADE, related_name="unita",
    )
    nome                = models.CharField(max_length=200, verbose_name="Nome / Intestatario")
    servizio_effettuato = models.BooleanField(default=False, verbose_name="Servizio effettuato")
    incasso_effettuato  = models.BooleanField(default=False, verbose_name="Incasso effettuato")
    importo_da_incassare = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Importo da incassare",
        help_text="Se vuoto usa il prezzo base del condominio",
    )

    class Meta:
        verbose_name = "Unità abitativa"
        verbose_name_plural = "Unità abitative"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def importo_effettivo(self):
        if self.importo_da_incassare is not None:
            return self.importo_da_incassare
        return self.condominio.prezzo_base


class RigaProdottoCondominio(models.Model):
    condominio = models.ForeignKey(
        CondominioODS, on_delete=models.CASCADE, related_name="prodotti",
    )
    prodotto   = models.ForeignKey(
        "magazzino.Prodotto", on_delete=models.PROTECT, related_name="righe_condominio",
    )
    quantita   = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("1.000"),
        verbose_name="Quantità",
    )
    confermato = models.BooleanField(
        default=False, verbose_name="Confermato",
        help_text="True = quantità già scalata da ScortaMezzo",
    )

    class Meta:
        verbose_name = "Prodotto condominio"
        verbose_name_plural = "Prodotti condominio"
        ordering = ["prodotto__nome_prodotto"]

    def __str__(self):
        return f"{self.prodotto} × {self.quantita}"

    def _mezzo_condominio(self):
        c = self.condominio
        if c.distinta_id:
            row = Distinta.objects.filter(pk=c.distinta_id).values("mezzo_id").first()
            if row and row["mezzo_id"]:
                from cespiti.models import Automezzo
                return Automezzo.objects.filter(pk=row["mezzo_id"]).first()
        if c.tecnico_id:
            from cespiti.models import Automezzo
            return Automezzo.objects.filter(assegnato_a_id=c.tecnico_id, attivo=True).first()
        return None

    def save(self, *args, **kwargs):
        old_qty = Decimal("0")
        old_confermato = False
        if self.pk:
            old = RigaProdottoCondominio.objects.filter(pk=self.pk).values_list(
                "quantita", "confermato"
            ).first()
            if old:
                old_qty, old_confermato = old
                old_qty = old_qty or Decimal("0")
        super().save(*args, **kwargs)
        qty_prima = old_qty if old_confermato else Decimal("0")
        qty_dopo  = self.quantita if self.confermato else Decimal("0")
        delta = qty_dopo - qty_prima
        if delta:
            mezzo = self._mezzo_condominio()
            if mezzo:
                from magazzino.models import ScortaMezzo
                from django.db.models import F
                sm, _ = ScortaMezzo.objects.get_or_create(
                    mezzo=mezzo, prodotto=self.prodotto,
                    defaults={"quantita": Decimal("0")},
                )
                ScortaMezzo.objects.filter(pk=sm.pk).update(quantita=F("quantita") - delta)

    def delete(self, *args, **kwargs):
        if self.confermato:
            mezzo = self._mezzo_condominio()
            if mezzo:
                from magazzino.models import ScortaMezzo
                from django.db.models import F
                sm = ScortaMezzo.objects.filter(mezzo=mezzo, prodotto=self.prodotto).first()
                if sm:
                    ScortaMezzo.objects.filter(pk=sm.pk).update(
                        quantita=F("quantita") + self.quantita
                    )
        super().delete(*args, **kwargs)
