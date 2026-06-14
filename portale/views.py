from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from anagrafica_r2.models import Azienda, Filiale
from servizi.models import ODS, ConsumoMateriale
from .models import RichiestaIntervento, SegnalazioneInfestazione, FirmaDigitale


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_cliente(request):
    """Ritorna l'Azienda legata all'utente portale, o None."""
    try:
        return request.user.cliente_portale
    except Azienda.DoesNotExist:
        return None


def portal_login_required(view_fn):
    """Decorator: redirect a /cliente/login/ se non autenticato o non cliente portale."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('portale:login')
        if _get_cliente(request) is None:
            logout(request)
            return redirect('portale:login')
        return view_fn(request, *args, **kwargs)
    wrapper.__name__ = view_fn.__name__
    return wrapper


def _notify_riferimento(cliente, oggetto, messaggio):
    """Invia email + chat all'utente di riferimento del cliente."""
    ref = cliente.utente_riferimento
    if not ref:
        return

    # Email
    if ref.email:
        try:
            send_mail(
                subject=f"[Portale Clienti] {oggetto}",
                message=f"Cliente: {cliente.ragione_sociale}\n\n{messaggio}",
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[ref.email],
                fail_silently=True,
            )
        except Exception:
            pass

    # Chat interna
    try:
        from comunicazioni.models import ChatConversazione, ChatMessaggio
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Cerca o crea conversazione 1:1 tra sistema e riferimento
        conv = (ChatConversazione.objects
                .filter(partecipanti=ref)
                .filter(partecipanti__pk=ref.pk)
                .first())
        if not conv:
            conv = ChatConversazione.objects.create(creata_da=ref)
            conv.partecipanti.add(ref)

        ChatMessaggio.objects.create(
            conversazione=conv,
            mittente=ref,
            testo=f"[Portale cliente — {cliente.ragione_sociale}]\n{oggetto}\n\n{messaggio}",
        )
        conv.last_message_at = timezone.now()
        conv.save(update_fields=['last_message_at'])
    except Exception:
        pass


# ── Autenticazione ────────────────────────────────────────────────────────────

def portal_login(request):
    if request.user.is_authenticated and _get_cliente(request):
        return redirect('portale:dashboard')
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user and hasattr(user, 'cliente_portale'):
            login(request, user)
            return redirect(request.POST.get('next') or 'portale:dashboard')
        from django.contrib.auth.forms import AuthenticationForm
        form = AuthenticationForm(data=request.POST)
    else:
        from django.contrib.auth.forms import AuthenticationForm
        form = AuthenticationForm()
    return render(request, 'portale/login.html', {'form': form, 'next': request.GET.get('next', '')})


def portal_logout(request):
    logout(request)
    return redirect('portale:login')


# ── Dashboard ─────────────────────────────────────────────────────────────────

@portal_login_required
def dashboard(request):
    cliente = _get_cliente(request)
    richieste_aperte = RichiestaIntervento.objects.filter(cliente=cliente, gestita=False)
    return render(request, 'portale/dashboard.html', {
        'cliente': cliente,
        'richieste_aperte': richieste_aperte,
    })


# ── Bollettini ────────────────────────────────────────────────────────────────

@portal_login_required
def bollettini(request):
    cliente = _get_cliente(request)
    filiale_ids = cliente.filiali.values_list('pk', flat=True)
    ods_list = (ODS.objects
                .filter(filiale_id__in=filiale_ids, stato='completato')
                .select_related('filiale')
                .prefetch_related('righe__servizio', 'firma_digitale')
                .order_by('-data_servizio'))
    return render(request, 'portale/bollettini.html', {'ods_list': ods_list})


