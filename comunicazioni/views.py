from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q

from .models import Promemoria, ChatConversazione, ChatMessaggio
from .forms import PromemoriaForm, NuovaConversazioneForm


# ── PROMEMORIA ────────────────────────────────────────────────────────────────

@login_required
def promemoria_list(request):
    stato_filter = request.GET.get('stato', '')
    qs = Promemoria.objects.filter(
        Q(user=request.user) | Q(assegnato_a=request.user)
    ).select_related('user', 'assegnato_a')

    if stato_filter:
        qs = qs.filter(stato=stato_filter)
    else:
        qs = qs.exclude(stato__in=['completato', 'annullato'])

    attivi_count = Promemoria.objects.filter(
        Q(user=request.user) | Q(assegnato_a=request.user),
        stato__in=['pending', 'in_corso'],
    ).count()

    return render(request, 'comunicazioni/promemoria_list.html', {
        'promemoria': qs,
        'stato_filter': stato_filter,
        'attivi_count': attivi_count,
    })


@login_required
def promemoria_create(request):
    if request.method == 'POST':
        form = PromemoriaForm(request.POST, user=request.user)
        if form.is_valid():
            p = form.save(commit=False)
            p.user = request.user
            p.save()
            messages.success(request, 'Promemoria creato.')
            return redirect('comunicazioni:promemoria_list')
    else:
        initial = {}
        if request.GET.get('link_url'):
            initial['link_url'] = request.GET['link_url']
        if request.GET.get('titolo'):
            initial['titolo'] = request.GET['titolo']
        form = PromemoriaForm(user=request.user, initial=initial)
    return render(request, 'comunicazioni/promemoria_form.html', {'form': form})


