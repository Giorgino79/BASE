"""
Module Manager - Sistema gestione moduli ModularBEF
===================================================
"""

from django.apps import apps
from django.conf import settings


# Moduli core obbligatori
#
# NOTA 2026-08-22: questo file era una copia letterale (mai adattata) di
# quello di em26 — citava app inesistenti in rattus26 (anagrafica, stabilimenti,
# prodotti, ricezioni, trasporti, preventivi_beni, automezzi, mail, pallets) e
# non ne dichiarava nessuna di quelle reali. Riscritto da un audit sistematico
# (import diretti + import locali/funzione, su tutti i file non-migration) sulle
# 15 app reali di rattus26.
CORE_MODULES = [
    'core',
    'users',
    'anagrafica_r2',  # equivalente rattus26 di "anagrafica" in em26 (clienti/fornitori)
    'whatsapp',  # Promosso a core 2026-08-26: prima incollato dentro core/whatsapp_sender.py
                 # (Green API), ora app dedicata identica a em26 — un'unica implementazione
                 # WhatsApp condivisa da ogni progetto, mai vendibile separatamente. Vedi
                 # Libro Mastro Capitolo 1 e memoria "CORE definition".
]

# Dipendenze tra moduli.
#
# Alcune coppie sono volutamente bidirezionali (es. acquisti<->magazzino,
# automezzi<->stabilimenti, magazzino<->servizi, servizi<->portale): il dizionario
# esprime "vanno installati insieme", non un DAG — un ciclo qui è accettabile
# se entrambi i lati usano import locali (non causa ImportError circolare
# Python), verificato per tutte le coppie qui sotto.
#
# users->comunicazioni e anagrafica_r2->servizi NON sono dichiarate qui pur
# essendo reali nel codice: sono state rese "degradanti con grazia" (try/except,
# vedi users/views.py::dashboard_view e anagrafica_r2/views.py::PrivatoDetailView)
# perché altrimenti, essendo users e anagrafica_r2 moduli core, avrebbero reso
# comunicazioni/servizi obbligatori per qualunque installazione.
MODULE_DEPENDENCIES = {
    'users': ['core'],
    'anagrafica_r2': ['core'],
    'comunicazioni': ['core', 'anagrafica_r2', 'users', 'servizi'],
    'corrispondenza': ['core', 'users'],
    'payroll': ['core', 'users'],
    # automezzi/stabilimenti: estratte da 'cespiti' il 26/08/2026 (prima
    # cespiti le conteneva entrambe insieme a TipoAttrezzatura/
    # AttrezzaturaAutomezzo, sector-specific, spostate in magazzino).
    # 'cespiti' e' stata RITIRATA dal catalogo (nessun modello, nessuna URL,
    # nessuna voce sidebar) — resta in INSTALLED_APPS solo come ancora
    # storica per le migrazioni, vedi cespiti/models.py. Non compare qui:
    # non e' piu' un modulo vendibile.
    # Sono app "comuni" (vedi memoria app-catalog-vision): stabilimenti e
    # automezzi devono restare identiche a quelle em26, riusabili da
    # qualunque settore. automezzi<->stabilimenti dichiarata bidirezionale
    # di proposito (stessa dashboard cross-stat gia' presente in em26).
    'stabilimenti': ['core', 'anagrafica_r2'],
    'automezzi': ['core', 'anagrafica_r2', 'stabilimenti'],
    'acquisti': ['core', 'anagrafica_r2', 'magazzino', 'contabilita'],
    'magazzino': ['core', 'acquisti', 'anagrafica_r2', 'stabilimenti', 'servizi', 'automezzi'],  # automezzi:
        # FK dirette (CaricoMezzo/ScortaMezzo/CaricoCisterna/ConsumoCisterna/Ricezione.mezzo);
        # stabilimenti: FK dirette (CaricoMezzo/Ricezione.stabilimento) + TipoAttrezzatura/
        # AttrezzaturaAutomezzo (sector-specific, spostate qui 26/08/2026).
    'servizi': ['core', 'anagrafica_r2', 'automezzi', 'comunicazioni', 'magazzino', 'portale', 'whatsapp'],
    'installazioni': ['core', 'magazzino', 'servizi'],  # le installazioni sono "figlie" di servizi
    'analysis': ['core', 'acquisti', 'magazzino', 'payroll', 'servizi'],  # mini-BI: legge da (quasi) tutti i moduli
    'portale': ['core', 'anagrafica_r2', 'comunicazioni', 'magazzino', 'servizi', 'whatsapp'],
    'fatturazione_attiva': ['core', 'anagrafica_r2', 'servizi'],
    # comunicazioni: la conferma di ricezione di un passaggio di cassa manda
    # un messaggio di chat dal ricevente al consegnante (vedi
    # contabilita/signals.py::notifica_conferma_ricezione).
    'contabilita': ['core', 'acquisti', 'anagrafica_r2', 'fatturazione_attiva', 'comunicazioni'],
    'whatsapp': ['core'],
}

