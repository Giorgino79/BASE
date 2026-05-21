"""
View admin per gestione moduli
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from core.module_manager import ModuleManager


@staff_member_required
def amministrazione_dashboard(request):
    """Hub amministrativo — accesso rapido alle funzioni di gestione sistema."""
    return render(request, "core/admin/amministrazione_dashboard.html", {})


@staff_member_required
def hr_dashboard_view(request):
    """Dashboard Human Resource — accesso centralizzato alle funzioni HR."""
    return render(request, "core/hr_dashboard.html", {})


@staff_member_required
def modules_dashboard(request):
    """Dashboard moduli installati"""
    installed = ModuleManager.get_installed_modules()
    all_modules_info = ModuleManager.get_all_modules_info()

    installed_modules = [m for m in all_modules_info if m["is_installed"]]
    not_installed_modules = [m for m in all_modules_info if not m["is_installed"]]
    dependency_issues = ModuleManager.check_all_dependencies()

    core_installed = len([m for m in installed_modules if m["is_core"]])
    optional_installed = len([m for m in installed_modules if not m["is_core"]])

    context = {
        "title": "Dashboard Moduli",
        "installed_modules": installed_modules,
        "not_installed_modules": not_installed_modules,
        "total_modules": len(all_modules_info),
        "total_installed": len(installed_modules),
        "core_installed": core_installed,
        "optional_installed": optional_installed,
        "core_modules": [m for m in installed_modules if m["is_core"]],
        "optional_modules": [m for m in installed_modules if not m["is_core"]],
        "has_issues": len(dependency_issues) > 0,
        "dependency_issues": dependency_issues,
    }

    return render(request, "core/admin/modules_dashboard.html", context)
