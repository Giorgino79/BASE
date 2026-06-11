from django.db import migrations


class Migration(migrations.Migration):
    """
    Applica il DDL di 0016 che non è stato eseguito sul DB di produzione
    (la migrazione era già segnata come applicata ma le tabelle mancano).
    Usa IF NOT EXISTS / ADD COLUMN IF NOT EXISTS per essere idempotente.
    """

    dependencies = [
        ("servizi", "0016_condominostabile_unitaabitativabase_condominioods_stabile"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS servizi_condominiostabile (
                    id BIGSERIAL PRIMARY KEY,
                    nome VARCHAR(200) NOT NULL,
                    indirizzo VARCHAR(300) NOT NULL,
                    prezzo_base DECIMAL(10,2) NOT NULL,
                    note TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS servizi_unitaabitativabase (
                    id BIGSERIAL PRIMARY KEY,
                    nome VARCHAR(200) NOT NULL,
                    importo_override DECIMAL(10,2),
                    stabile_id BIGINT NOT NULL
                        REFERENCES servizi_condominiostabile(id) ON DELETE CASCADE
                );
                ALTER TABLE servizi_condominioods
                    ADD COLUMN IF NOT EXISTS stabile_id BIGINT
                    REFERENCES servizi_condominiostabile(id) ON DELETE SET NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
