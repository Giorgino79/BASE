"""
Django command per setup iniziale permessi e gruppi
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = "Setup iniziale gruppi e permessi standard"

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-groups',
            action='store_true',
            help='Crea gruppi standard',
        )

        parser.add_argument(
            '--list-permissions',
            type=str,
            help='Lista permessi per una specifica app',
        )

        parser.add_argument(
            '--show-user-permissions',
            type=str,
            help='Mostra permessi di un utente (username)',
        )

    def handle(self, *args, **options):
        if options['create_groups']:
            self._create_standard_groups()

        if options['list_permissions']:
            self._list_app_permissions(options['list_permissions'])

        if options['show_user_permissions']:
            self._show_user_permissions(options['show_user_permissions'])

        if not any([options['create_groups'], options['list_permissions'], options['show_user_permissions']]):
            self.stdout.write(self.style.WARNING("Nessuna azione specificata. Usa --help per vedere le opzioni."))

    def _create_standard_groups(self):
        """Crea gruppi standard con permessi predefiniti"""
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("CREAZIONE GRUPPI STANDARD"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")

        # ===== GRUPPO: ADMIN COMPLETO =====
        admin_group, created = Group.objects.get_or_create(name='Admin Completo')
        if created:
            all_perms = Permission.objects.all()
            admin_group.permissions.add(*all_perms)
            self.stdout.write(self.style.SUCCESS(f"✓ Creato gruppo 'Admin Completo' con {all_perms.count()} permessi"))
        else:
            self.stdout.write(self.style.WARNING(f"○ Gruppo 'Admin Completo' già esistente"))

        # ===== GRUPPO: VISUALIZZATORE =====
        viewer_group, created = Group.objects.get_or_create(name='Visualizzatore')
        if created:
            view_perms = Permission.objects.filter(codename__startswith='view_')
            viewer_group.permissions.add(*view_perms)
            self.stdout.write(self.style.SUCCESS(f"✓ Creato gruppo 'Visualizzatore' con {view_perms.count()} permessi"))
        else:
            self.stdout.write(self.style.WARNING(f"○ Gruppo 'Visualizzatore' già esistente"))

        # ===== GRUPPO: MAGAZZINIERE =====
        magazzino_group, created = Group.objects.get_or_create(name='Magazziniere')
        if created:
            magazzino_apps = ['prodotti', 'ricezioni', 'acquisti']
            magazzino_perms = Permission.objects.filter(
                content_type__app_label__in=magazzino_apps
            )
            magazzino_group.permissions.add(*magazzino_perms)
            self.stdout.write(self.style.SUCCESS(f"✓ Creato gruppo 'Magazziniere' con {magazzino_perms.count()} permessi"))
        else:
            self.stdout.write(self.style.WARNING(f"○ Gruppo 'Magazziniere' già esistente"))

        # ===== GRUPPO: LOGISTICA =====
        logistica_group, created = Group.objects.get_or_create(name='Logistica')
        if created:
            logistica_apps = ['trasporti', 'automezzi', 'preventivi_beni']
            logistica_perms = Permission.objects.filter(
                content_type__app_label__in=logistica_apps
            )
            logistica_group.permissions.add(*logistica_perms)
            self.stdout.write(self.style.SUCCESS(f"✓ Creato gruppo 'Logistica' con {logistica_perms.count()} permessi"))
        else:
            self.stdout.write(self.style.WARNING(f"○ Gruppo 'Logistica' già esistente"))

        # ===== GRUPPO: HR =====
        hr_group, created = Group.objects.get_or_create(name='HR')
        if created:
            hr_apps = ['users', 'payroll']
            hr_perms = Permission.objects.filter(
                content_type__app_label__in=hr_apps
            )
            hr_group.permissions.add(*hr_perms)
            self.stdout.write(self.style.SUCCESS(f"✓ Creato gruppo 'HR' con {hr_perms.count()} permessi"))
        else:
            self.stdout.write(self.style.WARNING(f"○ Gruppo 'HR' già esistente"))

        # ===== GRUPPO: MANAGER =====
        manager_group, created = Group.objects.get_or_create(name='Manager')
        if created:
            # Manager può view/change su tutto, ma non delete
            manager_perms = Permission.objects.filter(
                codename__in=[p.codename for p in Permission.objects.all() if p.codename.startswith(('view_', 'change_', 'add_'))]
            )
            manager_group.permissions.add(*manager_perms)
            self.stdout.write(self.style.SUCCESS(f"✓ Creato gruppo 'Manager' con {manager_perms.count()} permessi"))
        else:
            self.stdout.write(self.style.WARNING(f"○ Gruppo 'Manager' già esistente"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("RIEPILOGO GRUPPI CREATI"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

        for group in Group.objects.all():
            perm_count = group.permissions.count()
            self.stdout.write(f"  • {group.name:20s} - {perm_count:3d} permessi")

        self.stdout.write("")

    def _list_app_permissions(self, app_label):
        """Lista tutti i permessi di un'app"""
        self.stdout.write(self.style.SUCCESS(f"=" * 70))
        self.stdout.write(self.style.SUCCESS(f"PERMESSI APP: {app_label}"))
        self.stdout.write(self.style.SUCCESS(f"=" * 70))
        self.stdout.write("")

        perms = Permission.objects.filter(
            content_type__app_label=app_label
        ).select_related('content_type')

        if not perms.exists():
            self.stdout.write(self.style.ERROR(f"Nessun permesso trovato per l'app '{app_label}'"))
            return

        # Raggruppa per model
        perms_by_model = {}
        for perm in perms:
            model = perm.content_type.model
            if model not in perms_by_model:
                perms_by_model[model] = []
            perms_by_model[model].append(perm)

        for model, model_perms in sorted(perms_by_model.items()):
            self.stdout.write(self.style.WARNING(f"Model: {model}"))
            for perm in model_perms:
                perm_code = f"{app_label}.{perm.codename}"
                self.stdout.write(f"  • {perm_code:40s} - {perm.name}")
            self.stdout.write("")

        self.stdout.write(f"Totale: {perms.count()} permessi")
        self.stdout.write("")

    def _show_user_permissions(self, username):
        """Mostra tutti i permessi di un utente"""
        from users.models import User

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Utente '{username}' non trovato"))
            return

        self.stdout.write(self.style.SUCCESS(f"=" * 70))
        self.stdout.write(self.style.SUCCESS(f"PERMESSI UTENTE: {username}"))
        self.stdout.write(self.style.SUCCESS(f"=" * 70))
        self.stdout.write("")

        # Info utente
        self.stdout.write(f"Nome completo: {user.get_full_name() or 'N/A'}")
        self.stdout.write(f"Email: {user.email or 'N/A'}")
        self.stdout.write(f"Superuser: {'Sì' if user.is_superuser else 'No'}")
        self.stdout.write(f"Staff: {'Sì' if user.is_staff else 'No'}")
        self.stdout.write("")

        # Gruppi
        groups = user.groups.all()
        if groups:
            self.stdout.write(self.style.WARNING(f"Gruppi ({groups.count()}):"))
            for group in groups:
                perm_count = group.permissions.count()
                self.stdout.write(f"  • {group.name} ({perm_count} permessi)")
            self.stdout.write("")

        # Permessi diretti
        direct_perms = user.user_permissions.all()
        if direct_perms:
            self.stdout.write(self.style.WARNING(f"Permessi Diretti ({direct_perms.count()}):"))
            for perm in direct_perms:
                perm_code = f"{perm.content_type.app_label}.{perm.codename}"
                self.stdout.write(f"  • {perm_code:40s} - {perm.name}")
            self.stdout.write("")

        # Tutti i permessi effettivi
        all_perms = user.get_all_permissions()
        if all_perms:
            self.stdout.write(self.style.WARNING(f"Tutti i Permessi Effettivi ({len(all_perms)}):"))

            # Raggruppa per app
            perms_by_app = {}
            for perm_code in sorted(all_perms):
                app = perm_code.split('.')[0]
                if app not in perms_by_app:
                    perms_by_app[app] = []
                perms_by_app[app].append(perm_code)

            for app, app_perms in sorted(perms_by_app.items()):
                self.stdout.write(f"  {app}: {len(app_perms)} permessi")
                for perm in app_perms:
                    self.stdout.write(f"    • {perm}")
            self.stdout.write("")
        else:
            self.stdout.write(self.style.WARNING("Nessun permesso assegnato"))
            self.stdout.write("")
