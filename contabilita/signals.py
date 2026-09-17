from decimal import Decimal

from django.conf import settings
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


def conto_custodia_di(user):
    """
    Il conto di custodia di uno user, creandolo (e collegandolo) al volo se
    per qualche motivo manca ancora — difesa in profondità: dovrebbe sempre
    esistere già grazie a `on_user_creato`, ma un passaggio di cassa non deve
    fallire per un utente storico mai passato dal backfill.
    """
    from contabilita.models import ContoContabile

    conto = ContoContabile.objects.filter(utente=user, tipo=ContoContabile.Tipo.CUSTODIA).first()
    if conto:
        return conto
    nome = user.get_full_name() or user.username
    conto = _get_or_create_conto(ContoContabile.Tipo.CUSTODIA, nome)
    if conto and not conto.utente_id:
        conto.utente = user
        conto.save(update_fields=['utente'])
    return conto


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def on_user_creato(sender, instance, created, **kwargs):
    """
    Ogni persona che può avere contanti/assegni in mano — tecnico, cassiere,
    impiegato, non solo chi guida un mezzo — ha il proprio conto di custodia,
    esattamente come un cliente o un fornitore. Nasce vuoto: il saldo si
    muove solo con un giroconto esplicito (vedi passaggio_cassa_create).
    """
    if created:
        conto_custodia_di(instance)


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


# ── PAS (passaggio di cassa fra persone) ─────────────────────────────────────
#
# Un PAS non genera mai un movimento di prima nota, nemmeno quando è
# confermato e nemmeno quando coinvolge un contabile: è solo un log di
# custodia (chi ha il contante in mano adesso), non un fatto contabile.
# L'unico ponte legittimo fra servizi e prima nota è la fattura (vedi
# servizi/views.py::chiudi_distinta_ufficio per l'incasso per ODS).

def notifica_conferma_ricezione(instance):
    """
    Messaggio di chat dal ricevente al consegnante, a conferma avvenuta —
    solo se anche chi consegna è una persona: se il denaro veniva dalla
    cassaforte non c'è nessuno a cui scrivere. Riusa la stessa logica di
    "trova o crea la conversazione diretta" già usata da
    comunicazioni.views.chat_nuova, per non aprirne una doppia se i due si
    sono già scritti.
    """
    if not instance.confermato_da_id or not instance.da_conto.utente_id:
        return None

    from django.utils import timezone as tz

    from comunicazioni.models import ChatConversazione, ChatMessaggio

    mittente = instance.confermato_da
    destinatario = instance.da_conto.utente

    conv = (ChatConversazione.objects
            .filter(tipo='direct', partecipanti=mittente)
            .filter(partecipanti=destinatario)
            .first())
    if not conv:
        conv = ChatConversazione.objects.create(tipo='direct', creata_da=mittente)
        conv.partecipanti.add(mittente, destinatario)

    messaggio = ChatMessaggio.objects.create(
        conversazione=conv,
        mittente=mittente,
        contenuto=f'Mi hai appena consegnato € {instance.importo_totale} — {instance.causale}',
    )
    conv.last_message_at = tz.now()
    conv.save(update_fields=['last_message_at'])
    return messaggio
