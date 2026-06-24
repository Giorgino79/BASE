"""
Print Mixins per CBV Django.

Aggiunge stampa lista/scheda a ListView e DetailView senza creare template ad hoc.
Basta definire print_fields sulla view: il template generico fa il resto.

Uso minimo lista:
    class ClienteListView(PrintListMixin, ListView):
        model = Cliente
        print_fields = ['nome', 'email', 'telefono']

Uso minimo dettaglio:
    class ClienteDetailView(PrintDetailMixin, DetailView):
        model = Cliente
        print_sections = [
            ('Dati anagrafici', ['nome', 'partita_iva']),
            ('Contatti',        ['email', 'telefono']),
        ]

Override template: crea {app}/{model}_print_list.html o {app}/{model}_print_detail.html
"""


class PrintListMixin:
    """
    Aggiunge stampa a qualsiasi ListView.

    Attributi configurabili:
      print_fields      — lista di str o (field_name, 'Etichetta')
      print_title       — titolo stampa (default: verbose_name_plural)
      print_orientation — 'portrait' | 'landscape'
    """

    print_fields = None
    print_title = None
    print_orientation = 'portrait'

    def is_print_request(self):
        return self.request.GET.get('print') == '1'

    def get_print_title(self):
        if self.print_title:
            return self.print_title
        if hasattr(self, 'model') and self.model:
            return str(self.model._meta.verbose_name_plural).capitalize()
        return 'Elenco'

    def get_print_fields(self):
        if self.print_fields:
            return self._normalize_fields(self.print_fields)
        if hasattr(self, 'model') and self.model:
            return [
                (f.name, str(f.verbose_name).capitalize())
                for f in self.model._meta.get_fields()
                if hasattr(f, 'verbose_name') and not getattr(f, 'is_relation', False)
            ]
        return []

    def _normalize_fields(self, fields):
        result = []
        for f in fields:
            if isinstance(f, (list, tuple)):
                result.append((str(f[0]), str(f[1])))
            else:
                label = str(f).replace('_', ' ').capitalize()
                if hasattr(self, 'model') and self.model:
                    try:
                        field_obj = self.model._meta.get_field(f)
                        if hasattr(field_obj, 'verbose_name'):
                            label = str(field_obj.verbose_name).capitalize()
                    except Exception:
                        pass
                result.append((str(f), label))
        return result

    def get_print_url(self):
        params = self.request.GET.copy()
        params['print'] = '1'
        params.pop('page', None)
        return '?' + params.urlencode()

    def get_paginate_by(self, queryset):
        if self.is_print_request():
            return None
        return super().get_paginate_by(queryset)

    def get_template_names(self):
        if self.is_print_request():
            if hasattr(self, 'model') and self.model:
                specific = (
                    f"{self.model._meta.app_label}/"
                    f"{self.model._meta.model_name}_print_list.html"
                )
                return [specific, 'commons_templates/print_list.html']
            return ['commons_templates/print_list.html']
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['print_url'] = self.get_print_url()
        ctx['is_print_mode'] = self.is_print_request()
        if self.is_print_request():
            ctx['print_title'] = self.get_print_title()
            ctx['print_fields'] = self.get_print_fields()
            ctx['print_orientation'] = self.print_orientation
        return ctx


class PrintDetailMixin:
    """
    Aggiunge stampa scheda a qualsiasi DetailView.

    Attributi configurabili:
      print_fields   — lista di str o (field_name, 'Etichetta')
      print_sections — lista di (titolo, [field_names]) per raggruppare i campi
      print_title    — titolo stampa (default: str(object))
    """

    print_fields = None
    print_sections = None
    print_title = None

    def is_print_request(self):
        return self.request.GET.get('print') == '1'

    def get_print_title(self):
        if self.print_title:
            return self.print_title
        if hasattr(self, 'object') and self.object:
            return str(self.object)
        return 'Dettaglio'

    def _normalize_fields(self, fields):
        result = []
        for f in fields:
            if isinstance(f, (list, tuple)):
                result.append((str(f[0]), str(f[1])))
            else:
                label = str(f).replace('_', ' ').capitalize()
                if hasattr(self, 'model') and self.model:
                    try:
                        field_obj = self.model._meta.get_field(f)
                        if hasattr(field_obj, 'verbose_name'):
                            label = str(field_obj.verbose_name).capitalize()
                    except Exception:
                        pass
                result.append((str(f), label))
        return result

    def get_print_fields(self):
        if self.print_fields:
            return self._normalize_fields(self.print_fields)
        if hasattr(self, 'model') and self.model:
            return [
                (f.name, str(f.verbose_name).capitalize())
                for f in self.model._meta.get_fields()
                if hasattr(f, 'verbose_name') and not getattr(f, 'is_relation', False)
            ]
        return []

    def get_print_sections(self):
        if self.print_sections:
            return [
                (title, self._normalize_fields(fields))
                for title, fields in self.print_sections
            ]
        return None

    def get_print_url(self):
        params = self.request.GET.copy()
        params['print'] = '1'
        return '?' + params.urlencode()

    def get_template_names(self):
        if self.is_print_request():
            if hasattr(self, 'model') and self.model:
                specific = (
                    f"{self.model._meta.app_label}/"
                    f"{self.model._meta.model_name}_print_detail.html"
                )
                return [specific, 'commons_templates/print_detail.html']
            return ['commons_templates/print_detail.html']
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['print_url'] = self.get_print_url()
        ctx['is_print_mode'] = self.is_print_request()
        if self.is_print_request():
            ctx['print_title'] = self.get_print_title()
            ctx['print_fields'] = self.get_print_fields()
            ctx['print_sections'] = self.get_print_sections()
        return ctx