# Versioni moduli (da aggiornare manualmente o automaticamente)
MODULE_VERSIONS = {
    'core': '1.0.0',
    'users': '1.0.0',
    'anagrafica_r2': '1.0.0',
    'comunicazioni': '1.0.0',
    'corrispondenza': '1.0.0',
    'payroll': '1.0.0',
    'stabilimenti': '1.0.0',
    'automezzi': '1.0.0',
    'whatsapp': '1.0.0',
    'acquisti': '1.0.0',
    'magazzino': '1.0.0',
    'servizi': '1.0.0',
    'installazioni': '1.0.0',
    'analysis': '1.0.0',
    'portale': '1.0.0',
    'fatturazione_attiva': '1.0.0',
    'contabilita': '1.0.0',
}


class ModuleManager:
    """Gestione moduli installati e dipendenze"""

    @staticmethod
    def get_installed_modules():
        """Ritorna lista moduli installati (esclusi Django/third-party)"""
        installed = []
        for app_config in apps.get_app_configs():
            app_name = app_config.name
            # Filtra solo moduli del progetto (quelli in MODULE_DEPENDENCIES o CORE_MODULES)
            if app_name in MODULE_DEPENDENCIES or app_name in CORE_MODULES:
                installed.append(app_name)
        return installed

    @staticmethod
    def check_dependencies(module_name):
        """Verifica se tutte le dipendenze di un modulo sono soddisfatte"""
        if module_name not in MODULE_DEPENDENCIES:
            # Se non ha dipendenze definite, consideriamo OK
            return True, []

        required = MODULE_DEPENDENCIES[module_name]
        installed = ModuleManager.get_installed_modules()

        missing = [mod for mod in required if mod not in installed]

        return len(missing) == 0, missing

    @staticmethod
    def check_all_dependencies():
        """Verifica dipendenze di tutti i moduli installati"""
        results = {}
        for module in ModuleManager.get_installed_modules():
            ok, missing = ModuleManager.check_dependencies(module)
            if not ok:
                results[module] = missing
        return results

    @staticmethod
    def is_core_module(module_name):
        """Verifica se un modulo è core (non rimovibile)"""
        return module_name in CORE_MODULES

    @staticmethod
    def get_module_version(module_name):
        """Ritorna versione modulo"""
        return MODULE_VERSIONS.get(module_name, 'Unknown')

    @staticmethod
    def get_module_info(module_name):
        """Ritorna info complete su un modulo"""
        # Controlla se è nei moduli conosciuti
        is_known = module_name in MODULE_DEPENDENCIES or module_name in CORE_MODULES

        if not is_known:
            return None

        return {
            'name': module_name,
            'version': ModuleManager.get_module_version(module_name),
            'is_core': ModuleManager.is_core_module(module_name),
            'dependencies': MODULE_DEPENDENCIES.get(module_name, []),
            'is_installed': module_name in ModuleManager.get_installed_modules(),
        }

    @staticmethod
    def get_all_modules_info():
        """Ritorna info su tutti i moduli conosciuti"""
        all_modules = set(CORE_MODULES) | set(MODULE_DEPENDENCIES.keys())
        return [
            ModuleManager.get_module_info(module)
            for module in sorted(all_modules)
            if ModuleManager.get_module_info(module) is not None
        ]
