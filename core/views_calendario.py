"""
Views per il calendario aziendale e personale.

- CalendarioView: calendario aziendale, aggrega eventi da tutte le app
  registrate nel CalendarioRegistry con controllo permessi automatico.
- CalendarioPersonaleView: calendario personale dell'utente corrente,
  mostra ferie, permessi e promemoria dell'utente stesso.
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from datetime import datetime

from .calendario_registry import CalendarioRegistry


class CalendarioView(LoginRequiredMixin, TemplateView):
    """Calendario aziendale: eventi da tutte le app (con permessi)."""
    template_name = 'core/calendario.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Calendario Aziendale'
        context['providers_info'] = CalendarioRegistry.get_providers_info(self.request.user)
        context['categories'] = CalendarioRegistry.get_categories()
        return context


class CalendarioPersonaleView(LoginRequiredMixin, TemplateView):
    """Calendario personale: solo eventi dell'utente corrente."""
    template_name = 'core/calendario_personale.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Il Mio Calendario'
        return context


class CalendarioEventiAPIView(LoginRequiredMixin, View):
    """
    API JSON per il calendario aziendale.
    Usa CalendarioRegistry per aggregare eventi con controllo permessi.
    """

    def get(self, request):
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')

        # providers arriva come stringa CSV: "ferie_approvate,giri_distribuzione,..."
        # (FullCalendar 6 serializza gli array con virgola, non come param multipli)
        providers_raw = request.GET.get('providers', '')
        providers = [p.strip() for p in providers_raw.split(',') if p.strip()] if providers_raw else []

        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if start_date else None
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00')) if end_date else None
        except (ValueError, AttributeError):
            start = None
            end = None

        eventi = CalendarioRegistry.get_events_for_user(
            user=request.user,
            start_date=start,
            end_date=end,
            providers=providers if providers else None,
        )

        return JsonResponse(eventi, safe=False)


class CalendarioPersonaleEventiAPIView(LoginRequiredMixin, View):
    """
    API JSON per il calendario personale dell'utente.
    Aggrega direttamente ferie, permessi e promemoria dell'utente corrente.
    """

    def get(self, request):
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')

        try:
            start = datetime.fromisoformat(start_str.replace('Z', '+00:00')) if start_str else None
            end = datetime.fromisoformat(end_str.replace('Z', '+00:00')) if end_str else None
        except (ValueError, AttributeError):
            start = None
            end = None

        eventi = []
        user = request.user

        # --- Ferie dell'utente ---
        try:
            from users.models import RichiestaFerie
            from django.urls import reverse

            ferie_qs = RichiestaFerie.objects.filter(user=user)
            if start:
                ferie_qs = ferie_qs.filter(data_fine__gte=start.date())
            if end:
                ferie_qs = ferie_qs.filter(data_inizio__lte=end.date())

            colori_ferie = {
                'in_attesa': '#ffc107',
                'approvata': '#28a745',
                'rifiutata': '#dc3545',
            }

            for feria in ferie_qs.select_related('user')[:100]:
                # FullCalendar: end è esclusivo, aggiungiamo 1 giorno
                from datetime import timedelta
                data_fine_display = feria.data_fine + timedelta(days=1)
                eventi.append({
                    'id': f'ferie-{feria.pk}',
                    'title': f'Ferie ({feria.get_stato_display()})',
                    'start': feria.data_inizio.isoformat(),
                    'end': data_fine_display.isoformat(),
                    'color': colori_ferie.get(feria.stato, '#6c757d'),
                    'allDay': True,
                    'url': reverse('users:richieste_ferie_list'),
                    'extendedProps': {
                        'tipo': 'ferie',
                        'stato': feria.get_stato_display(),
                        'giorni': feria.giorni_richiesti,
                    }
                })
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Errore provider ferie personali: {e}")

        # --- Permessi dell'utente ---
        try:
            from users.models import RichiestaPermesso

            permessi_qs = RichiestaPermesso.objects.filter(user=user)
            if start:
                permessi_qs = permessi_qs.filter(data__gte=start.date())
            if end:
                permessi_qs = permessi_qs.filter(data__lte=end.date())

            colori_permessi = {
                'in_attesa': '#fd7e14',
                'approvata': '#17a2b8',
                'rifiutata': '#dc3545',
            }

            for permesso in permessi_qs[:100]:
                from datetime import datetime as dt, timedelta
                ora_inizio = dt.combine(permesso.data, permesso.ora_inizio)
                ora_fine = dt.combine(permesso.data, permesso.ora_fine)
                eventi.append({
                    'id': f'permesso-{permesso.pk}',
                    'title': f'Permesso ({permesso.get_stato_display()})',
                    'start': ora_inizio.isoformat(),
                    'end': ora_fine.isoformat(),
                    'color': colori_permessi.get(permesso.stato, '#6c757d'),
                    'allDay': False,
                    'url': reverse('users:richieste_ferie_list'),
                    'extendedProps': {
                        'tipo': 'permesso',
                        'stato': permesso.get_stato_display(),
                        'ore': str(permesso.ore_richieste),
                    }
                })
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Errore provider permessi personali: {e}")

        # --- Promemoria dell'utente ---
        try:
            from mail.models import Promemoria
            from django.db.models import Q
            from django.urls import reverse

            prom_qs = Promemoria.objects.filter(
                Q(user=user) | Q(assegnato_a=user)
            ).exclude(stato='cancelled').exclude(data_scadenza__isnull=True)

            if start:
                prom_qs = prom_qs.filter(data_scadenza__gte=start)
            if end:
                prom_qs = prom_qs.filter(data_scadenza__lte=end)

            colori_prom = {
                'pending': '#6c757d',
                'in_progress': '#007bff',
                'completed': '#28a745',
            }
            colori_priorita = {
                'urgente': '#dc3545',
                'alta': '#fd7e14',
                'media': '#007bff',
                'bassa': '#6c757d',
            }

            for prom in prom_qs.select_related('user', 'assegnato_a')[:100]:
                color = colori_priorita.get(prom.priorita, colori_prom.get(prom.stato, '#6c757d'))
                eventi.append({
                    'id': f'promemoria-{prom.pk}',
                    'title': f'📌 {prom.titolo}',
                    'start': prom.data_scadenza.isoformat(),
                    'color': color,
                    'url': reverse('mail:promemoria_detail', kwargs={'pk': prom.pk}),
                    'extendedProps': {
                        'tipo': 'promemoria',
                        'stato': prom.get_stato_display(),
                        'priorita': prom.get_priorita_display(),
                        'descrizione': prom.descrizione[:100] if prom.descrizione else '',
                    }
                })
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Errore provider promemoria personali: {e}")

        # --- EventoPersonale dell'utente ---
        try:
            from users.models import EventoPersonale
            from django.db.models import Q
            from django.urls import reverse

            ep_qs = EventoPersonale.objects.filter(utente=user, completato=False)
            if start and end:
                ep_qs = ep_qs.filter(
                    Q(data_inizio__lte=end) &
                    (Q(data_fine__isnull=True, data_inizio__gte=start) |
                     Q(data_fine__isnull=False, data_fine__gte=start))
                )
            elif start:
                ep_qs = ep_qs.filter(
                    Q(data_fine__isnull=True, data_inizio__gte=start) |
                    Q(data_fine__isnull=False, data_fine__gte=start)
                )
            elif end:
                ep_qs = ep_qs.filter(data_inizio__lte=end)

            for ep in ep_qs[:200]:
                eventi.append({
                    'id': f'evento-personale-{ep.pk}',
                    'title': ep.titolo,
                    'start': ep.data_inizio.isoformat(),
                    'end': ep.data_fine.isoformat() if ep.data_fine else None,
                    'allDay': ep.tutto_il_giorno,
                    'color': ep.colore or '#6f42c1',
                    'url': reverse('users:evento_personale_update', kwargs={'pk': ep.pk}),
                    'extendedProps': {
                        'tipo': 'evento_personale',
                        'sottotipo': ep.get_tipo_display(),
                        'priorita': ep.get_priorita_display(),
                        'descrizione': ep.descrizione[:100] if ep.descrizione else '',
                    }
                })
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Errore provider EventoPersonale: {e}")

        # --- Eventi manuali dell'utente (EventoCalendario) ---
        try:
            from .models import EventoCalendario
            from django.db.models import Q

            filtro = Q(creato_da=user) | Q(visibilita='aziendale')
            if start and end:
                filtro &= Q(data_inizio__lte=end) & (
                    Q(data_fine__isnull=True, data_inizio__gte=start) |
                    Q(data_fine__isnull=False, data_fine__gte=start)
                )
            elif start:
                filtro &= Q(data_fine__isnull=True, data_inizio__gte=start) | \
                           Q(data_fine__isnull=False, data_fine__gte=start)
            elif end:
                filtro &= Q(data_inizio__lte=end)

            for ev in EventoCalendario.objects.filter(filtro).select_related('creato_da')[:200]:
                eventi.append(ev.to_fullcalendar())
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Errore provider eventi manuali personali: {e}")

        return JsonResponse(eventi, safe=False)


