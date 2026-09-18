# Generated manually (ambiente locale privo di dipendenze per eseguire makemigrations)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('servizi', '0028_alter_distinta_mezzo'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrattoriga',
            name='periodicita',
            field=models.CharField(
                choices=[
                    ('mensile', 'Mensile'),
                    ('bimestrale', 'Bimestrale'),
                    ('trimestrale', 'Trimestrale'),
                    ('semestrale', 'Semestrale'),
                    ('annuale', 'Annuale'),
                    ('a_chiamata', 'A chiamata'),
                ],
                default='mensile',
                max_length=20,
                verbose_name='Periodicità',
            ),
        ),
    ]
