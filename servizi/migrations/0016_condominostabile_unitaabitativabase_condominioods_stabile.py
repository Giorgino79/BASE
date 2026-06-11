import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Crea CondominioStabile, UnitaAbitativaBase e aggiunge stabile a CondominioODS.
    Usa SeparateDatabaseAndState + RunSQL per aggirare il bug Django 5.2 che
    causa ValueError su resolve_related_fields per FK verso modelli creati
    in precedenti migration. Tutto il DDL è in un unico RunSQL per garantire
    l'ordine corretto (condominostabile prima di unitaabitativabase).
    """

    dependencies = [
        ("servizi", "0015_rigaprodottocondominio_confermato"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="CondominioStabile",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("nome", models.CharField(max_length=200, verbose_name="Nome stabile")),
                        ("indirizzo", models.CharField(max_length=300, verbose_name="Indirizzo")),
                        ("prezzo_base", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Prezzo base per unità")),
                        ("note", models.TextField(blank=True)),
                    ],
                    options={
                        "verbose_name": "Stabile",
                        "verbose_name_plural": "Stabili",
                        "ordering": ["nome"],
                    },
                ),
                migrations.CreateModel(
                    name="UnitaAbitativaBase",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("nome", models.CharField(max_length=200, verbose_name="Nome / Intestatario")),
                        ("importo_override", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="Importo specifico")),
                        ("stabile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="unita", to="servizi.condominiostabile")),
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
                        to="servizi.condominiostabile",
                        verbose_name="Stabile",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE servizi_condominiostabile (
                            id BIGSERIAL PRIMARY KEY,
                            nome VARCHAR(200) NOT NULL,
                            indirizzo VARCHAR(300) NOT NULL,
                            prezzo_base DECIMAL(10,2) NOT NULL,
                            note TEXT NOT NULL DEFAULT ''
                        );
                        CREATE INDEX ON servizi_condominiostabile (nome);

                        CREATE TABLE servizi_unitaabitativabase (
                            id BIGSERIAL PRIMARY KEY,
                            nome VARCHAR(200) NOT NULL,
                            importo_override DECIMAL(10,2),
                            stabile_id BIGINT NOT NULL
                                REFERENCES servizi_condominiostabile(id) ON DELETE CASCADE
                        );
                        CREATE INDEX ON servizi_unitaabitativabase (stabile_id);
                        CREATE INDEX ON servizi_unitaabitativabase (nome);

                        ALTER TABLE servizi_condominioods
                            ADD COLUMN stabile_id BIGINT
                            REFERENCES servizi_condominiostabile(id) ON DELETE SET NULL;
                    """,
                    reverse_sql="""
                        ALTER TABLE servizi_condominioods DROP COLUMN IF EXISTS stabile_id;
                        DROP TABLE IF EXISTS servizi_unitaabitativabase;
                        DROP TABLE IF EXISTS servizi_condominiostabile;
                    """,
                ),
            ],
        ),
    ]