@portal_login_required
def bollettino_pdf(request, pk):
    """Proxy al PDF bollettino esistente del gestionale, verificando che l'ODS appartenga al cliente."""
    cliente = _get_cliente(request)
    filiale_ids = cliente.filiali.values_list('pk', flat=True)
    ods = get_object_or_404(ODS, pk=pk, filiale_id__in=filiale_ids)

    from django.template.loader import render_to_string
    from core.pdf_generator import generate_pdf_from_html, PDFConfig

    if ods.filiale:
        cliente_nome = ods.filiale.cliente.ragione_sociale
        cliente_indirizzo = getattr(ods.filiale, 'indirizzo', '') or getattr(ods.filiale.cliente, 'indirizzo', '')
        cliente_citta = getattr(ods.filiale, 'citta', '') or getattr(ods.filiale.cliente, 'citta', '')
    else:
        cliente_nome = cliente_indirizzo = cliente_citta = ''

    servizi_ods = {r.servizio.nome.strip().upper() for r in ods.righe.all()}
    def _svc(nome): return {'nome': nome, 'selezionato': nome.upper() in servizi_ods}

    # Includi firma digitale se presente
    firma = None
    try:
        firma = ods.firma_digitale.firma_svg
    except FirmaDigitale.DoesNotExist:
        pass

    ctx = {
        'ods': ods,
        'cliente_nome': cliente_nome,
        'cliente_indirizzo': cliente_indirizzo,
        'cliente_citta': cliente_citta,
        'servizi_sx': [_svc(n) for n in ['Profilassi', 'Disinfestazione', 'Derattizzazione', 'Sanificazione', 'Monitoraggio']],
        'servizi_dx': [_svc(n) for n in ['Lotta Integrata', 'Demuscazione', 'Antimurina', 'Deblattizzazione', 'Deformicazione', 'Antilarvale']],
        'prodotti_usati': [c for r in ods.righe.all() for c in r.consumi.all() if c.confermato],
        'oggi': timezone.now().date(),
        'firma_data': firma,
        'azienda_nome': 'SERVAL SRLS UNIPERSONALE',
        'azienda_indirizzo': 'Via Polense 473, 00132 Roma',
        'azienda_piva': '12894481006',
        'azienda_email': 'servalsrls@pec.it',
        'azienda_tel': '340/8002527 - 342/5204852',
    }
    html = render_to_string('servizi/ods/bollettino_pdf.html', ctx, request=request)
    return generate_pdf_from_html(html, PDFConfig(filename=f'bollettino_{ods.numero}.pdf'))


# ── Firma digitale ────────────────────────────────────────────────────────────

@portal_login_required
def firma_bollettino(request, pk):
    cliente = _get_cliente(request)
    filiale_ids = cliente.filiali.values_list('pk', flat=True)
    ods = get_object_or_404(ODS, pk=pk, filiale_id__in=filiale_ids, stato='completato')

    if hasattr(ods, 'firma_digitale'):
        messages.info(request, 'Questo bollettino è già stato firmato.')
        return redirect('portale:bollettini')

    if request.method == 'POST':
        firma_data = request.POST.get('firma_data', '')
        firmato_da = request.POST.get('firmato_da', '')
        if firma_data:
            FirmaDigitale.objects.create(
                ods=ods,
                firma_svg=firma_data,
                firmato_da=firmato_da,
            )
            messages.success(request, f'Bollettino {ods.numero} firmato con successo.')
            return redirect('portale:bollettini')

    return render(request, 'portale/firma_bollettino.html', {'ods': ods})


# ── Richiesta intervento ──────────────────────────────────────────────────────

@portal_login_required
def intervento(request):
    cliente = _get_cliente(request)
    filiali = cliente.filiali.filter(attivo=True)

    if request.method == 'POST':
        filiale_id = request.POST.get('filiale') or None
        filiale = Filiale.objects.filter(pk=filiale_id, cliente=cliente).first() if filiale_id else None
        richiesta = RichiestaIntervento.objects.create(
            cliente=cliente,
            filiale=filiale,
            tipo_problema=request.POST.get('tipo_problema', ''),
            urgenza=request.POST.get('urgenza', 'normale'),
            descrizione=request.POST.get('descrizione', ''),
            data_preferita=request.POST.get('data_preferita') or None,
        )
        urgenza_label = dict(RichiestaIntervento.URGENZA_CHOICES).get(richiesta.urgenza, '')
        _notify_riferimento(
            cliente,
            oggetto=f"Richiesta intervento [{urgenza_label.upper()}] — {richiesta.tipo_problema}",
            messaggio=(
                f"Sede: {filiale or 'Sede principale'}\n"
                f"Data preferita: {richiesta.data_preferita or 'non specificata'}\n\n"
                f"{richiesta.descrizione}"
            ),
        )
        messages.success(request, 'Richiesta inviata. Il nostro team ti contatterà a breve.')
        return redirect('portale:dashboard')

    return render(request, 'portale/intervento_form.html', {'filiali': filiali})


