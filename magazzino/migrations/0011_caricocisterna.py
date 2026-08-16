# Generated manually (ambiente locale privo di dipendenze per eseguire makemigrations)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cespiti', '0001_initial'),
        ('magazzino', '0010_ricezione_mezzo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CaricoCisterna',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('litri_acqua', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Litri acqua caricati')),
                ('note', models.CharField(blank=True, max_length=300, verbose_name='Note')),
                ('data', models.DateTimeField(auto_now_add=True, verbose_name='Data/ora carico')),
                ('mezzo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='carichi_cisterna', to='cespiti.automezzo')),
                ('operatore', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='carichi_cisterna', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Carico cisterna',
                'verbose_name_plural': 'Carichi cisterna',
                'ordering': ['-data'],
            },
        ),
        migrations.CreateModel(
            name='RigaCaricoCisterna',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('percentuale_diluizione', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='Diluizione (%)')),
                ('carico', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='righe', to='magazzino.caricocisterna')),
                ('prodotto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='righe_carico_cisterna', to='magazzino.prodotto', verbose_name='Prodotto utilizzato')),
            ],
            options={
                'verbose_name': 'Riga carico cisterna',
                'verbose_name_plural': 'Righe carico cisterna',
            },
        ),
    ]
