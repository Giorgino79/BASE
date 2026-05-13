"""
View Mixins per ModularBEF

Mixins riutilizzabili per Class-Based Views.
"""

from django.contrib.auth.mixins import PermissionRequiredMixin as DjangoPermissionMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.generic.base import ContextMixin


# ============================================================================
# PERMISSION MIXINS
# ============================================================================


class PermissionRequiredMixin(DjangoPermissionMixin):
    """
    Enhanced PermissionRequiredMixin con gestione errori migliorata.

    Usage:
        class MiaView(PermissionRequiredMixin, ListView):
            permission_required = 'app.view_model'
            # oppure
            permission_required = ['app.view_model', 'app.change_model']
    """

    def handle_no_permission(self):
        """
        Override per mostrare pagina 403 personalizzata invece di redirect.
        """
        if self.raise_exception or self.request.user.is_authenticated:
            raise PermissionDenied(
                f"Non hai i permessi necessari per accedere a questa risorsa. "
                f"Permessi richiesti: {self.get_permission_required()}"
            )
        return super().handle_no_permission()


class MultiplePermissionsRequiredMixin(ContextMixin):
    """
    Mixin per richiedere permessi multipli con logica AND/OR.

    Usage:
        class MiaView(MultiplePermissionsRequiredMixin, ListView):
            permissions = {
                'all': ['app.view_model', 'app.change_model'],  # AND
                'any': ['app.delete_model', 'app.is_superuser'],  # OR
            }
    """

    permissions = None  # Dict con 'all' e/o 'any'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permissions():
            raise PermissionDenied("Permessi insufficienti")
        return super().dispatch(request, *args, **kwargs)

    def has_permissions(self):
        """
        Verifica se l'utente ha i permessi richiesti.

        Returns:
            bool: True se ha i permessi
        """
        perms = self.permissions or {}
        user = self.request.user

        # Verifica permessi 'all' (AND)
        if "all" in perms:
            if not user.has_perms(perms["all"]):
                return False

        # Verifica permessi 'any' (OR)
        if "any" in perms:
            if not any(user.has_perm(perm) for perm in perms["any"]):
                return False

        return True


class OwnerRequiredMixin:
    """
    Mixin per verificare che l'utente sia il proprietario dell'oggetto.

    Usage:
        class MiaView(OwnerRequiredMixin, DetailView):
            owner_field = 'created_by'  # Campo che contiene l'owner
    """

    owner_field = "created_by"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        owner = getattr(obj, self.owner_field, None)

        if owner != request.user and not request.user.is_superuser:
            raise PermissionDenied("Non sei il proprietario di questa risorsa")

        return super().dispatch(request, *args, **kwargs)


# ============================================================================
# AJAX MIXINS
# ============================================================================


