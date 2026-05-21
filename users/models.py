"""
Models per l'app users.

Include:
- User (CustomUser estende AbstractUser)
- Timbratura (ingressi/uscite con 3 turni)
- GiornataLavorativa (riepilogo giornaliero)
- RichiestaFerie (workflow approvazione)
- RichiestaPermesso (workflow approvazione)
- LetteraRichiamo (lettere disciplinari)
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from core.mixins import TimestampMixin, AllegatiMixin, SoftDeleteMixin


# ============================================================================
# USER MODEL
# ============================================================================


class User(AbstractUser, AllegatiMixin, TimestampMixin, SoftDeleteMixin):
    """
    Model User personalizzato.

    Usa Django Permissions nativo.
    Ogni user ha codice dipendente univoco a 3 cifre.
    """

    # ========== IDENTIFICATIVI ==========
    codice_dipendente = models.CharField(
        "Codice Dipendente",
        max_length=3,
        unique=True,
        help_text="Codice numerico 3 cifre (es. 001, 002, 156)",
    )

    # ========== DATI ANAGRAFICI ==========
    data_nascita = models.DateField("Data di nascita", null=True, blank=True)
    luogo_nascita = models.CharField("Luogo di nascita", max_length=100, blank=True)
    codice_fiscale = models.CharField(
        "Codice Fiscale",
        max_length=16,
        unique=True,
        help_text="Codice fiscale italiano (16 caratteri)",
    )

    # ========== DOCUMENTI ==========
    carta_d_identita = models.CharField(
        "Carta d'Identità",
        max_length=200,
        blank=True,
        help_text="Numero carta d'identità",
    )
    data_scadenza_ci = models.DateField("Scadenza Carta d'Identità", null=True, blank=True)
    patente_di_guida = models.CharField(
        "Patente di Guida", max_length=200, blank=True, help_text="Numero patente"
    )
    data_scadenza_patente = models.DateField("Scadenza Patente", null=True, blank=True)
    categorie_patente = models.CharField(
        "Categorie Patente", max_length=20, blank=True, help_text="Es. B, C, D"
    )

    # ========== FOTO DOCUMENTI ==========
    foto_carta_identita = models.ImageField(
        "Foto Carta d'Identità",
        upload_to="users/documenti/carta_identita/%Y/%m/",
        null=True,
        blank=True,
    )
    foto_codice_fiscale = models.ImageField(
        "Foto Codice Fiscale",
        upload_to="users/documenti/codice_fiscale/%Y/%m/",
        null=True,
        blank=True,
    )
    foto_patente = models.ImageField(
        "Foto Patente",
        upload_to="users/documenti/patente/%Y/%m/",
        null=True,
        blank=True,
    )

    # ========== CONTATTI ==========
    telefono = models.CharField("Telefono", max_length=20, blank=True)
    telefono_emergenza = models.CharField("Telefono emergenza", max_length=20, blank=True)
    indirizzo = models.CharField("Indirizzo", max_length=200, blank=True)
    citta = models.CharField("Città", max_length=100, blank=True)
    cap = models.CharField("CAP", max_length=5, blank=True)
    provincia = models.CharField("Provincia", max_length=2, blank=True)

    # ========== DATI LAVORATIVI ==========
    data_assunzione = models.DateField("Data assunzione", null=True, blank=True)
    data_cessazione = models.DateField("Data cessazione", null=True, blank=True)
    qualifica = models.CharField("Qualifica", max_length=100, blank=True)
    reparto = models.CharField("Reparto", max_length=100, blank=True)

    # ========== POSIZIONI CONTRIBUTIVE ==========
    posizione_inail = models.CharField(
        "Posizione INAIL",
        max_length=200,
        blank=True,
        help_text="Codice posizione assicurativa INAIL",
    )
    posizione_inps = models.CharField(
        "Posizione INPS",
        max_length=200,
        blank=True,
        help_text="Codice posizione contributiva INPS",
    )

    # ========== STATO ==========
    STATO_CHOICES = [
        ("attivo", "Attivo"),
        ("sospeso", "Sospeso"),
        ("cessato", "Cessato"),
        ("in_prova", "In Prova"),
    ]
    stato = models.CharField(
        "Stato", max_length=20, choices=STATO_CHOICES, default="in_prova"
    )

    # ========== FOTO PROFILO ==========
    foto_profilo = models.ImageField(
        "Foto profilo", upload_to="users/profili/%Y/%m/", null=True, blank=True
    )

    # ========== FERIE E PERMESSI ==========
    giorni_ferie_anno = models.PositiveIntegerField("Giorni ferie annuali", default=26)
    giorni_ferie_residui = models.PositiveIntegerField("Giorni ferie residui", default=26)
    ore_permesso_residue = models.DecimalField(
        "Ore permesso residue", max_digits=5, decimal_places=2, default=0
    )

    # ========== NOTE ==========
    note = models.TextField(
        "Note", blank=True, help_text="Note generali sul dipendente"
    )
    note_interne = models.TextField(
        "Note interne", blank=True, help_text="Note riservate agli amministratori"
    )

    # ========== TEMPLATE PERMESSI ==========
    template_permessi_applicato = models.ForeignKey(
        "core.PermissionTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Template Permessi Applicato",
        related_name="utenti_associati",
    )

    class Meta:
        db_table = "users_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["codice_dipendente"]
        permissions = [
            ("gestione_completa_users", "Può gestire completamente gli users"),
            ("visualizza_dashboard_admin", "Può visualizzare dashboard amministratore"),
            ("approva_ferie", "Può approvare richieste ferie"),
            ("approva_permessi", "Può approvare richieste permessi"),
            ("emetti_lettera_richiamo", "Può emettere lettere di richiamo"),
            ("visualizza_report_presenze", "Può visualizzare report presenze"),
        ]
        indexes = [
            models.Index(fields=["codice_dipendente"]),
            models.Index(fields=["stato"]),
            models.Index(fields=["data_assunzione"]),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.codice_dipendente})"

    @classmethod
    def get_search_fields(cls):
        return [
            "username",
            "first_name",
            "last_name",
            "email",
            "codice_dipendente",
            "codice_fiscale",
            "qualifica",
            "reparto",
        ]

    def get_search_result_display(self):
        qualifica_str = f" - {self.qualifica}" if self.qualifica else ""
        return f"{self.get_full_name()} ({self.codice_dipendente}){qualifica_str}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("users:user_detail", args=[self.pk])

    def get_badge_qr(self):
        return self.allegati.filter(nome_originale__startswith="badge_qr_").first()

    @property
    def eta(self):
        if not self.data_nascita:
            return None
        from datetime import date
        today = date.today()
        return (
            today.year
            - self.data_nascita.year
            - ((today.month, today.day) < (self.data_nascita.month, self.data_nascita.day))
        )

    @property
    def anni_servizio(self):
        if not self.data_assunzione:
            return None
        from datetime import date
        return date.today().year - self.data_assunzione.year

    @property
    def is_attivo(self):
        return self.stato == "attivo"

    @property
    def ferie_utilizzate(self):
        return self.giorni_ferie_anno - self.giorni_ferie_residui

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not self.codice_dipendente:
            self.codice_dipendente = self._genera_codice_dipendente()
        super().save(*args, **kwargs)

        if is_new:
            try:
                self.genera_e_salva_qr_code(
                    filename=f"badge_qr_{self.codice_dipendente}.png",
                    descrizione=f"QR Code Badge - {self.get_full_name()}",
                )
            except Exception:
                pass

    def _genera_codice_dipendente(self):
        ultimo = User.objects.order_by("-codice_dipendente").first()
        if ultimo and ultimo.codice_dipendente:
            try:
                return f"{int(ultimo.codice_dipendente) + 1:03d}"
            except ValueError:
                pass
        return "001"

    def clean(self):
        super().clean()
        if self.codice_fiscale and len(self.codice_fiscale) != 16:
            raise ValidationError(
                {"codice_fiscale": "Il codice fiscale deve essere di 16 caratteri"}
            )

    def delete(self, *args, **kwargs):
        self.soft_delete()


# ============================================================================
# TIMBRATURA
# ============================================================================


class Timbratura(TimestampMixin):
    TIPO_CHOICES = [("ingresso", "Ingresso"), ("uscita", "Uscita")]
    TURNO_CHOICES = [
        ("mattina", "Mattina"),
        ("pomeriggio", "Pomeriggio"),
        ("notte", "Notte"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="timbrature", verbose_name="User"
    )
    data = models.DateField("Data", auto_now_add=True)
    ora = models.TimeField("Ora", auto_now_add=True)
    tipo = models.CharField("Tipo", max_length=10, choices=TIPO_CHOICES)
    turno = models.CharField("Turno", max_length=15, choices=TURNO_CHOICES)
    latitudine = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitudine = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    note = models.CharField("Note", max_length=200, blank=True)

    class Meta:
        db_table = "users_timbratura"
        verbose_name = "Timbratura"
        verbose_name_plural = "Timbrature"
        ordering = ["-data", "-ora"]
        unique_together = [["user", "data", "tipo", "turno"]]
        indexes = [
            models.Index(fields=["user", "data"]),
            models.Index(fields=["data"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_tipo_display()} {self.turno} - {self.data} {self.ora}"


# ============================================================================
# GIORNATA LAVORATIVA
# ============================================================================


class GiornataLavorativa(TimestampMixin):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="giornate", verbose_name="User"
    )
    data = models.DateField("Data")
    ore_mattina = models.DecimalField("Ore Mattina", max_digits=4, decimal_places=2, default=0)
    ore_pomeriggio = models.DecimalField("Ore Pomeriggio", max_digits=4, decimal_places=2, default=0)
    ore_notte = models.DecimalField("Ore Notte", max_digits=4, decimal_places=2, default=0)
    ore_totali = models.DecimalField("Ore Totali", max_digits=5, decimal_places=2, default=0)
    ore_straordinarie = models.DecimalField(
        "Ore Straordinarie", max_digits=5, decimal_places=2, default=0
    )
    conclusa = models.BooleanField("Giornata conclusa", default=False)
    note = models.TextField("Note", blank=True)

    class Meta:
        db_table = "users_giornata_lavorativa"
        verbose_name = "Giornata Lavorativa"
        verbose_name_plural = "Giornate Lavorative"
        ordering = ["-data"]
        unique_together = [["user", "data"]]
        indexes = [
            models.Index(fields=["user", "data"]),
            models.Index(fields=["data"]),
            models.Index(fields=["conclusa"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.data} ({self.ore_totali}h)"

    ORE_ORDINARIE_GIORNO = 8      # soglia giornaliera D.Lgs. 66/2003
    ORE_ORDINARIE_SETTIMANA = 40  # soglia settimanale D.Lgs. 66/2003

    def calcola_ore(self):
        from datetime import datetime, timedelta

        timbrature = self.user.timbrature.filter(data=self.data).order_by("turno", "ora")
        ore_per_turno = {"mattina": 0, "pomeriggio": 0, "notte": 0}
        for turno in ["mattina", "pomeriggio", "notte"]:
            ingresso = timbrature.filter(turno=turno, tipo="ingresso").first()
            uscita = timbrature.filter(turno=turno, tipo="uscita").first()
            if ingresso and uscita:
                dt_ingresso = datetime.combine(self.data, ingresso.ora)
                dt_uscita = datetime.combine(self.data, uscita.ora)
                if dt_uscita < dt_ingresso:
                    dt_uscita += timedelta(days=1)
                ore = (dt_uscita - dt_ingresso).total_seconds() / 3600
                ore_per_turno[turno] = round(ore, 2)

        self.ore_mattina = ore_per_turno["mattina"]
        self.ore_pomeriggio = ore_per_turno["pomeriggio"]
        self.ore_notte = ore_per_turno["notte"]
        self.ore_totali = sum(ore_per_turno.values())
        # Straordinario giornaliero: ore oltre la soglia di 8h (art. 3 D.Lgs. 66/2003)
        self.ore_straordinarie = max(0, float(self.ore_totali) - self.ORE_ORDINARIE_GIORNO)
        self.save()

    @property
    def ore_ordinarie(self):
        """Ore rientranti nell'orario normale (max 8h/giorno)."""
        return min(float(self.ore_totali), self.ORE_ORDINARIE_GIORNO)

    @classmethod
    def calcola_straordinari_settimanali(cls, user, anno, settimana_iso):
        """
        Straordinario settimanale: ore > 40h/settimana che non sono già
        conteggiate come straordinario giornaliero.
        """
        import datetime
        lun = datetime.date.fromisocalendar(anno, settimana_iso, 1)
        dom = datetime.date.fromisocalendar(anno, settimana_iso, 7)
        giornate = cls.objects.filter(user=user, data__range=(lun, dom))

        ore_settimana = sum(float(g.ore_totali) for g in giornate)
        ore_straord_giorn = sum(float(g.ore_straordinarie) for g in giornate)
        ore_ordinarie_sett = ore_settimana - ore_straord_giorn

        # Straordinario settimanale = ore ordinarie oltre le 40h settimanali
        strao_sett = max(0, ore_ordinarie_sett - cls.ORE_ORDINARIE_SETTIMANA)
        return {
            "ore_settimana": round(ore_settimana, 2),
            "ore_ordinarie": round(min(ore_ordinarie_sett, cls.ORE_ORDINARIE_SETTIMANA), 2),
            "straordinario_giornaliero": round(ore_straord_giorn, 2),
            "straordinario_settimanale": round(strao_sett, 2),
            "straordinario_totale": round(ore_straord_giorn + strao_sett, 2),
        }


