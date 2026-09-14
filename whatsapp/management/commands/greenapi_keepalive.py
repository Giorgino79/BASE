"""
Management command: greenapi_keepalive
Mantiene attiva la sessione Green API chiamando getStateInstance.
Da schedulare periodicamente (es. ogni 10 minuti) sullo scheduler della piattaforma.
"""

from django.core.management.base import BaseCommand

from whatsapp.services import is_configured, check_authorized


class Command(BaseCommand):
    help = "Mantiene attiva la connessione Green API (keep-alive)"

    def handle(self, *args, **options):
        if not is_configured():
            self.stdout.write(self.style.WARNING("Green API non configurata — skip"))
            return

        ok, err = check_authorized()
        if ok:
            self.stdout.write(self.style.SUCCESS("Green API OK — istanza autorizzata"))
        else:
            self.stdout.write(self.style.ERROR(f"Green API — {err}"))
