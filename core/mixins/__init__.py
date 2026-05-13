"""
Core Mixins Package

Mixins riutilizzabili per models e views.
"""

# Model Mixins - import eager (safe, no circular dependencies)
from .model_mixins import (
    TimestampMixin,
    SoftDeleteMixin,
    AllegatiMixin,
    QRCodeMixin,
    PDFMixin,
    AuditMixin,
)

# View Mixins - lazy import to avoid circular dependencies
# These will be imported when needed
def __getattr__(name):
    if name in ("PermissionRequiredMixin", "AjaxRequiredMixin", "JSONResponseMixin",
                "MultiplePermissionsRequiredMixin", "OwnerRequiredMixin",
                "FormValidMessageMixin", "FormInvalidMessageMixin",
                "UserFormKwargsMixin", "SetCreatedByMixin", "CustomPaginationMixin",
                "FilterMixin", "SearchMixin", "BreadcrumbMixin"):
        from . import view_mixins
        return getattr(view_mixins, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    # Model Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    "AllegatiMixin",
    "QRCodeMixin",
    "PDFMixin",
    "AuditMixin",
    # View Mixins (lazy loaded)
    "PermissionRequiredMixin",
    "AjaxRequiredMixin",
    "JSONResponseMixin",
]