# ============================================================================
# RICHIESTA FERIE
# ============================================================================


class RichiestaFerie(TimestampMixin):
    STATO_CHOICES = [
        ("in_attesa", "In Attesa"),
        ("approvata", "Approvata"),
        ("rifiutata", "Rifiutata"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="richieste_ferie", verbose_name="User"
    )
    data_inizio = models.DateField("Data inizio")
    data_fine = models.DateField("Data fine")
    giorni_richiesti = models.PositiveIntegerField("Giorni richiesti")
    motivo = models.TextField("Motivo", blank=True)
    stato = models.CharField(
        "Stato", max_length=20, choices=STATO_CHOICES, default="in_attesa"
    )
    gestita_da = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ferie_gestite",
        verbose_name="Gestita da",
    )
    gestita_il = models.DateTimeField("Gestita il", null=True, blank=True)
    motivazione_rifiuto = models.TextField("Motivazione rifiuto", blank=True)

    class Meta:
        db_table = "users_richiesta_ferie"
        verbose_name = "Richiesta Ferie"
        verbose_name_plural = "Richieste Ferie"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "stato"]),
            models.Index(fields=["stato"]),
            models.Index(fields=["data_inizio"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.data_inizio}/{self.data_fine} ({self.get_stato_display()})"

    def clean(self):
        super().clean()
        if self.data_inizio and self.data_fine and self.user_id:
            sovrapposte = RichiestaFerie.objects.filter(
                user=self.user_id,
                stato__in=["in_attesa", "approvata"],
                data_inizio__lte=self.data_fine,
                data_fine__gte=self.data_inizio,
            ).exclude(pk=self.pk if self.pk else None)
            if sovrapposte.exists():
                raise ValidationError("Hai già ferie richieste/approvate in questo periodo")

    def save(self, *args, **kwargs):
        if self.data_inizio and self.data_fine:
            self.giorni_richiesti = (self.data_fine - self.data_inizio).days + 1
        super().save(*args, **kwargs)

    def approva(self, amministratore):
        from django.utils import timezone
        from django.db import transaction
        from django.db.models import F

        with transaction.atomic():
            richiesta = RichiestaFerie.objects.select_for_update().get(pk=self.pk)
            if richiesta.stato != "in_attesa":
                raise ValidationError(f"Richiesta già gestita ({richiesta.get_stato_display()})")
            richiesta.stato = "approvata"
            richiesta.gestita_da = amministratore
            richiesta.gestita_il = timezone.now()
            richiesta.save()
            User.objects.filter(pk=self.user_id).update(
                giorni_ferie_residui=F("giorni_ferie_residui") - self.giorni_richiesti
            )

    def rifiuta(self, amministratore, motivazione):
        from django.utils import timezone
        from django.db import transaction

        with transaction.atomic():
            richiesta = RichiestaFerie.objects.select_for_update().get(pk=self.pk)
            if richiesta.stato != "in_attesa":
                raise ValidationError(f"Richiesta già gestita ({richiesta.get_stato_display()})")
            richiesta.stato = "rifiutata"
            richiesta.gestita_da = amministratore
            richiesta.gestita_il = timezone.now()
            richiesta.motivazione_rifiuto = motivazione
            richiesta.save()


# ============================================================================
# RICHIESTA PERMESSO
# ============================================================================


class RichiestaPermesso(TimestampMixin):
    STATO_CHOICES = [
        ("in_attesa", "In Attesa"),
        ("approvata", "Approvata"),
        ("rifiutata", "Rifiutata"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="richieste_permessi", verbose_name="User"
    )
    data = models.DateField("Data")
    ora_inizio = models.TimeField("Ora inizio")
    ora_fine = models.TimeField("Ora fine")
    ore_richieste = models.DecimalField("Ore richieste", max_digits=4, decimal_places=2)
    motivo = models.TextField("Motivo")
    stato = models.CharField(
        "Stato", max_length=20, choices=STATO_CHOICES, default="in_attesa"
    )
    gestita_da = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="permessi_gestiti",
        verbose_name="Gestita da",
    )
    gestita_il = models.DateTimeField("Gestita il", null=True, blank=True)
    motivazione_rifiuto = models.TextField("Motivazione rifiuto", blank=True)

    class Meta:
        db_table = "users_richiesta_permesso"
        verbose_name = "Richiesta Permesso"
        verbose_name_plural = "Richieste Permessi"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "stato"]),
            models.Index(fields=["stato"]),
            models.Index(fields=["data"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.data} ({self.ore_richieste}h) - {self.get_stato_display()}"

    def save(self, *args, **kwargs):
        if self.ora_inizio and self.ora_fine:
            from datetime import datetime
            dt_inizio = datetime.combine(self.data, self.ora_inizio)
            dt_fine = datetime.combine(self.data, self.ora_fine)
            self.ore_richieste = round((dt_fine - dt_inizio).total_seconds() / 3600, 2)
        super().save(*args, **kwargs)

    def approva(self, amministratore):
        from django.utils import timezone
        from django.db import transaction
        from django.db.models import F

        with transaction.atomic():
            richiesta = RichiestaPermesso.objects.select_for_update().get(pk=self.pk)
            if richiesta.stato != "in_attesa":
                raise ValidationError(f"Richiesta già gestita ({richiesta.get_stato_display()})")
            richiesta.stato = "approvata"
            richiesta.gestita_da = amministratore
            richiesta.gestita_il = timezone.now()
            richiesta.save()
            User.objects.filter(pk=self.user_id).update(
                ore_permesso_residue=F("ore_permesso_residue") - self.ore_richieste
            )

    def rifiuta(self, amministratore, motivazione):
        from django.utils import timezone
        from django.db import transaction

        with transaction.atomic():
            richiesta = RichiestaPermesso.objects.select_for_update().get(pk=self.pk)
            if richiesta.stato != "in_attesa":
                raise ValidationError(f"Richiesta già gestita ({richiesta.get_stato_display()})")
            richiesta.stato = "rifiutata"
            richiesta.gestita_da = amministratore
            richiesta.gestita_il = timezone.now()
            richiesta.motivazione_rifiuto = motivazione
            richiesta.save()


# ============================================================================
# LETTERA RICHIAMO
# ============================================================================


class LetteraRichiamo(TimestampMixin, AllegatiMixin):
    TIPO_CHOICES = [
        ("verbale", "Richiamo Verbale"),
        ("scritto", "Richiamo Scritto"),
        ("sospensione", "Sospensione"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lettere_richiamo", verbose_name="User"
    )
    tipo = models.CharField("Tipo", max_length=20, choices=TIPO_CHOICES)
    data_emissione = models.DateField("Data emissione", auto_now_add=True)
    motivo = models.TextField("Motivo")
    descrizione = models.TextField("Descrizione dettagliata")
    emessa_da = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="lettere_emesse",
        verbose_name="Emessa da",
    )
    giorni_sospensione = models.PositiveIntegerField("Giorni sospensione", null=True, blank=True)
    data_inizio_sospensione = models.DateField("Data inizio sospensione", null=True, blank=True)
    data_fine_sospensione = models.DateField("Data fine sospensione", null=True, blank=True)
    documento_pdf = models.FileField(
        "Documento PDF",
        upload_to="users/lettere_richiamo/%Y/%m/",
        null=True,
        blank=True,
    )
    user_ha_letto = models.BooleanField("User ha letto", default=False)
    data_lettura = models.DateTimeField("Data lettura", null=True, blank=True)

    class Meta:
        db_table = "users_lettera_richiamo"
        verbose_name = "Lettera di Richiamo"
        verbose_name_plural = "Lettere di Richiamo"
        ordering = ["-data_emissione"]
        indexes = [
            models.Index(fields=["user", "data_emissione"]),
            models.Index(fields=["tipo"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.user.get_full_name()} - {self.data_emissione}"


# ============================================================================
# CALENDARIO PERSONALE
# ============================================================================


class EventoPersonale(TimestampMixin, SoftDeleteMixin, models.Model):
    TIPO_CHOICES = [
        ("promemoria", "Promemoria"),
        ("appuntamento", "Appuntamento"),
        ("compleanno", "Compleanno"),
        ("scadenza", "Scadenza"),
        ("altro", "Altro"),
    ]
    PRIORITA_CHOICES = [
        ("bassa", "Bassa"),
        ("media", "Media"),
        ("alta", "Alta"),
    ]

    utente = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="eventi_personali", verbose_name="Utente"
    )
    titolo = models.CharField("Titolo", max_length=200)
    descrizione = models.TextField("Descrizione", blank=True)
    tipo = models.CharField("Tipo", max_length=20, choices=TIPO_CHOICES, default="promemoria")
    priorita = models.CharField(
        "Priorità", max_length=10, choices=PRIORITA_CHOICES, default="media"
    )
    data_inizio = models.DateTimeField("Data/Ora Inizio")
    data_fine = models.DateTimeField("Data/Ora Fine", null=True, blank=True)
    tutto_il_giorno = models.BooleanField("Tutto il giorno", default=False)
    ricorrente = models.BooleanField("Ricorrente", default=False)
    notifica_email = models.BooleanField("Notifica via email", default=False)
    colore = models.CharField("Colore", max_length=7, default="#007bff")
    completato = models.BooleanField("Completato", default=False)
    data_completamento = models.DateTimeField("Data completamento", null=True, blank=True)

    class Meta:
        db_table = "users_evento_personale"
        verbose_name = "Evento Personale"
        verbose_name_plural = "Eventi Personali"
        ordering = ["data_inizio"]
        indexes = [
            models.Index(fields=["utente", "data_inizio"]),
            models.Index(fields=["tipo"]),
            models.Index(fields=["completato"]),
        ]
        permissions = [
            ("view_own_eventi", "Può visualizzare i propri eventi personali"),
            ("manage_own_eventi", "Può gestire i propri eventi personali"),
        ]

    def __str__(self):
        return f"{self.titolo} - {self.data_inizio.strftime('%d/%m/%Y')}"

    def clean(self):
        super().clean()
        if self.data_fine and self.data_fine < self.data_inizio:
            raise ValidationError("La data di fine deve essere successiva alla data di inizio")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
