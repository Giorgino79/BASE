"""
Modelli per il sistema di gestione buste paga
Conforme al diritto del lavoro italiano
"""

from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date

User = get_user_model()


class CCNL(models.Model):
    """Contratto Collettivo Nazionale del Lavoro"""

    TIPO_CHOICES = [
        ("METALMECCANICI", "Metalmeccanici"),
        ("COMMERCIO", "Commercio e Terziario"),
        ("EDILIZIA", "Edilizia"),
        ("CHIMICI", "Chimici"),
        ("TRASPORTI", "Trasporti e Logistica"),
        ("PUBBLICO_IMPIEGO", "Pubblico Impiego"),
        ("SANITA", "Sanità Privata"),
        ("TURISMO", "Turismo e Pubblici Esercizi"),
        ("ALTRO", "Altro"),
    ]

    nome = models.CharField(max_length=200, verbose_name="Nome CCNL")
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, verbose_name="Tipo")
    data_inizio_validita = models.DateField(verbose_name="Data Inizio Validità")
    data_fine_validita = models.DateField(
        null=True, blank=True, verbose_name="Data Fine Validità"
    )

    # Parametri ferie e permessi
    giorni_ferie_annui = models.IntegerField(
        default=26, verbose_name="Giorni Ferie Annui", help_text="4 settimane + 2 giorni"
    )
    ore_rol_annue = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=88,
        verbose_name="Ore ROL Annue",
    )
    ore_permessi_retribuiti_annui = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=32,
        verbose_name="Ore Permessi Retribuiti Annui",
    )

    # Parametri straordinari
    percentuale_straordinario_feriale = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15,
        verbose_name="% Straordinario Feriale",
    )
    percentuale_straordinario_festivo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30,
        verbose_name="% Straordinario Festivo",
    )
    percentuale_straordinario_notturno = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50,
        verbose_name="% Straordinario Notturno",
    )

    # Tredicesima e quattordicesima
    ha_tredicesima = models.BooleanField(default=True, verbose_name="Ha Tredicesima")
    ha_quattordicesima = models.BooleanField(
        default=False, verbose_name="Ha Quattordicesima"
    )
    maturazione_quattordicesima = models.CharField(
        max_length=20,
        choices=[
            ("GIUGNO", "Giugno"),
            ("LUGLIO", "Luglio"),
            ("DICEMBRE", "Dicembre"),
        ],
        null=True,
        blank=True,
        verbose_name="Maturazione Quattordicesima",
    )

    # Scatti di anzianità
    ha_scatti_anzianita = models.BooleanField(
        default=True, verbose_name="Ha Scatti Anzianità"
    )
    anni_per_scatto = models.IntegerField(
        default=2, verbose_name="Anni per Scatto"
    )
    importo_scatto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Importo Scatto €",
    )
    numero_massimo_scatti = models.IntegerField(
        default=10, verbose_name="Numero Massimo Scatti"
    )

    note = models.TextField(blank=True, verbose_name="Note")

    class Meta:
        verbose_name = "CCNL"
        verbose_name_plural = "CCNL"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class LivelloInquadramento(models.Model):
    """Livelli di inquadramento per ogni CCNL"""

    ccnl = models.ForeignKey(
        CCNL, on_delete=models.CASCADE, related_name="livelli", verbose_name="CCNL"
    )
    codice = models.CharField(
        max_length=20, verbose_name="Codice", help_text="es. 1, 2, 3 o A1, B2, etc."
    )
    descrizione = models.CharField(
        max_length=200,
        verbose_name="Descrizione",
        help_text="es. Operaio generico, Impiegato di 3° livello",
    )
    paga_base_mensile = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Paga Base Mensile €",
    )
    ore_settimanali_standard = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=40,
        verbose_name="Ore Settimanali Standard",
    )

    class Meta:
        unique_together = ["ccnl", "codice"]
        ordering = ["ccnl", "codice"]
        verbose_name = "Livello Inquadramento"
        verbose_name_plural = "Livelli Inquadramento"

    def __str__(self):
        return f"{self.ccnl.nome} - Livello {self.codice} ({self.descrizione})"


