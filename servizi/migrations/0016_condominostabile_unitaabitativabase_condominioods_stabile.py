import django.db.models.deletion
from django.db import migrations, models


def create_stabile_tables(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    db = schema_editor.connection

    # Evita di ricreare tabelle già esistenti (idempotente)
    existing = db.introspection.table_names()

    if 'servizi_condominiostabile' not in existing:
        if vendor == 'sqlite':
            schema_editor.execute(
                "CREATE TABLE servizi_condominiostabile ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "nome VARCHAR(200) NOT NULL,"
                "indirizzo VARCHAR(300) NOT NULL,"
                "prezzo_base DECIMAL(10,2) NOT NULL,"
                "note TEXT NOT NULL DEFAULT ''"
                ")"
            )
            schema_editor.execute("CREATE INDEX idx_svz_stabile_nome ON servizi_condominiostabile (nome)")
        else:
            schema_editor.execute(
                "CREATE TABLE servizi_condominiostabile ("
                "id BIGSERIAL PRIMARY KEY,"
                "nome VARCHAR(200) NOT NULL,"
                "indirizzo VARCHAR(300) NOT NULL,"
                "prezzo_base DECIMAL(10,2) NOT NULL,"
                "note TEXT NOT NULL DEFAULT ''"
                ")"
            )
            schema_editor.execute("CREATE INDEX ON servizi_condominiostabile (nome)")

    if 'servizi_unitaabitativabase' not in existing:
        if vendor == 'sqlite':
            schema_editor.execute(
                "CREATE TABLE servizi_unitaabitativabase ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "nome VARCHAR(200) NOT NULL,"
                "importo_override DECIMAL(10,2),"
                "stabile_id INTEGER NOT NULL REFERENCES servizi_condominiostabile(id)"
                ")"
            )
            schema_editor.execute("CREATE INDEX idx_svz_unita_stabile ON servizi_unitaabitativabase (stabile_id)")
            schema_editor.execute("CREATE INDEX idx_svz_unita_nome ON servizi_unitaabitativabase (nome)")
        else:
            schema_editor.execute(
                "CREATE TABLE servizi_unitaabitativabase ("
                "id BIGSERIAL PRIMARY KEY,"
                "nome VARCHAR(200) NOT NULL,"
                "importo_override DECIMAL(10,2),"
                "stabile_id BIGINT NOT NULL REFERENCES servizi_condominiostabile(id) ON DELETE CASCADE"
                ")"
            )
            schema_editor.execute("CREATE INDEX ON servizi_unitaabitativabase (stabile_id)")
            schema_editor.execute("CREATE INDEX ON servizi_unitaabitativabase (nome)")

    # Aggiunge stabile_id a condominioods solo se non esiste già
    with db.cursor() as cursor:
        cols = [c.name for c in db.introspection.get_table_description(cursor, 'servizi_condominioods')]
    if 'stabile_id' not in cols:
        if vendor == 'sqlite':
            schema_editor.execute(
                "ALTER TABLE servizi_condominioods "
                "ADD COLUMN stabile_id INTEGER REFERENCES servizi_condominiostabile(id)"
            )
        else:
            schema_editor.execute(
                "ALTER TABLE servizi_condominioods "
                "ADD COLUMN stabile_id BIGINT "
                "REFERENCES servizi_condominiostabile(id) ON DELETE SET NULL"
            )


class Migration(migrations.Migration):
    """
    Crea CondominioStabile, UnitaAbitativaBase e aggiunge stabile a CondominioODS.
    Usa SeparateDatabaseAndState + RunPython (cross-database: SQLite e PostgreSQL).
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
                migrations.RunPython(create_stabile_tables, reverse_code=migrations.RunPython.noop),
            ],
        ),
    ]
