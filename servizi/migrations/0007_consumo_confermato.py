from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('servizi', '0006_distinta'),
    ]

    operations = [
        migrations.AddField(
            model_name='consumomateriale',
            name='confermato',
            field=models.BooleanField(
                default=False,
                verbose_name='Confermato',
                help_text='False = quantità prevista (non scala stock); True = effettivo (scala ScortaMezzo)',
            ),
        ),
    ]
