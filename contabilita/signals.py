from decimal import Decimal

from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver


# ── Conti da anagrafica ───────────────────────────────────────────────────────
# I conti cliente e fornitore non si creano a mano: nascono qui, appena viene
# registrata l'anagrafica. Il nome del conto coincide con quello che la
# fatturazione usa come destinatario (`dest_nome` / `str(fornitore)`), così i
# signal sulle fatture ritrovano questo conto invece di crearne un doppione.

def _get_or_create_conto(tipo, nome):
    from contabilita.models import ContoContabile

    nome = (nome or '').strip()
    if not nome:
        return None
    conto, _ = ContoContabile.objects.get_or_create(tipo=tipo, nome=nome)
    return conto


@receiver(post_save, sender='anagrafica.Azienda')
def on_azienda_creata(sender, instance, created, **kwargs):
    if created:
        from contabilita.models import ContoContabile
        _get_or_create_conto(ContoContabile.Tipo.CLIENTE, str(instance))


@receiver(post_save, sender='anagrafica.Privato')
def on_privato_creato(sender, instance, created, **kwargs):
    if created:
        from contabilita.models import ContoContabile
        _get_or_create_conto(ContoContabile.Tipo.CLIENTE, str(instance))


@receiver(post_save, sender='anagrafica.Fornitore')
def on_fornitore_creato(sender, instance, created, **kwargs):
    if created:
        from contabilita.models import ContoContabile
        _get_or_create_conto(ContoContabile.Tipo.FORNITORE, str(instance))


# ── Movimenti da fatture ──────────────────────────────────────────────────────
#
# Ogni fattura genera due movimenti, non uno: un rigo per l'imponibile e uno
# per l'IVA, mai un unico importo lordo — senza scorporo non si può sapere
# quanta IVA a debito/credito è maturata in un periodo (vedi scadenziario).
#
# Le funzioni `registra_*` sono estratte a parte (non dentro il signal) per lo
# stesso motivo del modulo da cui sono state adattate: un futuro comando di
# backfill per le fatture emesse prima di questo cambiamento potrà richiamarle
# senza duplicarne la logica. Sono idempotenti per singolo rigo: se
# l'imponibile esiste già ma l'IVA no, rilanciarle crea solo il rigo mancante.


def registra_fattura_vendita(instance):
    from fatturazione_attiva.models import Fattura

    from contabilita.models import ContoContabile, MovimentoPrimaNota

    if instance.stato == Fattura.Stato.ANNULLATA:
        return False
    if not instance.totale:
        return False

    esistenti = MovimentoPrimaNota.objects.filter(fattura_attiva=instance)
    ha_imponibile = esistenti.filter(
        Q(conto_dare__tipo=ContoContabile.Tipo.GENERICO) | Q(conto_avere__tipo=ContoContabile.Tipo.GENERICO)
    ).exists()
    ha_iva = esistenti.filter(
        Q(conto_dare__tipo=ContoContabile.Tipo.IVA_DEBITO) | Q(conto_avere__tipo=ContoContabile.Tipo.IVA_DEBITO)
    ).exists()

    conto_cliente, _ = ContoContabile.objects.get_or_create(
        tipo=ContoContabile.Tipo.CLIENTE,
        nome=instance.dest_nome,
    )
    conto_ricavi, _ = ContoContabile.objects.get_or_create(
        tipo=ContoContabile.Tipo.GENERICO,
        nome='Ricavi da fatturazione',
    )

    imponibile = instance.imponibile or Decimal('0.00')
    iva = instance.importo_iva or Decimal('0.00')
    creati = False

    if imponibile and not ha_imponibile:
        MovimentoPrimaNota.objects.create(
            data=instance.data_emissione,
            causale=f'Fattura n. {instance.numero} — {instance.dest_nome}',
            importo=imponibile,
            tipo=MovimentoPrimaNota.Tipo.FATTURA_CLIENTE,
            conto_dare=conto_cliente,
            conto_avere=conto_ricavi,
            numero_documento=instance.numero,
            fattura_attiva=instance,
            is_automatico=True,
            creato_da=instance.emessa_da,
        )
        creati = True

    if iva and not ha_iva:
        conto_iva_debito, _ = ContoContabile.objects.get_or_create(
            tipo=ContoContabile.Tipo.IVA_DEBITO,
            nome='IVA a debito',
        )
        MovimentoPrimaNota.objects.create(
            data=instance.data_emissione,
            causale=f'IVA fattura n. {instance.numero} — {instance.dest_nome}',
            importo=iva,
            tipo=MovimentoPrimaNota.Tipo.FATTURA_CLIENTE,
            conto_dare=conto_cliente,
            conto_avere=conto_iva_debito,
            numero_documento=instance.numero,
            fattura_attiva=instance,
            is_automatico=True,
            creato_da=instance.emessa_da,
        )
        creati = True

    return creati


