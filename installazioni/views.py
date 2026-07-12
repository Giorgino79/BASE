from decimal import Decimal, InvalidOperation

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db import transaction, models as django_models
from django.forms import modelformset_factory
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Installazione, Postazione, InterventoInstallazione, RiscontroPostazione, Planimetria
from .forms import (
    InstallazioneForm, PostazioneForm,
    InterventoInstallazioneForm, RiscontroPostazioneForm,
    PlanimetriaForm,
)
from magazzino.models import Prodotto
from servizi.models import ODS, ODSRiga


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
        ).prefetch_related("postazioni", "interventi__tecnico", "interventi__prodotto", "planimetrie"),
        pk=pk,
    )

    if inst.filiale:
        invia_phone = inst.filiale.cliente.telefono or ""
        invia_email = inst.filiale.cliente.email_operativo or ""
        invia_nome  = inst.filiale.cliente.ragione_sociale
    elif inst.privato:
        invia_phone = getattr(inst.privato, "telefono", "")
        invia_email = getattr(inst.privato, "email", "")
        invia_nome  = str(inst.privato)
    else:
        invia_phone = invia_email = invia_nome = ""

    return render(request, "installazioni/installazione_detail.html", {
        "inst": inst,
        "postazioni": inst.postazioni.all(),
        "interventi": inst.interventi.select_related("tecnico", "prodotto").all(),
        "planimetrie": inst.planimetrie.all(),
        "planimetria_form": PlanimetriaForm(),
        "content_type_id": ContentType.objects.get_for_model(Installazione).pk,
        "object_id": inst.pk,
        "postazione_form": PostazioneForm(),
        "prodotti_disponibili": Prodotto.objects.filter(attivo=True).order_by("nome_prodotto"),
        "invia_phone": invia_phone,
        "invia_email": invia_email,
        "invia_nome": invia_nome,
        "pdf_url": reverse("installazioni:installazione_pdf", kwargs={"pk": inst.pk}),
    })


@login_required
@transaction.atomic
def installazione_create(request):
    if request.method == "POST":
        form = InstallazioneForm(request.POST)
        if form.is_valid():
            inst = form.save(commit=False)
            inst.created_by = request.user
            inst.save()

            # ODS automatico
            ods = ODS.objects.create(
                filiale=inst.filiale,
                privato=inst.privato,
                data_servizio=inst.data_installazione,
                stato=ODS.Stato.DA_ESPLETARE,
                note_intervento=f"Installazione {inst.numero} — {inst.servizio.nome}",
                created_by=request.user,
            )
            ODSRiga.objects.create(
                ods=ods,
                servizio=inst.servizio,
                prezzo=inst.servizio.tariffa_cartello,
                ordine=1,
            )
            inst.ods_creato = ods
            inst.save(update_fields=["ods_creato"])

            messages.success(request, f"Installazione {inst.numero} creata — ODS {ods.numero} generato automaticamente.")
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


@login_required
@require_POST
def installazione_chiudi(request, pk):
    inst = get_object_or_404(Installazione, pk=pk)
    inst.chiudi(request.user)
    messages.success(request, f"{inst.numero} segnata come completata il {inst.data_completamento:%d/%m/%Y}.")
    return redirect(inst.get_absolute_url())


@login_required
@require_POST
def installazione_riapri(request, pk):
    inst = get_object_or_404(Installazione, pk=pk)
    inst.riapri()
    messages.success(request, f"{inst.numero} riportata in corso.")
    return redirect(inst.get_absolute_url())


@login_required
def installazione_pdf(request, pk):
    """Report PDF di installazione completata: dati, postazioni, planimetrie con pin, QR."""
    from django.template.loader import render_to_string
    from core.pdf_generator import generate_pdf_from_html, PDFConfig
    import base64

    inst = get_object_or_404(
        Installazione.objects.select_related(
            "filiale__cliente", "privato", "servizio", "created_by", "chiusa_da",
        ),
        pk=pk,
    )
    postazioni = list(inst.postazioni.select_related("prodotto", "planimetria").order_by("numero"))

    planimetrie_ctx = []
    for pl in inst.planimetrie.all():
        pinned = [p for p in postazioni if p.planimetria_id == pl.pk and p.is_pinned]
        immagine_b64 = None
        errore_immagine = None
        try:
            img_bytes = pl.generate_annotated_image_bytes()
            immagine_b64 = base64.b64encode(img_bytes).decode("ascii")
        except Exception as exc:
            errore_immagine = str(exc)
        planimetrie_ctx.append({
            "planimetria": pl,
            "postazioni": pinned,
            "immagine_b64": immagine_b64,
            "errore_immagine": errore_immagine,
        })

    postazioni_qr = []
    for p in postazioni:
        try:
            qr_bytes = p.generate_qr_code(format="png")
            postazioni_qr.append({"postazione": p, "qr_b64": base64.b64encode(qr_bytes).decode("ascii")})
        except Exception:
            postazioni_qr.append({"postazione": p, "qr_b64": None})

    html = render_to_string("installazioni/pdf/installazione_pdf.html", {
        "inst": inst,
        "postazioni": postazioni,
        "planimetrie_ctx": planimetrie_ctx,
        "postazioni_qr": postazioni_qr,
    })
    filename = f"{inst.numero}_report_installazione.pdf"
    return generate_pdf_from_html(html, PDFConfig(filename=filename), output_type="response")


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
            foto = request.FILES.get("foto")
            if foto:
                post.aggiungi_allegato(foto, descrizione="Foto postazione", user=request.user)
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
            foto = request.FILES.get("foto")
            if foto:
                post.aggiungi_allegato(foto, descrizione="Foto postazione", user=request.user)
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