@login_required
def promemoria_update(request, pk):
    p = get_object_or_404(Promemoria, pk=pk, user=request.user)
    if request.method == 'POST':
        form = PromemoriaForm(request.POST, instance=p, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Promemoria aggiornato.')
            return redirect('comunicazioni:promemoria_list')
    else:
        form = PromemoriaForm(instance=p, user=request.user)
    return render(request, 'comunicazioni/promemoria_form.html', {'form': form, 'object': p})


@login_required
def promemoria_delete(request, pk):
    p = get_object_or_404(Promemoria, pk=pk, user=request.user)
    if request.method == 'POST':
        p.delete()
        messages.success(request, 'Promemoria eliminato.')
        return redirect('comunicazioni:promemoria_list')
    return render(request, 'comunicazioni/promemoria_confirm_delete.html', {'object': p})


@login_required
def promemoria_search_oggetto(request):
    """Ricerca veloce multi-modello per il widget link promemoria."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    from django.db.models import Q
    results = []

    try:
        from servizi.models import ODS, Distinta
        from django.urls import reverse

        # ODS
        ods_qs = ODS.objects.filter(
            Q(numero__icontains=q) |
            Q(privato__cognome__icontains=q) |
            Q(privato__nome__icontains=q) |
            Q(filiale__nome__icontains=q) |
            Q(filiale__cliente__ragione_sociale__icontains=q)
        ).select_related('privato', 'filiale__cliente')[:8]
        for o in ods_qs:
            cliente = str(o.privato) if o.privato else (str(o.filiale) if o.filiale else '—')
            results.append({
                'label': o.numero,
                'sub': cliente,
                'tipo': 'ODS',
                'url': o.get_absolute_url(),
            })

        # Distinte
        dist_qs = Distinta.objects.filter(
            Q(numero__icontains=q) |
            Q(nota__icontains=q) |
            Q(tecnico__first_name__icontains=q) |
            Q(tecnico__last_name__icontains=q)
        ).select_related('tecnico')[:5]
        for d in dist_qs:
            tecnico_nome = d.tecnico.get_full_name() if d.tecnico else ''
            results.append({
                'label': f'Distinta {d.numero}',
                'sub': (d.data.strftime('%d/%m/%Y') if d.data else '') + (f' — {tecnico_nome}' if tecnico_nome else ''),
                'tipo': 'Distinta',
                'url': d.get_absolute_url(),
            })
    except Exception:
        pass

    try:
        from anagrafica_r2.models import Privato, Azienda, Filiale
        from django.urls import reverse

        # Privati
        priv_qs = Privato.objects.filter(
            Q(cognome__icontains=q) | Q(nome__icontains=q) | Q(telefono__icontains=q)
        )[:5]
        for p in priv_qs:
            results.append({
                'label': p.nome_completo,
                'sub': p.citta or '',
                'tipo': 'Cliente privato',
                'url': p.get_absolute_url(),
            })

        # Aziende
        az_qs = Azienda.objects.filter(
            Q(ragione_sociale__icontains=q) | Q(marchio__icontains=q)
        )[:5]
        for a in az_qs:
            results.append({
                'label': a.ragione_sociale,
                'sub': a.marchio or a.citta or '',
                'tipo': 'Azienda',
                'url': a.get_absolute_url(),
            })
    except Exception:
        pass

    return JsonResponse({'results': results[:15]})


@login_required
def promemoria_toggle(request, pk):
    p = get_object_or_404(Promemoria, pk=pk)
    if p.user != request.user and p.assegnato_a != request.user:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    if p.stato == 'completato':
        p.stato = 'pending'
        p.completato_il = None
    else:
        p.stato = 'completato'
        p.completato_il = timezone.now()
    p.save()
    return JsonResponse({'stato': p.stato, 'completato': p.stato == 'completato'})


# ── CHAT ─────────────────────────────────────────────────────────────────────

def _conv_sidebar_data(user):
    qs = ChatConversazione.objects.filter(
        partecipanti=user
    ).prefetch_related('partecipanti').order_by('-last_message_at', '-created_at')
    result = []
    for conv in qs:
        result.append({
            'conv': conv,
            'title': conv.get_title_for(user),
            'unread': conv.unread_count_for(user),
            'ultimo': conv.messaggi.select_related('mittente').last(),
        })
    return result


@login_required
def chat_list(request):
    return render(request, 'comunicazioni/chat.html', {
        'conversazioni': _conv_sidebar_data(request.user),
        'selected_conv': None,
    })


@login_required
def chat_detail(request, pk):
    conv = get_object_or_404(ChatConversazione, pk=pk, partecipanti=request.user)

    if request.method == 'POST':
        contenuto = request.POST.get('contenuto', '').strip()
        if contenuto:
            msg = ChatMessaggio.objects.create(
                conversazione=conv,
                mittente=request.user,
                contenuto=contenuto,
            )
            msg.letto_da.add(request.user)
            conv.last_message_at = timezone.now()
            conv.save(update_fields=['last_message_at'])
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'id': msg.pk,
                    'contenuto': msg.contenuto,
                    'mittente': msg.mittente.get_full_name() or msg.mittente.username,
                    'created_at': msg.created_at.strftime('%d/%m %H:%M'),
                    'mine': True,
                })
        return redirect('comunicazioni:chat_detail', pk=pk)

    messaggi = conv.messaggi.select_related('mittente').all()
    for msg in messaggi.exclude(mittente=request.user):
        msg.letto_da.add(request.user)

    return render(request, 'comunicazioni/chat.html', {
        'conversazioni': _conv_sidebar_data(request.user),
        'selected_conv': conv,
        'conv_title': conv.get_title_for(request.user),
        'messaggi': messaggi,
    })


@login_required
def chat_nuova(request):
    if request.method == 'POST':
        form = NuovaConversazioneForm(request.POST, current_user=request.user)
        if form.is_valid():
            tipo = form.cleaned_data['tipo']
            destinatari = form.cleaned_data['destinatari']
            titolo = form.cleaned_data.get('titolo', '')

            if tipo == 'direct' and len(destinatari) == 1:
                other = destinatari[0]
                esistente = ChatConversazione.objects.filter(
                    tipo='direct', partecipanti=request.user
                ).filter(partecipanti=other).first()
                if esistente:
                    return redirect('comunicazioni:chat_detail', pk=esistente.pk)

            conv = ChatConversazione.objects.create(
                tipo=tipo, titolo=titolo, creata_da=request.user,
            )
            conv.partecipanti.add(request.user, *destinatari)
            return redirect('comunicazioni:chat_detail', pk=conv.pk)
    else:
        form = NuovaConversazioneForm(current_user=request.user)
    return render(request, 'comunicazioni/chat_nuova.html', {'form': form})


@login_required
def chat_messages_api(request, pk):
    conv = get_object_or_404(ChatConversazione, pk=pk, partecipanti=request.user)
    after_id = request.GET.get('after', 0)
    messaggi = conv.messaggi.filter(pk__gt=after_id).select_related('mittente')
    data = []
    for msg in messaggi:
        msg.letto_da.add(request.user)
        data.append({
            'id': msg.pk,
            'contenuto': msg.contenuto,
            'mittente': msg.mittente.get_full_name() or msg.mittente.username,
            'created_at': msg.created_at.strftime('%H:%M'),
            'mine': msg.mittente_id == request.user.pk,
        })
    return JsonResponse(data, safe=False)
