from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("servizi", "0015_rigaprodottocondominio_confermato"),
    ]

    operations = [
        migrations.CreateModel(
            name="CondominioStabile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=200, verbose_name="Nome stabile")),
                ("indirizzo", models.CharField(max_length=300, verbose_name="Indirizzo")),
                ("prezzo_base", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Prezzo base per unità", help_text="Prezzo predefinito quando si crea un ODS da questo stabile")),
                ("note", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Stabile",
                "verbose_name_plural": "Stabili",
                "ordering": ["nome"],
            },
        ),
    ]
