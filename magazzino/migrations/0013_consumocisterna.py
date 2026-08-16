# Generated manually (ambiente locale privo di dipendenze per eseguire makemigrations)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cespiti', '0001_initial'),
        ('servizi', '0026_consumomateriale_diluizione_percentuale'),
        ('magazzino', '0012_rigacaricocisterna_litri_inseriti'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsumoCisterna',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('litri_consumati', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Litri consumati')),
                ('data', models.DateTimeField(auto_now_add=True, verbose_name='Data/ora consumo')),
                ('mezzo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consumi_cisterna', to='cespiti.automezzo')),
                ('ods', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consumi_cisterna', to='servizi.ods')),
            ],
            options={
                'verbose_name': 'Consumo cisterna',
                'verbose_name_plural': 'Consumi cisterna',
                'ordering': ['-data'],
            },
        ),
    ]
