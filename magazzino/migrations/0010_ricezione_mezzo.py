from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cespiti', '0001_initial'),
        ('magazzino', '0009_prodotto_scorta_minima'),
    ]

    operations = [
        migrations.AddField(
            model_name='ricezione',
            name='mezzo',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ricezioni_mezzo',
                to='cespiti.automezzo',
                verbose_name='Mezzo destinatario',
            ),
        ),
    ]