class AjaxRequiredMixin:
    """
    Mixin per views che accettano solo richieste AJAX.

    Usage:
        class MiaView(AjaxRequiredMixin, View):
            def get(self, request):
                return JsonResponse({'status': 'ok'})
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return HttpResponseBadRequest("Solo richieste AJAX")
        return super().dispatch(request, *args, **kwargs)


class JSONResponseMixin:
    """
    Mixin per restituire facilmente risposte JSON.

    Usage:
        class MiaView(JSONResponseMixin, View):
            def get(self, request):
                data = {'status': 'ok', 'message': 'Success'}
                return self.render_to_json_response(data)
    """

    def render_to_json_response(self, context, **response_kwargs):
        """
        Restituisce JSON response.

        Args:
            context: Dati da serializzare
            **response_kwargs: Parametri aggiuntivi per JsonResponse

        Returns:
            JsonResponse
        """
        return JsonResponse(context, **response_kwargs)

    def render_to_json_error(self, error_message, status=400):
        """
        Restituisce JSON error response.

        Args:
            error_message: Messaggio di errore
            status: HTTP status code

        Returns:
            JsonResponse
        """
        return JsonResponse({"error": error_message}, status=status)


# ============================================================================
# FORM MIXINS
# ============================================================================


class FormValidMessageMixin:
    """
    Mixin per aggiungere success message dopo form valid.

    Usage:
        class MiaView(FormValidMessageMixin, CreateView):
            success_message = "Oggetto creato con successo!"
    """

    success_message = ""

    def form_valid(self, form):
        """Override per aggiungere message"""
        response = super().form_valid(form)
        if self.success_message:
            from django.contrib import messages

            messages.success(self.request, self.success_message)
        return response


class FormInvalidMessageMixin:
    """
    Mixin per aggiungere error message dopo form invalid.

    Usage:
        class MiaView(FormInvalidMessageMixin, CreateView):
            error_message = "Errore nel form, controlla i campi"
    """

    error_message = "Errore nel salvataggio. Controlla i campi."

    def form_invalid(self, form):
        """Override per aggiungere message"""
        from django.contrib import messages

        messages.error(self.request, self.error_message)
        return super().form_invalid(form)


class UserFormKwargsMixin:
    """
    Mixin per passare automaticamente request.user al form.

    Usage:
        class MiaView(UserFormKwargsMixin, CreateView):
            pass

        # Nel form __init__:
        def __init__(self, *args, **kwargs):
            self.user = kwargs.pop('user', None)
            super().__init__(*args, **kwargs)
    """

    def get_form_kwargs(self):
        """Aggiunge user ai kwargs del form"""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SetCreatedByMixin:
    """
    Mixin per impostare automaticamente created_by sul form.

    Usage:
        class MiaView(SetCreatedByMixin, CreateView):
            pass
    """

    def form_valid(self, form):
        """Imposta created_by prima del save"""
        if hasattr(form.instance, "created_by"):
            form.instance.created_by = self.request.user
        return super().form_valid(form)


# ============================================================================
# PAGINATION MIXINS
# ============================================================================


class CustomPaginationMixin:
    """
    Mixin per pagination customizzata con page size variabile.

    Usage:
        class MiaView(CustomPaginationMixin, ListView):
            default_page_size = 20
            max_page_size = 100
    """

    default_page_size = 20
    max_page_size = 100
    page_size_query_param = "page_size"

    def get_paginate_by(self, queryset):
        """
        Ottiene page size da query params o usa default.

        Returns:
            int: Numero items per pagina
        """
        page_size = self.request.GET.get(self.page_size_query_param)

        if page_size:
            try:
                page_size = int(page_size)
                # Limita al max
                if page_size > self.max_page_size:
                    page_size = self.max_page_size
                return page_size
            except ValueError:
                pass

        return self.default_page_size


# ============================================================================
# FILTER MIXINS
# ============================================================================


class FilterMixin:
    """
    Mixin per filtrare queryset da GET parameters.

    Usage:
        class MiaView(FilterMixin, ListView):
            filter_fields = ['status', 'category', 'date']

        # URL: ?status=active&category=5
    """

    filter_fields = []

    def get_queryset(self):
        """Applica filtri da GET params"""
        queryset = super().get_queryset()

        for field in self.filter_fields:
            value = self.request.GET.get(field)
            if value:
                filter_kwargs = {field: value}
                queryset = queryset.filter(**filter_kwargs)

        return queryset


class SearchMixin:
    """
    Mixin per search functionality.

    Usage:
        class MiaView(SearchMixin, ListView):
            search_fields = ['nome', 'descrizione', 'codice']

        # URL: ?q=search_term
    """

    search_fields = []
    search_query_param = "q"

    def get_queryset(self):
        """Applica ricerca se presente"""
        queryset = super().get_queryset()
        query = self.request.GET.get(self.search_query_param)

        if query and self.search_fields:
            from django.db.models import Q

            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f"{field}__icontains": query})

            queryset = queryset.filter(q_objects)

        return queryset

    def get_context_data(self, **kwargs):
        """Aggiunge query al context"""
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get(self.search_query_param, "")
        return context


# ============================================================================
# BREADCRUMB MIXIN
# ============================================================================


class BreadcrumbMixin:
    """
    Mixin per gestire breadcrumb navigation.

    Usage:
        class MiaView(BreadcrumbMixin, DetailView):
            breadcrumbs = [
                ('Home', '/'),
                ('Ordini', reverse_lazy('vendite:ordine_list')),
                ('Dettaglio', None),  # None = current page
            ]
    """

    breadcrumbs = []

    def get_context_data(self, **kwargs):
        """Aggiunge breadcrumbs al context"""
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = self.get_breadcrumbs()
        return context

    def get_breadcrumbs(self):
        """
        Ottiene lista breadcrumbs.

        Override per breadcrumbs dinamici.

        Returns:
            list: Lista di tuple (label, url)
        """
        return self.breadcrumbs
