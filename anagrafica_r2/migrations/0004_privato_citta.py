from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anagrafica', '0003_privato'),
    ]

    operations = [
        migrations.AddField(
            model_name='privato',
            name='citta',
            field=models.CharField(default='', max_length=100, verbose_name='Città'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='privato',
            name='zona',
            field=models.CharField(max_length=100, verbose_name='Zona'),
        ),
    ]
