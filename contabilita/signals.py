from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='fatturazione_attiva.Fattura')
def on_fattura_creata(sender, instance, created, **kwargs):
    """
    Quando viene creata una nuova Fattura, registra automaticamente
    la riga in prima nota: Dare = conto cliente, Avere = conto ricavi.
    """
    if not created:
        return

    from contabilita.models import ContoContabile, MovimentoPrimaNota

    conto_cliente, _ = ContoContabile.objects.get_or_create(
        tipo=ContoContabile.Tipo.CLIENTE,
        nome=instance.dest_nome,
    )

    conto_ricavi, _ = ContoContabile.objects.get_or_create(
        tipo=ContoContabile.Tipo.GENERICO,
        nome='Ricavi da fatturazione',
    )

    MovimentoPrimaNota.objects.create(
        data=instance.data_emissione,
        causale=f'Fattura n. {instance.numero} — {instance.dest_nome}',
        importo=instance.totale,
        tipo=MovimentoPrimaNota.Tipo.FATTURA_CLIENTE,
        conto_dare=conto_cliente,
        conto_avere=conto_ricavi,
        numero_documento=instance.numero,
        fattura_attiva=instance,
        is_automatico=True,
        creato_da=instance.emessa_da,
    )


@receiver(post_save, sender='acquisti.FatturaPassiva')
def on_fattura_passiva_creata(sender, instance, created, **kwargs):
    """
    Quando viene registrata una nuova FatturaPassiva (fattura ricevuta da un
    fornitore), registra automaticamente la riga in prima nota:
    Dare = conto costi, Avere = conto fornitore.
    """
    if not created:
        return

    from contabilita.models import ContoContabile, MovimentoPrimaNota

    conto_fornitore, _ = ContoContabile.objects.get_or_create(
        tipo=ContoContabile.Tipo.FORNITORE,
        nome=str(instance.fornitore),
    )

    conto_costi, _ = ContoContabile.objects.get_or_create(
        tipo=ContoContabile.Tipo.GENERICO,
        nome='Costi da fatturazione fornitori',
    )

    MovimentoPrimaNota.objects.create(
        data=instance.data_fattura,
        causale=f'Fattura fornitore {instance.numero_fattura} — {instance.fornitore}',
        importo=instance.totale,
        tipo=MovimentoPrimaNota.Tipo.FATTURA_FORNITORE,
        conto_dare=conto_costi,
        conto_avere=conto_fornitore,
        numero_documento=instance.numero_fattura,
        fattura_passiva=instance,
        is_automatico=True,
        creato_da=instance.created_by,
    )
