"""
Crea i conti contabili mancanti per le anagrafiche già esistenti.

I signal in contabilita/signals.py creano il conto solo alla registrazione di
una nuova anagrafica: questo comando copre chi era già a sistema.

Usage:
    python manage.py sync_conti_anagrafica [--dry-run]
"""

from django.core.management.base import BaseCommand

from anagrafica_r2.models import Azienda, Fornitore, Privato
from contabilita.models import ContoContabile


class Command(BaseCommand):
    help = "Crea i conti cliente/fornitore mancanti dalle anagrafiche esistenti"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra cosa verrebbe creato senza scrivere nel DB',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        gruppi = [
            ('Aziende',   Azienda.objects.all(),   ContoContabile.Tipo.CLIENTE),
            ('Privati',   Privato.objects.all(),   ContoContabile.Tipo.CLIENTE),
            ('Fornitori', Fornitore.objects.all(), ContoContabile.Tipo.FORNITORE),
        ]

        totale_creati = 0

        for etichetta, qs, tipo in gruppi:
            esistenti = set(
                ContoContabile.objects.filter(tipo=tipo).values_list('nome', flat=True)
            )
            mancanti = []
            for obj in qs:
                nome = str(obj).strip()
                if nome and nome not in esistenti:
                    mancanti.append(nome)
                    esistenti.add(nome)

            self.stdout.write(f"{etichetta}: {qs.count()} in anagrafica, {len(mancanti)} conti da creare")
            for nome in mancanti:
                self.stdout.write(f"  + [{tipo}] {nome}")
                if not dry_run:
                    ContoContabile.objects.get_or_create(tipo=tipo, nome=nome)
            totale_creati += len(mancanti)

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\n--dry-run: {totale_creati} conti NON creati."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n{totale_creati} conti creati."))
