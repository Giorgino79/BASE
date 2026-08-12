"""
Assegna MOV-<anno>-<progressivo> ai movimenti già a registro.

L'ordine è quello in cui sono entrati nel libro (data, poi created_at, poi pk):
il progressivo deve rispecchiare la sequenza storica, non l'ordine con cui il
database restituisce le righe.
"""

from django.db import migrations
from django.db.models import Max


def numera(apps, schema_editor):
    Movimento = apps.get_model('contabilita', 'MovimentoPrimaNota')

    # Se una parte fosse già numerata (migrazione rilanciata, dati importati),
    # si riparte dal massimo di ogni anno invece che da zero.
    contatori = {
        r['anno']: r['massimo']
        for r in (Movimento.objects
                  .filter(anno__isnull=False)
                  .values('anno')
                  .annotate(massimo=Max('progressivo')))
    }
    da_salvare = []

    for mov in Movimento.objects.order_by('data', 'created_at', 'pk').iterator(chunk_size=500):
        if mov.numero:
            continue
        anno = mov.data.year
        contatori[anno] = contatori.get(anno, 0) + 1
        mov.anno = anno
        mov.progressivo = contatori[anno]
        mov.numero = f'MOV-{anno}-{contatori[anno]:04d}'
        da_salvare.append(mov)

    Movimento.objects.bulk_update(da_salvare, ['anno', 'progressivo', 'numero'], batch_size=500)


def azzera(apps, schema_editor):
    Movimento = apps.get_model('contabilita', 'MovimentoPrimaNota')
    Movimento.objects.update(anno=None, progressivo=None, numero=None)


class Migration(migrations.Migration):

    dependencies = [
        ('contabilita', '0005_movimentoprimanota_anno_movimentoprimanota_numero_and_more'),
    ]

    operations = [
        migrations.RunPython(numera, azzera),
    ]
