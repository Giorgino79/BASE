from django.db import migrations, models


def assegna_numeri(apps, schema_editor):
    Distinta = apps.get_model("servizi", "Distinta")
    for d in Distinta.objects.order_by("creata_il", "pk"):
        anno = d.data.year
        prefix = f"DIS-{anno}-"
        ultimo = (
            Distinta.objects
            .filter(numero__startswith=prefix)
            .order_by("numero")
            .last()
        )
        if ultimo and ultimo.numero:
            try:
                n = int(ultimo.numero.split("-")[-1]) + 1
            except ValueError:
                n = 1
        else:
            n = 1
        d.numero = f"{prefix}{n:04d}"
        d.save(update_fields=["numero"])


class Migration(migrations.Migration):

    dependencies = [
        ('servizi', '0009_distinta_chiusura_ufficio'),
    ]

    operations = [
        migrations.AddField(
            model_name='distinta',
            name='numero',
            field=models.CharField(blank=True, max_length=20, verbose_name='Numero', default=''),
            preserve_default=False,
        ),
        migrations.RunPython(assegna_numeri, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='distinta',
            name='numero',
            field=models.CharField(blank=True, max_length=20, unique=True, verbose_name='Numero'),
        ),
    ]
