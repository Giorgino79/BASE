"""
Registry per gestione permissions sui modelli user-facing.

Questo modulo definisce quali modelli sono gestibili dagli admin
tramite il form di assegnazione permessi agli utenti.

IMPORTANTE:
- Solo i modelli registrati qui appariranno nel form permissions
- I modelli "di servizio" (Allegato, ModuloRegistry, etc.) NON vanno registrati
- Ogni nuovo modello user-facing VA REGISTRATO manualmente
"""

from django.apps import apps
from django.contrib.contenttypes.models import ContentType


class ModelPermissionRegistry:
    """
    Registry centralizzato per modelli gestibili con permissions.

    Pattern Singleton per garantire un unico registro globale.
    """

    _instance = None
    _registry = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._registry = {}
        return cls._instance

    def register(self, app_label, model_name, display_name=None, category=None, icon=None):
        """
        Registra un modello come gestibile con permissions.

        Args:
            app_label (str): Nome app Django (es. "users", "payroll")
            model_name (str): Nome modello lowercase (es. "user", "bustapaga")
            display_name (str): Nome visualizzato (es. "Utenti", "Buste Paga")
            category (str): Categoria per raggruppamento (es. "Gestione Personale")
            icon (str): Icona Bootstrap (es. "bi-people", "bi-cash-coin")

        Example:
            registry = ModelPermissionRegistry()
            registry.register(
                app_label="users",
                model_name="user",
                display_name="Utenti",
                category="Gestione Personale",
                icon="bi-people"
            )
        """
        key = f"{app_label}.{model_name}"

        # Verifica che il modello esista
        try:
            model_class = apps.get_model(app_label, model_name)
        except LookupError:
            raise ValueError(
                f"Modello {key} non trovato. Verifica app_label e model_name."
            )

        self._registry[key] = {
            "app_label": app_label,
            "model_name": model_name,
            "model_class": model_class,
            "display_name": display_name or model_class._meta.verbose_name_plural.title(),
            "category": category or app_label.title(),
            "icon": icon or "bi-file-earmark",
            "permissions": self._get_model_permissions(model_class),
        }

    def _get_model_permissions(self, model_class):
        """
        Ottiene i permessi Django standard per un modello.

        Returns:
            list: Lista di dict con codename, name, label
        """
        # Usa _meta invece di ContentType per evitare query al database
        app_label = model_class._meta.app_label
        model_name = model_class._meta.model_name
        permissions = []

        # Permessi CRUD standard Django
        for action, label in [
            ("add", "Creare"),
            ("view", "Visualizzare"),
            ("change", "Modificare"),
            ("delete", "Eliminare"),
        ]:
            codename = f"{action}_{model_name}"
            perm_name = f"{app_label}.{codename}"

            permissions.append(
                {
                    "codename": codename,
                    "full_name": perm_name,
                    "action": action,
                    "label": label,
                }
            )

        return permissions

    def get_registered_models(self):
        """
        Restituisce tutti i modelli registrati.

        Returns:
            dict: Dizionario {key: model_info}
        """
        return self._registry.copy()

    def get_models_by_category(self):
        """
        Restituisce modelli raggruppati per categoria.

        Returns:
            dict: {category: [model_info, ...]}
        """
        categorized = {}

        for model_info in self._registry.values():
            category = model_info["category"]
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(model_info)

        return categorized

    def is_registered(self, app_label, model_name):
        """Verifica se un modello è registrato"""
        key = f"{app_label}.{model_name}"
        return key in self._registry

    def get_model_info(self, app_label, model_name):
        """Ottiene informazioni su un modello registrato"""
        key = f"{app_label}.{model_name}"
        return self._registry.get(key)

    def unregister(self, app_label, model_name):
        """Rimuove un modello dal registro (usare con cautela!)"""
        key = f"{app_label}.{model_name}"
        if key in self._registry:
            del self._registry[key]


# ============================================================================
# REGISTRAZIONE MODELLI USER-FACING
# ============================================================================

