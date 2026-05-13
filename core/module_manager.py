"""
Module Manager - Sistema gestione moduli ModularBEF
===================================================
"""

from django.apps import apps
from django.conf import settings


# Moduli core obbligatori
CORE_MODULES = [
    'core',
    'users',
    'anagrafica',
    'stabilimenti',
]

# Dipendenze tra moduli
MODULE_DEPENDENCIES = {
    'users': ['core'],
    'anagrafica': ['core', 'users'],
    'stabilimenti': ['core'],
    'prodotti': ['core', 'anagrafica', 'stabilimenti'],
    'ricezioni': ['core', 'prodotti', 'acquisti', 'stabilimenti'],
    'acquisti': ['core', 'anagrafica'],
    'trasporti': ['core', 'anagrafica'],
    'preventivi_beni': ['core', 'anagrafica'],
    'automezzi': ['core', 'stabilimenti'],
    'payroll': ['core', 'users'],
    'mail': ['core'],
    'pallets': ['core', 'anagrafica', 'stabilimenti', 'mail'],  # Gestione contabilità pallet
}

# Versioni moduli (da aggiornare manualmente o automaticamente)
MODULE_VERSIONS = {
    'core': '1.0.0',
    'users': '1.0.0',
    'anagrafica': '1.0.0',
    'stabilimenti': '1.0.0',
    'prodotti': '1.0.0',
    'ricezioni': '1.0.0',
    'acquisti': '1.0.0',
    'trasporti': '1.0.0',
    'preventivi_beni': '1.0.0',
    'automezzi': '1.0.0',
    'payroll': '1.0.0',
    'mail': '1.0.0',
    'pallets': '1.0.0',  # Aggiunto 2026-02-08
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
