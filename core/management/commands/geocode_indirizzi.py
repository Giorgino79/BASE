"""
Management command: geocode_indirizzi
Geocodifica una tantum i Filiale/Privato/CondominioODS esistenti privi di lat/lng.
Da lanciare a mano dopo il deploy: heroku run python manage.py geocode_indirizzi
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from core.geocoding import geocode, is_configured


class Command(BaseCommand):
    help = "Geocodifica gli indirizzi esistenti senza latitudine/longitudine"

    def handle(self, *args, **options):
        if not is_configured():
            self.stdout.write(self.style.WARNING(
                "GOOGLE_MAPS_GEOCODING_API_KEY non configurata — skip"
            ))
            return

        from anagrafica_r2.models import Filiale, Privato
        from servizi.models import CondominioODS

        missing = Q(latitudine__isnull=True) | Q(longitudine__isnull=True)

        ok = failed = 0

        for filiale in Filiale.objects.filter(missing).exclude(indirizzo=""):
            coords = geocode(filiale.get_indirizzo_completo())
            if coords:
                filiale.latitudine, filiale.longitudine = coords
                filiale.save(update_fields=["latitudine", "longitudine"])
                ok += 1
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(
                    f"Filiale #{filiale.pk} ({filiale}) — indirizzo non geocodificato: {filiale.get_indirizzo_completo()!r}"
                ))

        for privato in Privato.objects.filter(missing).exclude(indirizzo=""):
            coords = geocode(privato.get_indirizzo_completo())
            if coords:
                privato.latitudine, privato.longitudine = coords
                privato.save(update_fields=["latitudine", "longitudine"])
                ok += 1
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(
                    f"Privato #{privato.pk} ({privato}) — indirizzo non geocodificato: {privato.get_indirizzo_completo()!r}"
                ))

        for condominio in CondominioODS.objects.filter(missing).exclude(indirizzo=""):
            coords = geocode(condominio.indirizzo)
            if coords:
                condominio.latitudine, condominio.longitudine = coords
                condominio.save(update_fields=["latitudine", "longitudine"])
                ok += 1
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(
                    f"CondominioODS #{condominio.pk} ({condominio}) — indirizzo non geocodificato: {condominio.indirizzo!r}"
                ))

        self.stdout.write(self.style.SUCCESS(f"Geocoding completato: {ok} ok, {failed} falliti."))