def registra_nota_credito(instance):
    from contabilita.models import ContoContabile, MovimentoPrimaNota

    if not instance.totale:
        return False

    esistenti = MovimentoPrimaNota.objects.filter(
        tipo=MovimentoPrimaNota.Tipo.NOTA_CREDITO_CLIENTE,
        numero_documento=instance.numero,
    )
    ha_imponibile = esistenti.filter(
        Q(conto_dare__tipo=ContoContabile.Tipo.GENERICO) | Q(conto_avere__tipo=ContoContabile.Tipo.GENERICO)
    ).exists()
    ha_iva = esistenti.filter(
        Q(conto_dare__tipo=ContoContabile.Tipo.IVA_DEBITO) | Q(conto_avere__tipo=ContoContabile.Tipo.IVA_DEBITO)
    ).exists()

    conto_cliente, _ = ContoContabile.objects.get_or_create(
        tipo=ContoContabile.Tipo.CLIENTE,
        nome=instance.dest_nome,
    )
    conto_ricavi, _ = ContoContabile.objects.get_or_create(
        tipo=ContoContabile.Tipo.GENERICO,
        nome='Ricavi da fatturazione',
    )

    imponibile = instance.imponibile or Decimal('0.00')
    iva = instance.importo_iva or Decimal('0.00')
    creati = False

    # Una nota di credito storna: stessi conti della fattura normale, dare e
    # avere scambiati, perché riduce quello che il cliente deve e i ricavi/
    # IVA già registrati.
    if imponibile and not ha_imponibile:
        MovimentoPrimaNota.objects.create(
            data=instance.data_emissione,
            causale=f'Nota credito n. {instance.numero} — {instance.dest_nome}',
            importo=imponibile,
            tipo=MovimentoPrimaNota.Tipo.NOTA_CREDITO_CLIENTE,
            conto_dare=conto_ricavi,
            conto_avere=conto_cliente,
            numero_documento=instance.numero,
            is_automatico=True,
            creato_da=instance.emessa_da,
        )
        creati = True

    if iva and not ha_iva:
        conto_iva_debito, _ = ContoContabile.objects.get_or_create(
            tipo=ContoContabile.Tipo.IVA_DEBITO,
            nome='IVA a debito',
        )
        MovimentoPrimaNota.objects.create(
            data=instance.data_emissione,
            causale=f'IVA nota credito n. {instance.numero} — {instance.dest_nome}',
            importo=iva,
            tipo=MovimentoPrimaNota.Tipo.NOTA_CREDITO_CLIENTE,
            conto_dare=conto_iva_debito,
            conto_avere=conto_cliente,
            numero_documento=instance.numero,
            is_automatico=True,
            creato_da=instance.emessa_da,
        )
        creati = True

    return creati


def registra_fattura_passiva(instance):
    from contabilita.models import ContoContabile, MovimentoPrimaNota

    if not instance.totale:
        return False

    esistenti = MovimentoPrimaNota.objects.filter(fattura_passiva=instance)
    ha_imponibile = esistenti.filter(
        Q(conto_dare__tipo=ContoContabile.Tipo.GENERICO) | Q(conto_avere__tipo=ContoContabile.Tipo.GENERICO)
    ).exists()
    ha_iva = esistenti.filter(
        Q(conto_dare__tipo=ContoContabile.Tipo.IVA_CREDITO) | Q(conto_avere__tipo=ContoContabile.Tipo.IVA_CREDITO)
    ).exists()

    conto_fornitore, _ = ContoContabile.objects.get_or_create(
        tipo=ContoContabile.Tipo.FORNITORE,
        nome=str(instance.fornitore),
    )
    conto_costi, _ = ContoContabile.objects.get_or_create(
        tipo=ContoContabile.Tipo.GENERICO,
        nome='Costi da fatturazione fornitori',
    )

    imponibile = instance.imponibile or Decimal('0.00')
    iva = instance.importo_iva or Decimal('0.00')
    creati = False

    if imponibile and not ha_imponibile:
        MovimentoPrimaNota.objects.create(
            data=instance.data_fattura,
            causale=f'Fattura fornitore {instance.numero_fattura} — {instance.fornitore}',
            importo=imponibile,
            tipo=MovimentoPrimaNota.Tipo.FATTURA_FORNITORE,
            conto_dare=conto_costi,
            conto_avere=conto_fornitore,
            numero_documento=instance.numero_fattura,
            fattura_passiva=instance,
            is_automatico=True,
            creato_da=instance.created_by,
        )
        creati = True

    if iva and not ha_iva:
        conto_iva_credito, _ = ContoContabile.objects.get_or_create(
            tipo=ContoContabile.Tipo.IVA_CREDITO,
            nome='IVA a credito',
        )
        MovimentoPrimaNota.objects.create(
            data=instance.data_fattura,
            causale=f'IVA fattura fornitore {instance.numero_fattura} — {instance.fornitore}',
            importo=iva,
            tipo=MovimentoPrimaNota.Tipo.FATTURA_FORNITORE,
            conto_dare=conto_iva_credito,
            conto_avere=conto_fornitore,
            numero_documento=instance.numero_fattura,
            fattura_passiva=instance,
            is_automatico=True,
            creato_da=instance.created_by,
        )
        creati = True

    return creati


@receiver(post_save, sender='fatturazione_attiva.Fattura')
def on_fattura_creata(sender, instance, created, **kwargs):
    if created:
        registra_fattura_vendita(instance)


@receiver(post_save, sender='fatturazione_attiva.NotaCredito')
def on_nota_credito_creata(sender, instance, created, **kwargs):
    if created:
        registra_nota_credito(instance)


@receiver(post_save, sender='acquisti.FatturaPassiva')
def on_fattura_passiva_creata(sender, instance, created, **kwargs):
    if created:
        registra_fattura_passiva(instance)
