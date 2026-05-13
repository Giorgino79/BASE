"""
Views per il calendario personale degli utenti.

Ogni utente ha un calendario personale nella propria dashboard
dove può creare e gestire eventi privati.
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views import View
from django.urls import reverse_lazy
from datetime import datetime
from .models import EventoPersonale
from .forms import EventoPersonaleForm


class EventoPersonaleAPIView(LoginRequiredMixin, View):
    """
    API per fornire eventi personali al calendario in formato JSON.
    Restituisce solo eventi dell'utente autenticato.
    """

    def get(self, request):
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')

        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if start_date else None
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00')) if end_date else None
        except (ValueError, AttributeError):
            start = None
            end = None

        eventi_qs = EventoPersonale.objects.filter(utente=request.user)

        if start and end:
            eventi_qs = eventi_qs.filter(
                data_inizio__gte=start,
                data_inizio__lte=end
            )

        eventi_qs = eventi_qs[:200]

        events = []
        for evento in eventi_qs:
            color = evento.colore
            title = evento.titolo
            if evento.completato:
                title = f'✓ {title}'
            if evento.priorita == 'alta':
                title = f'⚠️ {title}'

            events.append({
                'id': f'personal-{evento.id}',
                'title': title,
                'start': evento.data_inizio.isoformat(),
                'end': evento.data_fine.isoformat() if evento.data_fine else None,
                'allDay': evento.tutto_il_giorno,
                'color': color,
                'extendedProps': {
                    'tipo': evento.tipo,
                    'tipo_display': evento.get_tipo_display(),
                    'priorita': evento.priorita,
                    'descrizione': evento.descrizione,
                    'completato': evento.completato,
                    'evento_id': evento.id,
                }
            })

        return JsonResponse(events, safe=False)


class EventoPersonaleListView(LoginRequiredMixin, ListView):
    model = EventoPersonale
    template_name = 'users/evento_personale_list.html'
    context_object_name = 'eventi'
    paginate_by = 20

    def get_queryset(self):
        return EventoPersonale.objects.filter(
            utente=self.request.user
        ).order_by('-data_inizio')


class EventoPersonaleCreateView(LoginRequiredMixin, CreateView):
    model = EventoPersonale
    form_class = EventoPersonaleForm
    template_name = 'users/evento_personale_form.html'
    success_url = reverse_lazy('core:calendario_personale')

    def form_valid(self, form):
        form.instance.utente = self.request.user
        messages.success(self.request, 'Evento personale creato con successo!')
        return super().form_valid(form)


class EventoPersonaleUpdateView(LoginRequiredMixin, UpdateView):
    model = EventoPersonale
    form_class = EventoPersonaleForm
    template_name = 'users/evento_personale_form.html'
    success_url = reverse_lazy('core:calendario_personale')

    def get_queryset(self):
        return EventoPersonale.objects.filter(utente=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Evento personale aggiornato con successo!')
        return super().form_valid(form)


class EventoPersonaleDeleteView(LoginRequiredMixin, DeleteView):
    model = EventoPersonale
    success_url = reverse_lazy('core:calendario_personale')

    def get_queryset(self):
        return EventoPersonale.objects.filter(utente=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Evento personale eliminato con successo!')
        return super().delete(request, *args, **kwargs)


class EventoPersonaleToggleCompletato(LoginRequiredMixin, View):
    """API per marcare evento come completato/non completato"""

    def post(self, request, pk):
        try:
            evento = EventoPersonale.objects.get(pk=pk, utente=request.user)
            evento.completato = not evento.completato
            if evento.completato:
                evento.data_completamento = datetime.now()
            else:
                evento.data_completamento = None
            evento.save()
            return JsonResponse({'success': True, 'completato': evento.completato})
        except EventoPersonale.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Evento non trovato'}, status=404)
