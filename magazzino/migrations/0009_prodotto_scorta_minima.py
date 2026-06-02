from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('magazzino', '0008_bolla_firmata_ricezione'),
    ]

    operations = [
        migrations.AddField(
            model_name='prodotto',
            name='scorta_minima',
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text='Soglia sotto cui il prodotto compare nell\'avviso scorte basse',
                max_digits=10,
                null=True,
                verbose_name='Scorta minima',
            ),
        ),
    ]