# ── Galleria foto postazioni ──────────────────────────────────────────────────

@login_required
def installazione_galleria(request, pk):
    inst = get_object_or_404(Installazione, pk=pk)
    from core.models_legacy import Allegato

    post_ct = ContentType.objects.get_for_model(Postazione)
    postazioni = list(inst.postazioni.all())
    post_ids = [str(p.pk) for p in postazioni]

    foto_qs = Allegato.objects.filter(
        content_type=post_ct,
        object_id__in=post_ids,
    ).filter(
        django_models.Q(tipo_file__startswith="image/") |
        django_models.Q(nome_originale__iregex=r"\.(jpg|jpeg|png|gif|bmp|webp)$")
    ).order_by("object_id", "created_at")

    foto_map = {}
    for f in foto_qs:
        foto_map.setdefault(int(f.object_id), []).append(f)

    sezioni = [
        (post, foto_map[post.pk])
        for post in postazioni
        if post.pk in foto_map
    ]

    return render(request, "installazioni/installazione_galleria.html", {
        "inst": inst,
        "sezioni": sezioni,
        "n_foto": sum(len(f) for _, f in sezioni),
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


# ── Planimetrie ───────────────────────────────────────────────────────────────

@login_required
def planimetria_create(request, inst_pk):
    inst = get_object_or_404(Installazione, pk=inst_pk)
    if request.method == "POST":
        form = PlanimetriaForm(request.POST, request.FILES)
        if form.is_valid():
            planimetria = form.save(commit=False)
            planimetria.installazione = inst
            planimetria.created_by = request.user
            planimetria.save()
            messages.success(request, "Planimetria caricata.")
            return redirect(planimetria.get_absolute_url())
        dettagli = "; ".join(
            f"{form.fields[campo].label}: {', '.join(errori)}"
            for campo, errori in form.errors.items()
        )
        messages.error(request, f"Errore nel caricamento della planimetria — {dettagli}")
    return redirect(inst.get_absolute_url())


@login_required
def planimetria_detail(request, pk):
    planimetria = get_object_or_404(
        Planimetria.objects.select_related("installazione"), pk=pk,
    )
    inst = planimetria.installazione
    posizionate = list(
        planimetria.postazioni
        .filter(pos_x__isnull=False, pos_y__isnull=False)
        .select_related("prodotto")
    )
    da_posizionare = list(
        inst.postazioni
        .exclude(pk__in=[p.pk for p in posizionate])
        .select_related("prodotto", "planimetria")
    )
    return render(request, "installazioni/planimetria_detail.html", {
        "planimetria": planimetria,
        "inst": inst,
        "posizionate": posizionate,
        "da_posizionare": da_posizionare,
    })


@login_required
def planimetria_delete(request, pk):
    planimetria = get_object_or_404(Planimetria, pk=pk)
    inst = planimetria.installazione
    if request.method == "POST":
        planimetria.delete()
        messages.success(request, "Planimetria eliminata.")
        return redirect(inst.get_absolute_url())
    return render(request, "installazioni/planimetria_confirm_delete.html", {
        "planimetria": planimetria, "inst": inst,
    })


@login_required
@require_POST
def postazione_pin(request, pk):
    """AJAX: posiziona (o sposta) una postazione su una planimetria."""
    postazione = get_object_or_404(Postazione, pk=pk)
    planimetria_id = request.POST.get("planimetria_id")
    pos_x = request.POST.get("pos_x")
    pos_y = request.POST.get("pos_y")

    planimetria = get_object_or_404(
        Planimetria, pk=planimetria_id, installazione_id=postazione.installazione_id,
    )
    try:
        x = Decimal(pos_x).quantize(Decimal("0.01"))
        y = Decimal(pos_y).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return JsonResponse({"ok": False, "error": "Coordinate non valide."})
    if not (0 <= x <= 100 and 0 <= y <= 100):
        return JsonResponse({"ok": False, "error": "Coordinate fuori intervallo."})

    postazione.planimetria = planimetria
    postazione.pos_x = x
    postazione.pos_y = y
    postazione.save(update_fields=["planimetria", "pos_x", "pos_y"])
    return JsonResponse({"ok": True})


@login_required
@require_POST
def postazione_unpin(request, pk):
    """AJAX: rimuove una postazione dalla planimetria su cui era posizionata."""
    postazione = get_object_or_404(Postazione, pk=pk)
    postazione.planimetria = None
    postazione.pos_x = None
    postazione.pos_y = None
    postazione.save(update_fields=["planimetria", "pos_x", "pos_y"])
    return JsonResponse({"ok": True})
