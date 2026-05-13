"""
Django command per verificare stato moduli
"""

from django.core.management.base import BaseCommand
from core.module_manager import ModuleManager


class Command(BaseCommand):
    help = "Verifica stato moduli e dipendenze"

    def add_arguments(self, parser):
        parser.add_argument(
            '--module',
            type=str,
            help='Verifica un modulo specifico',
        )

        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Output dettagliato',
        )

    def handle(self, *args, **options):
        module_name = options.get('module')
        verbose = options.get('verbose', False)

        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("VERIFICA MODULI MODULARBEF"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")

        if module_name:
            # Verifica singolo modulo
            self._check_single_module(module_name, verbose)
        else:
            # Verifica tutti i moduli
            self._check_all_modules(verbose)

    def _check_single_module(self, module_name, verbose):
        """Verifica un singolo modulo"""
        info = ModuleManager.get_module_info(module_name)

        if not info:
            self.stdout.write(
                self.style.ERROR(f"❌ Modulo '{module_name}' non trovato")
            )
            return

        self.stdout.write(self.style.SUCCESS(f"📦 Modulo: {module_name}"))
        self.stdout.write("")

        # Info base
        self.stdout.write(f"  Versione: {info['version']}")
        self.stdout.write(f"  Core: {'Sì' if info['is_core'] else 'No'}")
        self.stdout.write(f"  Installato: {'Sì' if info['is_installed'] else 'No'}")

        # Dipendenze
        if info['dependencies']:
            self.stdout.write(f"  Dipendenze: {', '.join(info['dependencies'])}")

            # Verifica dipendenze
            ok, missing = ModuleManager.check_dependencies(module_name)
            if ok:
                self.stdout.write(self.style.SUCCESS("  ✓ Tutte le dipendenze soddisfatte"))
            else:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Dipendenze mancanti: {', '.join(missing)}")
                )
        else:
            self.stdout.write("  Dipendenze: Nessuna")

        self.stdout.write("")

    def _check_all_modules(self, verbose):
        """Verifica tutti i moduli"""

        # Moduli installati
        installed = ModuleManager.get_installed_modules()
        all_modules_info = ModuleManager.get_all_modules_info()

        self.stdout.write(
            self.style.SUCCESS(f"📦 Moduli totali conosciuti: {len(all_modules_info)}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"📦 Moduli installati: {len(installed)}")
        )
        self.stdout.write("")

        # Lista moduli installati
        self.stdout.write(self.style.WARNING("🔹 MODULI INSTALLATI:"))
        self.stdout.write("")

        core_modules = []
        optional_modules = []

        for info in all_modules_info:
            if info['is_installed']:
                if info['is_core']:
                    core_modules.append(info)
                else:
                    optional_modules.append(info)

        # Moduli core
        if core_modules:
            self.stdout.write("  📌 CORE (Obbligatori):")
            for info in core_modules:
                deps = f" (deps: {', '.join(info['dependencies'])})" if verbose and info['dependencies'] else ""
                self.stdout.write(
                    f"    ✓ {info['name']:20s} v{info['version']:10s}{deps}"
                )
            self.stdout.write("")

        # Moduli opzionali
        if optional_modules:
            self.stdout.write("  📦 OPZIONALI:")
            for info in optional_modules:
                deps = f" (deps: {', '.join(info['dependencies'])})" if verbose and info['dependencies'] else ""
                self.stdout.write(
                    f"    ✓ {info['name']:20s} v{info['version']:10s}{deps}"
                )
            self.stdout.write("")

        # Moduli NON installati
        not_installed = [info for info in all_modules_info if not info['is_installed']]
        if not_installed:
            self.stdout.write(self.style.WARNING("🔸 MODULI NON INSTALLATI:"))
            self.stdout.write("")
            for info in not_installed:
                core_badge = "[CORE]" if info['is_core'] else "[OPTIONAL]"
                self.stdout.write(
                    f"    ○ {info['name']:20s} v{info['version']:10s} {core_badge}"
                )
            self.stdout.write("")

        # Verifica dipendenze
        self.stdout.write(self.style.WARNING("🔍 VERIFICA DIPENDENZE:"))
        self.stdout.write("")

        issues = ModuleManager.check_all_dependencies()

        if issues:
            self.stdout.write(self.style.ERROR("❌ PROBLEMI RILEVATI:"))
            self.stdout.write("")
            for module, missing in issues.items():
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {module}: mancano {', '.join(missing)}")
                )
            self.stdout.write("")
        else:
            self.stdout.write(self.style.SUCCESS("✅ Tutte le dipendenze soddisfatte!"))
            self.stdout.write("")

        # Summary
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("RIEPILOGO:"))
        self.stdout.write(f"  • Moduli core installati: {len(core_modules)}")
        self.stdout.write(f"  • Moduli opzionali installati: {len(optional_modules)}")
        self.stdout.write(f"  • Moduli non installati: {len(not_installed)}")
        self.stdout.write(f"  • Problemi dipendenze: {len(issues)}")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")
