import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('servizi', '0008_distinta_mezzo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='distinta',
            name='importo_ricevuto',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10,
                null=True, verbose_name='Importo ricevuto',
            ),
        ),
        migrations.AddField(
            model_name='distinta',
            name='chiusa_da',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='distinte_chiuse',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Chiusa da',
            ),
        ),
        migrations.AddField(
            model_name='distinta',
            name='chiusa_il',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Chiusa il'),
        ),
    ]