# ─────────────────────────────────────────────────────────────────────────────
# CRUD EventoCalendario
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def evento_calendario_create(request):
    """Crea un nuovo evento calendario (via modal AJAX o pagina)."""
    from .forms_calendario import EventoCalendarioForm
    from .models import EventoCalendario

    # Pre-popola data_inizio da parametro GET (clic su cella FullCalendar)
    initial = {}
    date_param = request.GET.get('date')
    if date_param:
        try:
            initial['data_inizio'] = datetime.fromisoformat(date_param)
        except ValueError:
            pass

    if request.method == 'POST':
        form = EventoCalendarioForm(request.POST)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.creato_da = request.user
            evento.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'evento': evento.to_fullcalendar()})
            messages.success(request, 'Evento creato.')
            next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
            return redirect(next_url)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = EventoCalendarioForm(initial=initial)

    return render(request, 'core/evento_calendario_form.html', {
        'form': form,
        'titolo_pagina': 'Nuovo Evento',
        'action': 'create',
    })


@login_required
def evento_calendario_edit(request, pk):
    """Modifica un evento calendario (solo il creatore)."""
    from .forms_calendario import EventoCalendarioForm
    from .models import EventoCalendario

    evento = get_object_or_404(EventoCalendario, pk=pk, creato_da=request.user)

    if request.method == 'POST':
        form = EventoCalendarioForm(request.POST, instance=evento)
        if form.is_valid():
            form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'evento': evento.to_fullcalendar()})
            messages.success(request, 'Evento aggiornato.')
            next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
            return redirect(next_url)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = EventoCalendarioForm(instance=evento)

    return render(request, 'core/evento_calendario_form.html', {
        'form': form,
        'evento': evento,
        'titolo_pagina': 'Modifica Evento',
        'action': 'edit',
    })


@login_required
def evento_calendario_delete(request, pk):
    """Elimina un evento calendario (solo il creatore)."""
    from .models import EventoCalendario

    evento = get_object_or_404(EventoCalendario, pk=pk, creato_da=request.user)

    if request.method == 'POST':
        evento.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.success(request, 'Evento eliminato.')
        next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
        return redirect(next_url)

    return render(request, 'core/evento_calendario_confirm_delete.html', {'evento': evento})
