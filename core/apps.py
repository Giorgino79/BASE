from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core - Sistema Base"

    def ready(self):
        """
        Inizializzazione app al caricamento Django.

        Registra i modelli user-facing nel ModelPermissionRegistry.
        """
        # Import qui per evitare problemi di import circolari
        from .permissions_registry import register_default_models

        # Registra modelli di default
        register_default_models()

        # Registra provider eventi manuali nel CalendarioRegistry
        try:
            from .calendario_registry import CalendarioRegistry

            def get_eventi_manuali(user, start_date, end_date):
                from .models import EventoCalendario
                from django.db.models import Q

                filtro = Q(visibilita='aziendale') | Q(creato_da=user)

                # Includi eventi che si sovrappongono all'intervallo richiesto
                if start_date and end_date:
                    filtro &= Q(data_inizio__lte=end_date) & (
                        Q(data_fine__isnull=True, data_inizio__gte=start_date) |
                        Q(data_fine__isnull=False, data_fine__gte=start_date)
                    )
                elif start_date:
                    filtro &= Q(data_fine__isnull=True, data_inizio__gte=start_date) | \
                               Q(data_fine__isnull=False, data_fine__gte=start_date)
                elif end_date:
                    filtro &= Q(data_inizio__lte=end_date)

                qs = EventoCalendario.objects.filter(filtro).select_related('creato_da')
                return [e.to_fullcalendar() for e in qs[:200]]

            CalendarioRegistry.register(
                name='eventi_manuali',
                provider_func=get_eventi_manuali,
                permission=None,  # Tutti gli autenticati; filtro interno per visibilità
                category='Miei eventi',
                description='Miei eventi',
                color='#6f42c1',
                priority=5,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Errore registrazione CalendarioRegistry (eventi manuali): {e}")

        # Sidebar: voce Amministrazione (sopra HR)
        from core.sidebar import register_nav
        register_nav("amministrazione", "Amministrazione", [
            {"label": "Amministrazione", "url": "core:amministrazione_dashboard",
             "icon": "bi-gear-fill", "staff_only": True,
             "active_app": "core", "active_url_contains": "amministrazione"},
        ], order=5)

        # Sidebar: Calendario aziendale (visibile a tutti)
        register_nav("calendario", "Calendario", [
            {"label": "Calendario aziendale", "url": "core:calendario_aziendale",
             "icon": "bi-calendar2-week",
             "active_app": "core", "active_url_contains": "calendario"},
        ], order=6)
