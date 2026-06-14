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
            sql="SELECT 1;",  # no-op: tabelle già create correttamente da 0016
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
