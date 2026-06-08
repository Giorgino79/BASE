from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('servizi', '0014_contratto_filiale_riga'),
    ]

    operations = [
        migrations.AddField(
            model_name='rigaprodottocondominio',
            name='confermato',
            field=models.BooleanField(
                default=False,
                verbose_name='Confermato',
                help_text='True = quantità già scalata da ScortaMezzo',
            ),
        ),
    ]
