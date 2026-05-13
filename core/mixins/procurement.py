"""
Procurement Mixin for models that are targets of procurement processes.

This mixin provides common functionality for models that can be used
as targets in procurement/purchasing workflows.
"""

from django.db import models


class ProcurementTargetMixin(models.Model):
    """
    Mixin per modelli che sono obiettivi di processi di approvvigionamento.

    Fornisce campi e metodi comuni per:
    - Richieste di trasporto
    - Ordini di acquisto
    - Altri processi di procurement
    """

    class Meta:
        abstract = True

    # Il mixin è attualmente vuoto ma può essere esteso
    # per aggiungere funzionalità comuni come:
    # - Tracciamento dello stato del procurement
    # - Log delle modifiche
    # - Integrazione con sistema di notifiche

    def get_procurement_status(self):
        """Restituisce lo stato del procurement se disponibile."""
        if hasattr(self, 'stato'):
            return self.stato
        return None

    def is_procurement_active(self):
        """Verifica se il processo di procurement è attivo."""
        status = self.get_procurement_status()
        if status:
            inactive_states = ['ANNULLATA', 'ANNULLATO', 'COMPLETATO', 'PAGATO', 'CONSEGNATO']
            return status not in inactive_states
        return True
