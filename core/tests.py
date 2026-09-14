from django.test import TestCase

from core.module_manager import ModuleManager


class ModuleDependencyGraphTest(TestCase):
    """
    Garantisce che core/module_manager.py::MODULE_DEPENDENCIES resti completo:
    ogni app installata deve avere una voce, e le sue dipendenze dichiarate
    devono essere tutte effettivamente installate. Un fallimento qui vuol dire
    che una nuova app e' stata aggiunta a INSTALLED_APPS senza dichiarare le
    proprie dipendenze in module_manager.py (esattamente il tipo di deriva
    corretta il 2026-08-22, quando il file era una copia mai adattata di em26
    e non dichiarava nessuna delle 15 app reali di rattus26).
    """

    def test_no_missing_dependencies(self):
        missing = ModuleManager.check_all_dependencies()
        self.assertEqual(missing, {}, f"Dipendenze non soddisfatte: {missing}")
