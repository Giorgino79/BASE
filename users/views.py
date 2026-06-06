"""
Views per l'app users.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum
from django.db import transaction
from django.core.paginator import Paginator
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from datetime import datetime, date, timedelta

from .models import (
    User,
    Timbratura,
    GiornataLavorativa,
    RichiestaFerie,
    RichiestaPermesso,
    LetteraRichiamo,
)
from .forms import (
    LoginForm,
    UserCreateForm,
    UserUpdateForm,
    UserProfiloForm,
    TimbraturaForm,
    TimbraturaQuickForm,
    RichiestaFerieForm,
    RichiestaFerieAdminForm,
    RichiestaPermessoForm,
    ApprovaRifiutaForm,
    LetteraRichiamoForm,
)
from .forms_permissions import UserPermissionsForm


# ============================================================================
# AUTENTICAZIONE
# ============================================================================


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if form.cleaned_data.get("remember_me"):
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)

            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

            messages.success(request, f"Benvenuto, {user.get_full_name() or user.username}!")

            next_url = request.GET.get("next") or request.POST.get("next")
            return redirect(next_url if next_url else "dashboard")
        else:
            messages.error(request, "Credenziali non valide. Riprova.")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    messages.info(request, "Logout effettuato con successo.")
    return redirect("users:login")


# ============================================================================
# DASHBOARD
# ============================================================================


@login_required
def dashboard_view(request):
    from comunicazioni.models import Promemoria, ChatConversazione, ChatMessaggio
    from django.db.models import Q

    oggi = date.today()

    users_attivi = User.objects.filter(stato="attivo").count()

    giornata_oggi = request.user.giornate.filter(data=oggi).first()
    ore_oggi = giornata_oggi.ore_totali if giornata_oggi else 0

    ferie_pending = request.user.richieste_ferie.filter(stato="in_attesa").count()
    permessi_pending = request.user.richieste_permessi.filter(stato="in_attesa").count()
    richieste_pending = ferie_pending + permessi_pending

    promemoria_attivi = Promemoria.objects.filter(
        assegnato_a=request.user, stato__in=["pending", "in_corso"]
    ).count()

    recent_promemoria = Promemoria.objects.filter(
        Q(assegnato_a=request.user) | Q(user=request.user),
        stato__in=["pending", "in_corso"],
    ).distinct().order_by("-created_at")[:5]

    total_conversations = ChatConversazione.objects.filter(
        partecipanti=request.user
    ).count()

    unread_messages = ChatMessaggio.objects.filter(
        conversazione__partecipanti=request.user
    ).exclude(mittente=request.user).exclude(letto_da=request.user).count()

    context = {
        "oggi": oggi,
        "stats": {
            "users_attivi": users_attivi,
            "ore_oggi": ore_oggi,
            "richieste_pending": richieste_pending,
            "promemoria_attivi": promemoria_attivi,
            "total_conversations": total_conversations,
            "unread_messages": unread_messages,
        },
        "recent_promemoria": recent_promemoria,
    }

    return render(request, "commons_templates/dashboard.html", context)


# ============================================================================
# CRUD USERS
# ============================================================================


@login_required
@permission_required("users.view_user", raise_exception=True)
def user_list_view(request):
    qs = User.objects.all().order_by("last_name", "first_name")

    attivo = request.GET.get("attivo")
    if attivo == "1":
        qs = qs.filter(is_active=True)
    elif attivo == "0":
        qs = qs.filter(is_active=False)

    q = request.GET.get("q")
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )

    paginator = Paginator(qs, 25)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    return render(request, "users/user_list.html", {
        "object_list": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
    })


@login_required
@permission_required("users.add_user", raise_exception=True)
@require_http_methods(["GET", "POST"])
def user_create_view(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"User {user.username} (codice: {user.codice_dipendente}) creato con successo!",
            )
            return redirect("users:user_detail", pk=user.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == "__all__":
                        messages.error(request, f"Errore: {error}")
                    else:
                        field_label = (
                            form.fields[field].label if field in form.fields else field
                        )
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = UserCreateForm()

    return render(request, "users/user_form.html", {"form": form, "title": "Crea Nuovo User"})


@login_required
@permission_required("users.view_user", raise_exception=True)
def user_detail_view(request, pk):
    user = get_object_or_404(User, pk=pk)

    oggi = date.today()
    mese_corrente = oggi.replace(day=1)
    timbrature_mese = user.timbrature.filter(data__gte=mese_corrente).count()
    giornate_mese = user.giornate.filter(data__gte=mese_corrente)
    ore_mese = giornate_mese.aggregate(totale=Sum("ore_totali"))["totale"] or 0

    ferie_pending = user.richieste_ferie.filter(stato="in_attesa").count()
    permessi_pending = user.richieste_permessi.filter(stato="in_attesa").count()
    lettere_non_lette = user.lettere_richiamo.filter(user_ha_letto=False).count()

    content_type = ContentType.objects.get_for_model(User)

    breadcrumbs = [
        {"label": "Dashboard", "url": "/"},
        {"label": "Dipendenti", "url": "/users/"},
        {"label": user.get_full_name() or user.username, "url": None},
    ]

    detail_config = {
        "title": user.get_full_name() or user.username,
        "subtitle": f"Codice: {user.codice_dipendente} | Username: {user.username}",
        "sections": [
            {
                "title": "Dati Anagrafici",
                "icon": "bi-person-vcard",
                "fields": [
                    {"label": "Email", "value": user.email or "-"},
                    {
                        "label": "Data Nascita",
                        "value": (
                            f'{user.data_nascita.strftime("%d/%m/%Y")} ({user.eta} anni)'
                            if user.data_nascita and user.eta
                            else (user.data_nascita.strftime("%d/%m/%Y") if user.data_nascita else "-")
                        ),
                    },
                    {"label": "Luogo Nascita", "value": user.luogo_nascita or "-"},
                    {"label": "Codice Fiscale", "value": user.codice_fiscale or "-"},
                    {"label": "Telefono", "value": user.telefono or "-"},
                    {"label": "Telefono Emergenza", "value": user.telefono_emergenza or "-"},
                    {
                        "label": "Indirizzo",
                        "value": (
                            f"{user.indirizzo}<br>{user.cap} {user.citta} ({user.provincia})"
                            if user.indirizzo
                            else "-"
                        ),
                    },
                ],
            },
            {
                "title": "Dati Lavorativi",
                "icon": "bi-briefcase",
                "fields": [
                    {
                        "label": "Stato",
                        "value": user.get_stato_display(),
                        "badge": True,
                        "badge_color": (
                            "success"
                            if user.stato == "attivo"
                            else ("warning" if user.stato == "sospeso" else "secondary")
                        ),
                    },
                    {"label": "Qualifica", "value": user.qualifica or "-"},
                    {"label": "Reparto", "value": user.reparto or "-"},
                    {
                        "label": "Data Assunzione",
                        "value": (
                            f'{user.data_assunzione.strftime("%d/%m/%Y")} ({user.anni_servizio} anni)'
                            if user.data_assunzione and user.anni_servizio
                            else (user.data_assunzione.strftime("%d/%m/%Y") if user.data_assunzione else "-")
                        ),
                    },
                    {
                        "label": "Data Cessazione",
                        "value": (
                            user.data_cessazione.strftime("%d/%m/%Y")
                            if user.data_cessazione
                            else "-"
                        ),
                    },
                    {"label": "Ferie Annuali", "value": f"{user.giorni_ferie_anno} giorni"},
                    {"label": "Ferie Utilizzate", "value": f"{user.ferie_utilizzate} giorni"},
                    {"label": "Ferie Residue", "value": f"{user.giorni_ferie_residui} giorni"},
                    {"label": "Permessi Residui", "value": f"{user.ore_permesso_residue} ore"},
                ],
            },
            {
                "title": "Statistiche Mese Corrente",
                "icon": "bi-graph-up",
                "fields": [
                    {"label": "Timbrature", "value": timbrature_mese},
                    {"label": "Ore Lavorate", "value": f"{ore_mese:.2f} ore"},
                    {
                        "label": "Richieste Pending",
                        "value": ferie_pending + permessi_pending,
                        "badge": (ferie_pending + permessi_pending) > 0,
                        "badge_color": "warning",
                    },
                    {
                        "label": "Lettere Richiamo Non Lette",
                        "value": lettere_non_lette,
                        "badge": lettere_non_lette > 0,
                        "badge_color": "danger",
                    },
                ],
            },
        ],
        "back_url": "users:user_list",
        "edit_url": "users:user_update",
        "show_allegati": True,
        "show_metadata": True,
        "sidebar_template": "users/includes/user_detail_sidebar.html",
    }

    tab = request.GET.get("tab", "info")
    storico_richieste = user.richieste_ferie.order_by("-data_inizio")[:20]

    # Presenze tab: raggruppa timbrature per giorno → stesso layout di timbratura_list
    from datetime import datetime as dt
    TURNO_ORDER = {"mattina": 0, "pomeriggio": 1, "notte": 2}
    tq = user.timbrature.order_by("data", "turno", "ora")
    gruppi = {}
    for t in tq:
        key = (t.data, t.turno)
        if key not in gruppi:
            gruppi[key] = {"data": t.data, "user": t.user, "turno": t.turno, "ingresso": None, "uscita": None, "ore_f": 0.0}
        if t.tipo == "ingresso":
            gruppi[key]["ingresso"] = t
        elif t.tipo == "uscita":
            gruppi[key]["uscita"] = t
    for r in gruppi.values():
        if r["ingresso"] and r["uscita"]:
            delta = dt.combine(r["data"], r["uscita"].ora) - dt.combine(r["data"], r["ingresso"].ora)
            if delta.total_seconds() < 0:
                delta += timedelta(days=1)
            r["ore_f"] = round(delta.total_seconds() / 3600, 2)
    giorni_p = {}
    for r in gruppi.values():
        dkey = r["data"]
        if dkey not in giorni_p:
            giorni_p[dkey] = {"data": r["data"], "user": r["user"], "turni": [], "ore_totali": 0.0}
        giorni_p[dkey]["turni"].append(r)
        giorni_p[dkey]["ore_totali"] += r["ore_f"]
    for g in giorni_p.values():
        ore_tot = g["ore_totali"]
        g["ore_ordinarie"] = min(ore_tot, 8.0)
        g["ore_straordinarie"] = max(0.0, ore_tot - 8.0)
        g["ha_straordinario"] = g["ore_straordinarie"] > 0
        g["turni"].sort(key=lambda x: TURNO_ORDER.get(x["turno"], 9))
    giorni_presenze = sorted(giorni_p.values(), key=lambda x: -x["data"].toordinal())

    context = {
        "profile_user": user,
        "user_obj": user,
        "object": user,
        "content_type_id": content_type.id,
        "timbrature_mese": timbrature_mese,
        "ore_mese": ore_mese,
        "ferie_pending": ferie_pending,
        "permessi_pending": permessi_pending,
        "lettere_non_lette": lettere_non_lette,
        "breadcrumbs": breadcrumbs,
        "detail_config": detail_config,
        "tab": tab,
        "giorni_presenze": giorni_presenze,
        "storico_richieste": storico_richieste,
        "allegati": user.allegati.select_related("uploaded_by").order_by("-created_at"),
    }

    return render(request, "users/user_detail.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def user_update_view(request, pk):
    user = get_object_or_404(User, pk=pk)

    if not request.user.has_perm("users.change_user"):
        if request.user.pk != user.pk:
            messages.error(request, "Non hai i permessi per modificare questo user.")
            return redirect("users:user_detail", pk=pk)

        if request.method == "POST":
            form = UserProfiloForm(request.POST, request.FILES, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, "Foto profilo aggiornata!")
                return redirect("users:user_detail", pk=pk)
        else:
            form = UserProfiloForm(instance=user)

        return render(
            request,
            "users/user_profilo_form.html",
            {"form": form, "user_obj": user, "title": "Modifica Foto Profilo"},
        )

    if request.method == "POST":
        form = UserUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f"User {user.username} aggiornato con successo!")
            return redirect("users:user_detail", pk=pk)
        else:
            messages.error(request, "Errore nell'aggiornamento. Verifica i campi.")
    else:
        form = UserUpdateForm(instance=user)

    return render(
        request,
        "users/user_form.html",
        {"form": form, "user_obj": user, "title": f"Modifica User: {user.username}"},
    )


# ============================================================================
# TIMBRATURE
# ============================================================================


@login_required
@require_http_methods(["POST"])
def timbratura_quick_view(request):
    form = TimbraturaQuickForm(request.POST)
    if form.is_valid():
        timbratura = Timbratura.objects.create(
            user=request.user,
            tipo=form.cleaned_data["tipo"],
            turno=form.cleaned_data["turno"],
            data=date.today(),
            ora=datetime.now().time(),
        )
        giornata, _ = GiornataLavorativa.objects.get_or_create(
            user=request.user, data=timbratura.data
        )
        giornata.calcola_ore()
        giornata.save()
        return JsonResponse(
            {
                "success": True,
                "message": f"Timbratura {timbratura.get_tipo_display()} - {timbratura.get_turno_display()} registrata!",
                "data": timbratura.data.isoformat(),
                "ora": timbratura.ora.strftime("%H:%M"),
            }
        )
    return JsonResponse({"success": False, "errors": form.errors}, status=400)


@login_required
def timbratura_stato_api(request):
    """Restituisce il turno aperto oggi (ingresso senza uscita corrispondente)."""
    oggi = date.today()
    timbrature_oggi = Timbratura.objects.filter(
        user=request.user, data=oggi
    ).values("tipo", "turno")

    ingressi = {t["turno"] for t in timbrature_oggi if t["tipo"] == "ingresso"}
    uscite = {t["turno"] for t in timbrature_oggi if t["tipo"] == "uscita"}
    turni_aperti = ingressi - uscite

    TURNO_ORDER = ["mattina", "pomeriggio", "notte"]
    turno_aperto = next((t for t in TURNO_ORDER if t in turni_aperti), None)

    return JsonResponse({
        "turno_aperto": turno_aperto,
        "ingressi": list(ingressi),
        "uscite": list(uscite),
    })


@login_required
@require_http_methods(["POST"])
def chiudi_giornata_view(request):
    oggi = date.today()
    try:
        giornata, _ = GiornataLavorativa.objects.get_or_create(
            user=request.user, data=oggi
        )
        giornata.calcola_ore()
        giornata.conclusa = True
        giornata.save()
        return JsonResponse(
            {
                "success": True,
                "message": f"Giornata chiusa! Ore totali: {giornata.ore_totali}h",
                "ore_totali": float(giornata.ore_totali),
                "ore_mattina": float(giornata.ore_mattina),
                "ore_pomeriggio": float(giornata.ore_pomeriggio),
                "ore_notte": float(giornata.ore_notte),
                "ore_straordinarie": float(giornata.ore_straordinarie),
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@permission_required("users.change_timbratura", raise_exception=True)
@require_http_methods(["GET", "POST"])
def timbratura_update_view(request, pk):
    timbratura = get_object_or_404(Timbratura, pk=pk)
    if request.method == "POST":
        form = TimbraturaForm(request.POST, instance=timbratura)
        if form.is_valid():
            form.save()
            messages.success(request, "Timbratura aggiornata.")
            return redirect("users:timbratura_list")
    else:
        form = TimbraturaForm(instance=timbratura)
    return render(request, "users/timbratura_form.html", {"form": form, "object": timbratura})


@login_required
def timbratura_list_view(request):
    from datetime import datetime as dt

    if request.user.is_staff:
        qs = Timbratura.objects.all().select_related("user")
        user_filter = request.GET.get("user")
        if user_filter:
            qs = qs.filter(user_id=user_filter)
    else:
        qs = request.user.timbrature.all().select_related("user")

    dal = request.GET.get("dal")
    if dal:
        qs = qs.filter(data__gte=dal)
    al = request.GET.get("al")
    if al:
        qs = qs.filter(data__lte=al)

    # --- Raggruppa per (data, user, turno) ---
    TURNO_ORDER = {"mattina": 0, "pomeriggio": 1, "notte": 2}
    gruppi = {}
    for t in qs.order_by("data", "user_id", "turno", "ora"):
        key = (t.data, t.user_id, t.turno)
        if key not in gruppi:
            gruppi[key] = {"data": t.data, "user": t.user, "turno": t.turno, "ingresso": None, "uscita": None, "ore_f": 0.0}
        if t.tipo == "ingresso":
            gruppi[key]["ingresso"] = t
        elif t.tipo == "uscita":
            gruppi[key]["uscita"] = t

    # Calcola ore per turno
    for r in gruppi.values():
        if r["ingresso"] and r["uscita"]:
            from datetime import timedelta
            delta = dt.combine(r["data"], r["uscita"].ora) - dt.combine(r["data"], r["ingresso"].ora)
            if delta.total_seconds() < 0:
                delta += timedelta(days=1)
            r["ore_f"] = round(delta.total_seconds() / 3600, 2)

    # --- Raggruppa per giorno per calcolare ore/straordinari giornalieri ---
    giorni = {}
    for r in gruppi.values():
        dkey = (r["data"], r["user"].pk)
        if dkey not in giorni:
            giorni[dkey] = {"data": r["data"], "user": r["user"], "turni": [], "ore_totali": 0.0}
        giorni[dkey]["turni"].append(r)
        giorni[dkey]["ore_totali"] += r["ore_f"]

    for g in giorni.values():
        ore_tot = g["ore_totali"]
        g["ore_ordinarie"] = min(ore_tot, 8.0)
        g["ore_straordinarie"] = max(0.0, ore_tot - 8.0)
        g["ha_straordinario"] = g["ore_straordinarie"] > 0
        iso = g["data"].isocalendar()
        g["settimana_iso"] = (iso[0], iso[1])
        # Ordina turni per ordine naturale
        g["turni"].sort(key=lambda x: TURNO_ORDER.get(x["turno"], 9))

    # --- Raggruppa per settimana ISO per calcolare straordinari settimanali ---
    settimane = {}
    for g in giorni.values():
        wkey = (g["user"].pk, g["settimana_iso"])
        if wkey not in settimane:
            settimane[wkey] = {"user": g["user"], "settimana": g["settimana_iso"], "ore_ordinarie": 0.0, "ore_straord_giorn": 0.0}
        settimane[wkey]["ore_ordinarie"] += g["ore_ordinarie"]
        settimane[wkey]["ore_straord_giorn"] += g["ore_straordinarie"]

    for s in settimane.values():
        s["ore_straord_sett"] = max(0.0, s["ore_ordinarie"] - 40.0)
        s["ore_straordinarie_totali"] = s["ore_straord_giorn"] + s["ore_straord_sett"]

    # Annota ogni giorno con i totali settimanali
    for g in giorni.values():
        wkey = (g["user"].pk, g["settimana_iso"])
        g["sett"] = settimane.get(wkey, {})

    # Ordina per data decrescente
    giorni_lista = sorted(giorni.values(), key=lambda x: (-x["data"].toordinal(), x["user"].last_name))

    paginator = Paginator(giorni_lista, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    tutti_utenti = User.objects.filter(is_active=True).order_by("last_name", "first_name") if request.user.is_staff else []

    return render(request, "users/timbratura_list.html", {
        "giorni": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "tutti_utenti": tutti_utenti,
    })


@login_required
@login_required
def giornata_lavorativa_list_view(request):
    if request.user.is_staff:
        giornate = GiornataLavorativa.objects.all().select_related("user").order_by("-data")
        user_filter = request.GET.get("user")
        if user_filter:
            giornate = giornate.filter(user_id=user_filter)
        tutti_utenti = User.objects.filter(is_active=True).order_by("last_name", "first_name")
    else:
        giornate = request.user.giornate.all().order_by("-data")
        tutti_utenti = []

    # Filtro per mese (input type=month → "YYYY-MM")
    mese = request.GET.get("mese")
    if mese:
        try:
            anno, m = mese.split("-")
            giornate = giornate.filter(data__year=int(anno), data__month=int(m))
        except (ValueError, AttributeError):
            mese = None
    else:
        # Default: mese corrente
        oggi = date.today()
        mese = oggi.strftime("%Y-%m")
        giornate = giornate.filter(data__year=oggi.year, data__month=oggi.month)

    stato = request.GET.get("stato")
    if stato == "conclusa":
        giornate = giornate.filter(conclusa=True)
    elif stato == "in_corso":
        giornate = giornate.filter(conclusa=False)

    ore_totali = giornate.aggregate(totale=Sum("ore_totali"))["totale"] or 0
    straordinari = giornate.aggregate(totale=Sum("ore_straordinarie"))["totale"] or 0
    num_giornate = giornate.count()
    media_ore = ore_totali / num_giornate if num_giornate > 0 else 0

    # URL PDF con i filtri correnti (per il modal invia)
    from django.urls import reverse as _reverse
    from urllib.parse import urlencode as _urlencode
    _pdf_params = {k: v for k, v in [("mese", mese), ("stato", stato)] if v}
    if request.user.is_staff and user_filter:
        _pdf_params["user"] = user_filter
    giornate_pdf_url = _reverse("users:giornate_export_pdf") + (
        "?" + _urlencode(_pdf_params) if _pdf_params else ""
    )

    # Destinatario del messaggio
    if request.user.is_staff and user_filter:
        try:
            _dest = User.objects.get(pk=user_filter)
        except User.DoesNotExist:
            _dest = request.user
    else:
        _dest = request.user

    return render(request, "users/giornata_list.html", {
        "giornate": giornate,
        "ore_totali": ore_totali,
        "straordinari": straordinari,
        "media_ore": media_ore,
        "mese": mese,
        "tutti_utenti": tutti_utenti,
        "locked_user": None if request.user.is_staff else request.user,
        "giornate_pdf_url": giornate_pdf_url,
        "invia_destinatario": _dest,
    })


# ============================================================================
# FERIE E PERMESSI
# ============================================================================


@login_required
@require_http_methods(["GET", "POST"])
def richiesta_ferie_create_view(request):
    if request.method == "POST":
        form = RichiestaFerieForm(request.POST)
        if form.is_valid():
            try:
                richiesta = form.save(commit=False)
                richiesta.user = request.user
                if richiesta.giorni_richiesti > request.user.giorni_ferie_residui:
                    messages.error(
                        request,
                        f"Giorni richiesti ({richiesta.giorni_richiesti}) superiori a disponibili ({request.user.giorni_ferie_residui})",
                    )
                    return render(request, "users/richiesta_ferie_form.html", {"form": form})
                form_with_user = RichiestaFerieForm(request.POST, instance=richiesta)
                if form_with_user.is_valid():
                    form_with_user.save()
                    messages.success(request, "Richiesta ferie inviata!")
                    return redirect("users:richieste_ferie_list")
                else:
                    for field, errors in form_with_user.errors.items():
                        for error in errors:
                            messages.error(request, str(error))
                    return render(request, "users/richiesta_ferie_form.html", {"form": form_with_user})
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, "users/richiesta_ferie_form.html", {"form": form})
        else:
            messages.error(request, "Errore nella richiesta. Verifica i campi.")
    else:
        form = RichiestaFerieForm()

    return render(
        request,
        "users/richiesta_ferie_form.html",
        {"form": form, "giorni_disponibili": request.user.giorni_ferie_residui},
    )


@login_required
@require_http_methods(["GET", "POST"])
def richiesta_permesso_create_view(request):
    if request.method == "POST":
        form = RichiestaPermessoForm(request.POST)
        if form.is_valid():
            richiesta = form.save(commit=False)
            richiesta.user = request.user
            richiesta.save()
            messages.success(request, "Richiesta permesso inviata!")
            return redirect("users:richieste_permessi_list")
        else:
            messages.error(request, "Errore nella richiesta. Verifica i campi.")
    else:
        form = RichiestaPermessoForm()

    return render(
        request,
        "users/richiesta_permesso_form.html",
        {"form": form, "ore_disponibili": request.user.ore_permesso_residue},
    )


@login_required
@require_http_methods(["GET", "POST"])
def richiesta_ferie_update_view(request, pk):
    richiesta = get_object_or_404(RichiestaFerie, pk=pk, user=request.user, stato="in_attesa")
    if request.method == "POST":
        form = RichiestaFerieForm(request.POST, instance=richiesta)
        if form.is_valid():
            form.save()
            messages.success(request, "Richiesta aggiornata.")
            return redirect("users:richieste_ferie_list")
    else:
        form = RichiestaFerieForm(instance=richiesta)
    return render(request, "users/richiesta_ferie_form.html", {"form": form, "object": richiesta})


@login_required
def richieste_ferie_list_view(request):
    richieste = request.user.richieste_ferie.all().order_by("-created_at")
    stato = request.GET.get("stato")
    if stato:
        richieste = richieste.filter(stato=stato)
    paginator = Paginator(richieste, 20)
    richieste_page = paginator.get_page(request.GET.get("page"))
    return render(request, "users/richieste_ferie_list.html", {"richieste": richieste_page})


@login_required
def richieste_permessi_list_view(request):
    richieste = request.user.richieste_permessi.all().order_by("-created_at")
    stato = request.GET.get("stato")
    if stato:
        richieste = richieste.filter(stato=stato)
    paginator = Paginator(richieste, 20)
    richieste_page = paginator.get_page(request.GET.get("page"))
    return render(request, "users/richieste_permessi_list.html", {"richieste": richieste_page})


@login_required
@permission_required("users.approva_ferie", raise_exception=True)
def richiesta_ferie_gestisci_view(request, pk):
    richiesta = get_object_or_404(RichiestaFerie, pk=pk)
    if request.method == "POST":
        form = ApprovaRifiutaForm(request.POST)
        if form.is_valid():
            azione = form.cleaned_data["azione"]
            if azione == "approva":
                richiesta.approva(amministratore=request.user)
                messages.success(request, f"Ferie di {richiesta.user.get_full_name()} approvate!")
            else:
                richiesta.rifiuta(
                    amministratore=request.user,
                    motivazione=form.cleaned_data["motivazione_rifiuto"],
                )
                messages.warning(request, f"Ferie di {richiesta.user.get_full_name()} rifiutate.")
            return redirect("users:richieste_ferie_admin_list")
        else:
            messages.error(request, "Errore nella gestione richiesta.")
            return redirect("users:richieste_ferie_admin_list")

    altre_richieste = (
        RichiestaFerie.objects.filter(user=richiesta.user).exclude(pk=pk).order_by("-created_at")[:5]
    )
    return render(
        request,
        "users/richiesta_ferie_gestisci.html",
        {"richiesta": richiesta, "altre_richieste": altre_richieste, "form": ApprovaRifiutaForm()},
    )


@login_required
@permission_required("users.approva_permessi", raise_exception=True)
def richiesta_permesso_gestisci_view(request, pk):
    richiesta = get_object_or_404(RichiestaPermesso, pk=pk)
    if request.method == "POST":
        form = ApprovaRifiutaForm(request.POST)
        if form.is_valid():
            azione = form.cleaned_data["azione"]
            if azione == "approva":
                richiesta.approva(amministratore=request.user)
                messages.success(request, f"Permesso di {richiesta.user.get_full_name()} approvato!")
            else:
                richiesta.rifiuta(
                    amministratore=request.user,
                    motivazione=form.cleaned_data["motivazione_rifiuto"],
                )
                messages.warning(request, f"Permesso di {richiesta.user.get_full_name()} rifiutato.")
            return redirect("users:richieste_permessi_admin_list")
        else:
            messages.error(request, "Errore nella gestione richiesta.")
            return redirect("users:richieste_permessi_admin_list")

    altre_richieste = (
        RichiestaPermesso.objects.filter(user=richiesta.user)
        .exclude(pk=pk)
        .order_by("-created_at")[:5]
    )
    return render(
        request,
        "users/richiesta_permesso_gestisci.html",
        {"richiesta": richiesta, "altre_richieste": altre_richieste, "form": ApprovaRifiutaForm()},
    )


@login_required
@permission_required("users.approva_ferie", raise_exception=True)
def richieste_ferie_admin_list_view(request):
    stato_filter = request.GET.get("stato", "in_attesa")
    user_filter = request.GET.get("user")

    richieste = RichiestaFerie.objects.all().select_related("user")
    if stato_filter:
        richieste = richieste.filter(stato=stato_filter)
    if user_filter:
        richieste = richieste.filter(user_id=user_filter)
    richieste = richieste.order_by("-created_at")

    richieste_pending_count = RichiestaFerie.objects.filter(stato="in_attesa").count()
    tutti_utenti = User.objects.filter(is_active=True).order_by("last_name", "first_name")
    paginator = Paginator(richieste, 20)
    richieste_page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "users/richieste_ferie_admin_list.html",
        {
            "richieste": richieste_page,
            "richieste_pending_count": richieste_pending_count,
            "tutti_utenti": tutti_utenti,
            "stato_filter": stato_filter,
        },
    )


@login_required
@permission_required("users.approva_ferie", raise_exception=True)
def richiesta_ferie_admin_create_view(request):
    if request.method == "POST":
        form = RichiestaFerieAdminForm(request.POST)
        if form.is_valid():
            try:
                richiesta = form.save(commit=False)
                richiesta.giorni_richiesti = form.cleaned_data.get("giorni_richiesti", 0)
                richiesta.full_clean()
                richiesta.save()
                richiesta.approva(request.user)
                messages.success(
                    request,
                    f"Ferie registrate per {richiesta.user.get_full_name()} ({richiesta.data_inizio} - {richiesta.data_fine}).",
                )
                return redirect("users:richieste_ferie_admin_list")
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Errore nella richiesta. Verifica i campi.")
    else:
        form = RichiestaFerieAdminForm()
    return render(request, "users/richiesta_ferie_admin_form.html", {"form": form})


@login_required
@permission_required("users.approva_permessi", raise_exception=True)
def richieste_permessi_admin_list_view(request):
    filter_type = request.GET.get("filter", "in_attesa")
    richieste = (
        RichiestaPermesso.objects.all()
        if filter_type == "tutte"
        else RichiestaPermesso.objects.filter(stato=filter_type)
    )
    richieste = richieste.select_related("user").order_by("-created_at")
    richieste_pending = RichiestaPermesso.objects.filter(stato="in_attesa")
    paginator = Paginator(richieste, 20)
    richieste_page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "users/richieste_permessi_admin_list.html",
        {"richieste": richieste_page, "richieste_pending": richieste_pending, "filter": filter_type},
    )


# ============================================================================
# LETTERA RICHIAMO
# ============================================================================


@login_required
@permission_required("users.emetti_lettera_richiamo", raise_exception=True)
@require_http_methods(["GET", "POST"])
def lettera_richiamo_create_view(request):
    if request.method == "POST":
        form = LetteraRichiamoForm(request.POST)
        if form.is_valid():
            lettera = form.save(commit=False)
            lettera.emessa_da = request.user
            lettera.save()
            messages.success(
                request,
                f"Lettera {lettera.get_tipo_display()} emessa per {lettera.user.get_full_name()}.",
            )
            return redirect("users:user_detail", pk=lettera.user.pk)
        else:
            messages.error(request, "Errore nell'emissione lettera.")
    else:
        form = LetteraRichiamoForm()
    return render(request, "users/lettera_richiamo_form.html", {"form": form})


@login_required
@permission_required("users.emetti_lettera_richiamo", raise_exception=True)
@require_http_methods(["GET", "POST"])
def lettera_richiamo_update_view(request, pk):
    lettera = get_object_or_404(LetteraRichiamo, pk=pk)
    if request.method == "POST":
        form = LetteraRichiamoForm(request.POST, instance=lettera)
        if form.is_valid():
            form.save()
            messages.success(request, "Lettera aggiornata.")
            return redirect("users:lettera_richiamo_list")
        else:
            messages.error(request, "Correggi gli errori nel form.")
    else:
        form = LetteraRichiamoForm(instance=lettera)
    return render(request, "users/lettera_richiamo_form.html", {"form": form, "object": lettera})


@login_required
def lettera_richiamo_list_view(request):
    if request.user.is_superuser or request.user.has_perm("users.emetti_lettera_richiamo"):
        lettere = LetteraRichiamo.objects.all().select_related("user", "emessa_da")
        search = request.GET.get("search")
        if search:
            lettere = lettere.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__codice_dipendente__icontains=search)
            )
        tipo = request.GET.get("tipo")
        if tipo:
            lettere = lettere.filter(tipo=tipo)
        data_da = request.GET.get("data_da")
        if data_da:
            lettere = lettere.filter(data_emissione__gte=data_da)
        data_a = request.GET.get("data_a")
        if data_a:
            lettere = lettere.filter(data_emissione__lte=data_a)
    else:
        lettere = request.user.lettere_richiamo.all()
        lettere.filter(user_ha_letto=False).update(
            user_ha_letto=True, data_lettura=timezone.now()
        )

    lettere = lettere.order_by("-data_emissione")
    return render(request, "users/lettera_richiamo_list.html", {"lettere": lettere})


# ============================================================================
# PROFILO E IMPOSTAZIONI
# ============================================================================


@login_required
def profilo_view(request):
    from django.urls import reverse
    user = request.user
    oggi = date.today()
    anno = oggi.year
    ferie_approvate = user.richieste_ferie.filter(
        stato="approvata", data_inizio__year=anno
    ).aggregate(tot=Sum("giorni_richiesti"))["tot"] or 0
    ferie_in_attesa = user.richieste_ferie.filter(
        stato="in_attesa", data_inizio__year=anno
    ).count()
    ore_permesso = user.richieste_permessi.filter(
        stato="approvata", data__year=anno
    ).aggregate(tot=Sum("ore_richieste"))["tot"] or 0

    ct_id = ContentType.objects.get_for_model(User).pk

    extra_actions = [
        {"label": "Tesserino", "url": reverse("users:tesserino"), "icon": "bi-person-badge"},
        {"label": "Nuovo Evento", "url": reverse("users:evento_personale_create"), "icon": "bi-calendar-plus"},
        {"label": "Richiedi Ferie", "url": reverse("users:richiesta_ferie_create"), "icon": "bi-sun"},
        {"label": "Richiedi Permesso", "url": reverse("users:richiesta_permesso_create"), "icon": "bi-clock"},
        {"label": "Le Mie Giornate", "url": reverse("users:giornata_list"), "icon": "bi-calendar3"},
        {"label": "Ferie & Permessi", "url": reverse("users:richieste_ferie_list"), "icon": "bi-calendar-check"},
    ]

    return render(request, "users/profilo.html", {
        "object": user,
        "content_type_id": ct_id,
        "object_id": user.pk,
        "page_title": "Il mio profilo",
        "edit_url": reverse("users:profilo_update"),
        "extra_actions": extra_actions,
        "oggi": oggi,
        "ferie_approvate": ferie_approvate,
        "ferie_in_attesa": ferie_in_attesa,
        "ore_permesso": ore_permesso,
    })


@login_required
@require_http_methods(["GET", "POST"])
def profilo_update_view(request):
    if request.method == "POST":
        form = UserProfiloForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profilo aggiornato con successo!")
            return redirect("users:profilo")
        else:
            messages.error(request, "Correggi gli errori nel form.")
    else:
        form = UserProfiloForm(instance=request.user)
    return render(request, "users/user_profilo_form.html", {"form": form})


@login_required
def impostazioni_view(request):
    return render(request, "users/impostazioni.html")


@login_required
def tesserino_view(request, pk=None):
    if pk and request.user.is_staff:
        tesserino_user = get_object_or_404(User, pk=pk)
    else:
        tesserino_user = request.user
    return render(request, "users/tesserino.html", {
        "tesserino_user": tesserino_user,
        "today": date.today(),
    })


@login_required
def tesserino_pdf_view(request):
    from core.pdf_generator import generate_tesserino_pdf
    from django.conf import settings
    import os

    logo_path = getattr(settings, "LOGO_PATH", None)
    if not logo_path:
        candidates = []
        if settings.STATICFILES_DIRS:
            candidates.append(os.path.join(settings.STATICFILES_DIRS[0], "img", "logo.png"))
        if getattr(settings, "STATIC_ROOT", None):
            candidates.append(os.path.join(settings.STATIC_ROOT, "img", "logo.png"))
        for p in candidates:
            if os.path.exists(p):
                logo_path = p
                break

    return generate_tesserino_pdf(request.user, logo_path=logo_path)


@login_required
def change_password_view(request):
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash

    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password aggiornata con successo!")
            return redirect("users:profilo")
        else:
            messages.error(request, "Correggi gli errori nel form.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "users/change_password.html", {"form": form})


# ============================================================================
# GESTIONE PERMESSI UTENTE
# ============================================================================


@login_required
@permission_required("users.change_user", raise_exception=True)
@require_http_methods(["GET", "POST"])
def user_permissions_manage_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        form = UserPermissionsForm(request.POST, user_obj=user_obj)
        if form.is_valid():
            try:
                form.save()
                messages.success(
                    request,
                    f"Permessi per {user_obj.get_full_name() or user_obj.username} aggiornati!",
                )
                return redirect("users:user_detail", pk=pk)
            except Exception as e:
                messages.error(request, f"Errore nel salvataggio permessi: {str(e)}")
        else:
            messages.error(request, "Errore nella validazione form.")
    else:
        form = UserPermissionsForm(user_obj=user_obj)

    fields_by_category = form.get_fields_by_category()

    available_templates = []
    if request.user.has_perm("users.gestione_completa_users"):
        from core.models_permissions import PermissionTemplate
        available_templates = PermissionTemplate.objects.filter(attivo=True).order_by("nome")

    context = {
        "form": form,
        "user_obj": user_obj,
        "profile_user": user_obj,
        "fields_by_category": fields_by_category,
        "available_templates": available_templates,
        "title": f"Gestione Permessi - {user_obj.get_full_name() or user_obj.username}",
    }

    return render(request, "users/user_permissions_form.html", context)


@login_required
@permission_required("users.gestione_completa_users", raise_exception=True)
@require_http_methods(["POST"])
def user_permissions_apply_template_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    template_id = request.POST.get("template_id")
    sovrascrivi = request.POST.get("sovrascrivi") == "1"

    if not template_id:
        messages.error(request, "Nessun template selezionato.")
        return redirect("users:user_permissions", pk=pk)

    try:
        from core.models_permissions import PermissionTemplate
        template = get_object_or_404(PermissionTemplate, pk=template_id, attivo=True)
        with transaction.atomic():
            if sovrascrivi:
                user_obj.user_permissions.clear()
            stats = template.applica_a_utente(user_obj)
            user_obj.template_permessi_applicato = template
            user_obj.save(update_fields=["template_permessi_applicato"])
            total_added = stats["permessi_crud_aggiunti"] + stats["permessi_base_aggiunti"]
            messages.success(
                request,
                f"Template '{template.nome}' applicato! Aggiunti {total_added} permessi.",
            )
            for errore in stats["errori"]:
                messages.warning(request, f"Attenzione: {errore}")
        return redirect("users:user_permissions", pk=pk)
    except Exception as e:
        messages.error(request, f"Errore: {str(e)}")
        return redirect("users:user_permissions", pk=pk)


# ============================================================================
# EXPORT GIORNATE
# ============================================================================


def _build_giornate_queryset(request):
    """Restituisce la queryset filtrata con timbrature prefetchate."""
    if request.user.is_staff:
        qs = GiornataLavorativa.objects.all().select_related("user").order_by("-data")
        user_filter = request.GET.get("user")
        if user_filter:
            qs = qs.filter(user_id=user_filter)
    else:
        qs = request.user.giornate.all().select_related("user").order_by("-data")

    mese = request.GET.get("mese")
    if mese:
        try:
            anno, mese_num = mese.split("-")
            qs = qs.filter(data__year=anno, data__month=mese_num)
        except ValueError:
            pass

    stato = request.GET.get("stato")
    if stato == "conclusa":
        qs = qs.filter(conclusa=True)
    elif stato == "in_corso":
        qs = qs.filter(conclusa=False)

    return qs


def _timbrature_map(giornate):
    """Prefetch timbrature e ritorna un dict {(user_id, data, turno, tipo): ora}."""
    from django.db.models import Q

    user_ids = list({g.user_id for g in giornate})
    date_list = list({g.data for g in giornate})
    timb = Timbratura.objects.filter(
        user_id__in=user_ids, data__in=date_list
    ).values("user_id", "data", "turno", "tipo", "ora")
    return {(t["user_id"], t["data"], t["turno"], t["tipo"]): t["ora"] for t in timb}


def _timb_str(tmap, user_id, data, turno, tipo):
    ora = tmap.get((user_id, data, turno, tipo))
    return ora.strftime("%H:%M") if ora else "-"


def _row_giornata(g, tmap, is_staff):
    row = {}
    if is_staff:
        row["Dipendente"] = g.user.get_full_name() or g.user.username
    row["Data"] = g.data
    uid = g.user_id
    d = g.data
    row["Entr. Mattina"] = _timb_str(tmap, uid, d, "mattina", "ingresso")
    row["Usc. Mattina"] = _timb_str(tmap, uid, d, "mattina", "uscita")
    row["Entr. Pomerigg."] = _timb_str(tmap, uid, d, "pomeriggio", "ingresso")
    row["Usc. Pomerigg."] = _timb_str(tmap, uid, d, "pomeriggio", "uscita")
    row["Entr. Notte"] = _timb_str(tmap, uid, d, "notte", "ingresso")
    row["Usc. Notte"] = _timb_str(tmap, uid, d, "notte", "uscita")
    row["Ore Mat."] = float(g.ore_mattina)
    row["Ore Pom."] = float(g.ore_pomeriggio)
    row["Ore Notte"] = float(g.ore_notte)
    row["Ore Totali"] = float(g.ore_totali)
    row["Straord."] = float(g.ore_straordinarie)
    row["Stato"] = "Chiusa" if g.conclusa else "Aperta"
    if g.note:
        row["Note"] = g.note
    return row


@login_required
def giornate_export_excel(request):
    from core.excel_generator import generate_excel_response

    giornate = list(_build_giornate_queryset(request))
    tmap = _timbrature_map(giornate)
    is_staff = request.user.is_staff

    data = [_row_giornata(g, tmap, is_staff) for g in giornate]

    base_headers = []
    if is_staff:
        base_headers.append("Dipendente")
    base_headers += [
        "Data",
        "Entr. Mattina", "Usc. Mattina",
        "Entr. Pomerigg.", "Usc. Pomerigg.",
        "Entr. Notte", "Usc. Notte",
        "Ore Mat.", "Ore Pom.", "Ore Notte",
        "Ore Totali", "Straord.", "Stato",
    ]
    if any(r.get("Note") for r in data):
        base_headers.append("Note")

    filename = f"giornate_{timezone.now().strftime('%Y%m%d')}"
    return generate_excel_response(data, filename, sheet_name="Giornate Lavorative", headers=base_headers)


@login_required
def giornate_export_pdf(request):
    from core.pdf_generator import generate_pdf_response

    giornate = list(_build_giornate_queryset(request))
    tmap = _timbrature_map(giornate)
    is_staff = request.user.is_staff

    data = [_row_giornata(g, tmap, is_staff) for g in giornate]

    base_headers = []
    if is_staff:
        base_headers.append("Dipendente")
    base_headers += [
        "Data",
        "Entr. Mattina", "Usc. Mattina",
        "Entr. Pomerigg.", "Usc. Pomerigg.",
        "Entr. Notte", "Usc. Notte",
        "Ore Mat.", "Ore Pom.", "Ore Notte",
        "Ore Totali", "Straord.", "Stato",
    ]
    if any(r.get("Note") for r in data):
        base_headers.append("Note")

    if is_staff:
        title = "Giornate Lavorative - Tutti i dipendenti"
    else:
        title = f"Giornate Lavorative - {request.user.get_full_name() or request.user.username}"

    filename = f"giornate_{timezone.now().strftime('%Y%m%d')}"
    return generate_pdf_response(data, filename, title=title, headers=base_headers)
