"""
Modelli per gestione Template Permessi.

Sistema per creare e riutilizzare insiemi predefiniti di permessi
da applicare agli utenti.
"""

from django.db import models
from django.contrib.auth.models import Permission
from core.mixins import TimestampMixin


class PermissionTemplate(TimestampMixin):
    """
    Template di permessi riutilizzabile.

    Permette agli admin di creare insiemi predefiniti di permessi
    (es. "Responsabile HR", "Addetto Payroll") che possono essere
    applicati rapidamente agli utenti.

    Il template è un preset: applica i permessi una volta all'utente,
    poi l'utente ha permessi indipendenti.
    """

    nome = models.CharField(
        "Nome Template",
        max_length=100,
        unique=True,
        help_text="Es. 'Responsabile HR', 'Addetto Payroll'"
    )

    descrizione = models.TextField(
        "Descrizione",
        blank=True,
        help_text="Descrizione dei permessi inclusi in questo template"
    )

    # Permessi CRUD sui modelli (molti-a-molti)
    permessi_crud = models.ManyToManyField(
        Permission,
        verbose_name="Permessi CRUD",
        related_name="templates_crud",
        blank=True,
        limit_choices_to={
            'content_type__app_label__in': ['users', 'payroll', 'core']
        },
        help_text="Permessi CRUD sui modelli (add, view, change, delete)"
    )

    # Permessi base operativi (stored as JSON per flessibilità)
    # Esempio: ["users.add_timbratura", "users.approva_ferie"]
    permessi_base = models.JSONField(
        "Permessi Base",
        default=list,
        blank=True,
        help_text="Permessi operativi base (timbrature, ferie, etc.)"
    )

    attivo = models.BooleanField(
        "Attivo",
        default=True,
        help_text="Se disattivato, il template non appare nelle selezioni"
    )

    # Statistiche
    n_utilizzi = models.PositiveIntegerField(
        "Numero Utilizzi",
        default=0,
        help_text="Quante volte questo template è stato applicato"
    )

    class Meta:
        db_table = "core_permission_template"
        verbose_name = "Template Permessi"
        verbose_name_plural = "Template Permessi"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["nome"]),
            models.Index(fields=["attivo"]),
        ]

    def __str__(self):
        return f"{self.nome}"

    def get_permessi_count(self):
        """Conta totale permessi nel template"""
        crud_count = self.permessi_crud.count()
        base_count = len(self.permessi_base) if self.permessi_base else 0
        return crud_count + base_count

    def applica_a_utente(self, user):
        """
        Applica tutti i permessi di questo template all'utente.

        Args:
            user: Istanza User

        Returns:
            dict: Statistiche applicazione {
                'permessi_crud_aggiunti': int,
                'permessi_base_aggiunti': int,
                'errori': list
            }
        """
        stats = {
            'permessi_crud_aggiunti': 0,
            'permessi_base_aggiunti': 0,
            'errori': []
        }

        # 1. Applica permessi CRUD
        permessi_crud = list(self.permessi_crud.all())
        if permessi_crud:
            user.user_permissions.add(*permessi_crud)
            stats['permessi_crud_aggiunti'] = len(permessi_crud)

        # 2. Applica permessi base
        if self.permessi_base:
            for perm_string in self.permessi_base:
                try:
                    app_label, codename = perm_string.split('.')
                    permission = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename
                    )
                    user.user_permissions.add(permission)
                    stats['permessi_base_aggiunti'] += 1
                except Permission.DoesNotExist:
                    stats['errori'].append(f"Permesso {perm_string} non trovato")
                except ValueError:
                    stats['errori'].append(f"Formato permesso {perm_string} non valido")

        # 3. Incrementa contatore utilizzi
        self.n_utilizzi += 1
        self.save(update_fields=['n_utilizzi'])

        return stats

    def get_permessi_base_display(self):
        """
        Restituisce i permessi base in formato leggibile.

        Returns:
            list: Lista di dict con info permessi base
        """
        if not self.permessi_base:
            return []

        permessi_info = []
        for perm_string in self.permessi_base:
            try:
                app_label, codename = perm_string.split('.')
                permission = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename
                )
                permessi_info.append({
                    'codename': codename,
                    'name': permission.name,
                    'app': app_label
                })
            except (Permission.DoesNotExist, ValueError):
                permessi_info.append({
                    'codename': perm_string,
                    'name': f"⚠️ {perm_string} (non trovato)",
                    'app': 'unknown'
                })

        return permessi_info
