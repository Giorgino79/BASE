from django.db import migrations
from django.db.models import F


def allinea_pagate(apps, schema_editor):
    """
    Le fatture già a 'pagata' prima dell'introduzione di `importo_incassato`
    sono incassate per intero: senza questo allineamento risulterebbero con
    residuo pieno e ricomparirebbero fra quelle da incassare.
    """
    Fattura = apps.get_model('fatturazione_attiva', 'Fattura')
    Fattura.objects.filter(stato='pagata').update(importo_incassato=F('totale'))


def azzera(apps, schema_editor):
    Fattura = apps.get_model('fatturazione_attiva', 'Fattura')
    Fattura.objects.filter(stato='pagata').update(importo_incassato=0)


class Migration(migrations.Migration):

    dependencies = [
        ('fatturazione_attiva', '0004_fattura_importo_incassato'),
    ]

    operations = [
        migrations.RunPython(allinea_pagate, azzera),
    ]
