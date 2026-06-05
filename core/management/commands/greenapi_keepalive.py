"""
Management command: greenapi_keepalive
Mantiene attiva la sessione Green API chiamando getStateInstance.
Da schedulare ogni 10 minuti su Heroku Scheduler.
"""

from django.core.management.base import BaseCommand
from core.whatsapp_sender import check_authorized, _credentials
import requests
from core.whatsapp_sender import GREENAPI_BASE


class Command(BaseCommand):
    help = "Mantiene attiva la connessione Green API (keep-alive)"

    def handle(self, *args, **options):
        iid, token = _credentials()
        if not iid or not token:
            self.stdout.write(self.style.WARNING("Green API non configurata — skip"))
            return

        ok, err = check_authorized()
        if ok:
            self.stdout.write(self.style.SUCCESS(f"Green API OK — istanza {iid} autorizzata"))
        else:
            self.stdout.write(self.style.ERROR(f"Green API — {err}"))
