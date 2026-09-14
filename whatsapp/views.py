from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import WAConfig, WAMessaggio, WABroadcast, WABroadcastDestinatario
from .forms import WAConfigForm, InvioSingoloForm, WABroadcastForm, BroadcastDestinatariForm
from . import services


@login_required
def dashboard(request):
    config = WAConfig.get_or_create_singleton()
    status = services.get_status()

    ultimi_messaggi = WAMessaggio.objects.order_by("-created_at")[:10]
    broadcast_recenti = WABroadcast.objects.order_by("-created_at")[:5]

    oggi = timezone.now().date()
    stats = {
        "oggi": WAMessaggio.objects.filter(created_at__date=oggi, stato="sent").count(),
        "settimana": WAMessaggio.objects.filter(
            created_at__date__gte=oggi - timezone.timedelta(days=7), stato="sent"
        ).count(),
        "totale": WAMessaggio.objects.filter(stato="sent").count(),
        "falliti": WAMessaggio.objects.filter(stato="failed").count(),
    }

    return render(request, "whatsapp/dashboard.html", {
        "config": config,
        "status": status,
        "ultimi_messaggi": ultimi_messaggi,
        "broadcast_recenti": broadcast_recenti,
        "stats": stats,
    })


@login_required
def impostazioni(request):
    config = WAConfig.get_or_create_singleton()

    if request.method == "POST":
        form = WAConfigForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            cfg = form.save()
            # Propaga le impostazioni al microservizio se connesso
            if cfg.stato_wa:
                services.set_status_text(cfg.stato_wa)
            if cfg.foto_profilo:
                services.set_profile_picture(cfg.foto_profilo.path)
            messages.success(request, "Impostazioni salvate.")
            return redirect("whatsapp:impostazioni")
    else:
        form = WAConfigForm(instance=config)

    status = services.get_status()
    return render(request, "whatsapp/impostazioni.html", {
        "form": form,
        "config": config,
        "status": status,
    })


@login_required
def invia_singolo(request):
    config = WAConfig.get_or_create_singleton()

    if request.method == "POST":
        form = InvioSingoloForm(request.POST)
        if form.is_valid():
            numero = form.cleaned_data["numero"].strip().replace("+", "").replace(" ", "")
            nome = form.cleaned_data["nome"]
            testo = form.cleaned_data["testo"]

            msg = WAMessaggio.objects.create(
                destinatario_numero=numero,
                destinatario_nome=nome,
                testo=testo,
                tipo="manuale",
            )

            result = services.send_message(numero, testo)
            if result.get("success"):
                msg.stato = "sent"
                msg.inviato_at = timezone.now()
                messages.success(request, f"Messaggio inviato a {nome or numero}.")
            else:
                msg.stato = "failed"
                msg.errore = result.get("error", "Errore sconosciuto")
                messages.error(request, f"Invio fallito: {msg.errore}")
            msg.save()

            return redirect("whatsapp:dashboard")
    else:
        # Pre-fill da anagrafica se passato come querystring ?numero=...&nome=...
        form = InvioSingoloForm(initial={
            "numero": request.GET.get("numero", ""),
            "nome": request.GET.get("nome", ""),
        })

    return render(request, "whatsapp/invia.html", {"form": form, "config": config})


@login_required
def broadcast_list(request):
    broadcasts = WABroadcast.objects.order_by("-created_at")
    return render(request, "whatsapp/broadcast_list.html", {"broadcasts": broadcasts})


@login_required
def broadcast_create(request):
    config = WAConfig.get_or_create_singleton()

    if request.method == "POST":
        form = WABroadcastForm(request.POST)
        dest_form = BroadcastDestinatariForm(request.POST)
        if form.is_valid() and dest_form.is_valid():
            broadcast = form.save()
            _popola_destinatari(broadcast, dest_form.cleaned_data)
            messages.success(request, f"Broadcast '{broadcast.titolo}' creato con {broadcast.totale} destinatari.")
            return redirect("whatsapp:broadcast_detail", pk=broadcast.pk)
    else:
        form = WABroadcastForm()
        dest_form = BroadcastDestinatariForm()

    return render(request, "whatsapp/broadcast_create.html", {
        "form": form,
        "dest_form": dest_form,
        "config": config,
    })