class ElementoRetributivo(models.Model):
    """Elementi retributivi configurabili per CCNL"""

    TIPO_CALCOLO_CHOICES = [
        ("FISSO", "Importo Fisso"),
        ("PERCENTUALE_PAGA_BASE", "Percentuale su Paga Base"),
        ("PERCENTUALE_RETRIBUZIONE", "Percentuale su Retribuzione Totale"),
        ("ORARIO", "Calcolato su Ore"),
    ]

    NATURA_CHOICES = [
        ("IMPONIBILE", "Imponibile (fiscale e contributivo)"),
        ("NON_IMPONIBILE", "Non Imponibile"),
        ("SOLO_FISCALE", "Imponibile solo fiscale"),
        ("SOLO_CONTRIBUTIVO", "Imponibile solo contributivo"),
    ]

    ccnl = models.ForeignKey(
        CCNL,
        on_delete=models.CASCADE,
        related_name="elementi_retributivi",
        verbose_name="CCNL",
    )
    nome = models.CharField(
        max_length=100,
        verbose_name="Nome",
        help_text="es. Contingenza, EDR, Indennità turno",
    )
    codice = models.CharField(max_length=20, verbose_name="Codice")
    tipo_calcolo = models.CharField(
        max_length=30, choices=TIPO_CALCOLO_CHOICES, verbose_name="Tipo Calcolo"
    )
    valore = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valore",
        help_text="Importo fisso o percentuale",
    )
    natura = models.CharField(
        max_length=20,
        choices=NATURA_CHOICES,
        default="IMPONIBILE",
        verbose_name="Natura",
    )
    incluso_tfr = models.BooleanField(default=True, verbose_name="Incluso in TFR")
    incluso_tredicesima = models.BooleanField(
        default=True, verbose_name="Incluso in Tredicesima"
    )
    attivo = models.BooleanField(default=True, verbose_name="Attivo")

    class Meta:
        unique_together = ["ccnl", "codice"]
        verbose_name = "Elemento Retributivo"
        verbose_name_plural = "Elementi Retributivi"
        ordering = ["ccnl", "codice"]

    def __str__(self):
        return f"{self.ccnl.nome} - {self.nome}"


