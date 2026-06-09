import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Crea UnitaAbitativaBase e aggiunge stabile a CondominioODS.
    Usa SeparateDatabaseAndState + RunSQL per aggirare un bug di risoluzione
    FK in Django 5.2 quando il target è in una migration precedente.
    """

    dependencies = [
        ("servizi", "0016_condominostabile_unitaabitativabase_condominioods_stabile"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="UnitaAbitativaBase",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("nome", models.CharField(max_length=200, verbose_name="Nome / Intestatario")),
                        ("importo_override", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="Importo specifico")),
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
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ods_set",
                        to="servizi.condominostabile",
                        verbose_name="Stabile",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE servizi_unitaabitativabase (
                            id BIGSERIAL PRIMARY KEY,
                            nome VARCHAR(200) NOT NULL,
                            importo_override DECIMAL(10,2),
                            stabile_id BIGINT NOT NULL
                                REFERENCES servizi_condominostabile(id) ON DELETE CASCADE
                        );
                        CREATE INDEX ON servizi_unitaabitativabase (stabile_id);
                        CREATE INDEX ON servizi_unitaabitativabase (nome);
                        ALTER TABLE servizi_condominioods
                            ADD COLUMN stabile_id BIGINT
                            REFERENCES servizi_condominostabile(id) ON DELETE SET NULL;
                    """,
                    reverse_sql="""
                        DROP TABLE IF EXISTS servizi_unitaabitativabase;
                        ALTER TABLE servizi_condominioods DROP COLUMN IF EXISTS stabile_id;
                    """,
                ),
            ],
        ),
    ]
