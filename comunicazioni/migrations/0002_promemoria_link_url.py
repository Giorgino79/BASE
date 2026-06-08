from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comunicazioni', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='promemoria',
            name='link_url',
            field=models.CharField(
                blank=True,
                help_text='URL della pagina correlata (es. ODS, cliente, distinta)',
                max_length=500,
                verbose_name='Link oggetto',
            ),
        ),
    ]
