"""
Ricostruisce le scritture di prima nota delle fatture emesse (e ricevute)
prima che i signal di contabilita esistessero.

Senza la riga in Dare del cliente il mastrino mostra solo gli incassi, quindi
un saldo negativo: un cliente che invece di doverci dei soldi risulta a
credito. Il credito non nasceva mai, si vedeva solo sparire.

Dopo l'inserimento tutta la numerazione viene rifatta in ordine di data: i
movimenti recuperati sono più vecchi di quelli già numerati, e un protocollo
che non segue le date sarebbe illeggibile.
"""

from django.db import migrations

CONTO_RICAVI = 'Ricavi da fatturazione'
CONTO_COSTI = 'Costi da fatturazione fornitori'


def recupera(apps, schema_editor):
    Fattura = apps.get_model('fatturazione_attiva', 'Fattura')
    FatturaPassiva = apps.get_model('acquisti', 'FatturaPassiva')
    Conto = apps.get_model('contabilita', 'ContoContabile')
    Mov = apps.get_model('contabilita', 'MovimentoPrimaNota')

    creati = 0

    # ── Fatture attive: Dare cliente, Avere ricavi ───────────────────────────
    gia_fatte = set(
        Mov.objects.filter(tipo='fattura_cliente', fattura_attiva__isnull=False)
        .values_list('fattura_attiva_id', flat=True)
    )
    # Le annullate non generano credito: non devono comparire a mastrino.
    mancanti = (Fattura.objects
                .exclude(pk__in=gia_fatte)
                .exclude(stato='annullata')
                .order_by('data_emissione', 'pk'))

    if mancanti.exists():
        ricavi, _ = Conto.objects.get_or_create(
            tipo='generico', nome=CONTO_RICAVI, defaults={'attivo': True})
        for f in mancanti:
            cliente, _ = Conto.objects.get_or_create(
                tipo='cliente', nome=f.dest_nome, defaults={'attivo': True})
            Mov.objects.create(
                data=f.data_emissione,
                causale=f'Fattura n. {f.numero} — {f.dest_nome}',
                importo=f.totale,
                tipo='fattura_cliente',
                conto_dare=cliente,
                conto_avere=ricavi,
                numero_documento=f.numero,
                fattura_attiva=f,
                is_automatico=True,
                creato_da_id=f.emessa_da_id,
            )
            creati += 1

    # ── Fatture passive: Dare costi, Avere fornitore ─────────────────────────
    gia_fatte = set(
        Mov.objects.filter(tipo='fattura_fornitore', fattura_passiva__isnull=False)
        .values_list('fattura_passiva_id', flat=True)
    )
    mancanti = (FatturaPassiva.objects
                .exclude(pk__in=gia_fatte)
                .exclude(stato_pagamento='annullata')
                .select_related('fornitore')
                .order_by('data_fattura', 'pk'))

    if mancanti.exists():
        costi, _ = Conto.objects.get_or_create(
            tipo='generico', nome=CONTO_COSTI, defaults={'attivo': True})
        for f in mancanti:
            fornitore, _ = Conto.objects.get_or_create(
                tipo='fornitore', nome=f.fornitore.ragione_sociale,
                defaults={'attivo': True})
            Mov.objects.create(
                data=f.data_fattura,
                causale=f'Fattura fornitore {f.numero_fattura} — {f.fornitore.ragione_sociale}',
                importo=f.totale,
                tipo='fattura_fornitore',
                conto_dare=costi,
                conto_avere=fornitore,
                numero_documento=f.numero_fattura,
                fattura_passiva=f,
                is_automatico=True,
                creato_da_id=f.created_by_id,
            )
            creati += 1

    if creati:
        rinumera(Mov)


def rinumera(Mov):
    """
    Rifà tutti i numeri in ordine di data. In due passate: `numero` è unico e
    `(anno, progressivo)` pure, quindi riassegnare sul posto collideresebbe
    con i numeri ancora occupati.
    """
    Mov.objects.update(anno=None, progressivo=None, numero=None)

    contatori = {}
    da_salvare = []
    for mov in Mov.objects.order_by('data', 'created_at', 'pk').iterator(chunk_size=500):
        anno = mov.data.year
        contatori[anno] = contatori.get(anno, 0) + 1
        mov.anno = anno
        mov.progressivo = contatori[anno]
        mov.numero = f'MOV-{anno}-{contatori[anno]:04d}'
        da_salvare.append(mov)

    Mov.objects.bulk_update(da_salvare, ['anno', 'progressivo', 'numero'], batch_size=500)


def indietro(apps, schema_editor):
    """Toglie solo le scritture ricostruite da questa migrazione."""
    Mov = apps.get_model('contabilita', 'MovimentoPrimaNota')
    Mov.objects.filter(tipo__in=['fattura_cliente', 'fattura_fornitore'],
                       is_automatico=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('contabilita', '0006_numera_movimenti_esistenti'),
        ('fatturazione_attiva', '0005_incassato_fatture_pagate'),
        ('acquisti', '0006_fatturapassiva_importo_pagato'),
    ]

    operations = [
        migrations.RunPython(recupera, indietro),
    ]
