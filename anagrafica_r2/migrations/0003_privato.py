from django.db import migrations, models
import django.urls


class Migration(migrations.Migration):

    dependencies = [
        ('anagrafica', '0002_fornitore'),
    ]

    operations = [
        migrations.CreateModel(
            name='Privato',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome')),
                ('cognome', models.CharField(max_length=100, verbose_name='Cognome')),
                ('telefono', models.CharField(max_length=20, verbose_name='Telefono')),
                ('indirizzo', models.CharField(max_length=200, verbose_name='Indirizzo (via)')),
                ('zona', models.CharField(max_length=100, verbose_name='Zona / Città')),
                ('codice_fiscale', models.CharField(blank=True, max_length=16, verbose_name='Codice Fiscale')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='Email')),
                ('cap', models.CharField(blank=True, max_length=5, verbose_name='CAP')),
                ('provincia', models.CharField(blank=True, max_length=5, verbose_name='Provincia')),
                ('attivo', models.BooleanField(default=True, verbose_name='Attivo')),
                ('note', models.TextField(blank=True, verbose_name='Note')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Cliente Privato',
                'verbose_name_plural': 'Clienti Privati',
                'ordering': ['cognome', 'nome'],
            },
        ),
    ]
