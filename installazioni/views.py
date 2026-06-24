from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db import transaction
from django.forms import modelformset_factory
from django.contrib.contenttypes.models import ContentType

from .models import Installazione, Postazione, InterventoInstallazione, RiscontroPostazione
from .forms import (
    InstallazioneForm, PostazioneForm,
    InterventoInstallazioneForm, RiscontroPostazioneForm,
)
from magazzino.models import Prodotto


# ── Installazioni ─────────────────────────────────────────────────────────────

@login_required
def installazione_list(request):
    qs = Installazione.objects.select_related(
        "filiale__cliente", "privato", "servizio",
    ).prefetch_related("postazioni")

    stato = request.GET.get("stato", "attive")
    if stato == "attive":
        qs = qs.filter(attiva=True)
    elif stato == "inattive":
        qs = qs.filter(attiva=False)

    cerca = request.GET.get("q", "").strip()
    if cerca:
        qs = qs.filter(numero__icontains=cerca)

    return render(request, "installazioni/installazione_list.html", {
        "installazioni": qs,
        "stato_sel": stato,
        "cerca": cerca,
    })


@login_required
def installazione_detail(request, pk):
    inst = get_object_or_404(
        Installazione.objects.select_related(
            "filiale__cliente", "privato", "servizio", "prodotto_principale", "created_by",
        ).prefetch_related("postazioni", "interventi__tecnico", "interventi__prodotto"),
        pk=pk,
    )
    return render(request, "installazioni/installazione_detail.html", {
        "inst": inst,
        "postazioni": inst.postazioni.all(),
        "interventi": inst.interventi.select_related("tecnico", "prodotto").all(),
        "content_type_id": ContentType.objects.get_for_model(Installazione).pk,
        "object_id": inst.pk,
        "postazione_form": PostazioneForm(),
        "prodotti_disponibili": Prodotto.objects.filter(attivo=True).order_by("nome_prodotto"),
    })


@login_required
def installazione_create(request):
    if request.method == "POST":
        form = InstallazioneForm(request.POST)
        if form.is_valid():
            inst = form.save(commit=False)
            inst.created_by = request.user
            inst.save()
            messages.success(request, f"Installazione {inst.numero} creata.")
            return redirect(inst.get_absolute_url())
    else:
        form = InstallazioneForm()
    return render(request, "installazioni/installazione_form.html", {
        "form": form, "title": "Nuova installazione",
    })


@login_required
def installazione_update(request, pk):
    inst = get_object_or_404(Installazione, pk=pk)
    if request.method == "POST":
        form = InstallazioneForm(request.POST, instance=inst)
        if form.is_valid():
            form.save()
            messages.success(request, "Installazione aggiornata.")
            return redirect(inst.get_absolute_url())
    else:
        form = InstallazioneForm(instance=inst)
    return render(request, "installazioni/installazione_form.html", {
        "form": form, "inst": inst, "title": f"Modifica {inst.numero}",
    })


# ── Postazioni ────────────────────────────────────────────────────────────────

@login_required
def postazione_detail(request, pk):
    post = get_object_or_404(
        Postazione.objects.select_related(
            "installazione__filiale__cliente",
            "installazione__privato",
            "installazione__servizio",
            "installazione__prodotto_principale",
        ),
        pk=pk,
    )
    interventi = post.installazione.interventi.select_related(
        "tecnico", "prodotto"
    ).prefetch_related("riscontri__postazione").all()

    return render(request, "installazioni/postazione_detail.html", {
        "post": post,
        "inst": post.installazione,
        "interventi": interventi,
        "content_type_id": ContentType.objects.get_for_model(Postazione).pk,
        "object_id": post.pk,
    })


@login_required
def postazione_create(request, inst_pk):
    inst = get_object_or_404(Installazione, pk=inst_pk)
    if request.method == "POST":
        form = PostazioneForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.installazione = inst
            post.save()
            messages.success(request, f"Postazione {post.numero:02d} aggiunta.")
            return redirect(inst.get_absolute_url() + "#postazioni")
    else:
        form = PostazioneForm()
    return render(request, "installazioni/postazione_form.html", {
        "form": form, "inst": inst, "title": "Aggiungi postazione",
    })


@login_required
def postazione_update(request, pk):
    post = get_object_or_404(Postazione, pk=pk)
    if request.method == "POST":
        form = PostazioneForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Postazione aggiornata.")
            return redirect(post.get_absolute_url())
    else:
        form = PostazioneForm(instance=post)
    return render(request, "installazioni/postazione_form.html", {
        "form": form, "inst": post.installazione, "post": post,
        "title": f"Modifica {post.label}",
    })


@login_required
def postazione_delete(request, pk):
    post = get_object_or_404(Postazione, pk=pk)
    inst = post.installazione
    if request.method == "POST":
        n = post.numero
        post.delete()
        messages.success(request, f"Postazione {n:02d} eliminata.")
        return redirect(inst.get_absolute_url())
    return render(request, "installazioni/postazione_confirm_delete.html", {
        "post": post, "inst": inst,
    })


# ── QR Code postazione ────────────────────────────────────────────────────────

@login_required
def postazione_qrcode(request, pk):
    post = get_object_or_404(Postazione, pk=pk)
    png_bytes = post.generate_qr_code(format="png")
    from django.http import HttpResponse
    return HttpResponse(png_bytes, content_type="image/png")


# ── Interventi ────────────────────────────────────────────────────────────────

@login_required
def intervento_detail(request, pk):
    intervento = get_object_or_404(
        InterventoInstallazione.objects.select_related(
            "installazione", "tecnico", "prodotto", "ods",
        ).prefetch_related("riscontri__postazione"),
        pk=pk,
    )
    return render(request, "installazioni/intervento_detail.html", {
        "intervento": intervento,
        "inst": intervento.installazione,
        "riscontri": intervento.riscontri.select_related("postazione").all(),
    })


@login_required
@transaction.atomic
def intervento_create(request, inst_pk):
    inst = get_object_or_404(Installazione, pk=inst_pk)
    postazioni = inst.postazioni.all()

    RiscontroFormSet = modelformset_factory(
        RiscontroPostazione,
        form=RiscontroPostazioneForm,
        extra=0,
    )

    if request.method == "POST":
        form = InterventoInstallazioneForm(request.POST)
        if form.is_valid():
            intervento = form.save(commit=False)
            intervento.installazione = inst
            intervento.created_by = request.user
            intervento.save()

            for post in postazioni:
                esito = request.POST.get(f"esito_{post.pk}", "")
                nota = request.POST.get(f"nota_{post.pk}", "")
                if esito:
                    RiscontroPostazione.objects.create(
                        intervento=intervento,
                        postazione=post,
                        esito=esito,
                        note=nota,
                    )

            messages.success(request, "Intervento registrato.")
            return redirect(intervento.get_absolute_url())
    else:
        form = InterventoInstallazioneForm(initial={"tecnico": request.user})

    return render(request, "installazioni/intervento_form.html", {
        "form": form,
        "inst": inst,
        "postazioni": postazioni,
        "esito_choices": RiscontroPostazione.Esito.choices,
        "title": "Nuovo intervento",
    })


@login_required
def intervento_delete(request, pk):
    intervento = get_object_or_404(InterventoInstallazione, pk=pk)
    inst = intervento.installazione
    if request.method == "POST":
        intervento.delete()
        messages.success(request, "Intervento eliminato.")
        return redirect(inst.get_absolute_url())
    return render(request, "installazioni/intervento_confirm_delete.html", {
        "intervento": intervento, "inst": inst,
    })
