# Generated manually (ambiente locale privo di dipendenze per eseguire makemigrations)
#
# Converte ContrattoRiga.periodicita da CharField a scelte fisse a
# ForeignKey verso il nuovo modello Periodicita, un elenco aperto che il
# cliente può estendere dal form del contratto. I 6 valori standard
# esistenti vengono creati come record e le righe contratto già presenti
# vengono agganciate al record corrispondente.

import django.db.models.deletion
from django.db import migrations, models

STANDARD = [
    ("mensile", "Mensile"),
    ("bimestrale", "Bimestrale"),
    ("trimestrale", "Trimestrale"),
    ("semestrale", "Semestrale"),
    ("annuale", "Annuale"),
    ("a_chiamata", "A chiamata"),
]


def popola_periodicita(apps, schema_editor):
    Periodicita = apps.get_model("servizi", "Periodicita")
    ContrattoRiga = apps.get_model("servizi", "ContrattoRiga")

    mappa = {}
    for codice, nome in STANDARD:
        obj, _ = Periodicita.objects.get_or_create(nome=nome)
        mappa[codice] = obj
    default = mappa["mensile"]

    for riga in ContrattoRiga.objects.all():
        riga.periodicita_fk = mappa.get(riga.periodicita_vecchia, default)
        riga.save(update_fields=["periodicita_fk"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('servizi', '0030_contratto_nome_remove_periodicita'),
    ]

    operations = [
        migrations.CreateModel(
            name='Periodicita',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, unique=True, verbose_name='Periodicità')),
                ('attivo', models.BooleanField(default=True, verbose_name='Attiva')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Periodicità',
                'verbose_name_plural': 'Periodicità',
                'ordering': ['nome'],
            },
        ),
        migrations.RenameField(
            model_name='contrattoriga',
            old_name='periodicita',
            new_name='periodicita_vecchia',
        ),
        migrations.AddField(
            model_name='contrattoriga',
            name='periodicita_fk',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='righe_contratto_tmp', to='servizi.periodicita',
            ),
        ),
        migrations.RunPython(popola_periodicita, noop),
        migrations.RemoveField(
            model_name='contrattoriga',
            name='periodicita_vecchia',
        ),
        migrations.RenameField(
            model_name='contrattoriga',
            old_name='periodicita_fk',
            new_name='periodicita',
        ),
        migrations.AlterField(
            model_name='contrattoriga',
            name='periodicita',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='righe_contratto', to='servizi.periodicita',
                verbose_name='Periodicità',
            ),
        ),
    ]
