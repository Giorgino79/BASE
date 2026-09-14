"""
Sincronizza core.models_legacy.ModuloRegistry con core.module_manager
(CORE_MODULES / MODULE_DEPENDENCIES / MODULE_VERSIONS).

Idempotente e SICURO su un'installazione già in uso: crea una riga per ogni
app conosciuta che non esiste ancora, con attivo=True (comportamento identico
a "nessun filtro" finché non si decide di curare il registry per un cliente
specifico) — non tocca MAI il campo `attivo` di una riga già esistente, quindi
rilanciarlo non spegne mai nulla.

Uso:
    python manage.py sync_module_registry
    python manage.py sync_module_registry --database clienteX
"""

from django.core.management.base import BaseCommand

from core.module_manager import CORE_MODULES, MODULE_DEPENDENCIES, MODULE_VERSIONS
from core.models_legacy import ModuloRegistry


class Command(BaseCommand):
    help = (
        "Crea in ModuloRegistry le righe mancanti per le app conosciute in "
        "module_manager.py. Non modifica righe già esistenti (mai disattiva "
        "moduli già attivi)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default="default",
            help="Alias del database target (utile per preparare l'istanza di un cliente).",
        )

    def handle(self, *args, **options):
        db = options["database"]
        known_apps = sorted(set(CORE_MODULES) | set(MODULE_DEPENDENCIES.keys()))

        creati, esistenti = 0, 0
        for app_name in known_apps:
            obj, created = ModuloRegistry.objects.using(db).get_or_create(
                codice=app_name,
                defaults={
                    "nome": app_name.replace("_", " ").title(),
                    "app_name": app_name,
                    "descrizione": f"Modulo {app_name} (descrizione da completare).",
                    "categoria": "base" if app_name in CORE_MODULES else "altro",
                    "attivo": True,
                    "obbligatorio": app_name in CORE_MODULES,
                    "versione": MODULE_VERSIONS.get(app_name, "1.0.0"),
                    "dipendenze": MODULE_DEPENDENCIES.get(app_name, []),
                },
            )
            if created:
                creati += 1
                self.stdout.write(self.style.SUCCESS(f"+ creato: {app_name}"))
            else:
                esistenti += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nFatto. {creati} righe create, {esistenti} già esistenti (invariate)."
            )
        )
