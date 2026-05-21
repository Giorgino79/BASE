from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CorrispondenzaForm, CorrispondenzaSearchForm, TipoCorrispondenzaForm
from .models import Corrispondenza, TipoCorrispondenza


def _get_or_403(user, pk):
    obj = get_object_or_404(Corrispondenza, pk=pk)
    if obj.creato_da != user and not user.has_perm('corrispondenza.can_view_all'):
        raise PermissionDenied
    return obj


def _qs_visibili(user):
    if user.has_perm('corrispondenza.can_view_all'):
        return Corrispondenza.objects.all()
    return Corrispondenza.objects.filter(creato_da=user)


@login_required
def lista(request):
    qs = _qs_visibili(request.user).select_related(
        'destinatario_utente', 'tipo_corrispondenza', 'creato_da'
    )
    stats = {
        'totale': qs.count(),
        'bozze': qs.filter(stato='bozza').count(),
        'inviate': qs.filter(stato='inviata').count(),
        'archiviate': qs.filter(stato='archiviata').count(),
    }

    search_form = CorrispondenzaSearchForm(request.GET or None)
    if search_form.is_valid():
        q = search_form.cleaned_data.get('q')
        if q:
            qs = qs.filter(
                Q(oggetto__icontains=q) |
                Q(contenuto__icontains=q) |
                Q(numero_protocollo__icontains=q) |
                Q(destinatario_nome__icontains=q) |
                Q(destinatario_utente__first_name__icontains=q) |
                Q(destinatario_utente__last_name__icontains=q)
            )
        if search_form.cleaned_data.get('stato'):
            qs = qs.filter(stato=search_form.cleaned_data['stato'])
        if search_form.cleaned_data.get('priorita'):
            qs = qs.filter(priorita=search_form.cleaned_data['priorita'])
        if search_form.cleaned_data.get('tipo'):
            qs = qs.filter(tipo_corrispondenza=search_form.cleaned_data['tipo'])
        if search_form.cleaned_data.get('data_da'):
            qs = qs.filter(created_at__date__gte=search_form.cleaned_data['data_da'])
        if search_form.cleaned_data.get('data_a'):
            qs = qs.filter(created_at__date__lte=search_form.cleaned_data['data_a'])

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'corrispondenza/lista.html', {
        'page_obj': page_obj,
        'search_form': search_form,
        'stats': stats,
    })


@login_required
def dettaglio(request, pk):
    corrispondenza = _get_or_403(request.user, pk)
    return render(request, 'corrispondenza/dettaglio.html', {'corrispondenza': corrispondenza})


@login_required
def crea(request):
    if request.method == 'POST':
        form = CorrispondenzaForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.creato_da = request.user
            obj.save()
            messages.success(request, f'Corrispondenza {obj.numero_protocollo} creata.')
            return redirect('corrispondenza:dettaglio', pk=obj.pk)
    else:
        form = CorrispondenzaForm()
    return render(request, 'corrispondenza/form.html', {'form': form, 'title': 'Nuova Corrispondenza'})


@login_required
def modifica(request, pk):
    corrispondenza = _get_or_403(request.user, pk)
    if not corrispondenza.can_edit:
        messages.warning(request, 'Una corrispondenza già inviata non può essere modificata.')
        return redirect('corrispondenza:dettaglio', pk=pk)
    if request.method == 'POST':
        form = CorrispondenzaForm(request.POST, request.FILES, instance=corrispondenza)
        if form.is_valid():
            form.save()
            messages.success(request, 'Corrispondenza aggiornata.')
            return redirect('corrispondenza:dettaglio', pk=pk)
    else:
        form = CorrispondenzaForm(instance=corrispondenza)
    return render(request, 'corrispondenza/form.html', {
        'form': form,
        'corrispondenza': corrispondenza,
        'title': f'Modifica {corrispondenza.numero_protocollo}',
    })


@login_required
def elimina(request, pk):
    corrispondenza = _get_or_403(request.user, pk)
    if not corrispondenza.can_edit:
        messages.error(request, 'Solo le bozze possono essere eliminate.')
        return redirect('corrispondenza:dettaglio', pk=pk)
    if request.method == 'POST':
        n = corrispondenza.numero_protocollo
        corrispondenza.delete()
        messages.success(request, f'Corrispondenza {n} eliminata.')
        return redirect('corrispondenza:lista')
    return render(request, 'corrispondenza/elimina.html', {'corrispondenza': corrispondenza})


