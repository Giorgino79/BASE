from django.conf import settings
from django.db import migrations


def crea_conti_custodia(apps, schema_editor):
    """
    Il receiver on_user_creato (contabilita/signals.py) crea il conto di
    custodia solo per gli utenti creati da qui in avanti: senza questo
    backfill, tutti gli utenti già esistenti al momento del rilascio
    resterebbero senza conto.
    """
    User = apps.get_model(settings.AUTH_USER_MODEL)
    ContoContabile = apps.get_model('contabilita', 'ContoContabile')

    for user in User.objects.all():
        # apps.get_model restituisce un modello storico: niente metodi
        # custom come get_full_name(), va ricostruito a mano.
        nome = (f'{user.first_name} {user.last_name}'.strip() or user.username or '').strip()
        if not nome:
            continue
        ContoContabile.objects.get_or_create(tipo='custodia', nome=nome)


def rimuovi_conti_custodia(apps, schema_editor):
    # Irreversibile per scelta: un conto già usato in movimenti non va
    # cancellato da una migration all'indietro, e distinguere "mai usato"
    # da "usato" qui non vale la complessità — il rollback resta manuale.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('contabilita', '0009_alter_contocontabile_tipo_passaggiocassa'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(crea_conti_custodia, rimuovi_conti_custodia),
    ]
