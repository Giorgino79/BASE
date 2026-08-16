# Generated manually (ambiente locale privo di dotenv per eseguire makemigrations)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('servizi', '0025_distinta_importo_os2_incassato'),
    ]

    operations = [
        migrations.AddField(
            model_name='consumomateriale',
            name='diluizione_percentuale',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Solo per prodotti in litri; modificabile solo da un amministratore.', max_digits=5, null=True, verbose_name='Diluizione (%)'),
        ),
    ]
