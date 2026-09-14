"""
Prepara lo stato dei moduli (ModuloRegistry) per l'istanza di UN cliente,
dato l'elenco dei moduli che ha acquistato.

Prima versione / fondamenta del workflow "download cliente" (stesso comando
introdotto per em26 — vedi docs/piani_azione/06_istruzioni_copia_cliente.md
in easymod26-main). Va lanciato sul database dedicato del cliente (un'istanza
per cliente, non multi-tenant condiviso).

ESPLICITAMENTE FUORI SCOPE in questa prima versione (da fare a mano finché
non si decide di automatizzarli):
  - branding/logo/nome del cliente nel sito
  - generazione di uno zip/pacchetto scaricabile
  - creazione automatica dell'app Heroku o di un ambiente di deploy
  - migrazione/seed dei dati del cliente

Uso:
    python manage.py package_client --modules anagrafica_r2,servizi,fatturazione_attiva
    python manage.py package_client --database clienteX --modules acquisti,magazzino
    python manage.py package_client --modules servizi --dry-run
"""

from django.core.management.base import BaseCommand, CommandError

from core.module_manager import CORE_MODULES, MODULE_DEPENDENCIES
from core.models_legacy import ModuloRegistry


class Command(BaseCommand):
    help = (
        "Attiva in ModuloRegistry solo i moduli acquistati dal cliente (piu' "
        "le dipendenze richieste e i moduli core), disattiva gli altri. "
        "Prima versione: non gestisce branding, packaging o deploy — solo lo "
        "stato dei moduli sul database target."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--modules",
            required=True,
            help="Elenco separato da virgole dei moduli acquistati (es. servizi,fatturazione_attiva).",
        )
        parser.add_argument(
            "--database",
            default="default",
            help="Alias del database target (il database dedicato del cliente).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra cosa verrebbe attivato/disattivato senza scrivere nulla.",
        )

    def handle(self, *args, **options):
        db = options["database"]
        dry_run = options["dry_run"]
        richiesti = {m.strip() for m in options["modules"].split(",") if m.strip()}

        known_apps = set(CORE_MODULES) | set(MODULE_DEPENDENCIES.keys())
        sconosciuti = richiesti - known_apps
        if sconosciuti:
            raise CommandError(
                f"Moduli sconosciuti (non presenti in core/module_manager.py): "
                f"{', '.join(sorted(sconosciuti))}"
            )

        # Espande l'elenco con le dipendenze richieste (transitivamente) e i core.
        da_attivare = set(CORE_MODULES) | set(richiesti)
        cambiato = True
        while cambiato:
            cambiato = False
            for modulo in list(da_attivare):
                for dep in MODULE_DEPENDENCIES.get(modulo, []):
                    if dep not in da_attivare:
                        da_attivare.add(dep)
                        cambiato = True

        aggiunti_da_dipendenze = da_attivare - set(CORE_MODULES) - richiesti
        if aggiunti_da_dipendenze:
            self.stdout.write(
                self.style.WARNING(
                    f"Dipendenze aggiunte automaticamente: {', '.join(sorted(aggiunti_da_dipendenze))}"
                )
            )

        da_disattivare = known_apps - da_attivare

        self.stdout.write(f"Database target: {db}")
        self.stdout.write(f"Moduli che risulteranno ATTIVI ({len(da_attivare)}): {', '.join(sorted(da_attivare))}")
        self.stdout.write(f"Moduli che risulteranno DISATTIVI ({len(da_disattivare)}): {', '.join(sorted(da_disattivare)) or '(nessuno)'}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n--dry-run: nessuna scrittura effettuata."))
            return

        aggiornati = 0
        for app_name in known_apps:
            attivo_target = app_name in da_attivare
            obj, created = ModuloRegistry.objects.using(db).get_or_create(
                codice=app_name,
                defaults={
                    "nome": app_name.replace("_", " ").title(),
                    "app_name": app_name,
                    "descrizione": f"Modulo {app_name} (descrizione da completare).",
                    "categoria": "base" if app_name in CORE_MODULES else "altro",
                    "attivo": attivo_target,
                    "obbligatorio": app_name in CORE_MODULES,
                },
            )
            if not created and obj.attivo != attivo_target and not obj.obbligatorio:
                obj.attivo = attivo_target
                obj.save(using=db)
                aggiornati += 1

        self.stdout.write(self.style.SUCCESS(f"\nFatto. {aggiornati} righe aggiornate su '{db}'."))
        self.stdout.write(
            self.style.WARNING(
                "Ricorda: questo comando non attiva MODULE_GATING_ENABLED — va fatto "
                "esplicitamente sull'istanza del cliente dopo aver verificato lo stato."
            )
        )