@login_required
@require_POST
def invia(request, pk):
    corrispondenza = _get_or_403(request.user, pk)
    if corrispondenza.stato == Corrispondenza.Stato.INVIATA:
        messages.warning(request, 'Già inviata.')
        return redirect('corrispondenza:dettaglio', pk=pk)
    corrispondenza.stato = Corrispondenza.Stato.INVIATA
    if not corrispondenza.data_invio:
        corrispondenza.data_invio = timezone.now().date()
    corrispondenza.save(update_fields=['stato', 'data_invio', 'updated_at'])

    invia_email = request.POST.get('invia_email') == 'on'
    if invia_email:
        email_dest = corrispondenza.get_destinatario_email()
        if email_dest:
            _invia_email(corrispondenza, email_dest)
            messages.success(request, f'Inviata e email spedita a {email_dest}.')
        else:
            messages.warning(request, 'Inviata, ma il destinatario non ha email.')
    else:
        messages.success(request, f'{corrispondenza.numero_protocollo} marcata come inviata.')
    return redirect('corrispondenza:dettaglio', pk=pk)


def _invia_email(corrispondenza, email_dest):
    from django.core.mail import send_mail
    from django.conf import settings
    try:
        send_mail(
            subject=f"Corrispondenza: {corrispondenza.oggetto}",
            message=corrispondenza.contenuto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_dest],
            fail_silently=True,
        )
    except Exception:
        pass


@login_required
def archivia(request, pk):
    corrispondenza = _get_or_403(request.user, pk)
    if corrispondenza.stato != Corrispondenza.Stato.INVIATA:
        messages.error(request, 'Solo le corrispondenze inviate possono essere archiviate.')
        return redirect('corrispondenza:dettaglio', pk=pk)
    if request.method == 'POST':
        corrispondenza.stato = Corrispondenza.Stato.ARCHIVIATA
        corrispondenza.save(update_fields=['stato', 'updated_at'])
        messages.success(request, 'Archiviata.')
        return redirect('corrispondenza:lista')
    return render(request, 'corrispondenza/archivia.html', {'corrispondenza': corrispondenza})


@login_required
def duplica(request, pk):
    orig = _get_or_403(request.user, pk)
    copia = Corrispondenza(
        tipo_destinatario=orig.tipo_destinatario,
        destinatario_utente=orig.destinatario_utente,
        destinatario_nome=orig.destinatario_nome,
        destinatario_indirizzo=orig.destinatario_indirizzo,
        destinatario_cap=orig.destinatario_cap,
        destinatario_citta=orig.destinatario_citta,
        destinatario_provincia=orig.destinatario_provincia,
        destinatario_email=orig.destinatario_email,
        destinatario_telefono=orig.destinatario_telefono,
        oggetto=f"Copia di: {orig.oggetto}",
        contenuto=orig.contenuto,
        tipo_corrispondenza=orig.tipo_corrispondenza,
        priorita=orig.priorita,
        note_interne=orig.note_interne,
        creato_da=request.user,
        stato=Corrispondenza.Stato.BOZZA,
    )
    copia.save()
    messages.success(request, f'Duplicata → {copia.numero_protocollo}')
    return redirect('corrispondenza:modifica', pk=copia.pk)


@login_required
def tipi_lista(request):
    """Gestione tipi di corrispondenza — lista + create inline."""
    if not request.user.is_staff:
        raise PermissionDenied

    tipi = TipoCorrispondenza.objects.all().order_by('nome')
    form = TipoCorrispondenzaForm()

    if request.method == 'POST':
        form = TipoCorrispondenzaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo aggiunto.')
            return redirect('corrispondenza:tipi_lista')

    return render(request, 'corrispondenza/tipi_lista.html', {'tipi': tipi, 'form': form})


@login_required
def tipo_modifica(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied
    tipo = get_object_or_404(TipoCorrispondenza, pk=pk)
    if request.method == 'POST':
        form = TipoCorrispondenzaForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo aggiornato.')
            return redirect('corrispondenza:tipi_lista')
    else:
        form = TipoCorrispondenzaForm(instance=tipo)
    return render(request, 'corrispondenza/tipo_form.html', {'form': form, 'tipo': tipo})


@login_required
@require_POST
def tipo_elimina(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied
    tipo = get_object_or_404(TipoCorrispondenza, pk=pk)
    tipo.delete()
    messages.success(request, f'Tipo "{tipo.nome}" eliminato.')
    return redirect('corrispondenza:tipi_lista')


@login_required
def pdf(request, pk):
    corrispondenza = _get_or_403(request.user, pk)
    from core.pdf_generator import genera_pdf_da_template
    return genera_pdf_da_template(
        'corrispondenza/pdf_lettera.html',
        {'corrispondenza': corrispondenza},
        filename=f"lettera_{corrispondenza.numero_protocollo}.pdf",
    )
