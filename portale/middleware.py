from django.shortcuts import redirect


PORTAL_PREFIX = '/cliente/'


class PortaleMiddleware:
    """
    Se l'utente autenticato è un cliente portale (ha un'Azienda collegata via portal_user),
    lo reindirizza sempre verso /cliente/ quando prova ad accedere a qualsiasi altra URL
    del gestionale interno.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.path.startswith(PORTAL_PREFIX)
            and not request.path.startswith('/admin/')
            and not request.path.startswith('/static/')
            and not request.path.startswith('/media/')
            and not request.path.startswith('/select2/')
            and self._is_portal_user(request.user)
        ):
            return redirect(PORTAL_PREFIX)

        return self.get_response(request)

    @staticmethod
    def _is_portal_user(user):
        try:
            return user.cliente_portale is not None
        except Exception:
            return False