class DatiContrattualiPayroll(models.Model):
    """Estensione dati contrattuali per payroll (OneToOne con User)"""

    TIPO_CONTRATTO_CHOICES = [
        ("TEMPO_INDETERMINATO", "Tempo Indeterminato"),
        ("TEMPO_DETERMINATO", "Tempo Determinato"),
        ("APPRENDISTATO", "Apprendistato"),
        ("SOMMINISTRAZIONE", "Somministrazione"),
        ("PART_TIME", "Part Time"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="dati_payroll",
        verbose_name="Dipendente",
    )
    ccnl = models.ForeignKey(
        CCNL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="CCNL Applicato",
    )
    livello = models.ForeignKey(
        LivelloInquadramento,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Livello Inquadramento",
    )
    tipo_contratto = models.CharField(
        max_length=30,
        choices=TIPO_CONTRATTO_CHOICES,
        default="TEMPO_INDETERMINATO",
        verbose_name="Tipo Contratto",
    )
    data_fine_contratto = models.DateField(
        null=True, blank=True, verbose_name="Data Fine Contratto"
    )
    data_cessazione = models.DateField(
        null=True, blank=True, verbose_name="Data Cessazione"
    )
    ore_settimanali = models.DecimalField(
        max_digits=5, decimal_places=2, default=40, verbose_name="Ore Settimanali"
    )
    percentuale_part_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
        verbose_name="% Part Time",
        help_text="100 = full time",
    )
    superminimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Superminimo €",
    )
    aliquota_addizionale_regionale = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        verbose_name="Addizionale Regionale %",
    )
    aliquota_addizionale_comunale = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        verbose_name="Addizionale Comunale %",
    )
    detrazione_lavoro_dipendente = models.BooleanField(
        default=True, verbose_name="Detrazione Lavoro Dipendente"
    )
    numero_figli_a_carico = models.IntegerField(
        default=0, verbose_name="Numero Figli a Carico"
    )
    coniuge_a_carico = models.BooleanField(
        default=False, verbose_name="Coniuge a Carico"
    )
    altri_familiari_a_carico = models.IntegerField(
        default=0, verbose_name="Altri Familiari a Carico"
    )
    iban = models.CharField(max_length=27, blank=True, verbose_name="IBAN")

    class Meta:
        verbose_name = "Dati Contrattuali Payroll"
        verbose_name_plural = "Dati Contrattuali Payroll"

    def __str__(self):
        return f"Dati Payroll - {self.user.get_full_name()}"

    def calcola_scatti_anzianita(self, alla_data=None):
        """Calcola il numero di scatti di anzianità maturati"""
        if not self.ccnl or not self.ccnl.ha_scatti_anzianita:
            return 0
        if not self.user.data_assunzione:
            return 0
        data_riferimento = alla_data or date.today()
        anni_servizio = (data_riferimento - self.user.data_assunzione).days / 365.25
        scatti = int(anni_servizio / self.ccnl.anni_per_scatto)
        return min(scatti, self.ccnl.numero_massimo_scatti)

    def calcola_paga_oraria(self):
        """Calcola la paga oraria base"""
        if not self.livello:
            return Decimal("0")
        ore_mensili = (self.ore_settimanali * Decimal("52")) / Decimal("12")
        if ore_mensili == 0:
            return Decimal("0")
        importo_scatti = self.calcola_scatti_anzianita() * (
            self.ccnl.importo_scatto if self.ccnl else Decimal("0")
        )
        paga_mensile = self.livello.paga_base_mensile + importo_scatti + self.superminimo
        return paga_mensile / ore_mensili


