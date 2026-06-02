from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('magazzino', '0001_initial'),
        ('servizi', '0005_ods_righe'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Distinta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField(verbose_name='Data servizi')),
                ('stato', models.CharField(choices=[('aperta', 'Aperta'), ('chiusa', 'Chiusa')], default='aperta', max_length=10, verbose_name='Stato')),
                ('nota', models.TextField(blank=True, verbose_name='Note')),
                ('creata_il', models.DateTimeField(auto_now_add=True)),
                ('creata_da', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='distinte_create', to=settings.AUTH_USER_MODEL)),
                ('tecnico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='distinte', to=settings.AUTH_USER_MODEL, verbose_name='Tecnico')),
            ],
            options={
                'verbose_name': 'Distinta',
                'verbose_name_plural': 'Distinte',
                'ordering': ['-data', '-creata_il'],
            },
        ),
        migrations.AddField(
            model_name='ods',
            name='distinta',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ods_set', to='servizi.distinta', verbose_name='Distinta'),
        ),
        migrations.AddField(
            model_name='ods',
            name='modalita_pagamento',
            field=models.CharField(blank=True, choices=[('contanti', 'Contanti'), ('carta', 'Carta'), ('paypal', 'PayPal'), ('non_incassato', 'Non incassato')], max_length=20, null=True, verbose_name='Modalità pagamento'),
        ),
        migrations.RemoveField(
            model_name='consumomateriale',
            name='descrizione',
        ),
        migrations.AddField(
            model_name='consumomateriale',
            name='prodotto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='consumi_servizi', to='magazzino.prodotto', verbose_name='Prodotto'),
            preserve_default=False,
        ),
    ]
