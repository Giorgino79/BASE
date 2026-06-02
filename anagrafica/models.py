
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
import re

User = get_user_model()


class Cliente(models.Model):
    """Modello per i clienti con gestione credito integrata"""

    TIPO_PAGAMENTO_CHOICES = [
        ("immediato", "Immediato"),
        ("15_giorni", "15 giorni"),
        ("30_giorni", "30 giorni"),
        ("60_giorni", "60 giorni"),
        ("90_giorni", "90 giorni"),
        ("120_giorni", "120 giorni"),
    ]

    # === DATI ANAGRAFICI ===
    ragione_sociale = models.CharField(max_length=200, help_text="Nome o Ragione Sociale")
    indirizzo = models.TextField(blank=True)
    citta = models.CharField(max_length=100, blank=True)
    cap = models.CharField(max_length=10, blank=True)
    provincia = models.CharField(max_length=5, blank=True, verbose_name='Provincia (sigla)', help_text='Es: MI, RM, PA')
    regione = models.CharField(max_length=100, blank=True, verbose_name='Regione')
    telefono = models.CharField(max_length=20)
    email = models.EmailField()

    # === DATI FISCALI ===
    # Almeno uno tra P.IVA e CF deve essere fornito
    partita_iva = models.CharField(max_length=15, blank=True)
    codice_fiscale = models.CharField(max_length=16, blank=True)
    codice_univoco = models.CharField(max_length=10, blank=True)
    pec = models.EmailField(blank=True)

    # === DATI COMMERCIALI ===
    tipo_pagamento = models.CharField(
        max_length=20, choices=TIPO_PAGAMENTO_CHOICES, default="immediato"
    )
    limite_credito = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text="Limite di credito concesso al cliente"
    )
    rappresentante = models.ForeignKey(
        'rappresentanti.Rappresentante',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='clienti',
        verbose_name='Rappresentante di competenza',
    )
    attivo = models.BooleanField(default=True)
    note = models.TextField(blank=True)

    # === TIMESTAMP ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clienti"
        ordering = ["ragione_sociale"]

    def __str__(self):
        return self.ragione_sociale

    @property
    def nome(self):
        """Alias per ragione_sociale per compatibilità"""
        return self.ragione_sociale

    @property
    def zona(self):
        """Restituisce la città come zona (per compatibilità template)"""
        return self.citta

    @property
    def is_cliente_create(self):
        """Verifica se il cliente è stato creato negli ultimi 7 giorni"""
        from django.utils import timezone
        from datetime import timedelta
        return self.created_at >= timezone.now() - timedelta(days=7)

    

    
    def get_absolute_url(self):
        return reverse("anagrafica:cliente_detail", kwargs={"pk": self.pk})

    @classmethod
    def get_search_fields(cls):
        return ["ragione_sociale", "partita_iva", "codice_fiscale", "email"]

    @classmethod
    def search(cls, query):
        from django.db.models import Q
        q = Q(ragione_sociale__icontains=query) | Q(partita_iva__icontains=query) | Q(codice_fiscale__icontains=query) | Q(email__icontains=query)
        return cls.objects.filter(q)[:5]

    def get_search_result_display(self):
        return f"{self.ragione_sociale} — {self.citta}" if self.citta else self.ragione_sociale

    def get_indirizzo_completo(self):
        """Restituisce l'indirizzo completo formattato"""
        parts = []
        if self.indirizzo:
            parts.append(self.indirizzo)
        if self.cap or self.citta:
            parts.append(f"{self.cap} {self.citta}".strip())
        return ", ".join(parts) if parts else "-"

    def clean(self):
        """Validazioni personalizzate"""
        # Almeno uno tra P.IVA e CF deve essere fornito
        if not self.partita_iva and not self.codice_fiscale:
            raise ValidationError(
                {
                    "partita_iva": "Specificare almeno Partita IVA o Codice Fiscale",
                    "codice_fiscale": "Specificare almeno Partita IVA o Codice Fiscale",
                }
            )

        

        # Validazione P.IVA (solo formato, non checksum)
        if self.partita_iva:
            self.partita_iva = self.partita_iva.replace(" ", "").upper()
            numbers = self.partita_iva[2:] if self.partita_iva.startswith("IT") else self.partita_iva
            if len(numbers) != 11 or not numbers.isdigit():
                raise ValidationError({"partita_iva": "Partita IVA non valida (11 cifre)"})

        # Validazione CF
        if self.codice_fiscale:
            self.codice_fiscale = self.codice_fiscale.replace(" ", "").upper()
            if not self._validate_codice_fiscale(self.codice_fiscale):
                raise ValidationError({"codice_fiscale": "Codice Fiscale non valido"})

    def _validate_partita_iva(self, piva):
        """Validazione Partita IVA italiana (accetta sia 00176830883 che IT00176830883)"""
        numbers = piva[2:] if piva.startswith("IT") else piva
        if len(numbers) != 11 or not numbers.isdigit():
            return False

        # Calcolo checksum
        odd_chars = [int(numbers[i]) for i in range(0, 10, 2)]
        even_chars = [int(numbers[i]) for i in range(1, 10, 2)]

        total = sum(odd_chars)
        for char in even_chars:
            doubled = char * 2
            total += doubled // 10 + doubled % 10

        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(numbers[10])

    def _validate_codice_fiscale(self, cf):
        """Validazione Codice Fiscale"""
        # Pattern per persone fisiche (16 caratteri)
        pattern_persona = r"^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$"
        # Pattern per aziende (11 cifre)
        pattern_azienda = r"^\d{11}$"

        return bool(re.match(pattern_persona, cf) or re.match(pattern_azienda, cf))


