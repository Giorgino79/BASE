# Generated manually (ambiente locale privo di dipendenze per eseguire makemigrations)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('servizi', '0029_contrattoriga_periodicita'),
    ]

    operations = [
        migrations.AddField(
            model_name='contratto',
            name='nome',
            field=models.CharField(
                blank=True,
                help_text='Facoltativo — utile per distinguere più contratti dello stesso cliente',
                max_length=200,
                verbose_name='Nome contratto',
            ),
        ),
        migrations.RemoveField(
            model_name='contratto',
            name='periodicita',
        ),
    ]
