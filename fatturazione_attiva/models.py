from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.db import models
from django.utils import timezone


def _next_numero(anno):
    """Progressivo fatture per anno: FA-2026-0001, FA-2026-0002, ..."""
    ultimo = (Fattura.objects
               .filter(anno=anno)
               .aggregate(m=models.Max('progressivo'))['m'] or 0)
    return ultimo + 1


class Fattura(models.Model):

    class Stato(models.TextChoices):
        EMESSA    = 'emessa',    'Emessa'
        PAGATA    = 'pagata',    'Pagata'
        ANNULLATA = 'annullata', 'Annullata'

    # Identificazione
    anno        = models.PositiveSmallIntegerField(verbose_name='Anno')
    progressivo = models.PositiveIntegerField(verbose_name='Progressivo')
    numero      = models.CharField(max_length=30, unique=True, verbose_name='Numero fattura')

    # Date
    data_emissione  = models.DateField(verbose_name='Data emissione')
    data_pagamento  = models.DateField(null=True, blank=True, verbose_name='Data pagamento')

    # Stato
    stato = models.CharField(
        max_length=12, choices=Stato.choices, default=Stato.EMESSA,
        verbose_name='Stato',
    )

    # Snapshot destinatario (dati al momento dell'emissione)
    dest_nome          = models.CharField(max_length=300, verbose_name='Destinatario')
    dest_indirizzo     = models.CharField(max_length=300, blank=True)
    dest_cap           = models.CharField(max_length=10, blank=True)
    dest_citta         = models.CharField(max_length=100, blank=True)
    dest_provincia     = models.CharField(max_length=5, blank=True)
    dest_partita_iva   = models.CharField(max_length=20, blank=True)
    dest_codice_fiscale = models.CharField(max_length=16, blank=True)
    dest_pec           = models.EmailField(blank=True)
    dest_codice_univoco = models.CharField(max_length=7, blank=True)

    # Snapshot emittente (dati settings al momento dell'emissione)
    emit_ragione_sociale = models.CharField(max_length=300, blank=True)
    emit_indirizzo       = models.CharField(max_length=300, blank=True)
    emit_cap_citta       = models.CharField(max_length=200, blank=True)
    emit_partita_iva     = models.CharField(max_length=20, blank=True)
    emit_codice_fiscale  = models.CharField(max_length=16, blank=True)
    emit_telefono        = models.CharField(max_length=30, blank=True)
    emit_email           = models.EmailField(blank=True)
    emit_iban            = models.CharField(max_length=40, blank=True)

    # Importi
    aliquota_iva   = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('22.00'),
                                          verbose_name='Aliquota IVA %')
    imponibile     = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Imponibile')
    importo_iva    = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='IVA')
    totale         = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Totale')

    # Note e condizioni
    note_pagamento = models.TextField(blank=True, verbose_name='Condizioni di pagamento')
    note           = models.TextField(blank=True, verbose_name='Note')

    # ODS collegati (M2M per storico)
    ods = models.ManyToManyField('servizi.ODS', blank=True, related_name='fatture',
                                  verbose_name='ODS collegati')

    # Audit
    emessa_da  = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        related_name='fatture_emesse', verbose_name='Emessa da',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fattura'
        verbose_name_plural = 'Fatture'
        ordering = ['-anno', '-progressivo']
        unique_together = [('anno', 'progressivo')]

    def __str__(self):
        return self.numero

    @classmethod
    def crea(cls, righe_rows, emessa_da, note=''):
        """
        Crea una Fattura con le sue RigaFattura a partire da righe_rows
        (lista di dict {ods, riga}) e salva tutto in una transazione.
        """
        from django.db import transaction
        from django.conf import settings as s

        fat_cfg = s.FATTURAZIONE
        aliquota = Decimal(str(fat_cfg.get('ALIQUOTA_IVA', 22)))
        oggi = timezone.localdate()
        anno = oggi.year

        imponibile = sum(
            (r['riga'].prezzo for r in righe_rows if r['riga'] and r['riga'].prezzo),
            Decimal('0.00'),
        )
        importo_iva = (imponibile * aliquota / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
        totale = imponibile + importo_iva

        dest = _build_destinatario(righe_rows)

        with transaction.atomic():
            prog = _next_numero(anno)
            numero = f"FA-{anno}-{prog:04d}"
            fattura = cls.objects.create(
                anno=anno,
                progressivo=prog,
                numero=numero,
                data_emissione=oggi,
                stato=cls.Stato.EMESSA,
                # destinatario
                dest_nome=dest['nome'],
                dest_indirizzo=dest['indirizzo'],
                dest_cap=dest['cap'],
                dest_citta=dest['citta'],
                dest_provincia=dest['provincia'],
                dest_partita_iva=dest['partita_iva'],
                dest_codice_fiscale=dest['codice_fiscale'],
                dest_pec=dest['pec'],
                dest_codice_univoco=dest.get('codice_univoco', ''),
                # emittente snapshot
                emit_ragione_sociale=fat_cfg.get('RAGIONE_SOCIALE', ''),
                emit_indirizzo=fat_cfg.get('INDIRIZZO', ''),
                emit_cap_citta=fat_cfg.get('CAP_CITTA', ''),
                emit_partita_iva=fat_cfg.get('PARTITA_IVA', ''),
                emit_codice_fiscale=fat_cfg.get('CODICE_FISCALE', ''),
                emit_telefono=fat_cfg.get('TELEFONO', ''),
                emit_email=fat_cfg.get('EMAIL', ''),
                emit_iban=fat_cfg.get('IBAN', ''),
                # importi
                aliquota_iva=aliquota,
                imponibile=imponibile,
                importo_iva=importo_iva,
                totale=totale,
                note_pagamento=fat_cfg.get('NOTE_PAGAMENTO', ''),
                note=note,
                emessa_da=emessa_da,
            )

            # Righe di dettaglio
            righe_db = []
            for r in righe_rows:
                ods = r['ods']
                riga = r['riga']
                righe_db.append(RigaFattura(
                    fattura=fattura,
                    ods_numero=ods.numero,
                    data_servizio=ods.data_servizio,
                    descrizione=riga.servizio.nome if riga else 'Servizio',
                    note=riga.note if riga else '',
                    importo=riga.prezzo if riga and riga.prezzo else Decimal('0.00'),
                ))
            RigaFattura.objects.bulk_create(righe_db)

            # Collega ODS e marcali come fatturati
            ods_ids = {r['ods'].pk for r in righe_rows}
            fattura.ods.set(ods_ids)
            from servizi.models import ODS as ODSModel
            ODSModel.objects.filter(pk__in=ods_ids).update(stato=ODSModel.Stato.FATTURATO)

        return fattura


class RigaFattura(models.Model):
    fattura      = models.ForeignKey(Fattura, on_delete=models.CASCADE,
                                      related_name='righe', verbose_name='Fattura')
    ods_numero   = models.CharField(max_length=20, verbose_name='N° ODS')
    data_servizio = models.DateField(verbose_name='Data servizio')
    descrizione  = models.CharField(max_length=300, verbose_name='Descrizione')
    note         = models.CharField(max_length=300, blank=True)
    importo      = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Importo')

    class Meta:
        verbose_name = 'Riga fattura'
        verbose_name_plural = 'Righe fattura'
        ordering = ['data_servizio', 'pk']

    def __str__(self):
        return f"{self.fattura.numero} — {self.descrizione}"


# ── helper condiviso ──────────────────────────────────────────────────────────

def _build_destinatario(rows):
    ods = rows[0]['ods']
    if ods.filiale:
        c = ods.filiale.cliente
        return {
            'nome':            c.ragione_sociale,
            'indirizzo':       c.indirizzo,
            'cap':             c.cap,
            'citta':           c.citta,
            'provincia':       getattr(c, 'provincia', ''),
            'partita_iva':     c.partita_iva,
            'codice_fiscale':  getattr(c, 'codice_fiscale', ''),
            'pec':             getattr(c, 'pec', ''),
            'codice_univoco':  getattr(c, 'codice_univoco', ''),
        }
    if ods.privato:
        p = ods.privato
        return {
            'nome':           str(p),
            'indirizzo':      p.indirizzo,
            'cap':            p.cap,
            'citta':          p.citta,
            'provincia':      getattr(p, 'provincia', ''),
            'partita_iva':    '',
            'codice_fiscale': p.codice_fiscale,
            'pec':            '',
            'codice_univoco': '',
        }
    return {'nome': '—', 'indirizzo': '', 'cap': '', 'citta': '',
            'provincia': '', 'partita_iva': '', 'codice_fiscale': '',
            'pec': '', 'codice_univoco': ''}
