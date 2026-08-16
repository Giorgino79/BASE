# Generated manually (ambiente locale privo di dipendenze per eseguire makemigrations)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('magazzino', '0011_caricocisterna'),
    ]

    operations = [
        migrations.AddField(
            model_name='rigacaricocisterna',
            name='litri_inseriti',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='Litri prodotto inseriti'),
            preserve_default=False,
        ),
    ]
