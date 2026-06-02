from django.db import migrations, models
import django.db.models.deletion


def crea_righe_da_ods(apps, schema_editor):
    """Converte ogni ODS esistente nella prima riga del nuovo modello ODSRiga."""
    ODS = apps.get_model('servizi', 'ODS')
    ODSRiga = apps.get_model('servizi', 'ODSRiga')
    for ods in ODS.objects.all():
        if ods.servizio_id:
            ODSRiga.objects.create(
                ods=ods,
                servizio_id=ods.servizio_id,
                prezzo=ods.prezzo,
                contratto_filiale_id=ods.contratto_filiale_id,
                ordine=0,
                note="",
            )


class Migration(migrations.Migration):

    dependencies = [
        ('servizi', '0004_ods_assistente'),
    ]

    operations = [
        migrations.CreateModel(
            name='ODSRiga',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ordine', models.PositiveSmallIntegerField(default=0, verbose_name='Ordine')),
                ('prezzo', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Prezzo')),
                ('note', models.CharField(blank=True, max_length=300, verbose_name='Note')),
                ('contratto_filiale', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='righe_ods', to='servizi.contrattofiliale', verbose_name='Contratto applicato')),
                ('ods', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='righe', to='servizi.ods', verbose_name='ODS')),
                ('servizio', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='righe_ods', to='servizi.servizio', verbose_name='Servizio')),
            ],
            options={
                'verbose_name': 'Riga ODS',
                'verbose_name_plural': 'Righe ODS',
                'ordering': ['ordine', 'pk'],
            },
        ),
        migrations.CreateModel(
            name='ConsumoMateriale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descrizione', models.CharField(max_length=200, verbose_name='Descrizione')),
                ('quantita', models.DecimalField(decimal_places=3, default=1, max_digits=10, verbose_name='Quantità')),
                ('note', models.CharField(blank=True, max_length=300, verbose_name='Note')),
                ('riga', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consumi', to='servizi.odsriga', verbose_name='Riga ODS')),
            ],
            options={
                'verbose_name': 'Consumo materiale',
                'verbose_name_plural': 'Consumi materiali',
            },
        ),
        migrations.RunPython(crea_righe_da_ods, migrations.RunPython.noop),
        migrations.RemoveField(model_name='ods', name='contratto_filiale'),
        migrations.RemoveField(model_name='ods', name='prezzo'),
        migrations.RemoveField(model_name='ods', name='servizio'),
    ]
