from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anagrafica', '0005_azienda_filiale_zona'),
    ]

    operations = [
        migrations.AddField(
            model_name='azienda',
            name='marchio',
            field=models.CharField(
                blank=True,
                help_text='Nome commerciale / marchio (se diverso dalla ragione sociale)',
                max_length=200,
                verbose_name='Marchio',
            ),
        ),
    ]
