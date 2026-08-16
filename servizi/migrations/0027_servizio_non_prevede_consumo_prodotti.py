# Generated manually (ambiente locale privo di dipendenze per eseguire makemigrations)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('servizi', '0026_consumomateriale_diluizione_percentuale'),
    ]

    operations = [
        migrations.AddField(
            model_name='servizio',
            name='non_prevede_consumo_prodotti',
            field=models.BooleanField(default=False, help_text="Se attivo, l'ODS può essere chiuso senza indicare prodotti utilizzati o litri cisterna consumati", verbose_name='Servizio che non prevede consumo di prodotti'),
        ),
    ]