@login_required
def broadcast_detail(request, pk):
    broadcast = get_object_or_404(WABroadcast, pk=pk)
    destinatari = broadcast.destinatari.order_by("stato", "nome")
    return render(request, "whatsapp/broadcast_detail.html", {
        "broadcast": broadcast,
        "destinatari": destinatari,
    })


@login_required
@require_POST
def broadcast_avvia(request, pk):
    """Avvia l'invio asincrono di un broadcast (task in background)."""
    broadcast = get_object_or_404(WABroadcast, pk=pk)
    if broadcast.stato != "bozza":
        messages.error(request, "Il broadcast non è in stato bozza.")
        return redirect("whatsapp:broadcast_detail", pk=pk)

    broadcast.stato = "in_corso"
    broadcast.avviato_at = timezone.now()
    broadcast.save()

    # Avvio thread in background per non bloccare la request
    import threading
    t = threading.Thread(target=_esegui_broadcast, args=(broadcast.pk,), daemon=True)
    t.start()

    messages.success(request, "Broadcast avviato. Puoi monitorare l'avanzamento in questa pagina.")
    return redirect("whatsapp:broadcast_detail", pk=pk)


@login_required
def api_status(request):
    """API JSON per polling dello stato connessione (usata dal template dashboard)."""
    return JsonResponse(services.get_status())


@login_required
@require_POST
def api_disconnetti(request):
    result = services.disconnect()
    return JsonResponse(result)


# ─── Helpers privati ───────────────────────────────────────────────────────────

def _popola_destinatari(broadcast, cleaned_data):
    from .contact_sources import contatti_per

    destinatari = []

    for fonte in cleaned_data.get("fonti", []):
        for numero, nome in contatti_per(fonte):
            if numero:
                destinatari.append(WABroadcastDestinatario(
                    broadcast=broadcast,
                    numero=_normalizza_numero(numero),
                    nome=nome,
                ))

    for riga in cleaned_data.get("numeri_manuali", "").splitlines():
        numero = riga.strip()
        if numero:
            destinatari.append(WABroadcastDestinatario(
                broadcast=broadcast,
                numero=_normalizza_numero(numero),
            ))

    # Deduplicazione per numero
    visti = set()
    unici = []
    for d in destinatari:
        if d.numero not in visti:
            visti.add(d.numero)
            unici.append(d)

    WABroadcastDestinatario.objects.bulk_create(unici)


def _normalizza_numero(numero):
    n = numero.strip().replace("+", "").replace(" ", "").replace("-", "")
    # Se inizia con 0 (numero italiano senza prefisso) → aggiungi 39
    if n.startswith("0"):
        n = "39" + n[1:]
    return n


def _esegui_broadcast(broadcast_pk):
    import time
    import random
    from django.db import connection

    try:
        broadcast = WABroadcast.objects.get(pk=broadcast_pk)
        config = WAConfig.get_or_create_singleton()

        for dest in broadcast.destinatari.filter(stato="pending"):
            if not config.attivo:
                break

            result = services.send_message(dest.numero, broadcast.messaggio)

            dest.inviato_at = timezone.now()
            if result.get("success"):
                dest.stato = "sent"
                WAMessaggio.objects.create(
                    destinatario_numero=dest.numero,
                    destinatario_nome=dest.nome,
                    testo=broadcast.messaggio,
                    stato="sent",
                    tipo="broadcast",
                    inviato_at=dest.inviato_at,
                )
            else:
                dest.stato = "failed"
                dest.errore = result.get("error", "")[:500]
            dest.save()

            delay = random.uniform(config.delay_min, config.delay_max)
            time.sleep(delay)

        broadcast.stato = "completata"
        broadcast.completato_at = timezone.now()
        broadcast.save()

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Errore broadcast {broadcast_pk}: {e}")
        try:
            WABroadcast.objects.filter(pk=broadcast_pk).update(stato="annullata")
        except Exception:
            pass
    finally:
        connection.close()
