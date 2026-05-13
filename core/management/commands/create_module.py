"""
Django management command to create new app from template.

Usage:
    python manage.py create_module vendite --model Ordine --with-crud --with-pdf --with-qr-code
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = "Crea una nuova app Django da template con opzioni configurabili"

    def add_arguments(self, parser):
        parser.add_argument(
            "app_name", type=str, help="Nome della nuova app (es: vendite)"
        )

        parser.add_argument(
            "--model",
            type=str,
            default="Item",
            help="Nome del model principale (es: Ordine)",
        )

        parser.add_argument(
            "--with-crud", action="store_true", help="Includi CRUD completo (default)"
        )

        parser.add_argument(
            "--with-allegati",
            action="store_true",
            help="Aggiungi AllegatiMixin al model",
        )

        parser.add_argument(
            "--with-pdf", action="store_true", help="Aggiungi PDFMixin e view PDF"
        )

        parser.add_argument(
            "--with-qr-code",
            action="store_true",
            help="Aggiungi QRCodeMixin e view QR Code",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Sovrascrive app esistente (attenzione!)",
        )

        parser.add_argument(
            "--with-api",
            action="store_true",
            help="Aggiungi DRF serializers e viewsets",
        )

        parser.add_argument(
            "--with-dashboard",
            action="store_true",
            help="Aggiungi dashboard view",
        )

        parser.add_argument(
            "--with-export",
            action="store_true",
            help="Aggiungi export PDF/Excel",
        )

        parser.add_argument(
            "--core-module",
            action="store_true",
            help="Marca come modulo core obbligatorio",
        )

        parser.add_argument(
            "--auto-install",
            action="store_true",
            help="Aggiungi automaticamente a INSTALLED_APPS (richiede conferma)",
        )

        parser.add_argument(
            "--auto-migrate",
            action="store_true",
            help="Esegui makemigrations e migrate automaticamente",
        )

    def handle(self, *args, **options):
        app_name = options["app_name"].lower()
        model_name = options["model"]
        force = options["force"]

        # Validazione
        if not app_name.isidentifier():
            raise CommandError(f"'{app_name}' non è un nome Python valido")

        if not model_name.isidentifier():
            raise CommandError(f"'{model_name}' non è un nome Python valido")

        # Paths
        base_dir = Path(settings.BASE_DIR)
        template_dir = base_dir / "_app_template"
        target_dir = base_dir / app_name

        # Verifica template esista
        if not template_dir.exists():
            raise CommandError(
                f"Template directory non trovata: {template_dir}\n"
                "Assicurati che _app_template/ esista nella root del progetto."
            )

        # Verifica app non esista già
        if target_dir.exists() and not force:
            raise CommandError(
                f"App '{app_name}' esiste già. Usa --force per sovrascrivere."
            )

        self.stdout.write(f"Creazione app '{app_name}' con model '{model_name}'...")

        # Prepara placeholders
        placeholders = self._prepare_placeholders(
            app_name, model_name, options
        )

        # Copia e processa template
        self._copy_and_process_template(template_dir, target_dir, placeholders, force)

        # Post-processing: rimuovi features non richieste
        self._cleanup_optional_features(target_dir, options)

        # Aggiorna documentazione con date
        self._update_documentation(target_dir, app_name, model_name, options)

        # Verifica dipendenze
        self._check_dependencies(app_name)

        # Post-creation tasks
        if options.get("auto_migrate"):
            self._run_migrations(app_name)

        # Istruzioni finali
        self._print_success_message(app_name, model_name)

    def _prepare_placeholders(self, app_name, model_name, options):
        """Prepara dictionary di placeholder -> replacement"""
        model_lower = model_name.lower()
        app_capital = app_name.capitalize()

        # Plurale semplice (aggiungi 'i' o 's')
        if model_name.endswith("e"):
            model_plural = model_name + "i"
        elif model_name.endswith("a"):
            model_plural = model_name[:-1] + "e"
        else:
            model_plural = model_name + "i"

        placeholders = {
            "APP_NAME": app_name,
            "APP_NAME_CAPITAL": app_capital,
            "APP_VERBOSE_NAME": app_capital,
            "MODEL_NAME": model_name,
            "MODEL_NAME_lower": model_lower,
            "MODEL_VERBOSE_NAME": model_name,
            "MODEL_VERBOSE_NAME_PLURAL": model_plural,
            "MODEL_DESCRIPTION": f"Model per gestire {model_plural.lower()}",
            "_app_template": app_name,  # Per nomi directory/file
        }

        return placeholders

    def _copy_and_process_template(self, template_dir, target_dir, placeholders, force):
        """Copia template e sostituisce placeholders"""

        if target_dir.exists() and force:
            shutil.rmtree(target_dir)

        shutil.copytree(template_dir, target_dir)

        # Rinomina directory template
        old_template_dir = target_dir / "templates" / "_app_template"
        new_template_dir = target_dir / "templates" / placeholders["APP_NAME"]
        if old_template_dir.exists():
            old_template_dir.rename(new_template_dir)

        old_static_dir = target_dir / "static" / "_app_template"
        new_static_dir = target_dir / "static" / placeholders["APP_NAME"]
        if old_static_dir.exists():
            old_static_dir.rename(new_static_dir)

        # Processa tutti i file
        for root, dirs, files in os.walk(target_dir):
            for filename in files:
                if filename.endswith((".py", ".html", ".md")):
                    filepath = Path(root) / filename
                    self._process_file(filepath, placeholders)

                # Rinomina file con placeholder
                if "MODEL_NAME_lower" in filename:
                    old_path = Path(root) / filename
                    new_filename = filename.replace(
                        "MODEL_NAME_lower", placeholders["MODEL_NAME_lower"]
                    )
                    new_path = Path(root) / new_filename
                    old_path.rename(new_path)

        self.stdout.write(self.style.SUCCESS(f"✓ Template copiato in {target_dir}"))

    def _process_file(self, filepath, placeholders):
        """Sostituisce placeholders in un file"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Sostituisci tutti i placeholders
            for placeholder, replacement in placeholders.items():
                content = content.replace(placeholder, replacement)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Warning: Errore processing {filepath}: {e}")
            )

    def _cleanup_optional_features(self, target_dir, options):
        """Rimuove features non richieste dal codice"""

        models_file = target_dir / "models.py"

        if models_file.exists():
            with open(models_file, "r") as f:
                content = f.read()

            # Se non richiesti, commenta i mixins
            if not options.get("with_allegati"):
                content = content.replace(
                    "from core.mixins import AllegatiMixin",
                    "# from core.mixins import AllegatiMixin",
                )

            if not options.get("with_pdf"):
                content = content.replace(
                    "from core.mixins import", "# from core.mixins import"
                ).replace("PDFMixin", "# PDFMixin")

            if not options.get("with_qr_code"):
                content = content.replace("QRCodeMixin", "# QRCodeMixin")

            with open(models_file, "w") as f:
                f.write(content)

    def _update_documentation(self, target_dir, app_name, model_name, options):
        """Aggiorna documentazione con date e info corrette"""
        today = datetime.now().strftime("%Y-%m-%d")

        # Aggiorna CHANGELOG.md con data corretta
        changelog_file = target_dir / "CHANGELOG.md"
        if changelog_file.exists():
            with open(changelog_file, "r", encoding="utf-8") as f:
                content = f.read()

            content = content.replace("YYYY-MM-DD", today)

            with open(changelog_file, "w", encoding="utf-8") as f:
                f.write(content)

        self.stdout.write(self.style.SUCCESS("✓ Documentazione aggiornata"))

    def _check_dependencies(self, app_name):
        """Verifica dipendenze moduli (se module_manager disponibile)"""
        try:
            from core.module_manager import ModuleManager

            # Verifica se moduli core sono installati
            installed = ModuleManager.get_installed_modules()
            core_modules = ['core', 'users']

            missing = [mod for mod in core_modules if mod not in installed]

            if missing:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ Warning: Moduli core mancanti: {', '.join(missing)}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("✓ Tutte le dipendenze core sono soddisfatte")
                )

        except ImportError:
            # module_manager non ancora disponibile, skip
            pass

    def _run_migrations(self, app_name):
        """Esegui makemigrations e migrate automaticamente"""
        import subprocess

        self.stdout.write(self.style.WARNING(f"\n🔄 Esecuzione migrations per {app_name}..."))

        try:
            # makemigrations
            result = subprocess.run(
                ["python", "manage.py", "makemigrations", app_name],
                capture_output=True,
                text=True
            )
            self.stdout.write(result.stdout)

            if result.returncode == 0:
                # migrate
                result = subprocess.run(
                    ["python", "manage.py", "migrate"],
                    capture_output=True,
                    text=True
                )
                self.stdout.write(result.stdout)

                if result.returncode == 0:
                    self.stdout.write(self.style.SUCCESS("✓ Migrations completate"))
                else:
                    self.stdout.write(
                        self.style.ERROR(f"✗ Errore durante migrate: {result.stderr}")
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f"✗ Errore durante makemigrations: {result.stderr}")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Errore esecuzione migrations: {e}")
            )

    def _print_success_message(self, app_name, model_name):
        """Stampa messaggio di successo con istruzioni"""

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS(f"✓ App '{app_name}' creata con successo!"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("📋 PROSSIMI PASSI:"))
        self.stdout.write("")

        steps = [
            f"1. Aggiungi '{app_name}' in INSTALLED_APPS (config/settings/base.py)",
            f"2. Aggiungi URLs in config/urls.py:",
            f'   path("{app_name}/", include("{app_name}.urls")),',
            "",
            f"3. Personalizza model in {app_name}/models.py",
            f"4. Crea migrations:",
            f"   python manage.py makemigrations {app_name}",
            f"   python manage.py migrate",
            "",
            f"5. Customizza templates in {app_name}/templates/{app_name}/",
            f"6. Esegui tests:",
            f"   pytest {app_name}/tests/",
            "",
            "7. Documenta il modulo:",
            f"   - Compila {app_name}/README_TECHNICAL.md",
            f"   - Compila {app_name}/README_USER.md",
            f"   - Aggiorna {app_name}/CHANGELOG.md",
            "",
            "8. Consulta:",
            "   - docs/APP_CREATION_GUIDE.md",
            "   - docs/APP_INTEGRATION_CHECKLIST.md",
            "   - docs/MODULE_DEPENDENCIES.md",
        ]

        for step in steps:
            if step:
                self.stdout.write(f"   {step}")
            else:
                self.stdout.write("")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("🚀 Buon lavoro!"))
        self.stdout.write("")
