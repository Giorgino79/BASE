import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cespiti', '0001_initial'),
        ('servizi', '0007_consumo_confermato'),
    ]

    operations = [
        migrations.AddField(
            model_name='distinta',
            name='mezzo',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='distinte_mezzo',
                to='cespiti.automezzo',
                verbose_name='Mezzo',
            ),
        ),
    ]