class Fornitore(models.Model):
    """Modello per i fornitori"""

    CATEGORIA_CHOICES = [
        ("materie_prime", "Materie Prime"),
        ("semilavorati", "Semilavorati"),
        ("servizi", "Servizi"),
        ("consulenza", "Consulenza"),
        ("software", "Software/IT"),
        ("trasporti", "Trasporti e Logistica"),
        ("altri", "Altri"),
    ]

    TIPO_PAGAMENTO_CHOICES = [
        ("bonifico_30", "Bonifico 30 gg"),
        ("bonifico_60", "Bonifico 60 gg"),
        ("bonifico_90", "Bonifico 90 gg"),
        ("bonifico_120", "Bonifico 120 gg"),
        ("rid_30", "RID 30 gg"),
        ("rid_60", "RID 60 gg"),
        ("riba_30", "RIBA 30 gg"),
        ("riba_60", "RIBA 60 gg"),
        ("contrassegno", "Contrassegno"),
        ("anticipo", "Anticipo 100%"),
        ("fine_mese", "Fine Mese"),
        ("immediato", "Pagamento Immediato"),
    ]

    PRIORITA_PAGAMENTO_CHOICES = [
        ("critica", "Critica (Urgente)"),
        ("alta", "Alta (Prioritaria)"),
        ("media", "Media (Normale)"),
        ("bassa", "Bassa (Differibile)"),
    ]

    # Dati anagrafici
    ragione_sociale = models.CharField(max_length=200, help_text="Nome o Ragione Sociale")
    indirizzo = models.TextField(blank=True)
    citta = models.CharField(max_length=100, blank=True)
    cap = models.CharField(max_length=10, blank=True)
    provincia = models.CharField(max_length=5, blank=True, verbose_name='Provincia (sigla)', help_text='Es: MI, RM, PA')
    regione = models.CharField(max_length=100, blank=True, verbose_name='Regione')
    telefono = models.CharField(max_length=20)
    email = models.EmailField()

    # Dati fiscali
    partita_iva = models.CharField(max_length=15)
    codice_fiscale = models.CharField(max_length=16, blank=True)
    pec = models.EmailField(
        blank=True, help_text="PEC del fornitore per fatturazione elettronica"
    )
    codice_destinatario = models.CharField(
        max_length=7, blank=True, help_text="Codice destinatario SDI (7 caratteri)"
    )

    # Dati bancari
    iban = models.CharField(max_length=34, blank=True)

    # Dati commerciali
    categoria = models.CharField(
        max_length=20, choices=CATEGORIA_CHOICES, default="altri"
    )
    tipo_pagamento = models.CharField(
        max_length=20, choices=TIPO_PAGAMENTO_CHOICES, default="bonifico_30"
    )
    priorita_pagamento_default = models.CharField(
        max_length=10,
        choices=PRIORITA_PAGAMENTO_CHOICES,
        default="media",
        help_text="Priorità di default per i pagamenti a questo fornitore",
    )

    # Referente
    referente_nome = models.CharField(max_length=100, blank=True)
    referente_telefono = models.CharField(max_length=20, blank=True)
    referente_email = models.EmailField(blank=True)

    # Stato
    attivo = models.BooleanField(default=True)
    note = models.TextField(blank=True)

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fornitore"
        verbose_name_plural = "Fornitori"
        ordering = ["ragione_sociale"]

    def __str__(self):
        return self.ragione_sociale

    @property
    def nome(self):
        """Alias per ragione_sociale per compatibilità"""
        return self.ragione_sociale

    
    @property
    def is_fornitore_create(self):
        """Verifica se il fornitore è stato creato negli ultimi 7 giorni"""
        from django.utils import timezone
        from datetime import timedelta
        return self.created_at >= timezone.now() - timedelta(days=7)

    def has_referente(self):
        """Verifica se il fornitore ha un referente"""
        return bool(self.referente_nome or self.referente_telefono or self.referente_email)

    def get_indirizzo_completo(self):
        """Restituisce l'indirizzo completo formattato"""
        parts = []
        if self.indirizzo:
            parts.append(self.indirizzo)
        if self.cap or self.citta:
            parts.append(f"{self.cap} {self.citta}".strip())
        return ", ".join(parts) if parts else "-"

    def get_absolute_url(self):
        return reverse("anagrafica:fornitore_detail", kwargs={"pk": self.pk})

    @classmethod
    def search(cls, query):
        from django.db.models import Q
        q = Q(ragione_sociale__icontains=query) | Q(partita_iva__icontains=query) | Q(codice_fiscale__icontains=query) | Q(email__icontains=query)
        return cls.objects.filter(q)[:5]

    def get_search_result_display(self):
        return f"{self.ragione_sociale} — {self.citta}" if self.citta else self.ragione_sociale

    def clean(self):
        """Validazioni personalizzate"""
        # Validazione P.IVA semplificata
        if self.partita_iva:
            self.partita_iva = (
                self.partita_iva.replace(" ", "").replace("-", "").upper()
            )
            if len(self.partita_iva) < 8 or len(self.partita_iva) > 15:
                raise ValidationError(
                    {"partita_iva": "Partita IVA deve essere tra 8 e 15 caratteri"}
                )

        # Validazione CF semplificata
        if self.codice_fiscale:
            self.codice_fiscale = self.codice_fiscale.replace(" ", "").upper()
            if len(self.codice_fiscale) < 8 or len(self.codice_fiscale) > 16:
                raise ValidationError(
                    {"codice_fiscale": "Codice Fiscale non valido (8-16 caratteri)"}
                )

        # Validazione IBAN
        if self.iban:
            self.iban = self.iban.replace(" ", "").upper()
            if not self._validate_iban(self.iban):
                raise ValidationError({"iban": "IBAN non valido"})

    def _validate_partita_iva(self, piva):
        """Validazione Partita IVA italiana (accetta sia 00176830883 che IT00176830883)"""
        numbers = piva[2:] if piva.startswith("IT") else piva
        if len(numbers) != 11 or not numbers.isdigit():
            return False

        # Calcolo checksum
        odd_chars = [int(numbers[i]) for i in range(0, 10, 2)]
        even_chars = [int(numbers[i]) for i in range(1, 10, 2)]

        total = sum(odd_chars)
        for char in even_chars:
            doubled = char * 2
            total += doubled // 10 + doubled % 10

        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(numbers[10])

    def _validate_codice_fiscale(self, cf):
        """Validazione Codice Fiscale"""
        pattern_persona = r"^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$"
        pattern_azienda = r"^\d{11}$"
        return bool(re.match(pattern_persona, cf) or re.match(pattern_azienda, cf))

    def _validate_iban(self, iban):
        """Validazione IBAN italiana base"""
        if not iban.startswith("IT"):
            return False
        if len(iban) != 27:  # IBAN italiano: IT + 25 caratteri
            return False
        return True
