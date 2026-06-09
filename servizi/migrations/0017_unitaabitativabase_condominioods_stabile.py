import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("servizi", "0016_condominostabile_unitaabitativabase_condominioods_stabile"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnitaAbitativaBase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=200, verbose_name="Nome / Intestatario")),
                ("importo_override", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="Importo specifico", help_text="Lascia vuoto per usare il prezzo base dello stabile")),
                ("stabile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="unita", to="servizi.condominostabile")),
            ],
            options={
                "verbose_name": "Unità abitativa base",
                "verbose_name_plural": "Unità abitative base",
                "ordering": ["nome"],
            },
        ),
        migrations.AddField(
            model_name="condominioods",
            name="stabile",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ods_set",
                to="servizi.condominostabile",
                verbose_name="Stabile",
            ),
        ),
    ]