# ── Segnalazione infestazione ─────────────────────────────────────────────────

@portal_login_required
def segnalazione(request):
    cliente = _get_cliente(request)
    filiali = cliente.filiali.filter(attivo=True)

    if request.method == 'POST':
        filiale_id = request.POST.get('filiale') or None
        filiale = Filiale.objects.filter(pk=filiale_id, cliente=cliente).first() if filiale_id else None
        seg = SegnalazioneInfestazione.objects.create(
            cliente=cliente,
            filiale=filiale,
            luogo=request.POST.get('luogo', ''),
            infestante=request.POST.get('infestante', ''),
            note=request.POST.get('note', ''),
            foto=request.FILES.get('foto'),
        )
        _notify_riferimento(
            cliente,
            oggetto=f"Segnalazione infestazione — {seg.infestante}",
            messaggio=f"Luogo: {seg.luogo}\nSede: {filiale or 'Sede principale'}\n\n{seg.note}",
        )
        messages.success(request, 'Segnalazione inviata. Il team SERVAL è stato avvisato.')
        return redirect('portale:dashboard')

    return render(request, 'portale/segnalazione_form.html', {'filiali': filiali})


# ── Calendario ────────────────────────────────────────────────────────────────

@portal_login_required
def calendario(request):
    cliente = _get_cliente(request)
    filiale_ids = cliente.filiali.values_list('pk', flat=True)
    oggi = timezone.localdate()
    ods_list = (ODS.objects
                .filter(filiale_id__in=filiale_ids,
                        stato__in=['programmato', 'da_espletare'],
                        data_servizio__gte=oggi)
                .select_related('filiale', 'tecnico')
                .prefetch_related('righe__servizio')
                .order_by('data_servizio', 'ora_inizio'))
    return render(request, 'portale/calendario.html', {'ods_list': ods_list})


# ── Storico prodotti ──────────────────────────────────────────────────────────

@portal_login_required
def storico_prodotti(request):
    cliente = _get_cliente(request)
    filiale_ids = cliente.filiali.values_list('pk', flat=True)
    prodotti = (ConsumoMateriale.objects
                .filter(riga__ods__filiale_id__in=filiale_ids, confermato=True)
                .select_related('prodotto', 'riga__ods', 'riga__ods__filiale')
                .order_by('-riga__ods__data_servizio'))
    return render(request, 'portale/storico_prodotti.html', {'prodotti': prodotti})


# ── Documenti PMC ─────────────────────────────────────────────────────────────

@portal_login_required
def documenti_pmc(request):
    cliente = _get_cliente(request)
    filiale_ids = cliente.filiali.values_list('pk', flat=True)
    from magazzino.models import Prodotto
    prodotto_ids = (ConsumoMateriale.objects
                    .filter(riga__ods__filiale_id__in=filiale_ids, confermato=True)
                    .values_list('prodotto_id', flat=True).distinct())
    prodotti = Prodotto.objects.filter(pk__in=prodotto_ids).order_by('nome_prodotto')
    return render(request, 'portale/documenti_pmc.html', {'prodotti': prodotti})


# ── Contratto ─────────────────────────────────────────────────────────────────

@portal_login_required
def contratto(request):
    cliente = _get_cliente(request)
    from servizi.models import Contratto
    contratti = (Contratto.objects
                 .filter(cliente=cliente, stato='attivo')
                 .prefetch_related('righe__servizio')
                 .order_by('-data_inizio'))
    return render(request, 'portale/contratto.html', {'contratti': contratti})
