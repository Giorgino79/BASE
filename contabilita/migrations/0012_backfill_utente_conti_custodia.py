from django.conf import settings
from django.db import migrations


def collega_utenti(apps, schema_editor):
    """
    I conti custodia creati prima di questa migrazione (dal signal
    on_user_creato, che allora non impostava ancora `utente`) restano
    orfani: li ricollega per nome, stessa costruzione usata dal signal
    (nome completo, o username se il nome è vuoto).
    """
    ContoContabile = apps.get_model('contabilita', 'ContoContabile')
    User = apps.get_model(settings.AUTH_USER_MODEL)

    utenti_per_nome = {}
    for user in User.objects.all():
        nome = f'{user.first_name} {user.last_name}'.strip() or user.username
        utenti_per_nome.setdefault(nome, user)

    for conto in ContoContabile.objects.filter(tipo='custodia', utente__isnull=True):
        utente = utenti_per_nome.get(conto.nome)
        if utente:
            conto.utente_id = utente.pk
            conto.save(update_fields=['utente'])


def scollega_utenti(apps, schema_editor):
    # Nessun rollback: ricollegare a mano non perde nulla di irreversibile.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('contabilita', '0011_remove_passaggiocassa_forma_and_more'),
    ]

    operations = [
        migrations.RunPython(collega_utenti, scollega_utenti),
    ]
