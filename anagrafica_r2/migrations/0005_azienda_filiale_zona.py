from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anagrafica', '0004_privato_citta'),
    ]

    operations = [
        # Azienda: aggiungi zona (obbligatorio, default '' per righe esistenti)
        migrations.AddField(
            model_name='azienda',
            name='zona',
            field=models.CharField(default='', max_length=100, verbose_name='Zona'),
            preserve_default=False,
        ),
        # Filiale: aggiungi zona, poi rimuovi regione
        migrations.AddField(
            model_name='filiale',
            name='zona',
            field=models.CharField(default='', max_length=100, verbose_name='Zona'),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='filiale',
            name='regione',
        ),
    ]
