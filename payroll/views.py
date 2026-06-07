"""
Views per il modulo Payroll
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model
from datetime import date
from decimal import Decimal

try:
    from users.models import GiornataLavorativa
    _GIORNATE_DISPONIBILI = True
except ImportError:
    _GIORNATE_DISPONIBILI = False

from .models import (
    DatiContrattualiPayroll,
    BustaPaga,
    CCNL,
    LivelloInquadramento,
    FeriePermessiPayroll,
    ManualePayroll,
)
from .services import PayrollCalculator

User = get_user_model()


@login_required
@permission_required("payroll.view_bustapaga", raise_exception=True)
def dipendenti_payroll_list(request):
    """Lista dipendenti per accesso rapido alle buste paga."""
    dipendenti = (
        User.objects.filter(is_active=True)
        .prefetch_related("buste_paga")
        .order_by("last_name", "first_name")
    )
    anno_corrente = date.today().year

    rows = []
    for u in dipendenti:
        ultima_busta = (
            u.buste_paga.filter(anno=anno_corrente).order_by("-mese").first()
        )
        try:
            ha_dati_payroll = bool(u.dati_payroll)
        except DatiContrattualiPayroll.DoesNotExist:
            ha_dati_payroll = False
        rows.append({"utente": u, "ultima_busta": ultima_busta, "ha_dati_payroll": ha_dati_payroll})

    return render(request, "payroll/dipendenti_payroll_list.html", {
        "rows": rows,
        "anno": anno_corrente,
    })


@login_required
@permission_required("payroll.view_daticontrattualiPayroll", raise_exception=True)
def dati_payroll_detail(request, user_pk):
    """Visualizza i dati payroll di un dipendente"""
    user_obj = get_object_or_404(User, pk=user_pk)

    try:
        dati_payroll = user_obj.dati_payroll
    except DatiContrattualiPayroll.DoesNotExist:
        dati_payroll = None

    context = {
        "user_obj": user_obj,
        "dati_payroll": dati_payroll,
    }

    return render(request, "payroll/dati_payroll_detail.html", context)


@login_required
@permission_required("payroll.change_daticontrattualiPayroll", raise_exception=True)
def dati_payroll_form(request, user_pk):
    """Form per configurare i dati payroll di un dipendente"""
    user_obj = get_object_or_404(User, pk=user_pk)

    try:
        dati_payroll = user_obj.dati_payroll
    except DatiContrattualiPayroll.DoesNotExist:
        dati_payroll = None

    ccnl_list = CCNL.objects.all()
    livelli_list = LivelloInquadramento.objects.all()

    if request.method == "POST":
        ccnl_id = request.POST.get("ccnl")
        livello_id = request.POST.get("livello")
        tipo_contratto = request.POST.get("tipo_contratto")
        ore_settimanali = request.POST.get("ore_settimanali")
        percentuale_part_time = request.POST.get("percentuale_part_time")
        superminimo = request.POST.get("superminimo")
        aliquota_addizionale_regionale = request.POST.get("aliquota_addizionale_regionale")
        aliquota_addizionale_comunale = request.POST.get("aliquota_addizionale_comunale")
        detrazione_lavoro_dipendente = request.POST.get("detrazione_lavoro_dipendente")
        numero_figli_a_carico = request.POST.get("numero_figli_a_carico")
        coniuge_a_carico = request.POST.get("coniuge_a_carico")
        altri_familiari_a_carico = request.POST.get("altri_familiari_a_carico")
        iban = request.POST.get("iban")
        data_fine_contratto = request.POST.get("data_fine_contratto")
        data_cessazione = request.POST.get("data_cessazione")

        try:
            with transaction.atomic():
                fields = dict(
                    ccnl=CCNL.objects.get(pk=ccnl_id) if ccnl_id else None,
                    livello=LivelloInquadramento.objects.get(pk=livello_id) if livello_id else None,
                    tipo_contratto=tipo_contratto,
                    ore_settimanali=Decimal(ore_settimanali) if ore_settimanali else Decimal("40.00"),
                    percentuale_part_time=Decimal(percentuale_part_time) if percentuale_part_time else Decimal("100.00"),
                    superminimo=Decimal(superminimo) if superminimo else Decimal("0.00"),
                    aliquota_addizionale_regionale=Decimal(aliquota_addizionale_regionale) if aliquota_addizionale_regionale else Decimal("0.00"),
                    aliquota_addizionale_comunale=Decimal(aliquota_addizionale_comunale) if aliquota_addizionale_comunale else Decimal("0.00"),
                    detrazione_lavoro_dipendente=(detrazione_lavoro_dipendente == "on"),
                    numero_figli_a_carico=int(numero_figli_a_carico) if numero_figli_a_carico else 0,
                    coniuge_a_carico=(coniuge_a_carico == "on"),
                    altri_familiari_a_carico=int(altri_familiari_a_carico) if altri_familiari_a_carico else 0,
                    iban=iban or "",
                    data_fine_contratto=data_fine_contratto or None,
                    data_cessazione=data_cessazione or None,
                )

                if dati_payroll:
                    for attr, value in fields.items():
                        setattr(dati_payroll, attr, value)
                    dati_payroll.save()
                    messages.success(request, f"Dati payroll aggiornati per {user_obj.get_full_name()}")
                else:
                    DatiContrattualiPayroll.objects.create(user=user_obj, **fields)
                    messages.success(request, f"Dati payroll creati per {user_obj.get_full_name()}")

            return redirect("users:user_detail", pk=user_obj.pk)

        except Exception as e:
            messages.error(request, f"Errore nel salvataggio: {e}")

    context = {
        "user_obj": user_obj,
        "dati_payroll": dati_payroll,
        "ccnl_list": ccnl_list,
        "livelli_list": livelli_list,
    }

    return render(request, "payroll/dati_payroll_form.html", context)


@login_required
@permission_required("payroll.view_bustapaga", raise_exception=True)
def busta_paga_list(request, user_pk):
    """Lista buste paga di un dipendente"""
    user_obj = get_object_or_404(User, pk=user_pk)
    buste = BustaPaga.objects.filter(user=user_obj).order_by("-anno", "-mese")
    buste_confermate_count = buste.filter(confermata=True).count()

    context = {
        "user_obj": user_obj,
        "buste": buste,
        "buste_confermate_count": buste_confermate_count,
    }

    return render(request, "payroll/busta_paga_list.html", context)


@login_required
@permission_required("payroll.view_bustapaga", raise_exception=True)
def busta_paga_detail(request, pk):
    """Dettaglio busta paga"""
    busta = get_object_or_404(BustaPaga, pk=pk)

    context = {
        "busta": busta,
        "competenze": busta.voci.filter(tipo="COMPETENZA"),
        "trattenute": busta.voci.filter(tipo="TRATTENUTA"),
        "detrazioni": busta.voci.filter(tipo="DEDUZIONE"),
    }

    return render(request, "payroll/busta_paga_detail.html", context)


@login_required
@permission_required("payroll.add_bustapaga", raise_exception=True)
def busta_paga_elabora(request, user_pk):
    """Form per elaborare una nuova busta paga"""
    user_obj = get_object_or_404(User, pk=user_pk)

    try:
        user_obj.dati_payroll
    except DatiContrattualiPayroll.DoesNotExist:
        messages.warning(
            request,
            f"Configura prima i dati payroll per {user_obj.get_full_name()}.",
        )
        return redirect("payroll:dati_payroll_form", user_pk=user_obj.pk)

    oggi = date.today()
    mese_default = oggi.month
    anno_default = oggi.year

    if request.method == "POST":
        mese = int(request.POST.get("mese", mese_default))
        anno = int(request.POST.get("anno", anno_default))

        def get_ore(key):
            val = request.POST.get(key)
            return Decimal(val) if val else Decimal("0")

        try:
            calculator = PayrollCalculator(user_obj, mese, anno)
            busta = calculator.calcola_busta_paga(
                ore_ordinarie=get_ore("ore_ordinarie"),
                ore_straordinari={
                    "feriale": get_ore("ore_straordinario_feriale"),
                    "festivo": get_ore("ore_straordinario_festivo"),
                    "notturno": get_ore("ore_straordinario_notturno"),
                },
                assenze={
                    "ferie": get_ore("ore_ferie"),
                    "rol": get_ore("ore_rol"),
                    "permessi": get_ore("ore_permessi"),
                    "malattia": get_ore("ore_malattia"),
                },
            )
            calculator.matura_ferie_permessi_mensili()

            messages.success(
                request,
                f"Busta paga elaborata con successo! Netto: € {busta.netto_busta:,.2f}",
            )
            return redirect("payroll:busta_paga_detail", pk=busta.pk)

        except Exception as e:
            messages.error(request, f"Errore nell'elaborazione: {e}")

    # Pre-popola ore da GiornataLavorativa del mese
    ore_auto = {}
    if _GIORNATE_DISPONIBILI:
        mese_q = int(request.GET.get("mese", mese_default))
        anno_q = int(request.GET.get("anno", anno_default))
        giornate = GiornataLavorativa.objects.filter(
            user=user_obj,
            data__year=anno_q,
            data__month=mese_q,
            conclusa=True,
        )
        if giornate.exists():
            tot = sum(g.ore_totali for g in giornate)
            straord = sum(g.ore_straordinarie for g in giornate)
            ore_auto = {
                "ore_ordinarie": round(float(tot - straord), 2),
                "ore_straordinario_feriale": round(float(straord), 2),
                "mese_auto": mese_q,
                "anno_auto": anno_q,
            }

    context = {
        "user_obj": user_obj,
        "mese_default": ore_auto.get("mese_auto", mese_default),
        "anno_default": ore_auto.get("anno_auto", anno_default),
        "ore_auto": ore_auto,
    }

    return render(request, "payroll/busta_paga_elabora.html", context)


@login_required
@permission_required("payroll.view_feriepermessipayroll", raise_exception=True)
def ferie_permessi_list(request, user_pk):
    """Lista ferie e permessi payroll di un dipendente"""
    user_obj = get_object_or_404(User, pk=user_pk)
    anno_corrente = date.today().year

    ferie_permessi = FeriePermessiPayroll.objects.filter(
        user=user_obj, anno=anno_corrente
    ).order_by("tipo")

    context = {
        "user_obj": user_obj,
        "ferie_permessi": ferie_permessi,
        "anno": anno_corrente,
    }

    return render(request, "payroll/ferie_permessi_list.html", context)


@login_required
def manuale_payroll(request):
    """Visualizza il manuale di compilazione form Payroll"""
    manuale = ManualePayroll.get_manuale_attivo()

    context = {
        "manuale": manuale,
        "puo_modificare": request.user.is_staff or request.user.is_superuser,
    }

    return render(request, "payroll/manuale_payroll.html", context)


@login_required
def manuale_payroll_edit(request):
    """Modifica il manuale di compilazione (solo admin)"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Non hai i permessi per modificare il manuale.")
        return redirect("payroll:manuale_payroll")

    manuale = ManualePayroll.get_manuale_attivo()

    if request.method == "POST":
        try:
            manuale.titolo = request.POST.get("titolo")
            manuale.contenuto = request.POST.get("contenuto")
            manuale.versione = request.POST.get("versione")
            manuale.modificato_da = request.user
            manuale.save()
            messages.success(request, "Manuale aggiornato con successo!")
            return redirect("payroll:manuale_payroll")
        except Exception as e:
            messages.error(request, f"Errore nel salvataggio: {e}")

    return render(request, "payroll/manuale_payroll_edit.html", {"manuale": manuale})