class BustaPaga(models.Model):
    """Busta paga mensile"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="buste_paga",
        verbose_name="Dipendente",
    )
    mese = models.IntegerField(verbose_name="Mese")  # 1-12
    anno = models.IntegerField(verbose_name="Anno")
    data_elaborazione = models.DateField(
        auto_now_add=True, verbose_name="Data Elaborazione"
    )

    # Ore lavorate
    ore_ordinarie = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="Ore Ordinarie"
    )
    ore_straordinario_feriale = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="Ore Straordinario Feriale"
    )
    ore_straordinario_festivo = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="Ore Straordinario Festivo"
    )
    ore_straordinario_notturno = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="Ore Straordinario Notturno"
    )

    # Assenze
    ore_ferie = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="Ore Ferie"
    )
    ore_rol = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="Ore ROL"
    )
    ore_permessi = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="Ore Permessi"
    )
    ore_malattia = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="Ore Malattia"
    )

    # Retribuzione lorda
    imponibile_fiscale = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Imponibile Fiscale €"
    )
    imponibile_contributivo = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Imponibile Contributivo €"
    )

    # Trattenute
    ritenute_previdenziali = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Ritenute Previdenziali €"
    )
    ritenute_irpef = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Ritenute IRPEF €"
    )
    addizionale_regionale = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Addizionale Regionale €"
    )
    addizionale_comunale = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Addizionale Comunale €"
    )
    altre_trattenute = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Altre Trattenute €"
    )

    # Detrazioni
    detrazioni_fiscali = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Detrazioni Fiscali €"
    )

    # Netto
    netto_busta = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Netto in Busta €"
    )

    # TFR maturato nel mese
    tfr_maturato = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="TFR Maturato €"
    )

    confermata = models.BooleanField(default=False, verbose_name="Confermata")

    class Meta:
        unique_together = ["user", "mese", "anno"]
        ordering = ["-anno", "-mese", "user"]
        verbose_name = "Busta Paga"
        verbose_name_plural = "Buste Paga"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.mese:02d}/{self.anno}"


class VoceBustaPaga(models.Model):
    """Singole voci della busta paga"""

    TIPO_VOCE_CHOICES = [
        ("COMPETENZA", "Competenza"),
        ("TRATTENUTA", "Trattenuta"),
        ("DEDUZIONE", "Deduzione"),
    ]

    busta_paga = models.ForeignKey(
        BustaPaga,
        on_delete=models.CASCADE,
        related_name="voci",
        verbose_name="Busta Paga",
    )
    tipo = models.CharField(
        max_length=20, choices=TIPO_VOCE_CHOICES, verbose_name="Tipo"
    )
    descrizione = models.CharField(max_length=200, verbose_name="Descrizione")
    quantita = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Quantità"
    )
    importo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Importo Unitario €"
    )
    importo_totale = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Importo Totale €"
    )
    imponibile_fiscale = models.BooleanField(
        default=True, verbose_name="Imponibile Fiscale"
    )
    imponibile_contributivo = models.BooleanField(
        default=True, verbose_name="Imponibile Contributivo"
    )

    class Meta:
        ordering = ["busta_paga", "tipo", "id"]
        verbose_name = "Voce Busta Paga"
        verbose_name_plural = "Voci Busta Paga"

    def __str__(self):
        return f"{self.busta_paga} - {self.descrizione}"


class FeriePermessiPayroll(models.Model):
    """Gestione maturazione e utilizzo ferie/permessi per payroll"""

    TIPO_CHOICES = [
        ("FERIE", "Ferie"),
        ("ROL", "ROL/Permessi"),
        ("PERMESSO_RETRIBUITO", "Permesso Retribuito"),
        ("PERMESSO_NON_RETRIBUITO", "Permesso Non Retribuito"),
        ("MALATTIA", "Malattia"),
        ("CONGEDO_PARENTALE", "Congedo Parentale"),
        ("L104", "Permesso L.104"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ferie_permessi_payroll",
        verbose_name="Dipendente",
    )
    anno = models.IntegerField(verbose_name="Anno")
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, verbose_name="Tipo")
    ore_maturate = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="Ore Maturate"
    )
    ore_residuo_anno_precedente = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="Ore Residuo Anno Precedente"
    )
    ore_godute = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="Ore Godute"
    )

    @property
    def ore_residue(self):
        return self.ore_maturate + self.ore_residuo_anno_precedente - self.ore_godute

    class Meta:
        unique_together = ["user", "anno", "tipo"]
        ordering = ["-anno", "user"]
        verbose_name = "Ferie/Permessi Payroll"
        verbose_name_plural = "Ferie/Permessi Payroll"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_tipo_display()} {self.anno}"


class ManualePayroll(models.Model):
    """Manuale di istruzioni per la compilazione dei form Payroll"""

    titolo = models.CharField(
        max_length=200,
        default="Manuale di Compilazione Form Payroll",
        verbose_name="Titolo",
    )
    contenuto = models.TextField(
        verbose_name="Contenuto",
        help_text="Contenuto del manuale in formato Markdown",
    )
    versione = models.CharField(
        max_length=20, default="1.0", verbose_name="Versione"
    )
    data_ultima_modifica = models.DateTimeField(
        auto_now=True, verbose_name="Data Ultima Modifica"
    )
    modificato_da = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manuali_modificati",
        verbose_name="Modificato Da",
    )

    class Meta:
        verbose_name = "Manuale Payroll"
        verbose_name_plural = "Manuali Payroll"
        ordering = ["-data_ultima_modifica"]

    def __str__(self):
        return f"{self.titolo} - v{self.versione}"

    @classmethod
    def get_manuale_attivo(cls):
        """Restituisce il manuale più recente o ne crea uno vuoto"""
        manuale = cls.objects.first()
        if not manuale:
            manuale = cls.objects.create(
                titolo="Manuale di Compilazione Form Payroll",
                contenuto="# Manuale in costruzione\n\nIl manuale è in fase di compilazione.",
                versione="1.0",
            )
        return manuale