def register_default_models():
    """
    Registra i modelli user-facing di default.
    Aggiungi nuove registrazioni quando installi nuovi moduli.
    """
    registry = ModelPermissionRegistry()

    # ========== APP: USERS ==========
    registry.register(
        app_label="users",
        model_name="user",
        display_name="Utenti / Dipendenti",
        category="👥 Users - Gestione Personale",
        icon="bi-people-fill",
    )

    registry.register(
        app_label="users",
        model_name="richiestaferie",
        display_name="Richieste Ferie",
        category="👥 Users - Gestione Personale",
        icon="bi-calendar-check",
    )

    registry.register(
        app_label="users",
        model_name="richiestapermesso",
        display_name="Richieste Permessi",
        category="👥 Users - Gestione Personale",
        icon="bi-clock-history",
    )

    registry.register(
        app_label="users",
        model_name="letterarichiamo",
        display_name="Lettere di Richiamo",
        category="👥 Users - Gestione Personale",
        icon="bi-exclamation-triangle-fill",
    )

    registry.register(
        app_label="users",
        model_name="giornatalavorativa",
        display_name="Giornate Lavorative",
        category="👥 Users - Gestione Personale",
        icon="bi-calendar3",
    )

    registry.register(
        app_label="users",
        model_name="timbratura",
        display_name="Timbrature",
        category="👥 Users - Gestione Personale",
        icon="bi-stopwatch",
    )

    registry.register(
        app_label="users",
        model_name="eventopersonale",
        display_name="Eventi Personali",
        category="👥 Users - Gestione Personale",
        icon="bi-calendar-heart",
    )

    # ========== APP: CORE (Calendario) ==========
    registry.register(
        app_label="core",
        model_name="eventocalendario",
        display_name="Eventi Calendario Aziendale",
        category="📅 Calendario",
        icon="bi-calendar-week",
    )

    # ========== APP: COMUNICAZIONI ==========
    registry.register(
        app_label="comunicazioni",
        model_name="promemoria",
        display_name="Promemoria",
        category="💬 Comunicazioni",
        icon="bi-bell-fill",
    )

    registry.register(
        app_label="comunicazioni",
        model_name="chatconversazione",
        display_name="Chat - Conversazioni",
        category="💬 Comunicazioni",
        icon="bi-chat-dots-fill",
    )

    registry.register(
        app_label="comunicazioni",
        model_name="chatmessaggio",
        display_name="Chat - Messaggi",
        category="💬 Comunicazioni",
        icon="bi-chat-left-text",
    )

    # ========== APP: CORRISPONDENZA ==========
    registry.register(
        app_label="corrispondenza",
        model_name="corrispondenza",
        display_name="Corrispondenza",
        category="📨 Corrispondenza",
        icon="bi-envelope-fill",
    )

    registry.register(
        app_label="corrispondenza",
        model_name="tipocorrispondenza",
        display_name="Tipi Corrispondenza",
        category="📨 Corrispondenza",
        icon="bi-tags-fill",
    )

    # ========== APP: ANAGRAFICA (anagrafica_r2) ==========
    registry.register(
        app_label="anagrafica",
        model_name="azienda",
        display_name="Aziende (Clienti)",
        category="🏢 Anagrafica",
        icon="bi-building",
    )

    registry.register(
        app_label="anagrafica",
        model_name="filiale",
        display_name="Filiali",
        category="🏢 Anagrafica",
        icon="bi-geo-alt-fill",
    )

    registry.register(
        app_label="anagrafica",
        model_name="privato",
        display_name="Clienti Privati",
        category="🏢 Anagrafica",
        icon="bi-person-vcard",
    )

    registry.register(
        app_label="anagrafica",
        model_name="fornitore",
        display_name="Fornitori",
        category="🏢 Anagrafica",
        icon="bi-truck",
    )

    # ========== APP: ACQUISTI ==========
    registry.register(
        app_label="acquisti",
        model_name="ordineacquisto",
        display_name="Ordini di Acquisto",
        category="🛒 Acquisti",
        icon="bi-cart-check",
    )

    registry.register(
        app_label="acquisti",
        model_name="fatturapassiva",
        display_name="Fatture Passive",
        category="🛒 Acquisti",
        icon="bi-receipt",
    )

    # ========== APP: MAGAZZINO ==========
    registry.register(
        app_label="magazzino",
        model_name="categoria",
        display_name="Categorie Prodotto",
        category="📦 Magazzino",
        icon="bi-tags",
    )

    registry.register(
        app_label="magazzino",
        model_name="prodotto",
        display_name="Prodotti",
        category="📦 Magazzino",
        icon="bi-box-seam",
    )

    registry.register(
        app_label="magazzino",
        model_name="ricezione",
        display_name="Ricezioni Merce",
        category="📦 Magazzino",
        icon="bi-box-arrow-in-down",
    )

    registry.register(
        app_label="magazzino",
        model_name="caricomezzo",
        display_name="Carichi Mezzo",
        category="📦 Magazzino",
        icon="bi-truck-flatbed",
    )

    registry.register(
        app_label="magazzino",
        model_name="caricocisterna",
        display_name="Carichi Cisterna",
        category="📦 Magazzino",
        icon="bi-droplet-fill",
    )

    # ========== APP: CESPITI (Automezzi e Stabilimenti) ==========
    registry.register(
        app_label="cespiti",
        model_name="automezzo",
        display_name="Automezzi",
        category="🚚 Cespiti - Automezzi e Stabilimenti",
        icon="bi-truck",
    )

    registry.register(
        app_label="cespiti",
        model_name="tipoattrezzatura",
        display_name="Tipi Attrezzatura",
        category="🚚 Cespiti - Automezzi e Stabilimenti",
        icon="bi-tools",
    )

    registry.register(
        app_label="cespiti",
        model_name="manutenzione",
        display_name="Manutenzioni",
        category="🚚 Cespiti - Automezzi e Stabilimenti",
        icon="bi-wrench-adjustable",
    )

    registry.register(
        app_label="cespiti",
        model_name="rifornimento",
        display_name="Rifornimenti",
        category="🚚 Cespiti - Automezzi e Stabilimenti",
        icon="bi-fuel-pump-fill",
    )

    registry.register(
        app_label="cespiti",
        model_name="eventoautomezzo",
        display_name="Eventi Automezzo",
        category="🚚 Cespiti - Automezzi e Stabilimenti",
        icon="bi-calendar-event",
    )

    registry.register(
        app_label="cespiti",
        model_name="stabilimento",
        display_name="Stabilimenti",
        category="🚚 Cespiti - Automezzi e Stabilimenti",
        icon="bi-building-gear",
    )

    registry.register(
        app_label="cespiti",
        model_name="costistabilimento",
        display_name="Costi Stabilimento",
        category="🚚 Cespiti - Automezzi e Stabilimenti",
        icon="bi-cash-coin",
    )

    registry.register(
        app_label="cespiti",
        model_name="docstabilimento",
        display_name="Documenti Stabilimento",
        category="🚚 Cespiti - Automezzi e Stabilimenti",
        icon="bi-file-earmark-text",
    )

    # ========== APP: SERVIZI ==========
    registry.register(
        app_label="servizi",
        model_name="servizio",
        display_name="Servizi",
        category="🧰 Servizi",
        icon="bi-gear-wide-connected",
    )

    registry.register(
        app_label="servizi",
        model_name="contratto",
        display_name="Contratti",
        category="🧰 Servizi",
        icon="bi-file-earmark-ruled",
    )

    registry.register(
        app_label="servizi",
        model_name="ods",
        display_name="Ordini di Servizio (ODS)",
        category="🧰 Servizi",
        icon="bi-clipboard-check",
    )

    registry.register(
        app_label="servizi",
        model_name="distinta",
        display_name="Distinte",
        category="🧰 Servizi",
        icon="bi-card-list",
    )

    registry.register(
        app_label="servizi",
        model_name="condominiostabile",
        display_name="Stabili Condominio",
        category="🧰 Servizi",
        icon="bi-buildings",
    )

    registry.register(
        app_label="servizi",
        model_name="condominioods",
        display_name="ODS Condominio",
        category="🧰 Servizi",
        icon="bi-clipboard2-check",
    )

    registry.register(
        app_label="servizi",
        model_name="pianoservizio",
        display_name="Piani Servizio",
        category="🧰 Servizi",
        icon="bi-calendar3-range",
    )

    # ========== APP: INSTALLAZIONI ==========
    registry.register(
        app_label="installazioni",
        model_name="installazione",
        display_name="Installazioni",
        category="🔧 Installazioni",
        icon="bi-tools",
    )

    registry.register(
        app_label="installazioni",
        model_name="planimetria",
        display_name="Planimetrie",
        category="🔧 Installazioni",
        icon="bi-map",
    )

    registry.register(
        app_label="installazioni",
        model_name="postazione",
        display_name="Postazioni",
        category="🔧 Installazioni",
        icon="bi-geo",
    )

    registry.register(
        app_label="installazioni",
        model_name="interventoinstallazione",
        display_name="Interventi Installazione",
        category="🔧 Installazioni",
        icon="bi-wrench",
    )

    # ========== APP: CONTABILITA ==========
    registry.register(
        app_label="contabilita",
        model_name="contocontabile",
        display_name="Conti Contabili",
        category="💳 Contabilità",
        icon="bi-bank",
    )

    registry.register(
        app_label="contabilita",
        model_name="movimentoprimanota",
        display_name="Movimenti Prima Nota",
        category="💳 Contabilità",
        icon="bi-journal-text",
    )

    registry.register(
        app_label="contabilita",
        model_name="impostazionicontabilita",
        display_name="Impostazioni Contabilità",
        category="💳 Contabilità",
        icon="bi-sliders",
    )

    # ========== APP: FATTURAZIONE ATTIVA ==========
    registry.register(
        app_label="fatturazione_attiva",
        model_name="fattura",
        display_name="Fatture Attive",
        category="🧾 Fatturazione Attiva",
        icon="bi-receipt-cutoff",
    )

    registry.register(
        app_label="fatturazione_attiva",
        model_name="notacredito",
        display_name="Note di Credito",
        category="🧾 Fatturazione Attiva",
        icon="bi-file-earmark-minus",
    )

    # ========== APP: PAYROLL ==========
    registry.register(
        app_label="payroll",
        model_name="bustapaga",
        display_name="Buste Paga",
        category="💰 Payroll",
        icon="bi-cash-coin",
    )

    registry.register(
        app_label="payroll",
        model_name="daticontrattualipayroll",
        display_name="Dati Contrattuali",
        category="💰 Payroll",
        icon="bi-file-earmark-person",
    )

    registry.register(
        app_label="payroll",
        model_name="manualepayroll",
        display_name="Manuale Payroll",
        category="💰 Payroll",
        icon="bi-book",
    )

    registry.register(
        app_label="payroll",
        model_name="feriepermessipayroll",
        display_name="Ferie e Permessi (Payroll)",
        category="💰 Payroll",
        icon="bi-calendar-check",
    )

    # ========== APP: PORTALE CLIENTI ==========
    registry.register(
        app_label="portale",
        model_name="richiestaintervento",
        display_name="Richieste Intervento",
        category="🌐 Portale Clienti",
        icon="bi-life-preserver",
    )

    registry.register(
        app_label="portale",
        model_name="segnalazioneinfestazione",
        display_name="Segnalazioni Infestazione",
        category="🌐 Portale Clienti",
        icon="bi-bug-fill",
    )

    # Aggiungi qui le registrazioni dei moduli futuri.
# UTILITY FUNCTIONS
# ============================================================================


def get_user_model_permissions(user):
    """
    Ottiene i permessi dell'utente sui modelli registrati.

    Args:
        user: Istanza User

    Returns:
        dict: {
            'app_label.model_name': {
                'can_add': bool,
                'can_view': bool,
                'can_change': bool,
                'can_delete': bool,
            }
        }
    """
    registry = ModelPermissionRegistry()
    user_perms = {}

    for key, model_info in registry.get_registered_models().items():
        model_class = model_info["model_class"]

        user_perms[key] = {
            "can_add": user.has_perm(f"{model_info['app_label']}.add_{model_info['model_name']}"),
            "can_view": user.has_perm(f"{model_info['app_label']}.view_{model_info['model_name']}"),
            "can_change": user.has_perm(f"{model_info['app_label']}.change_{model_info['model_name']}"),
            "can_delete": user.has_perm(f"{model_info['app_label']}.delete_{model_info['model_name']}"),
        }

    return user_perms


def get_registry():
    """Helper per ottenere l'istanza del registry"""
    return ModelPermissionRegistry()
