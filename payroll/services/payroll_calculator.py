"""
Servizio per il calcolo delle buste paga
Implementa tutta la logica retributiva conforme al diritto del lavoro italiano
"""

from decimal import Decimal
from datetime import date
from django.db import transaction
from ..models import (
    BustaPaga,
    VoceBustaPaga,
    FeriePermessiPayroll,
    DatiContrattualiPayroll,
)


class PayrollCalculator:
    """Calcola la busta paga secondo il CCNL applicabile"""

    # Aliquote IRPEF 2025 (aggiornare annualmente!)
    # Scaglioni: (limite_superiore, aliquota_percentuale)
    SCAGLIONI_IRPEF = [
        (15000, Decimal("23.00")),            # Fino a 15.000€: 23%
        (28000, Decimal("25.00")),            # Da 15.001€ a 28.000€: 25%
        (50000, Decimal("35.00")),            # Da 28.001€ a 50.000€: 35%
        (float("inf"), Decimal("43.00")),     # Oltre 50.000€: 43%
    ]

    # Contributi INPS a carico dipendente
    CONTRIBUTO_INPS_DIPENDENTE = Decimal("9.19")

    def __init__(self, user, mese, anno):
        self.user = user
        self.mese = mese
        self.anno = anno

        try:
            self.dati_payroll = user.dati_payroll
        except DatiContrattualiPayroll.DoesNotExist:
            raise ValueError(
                f"Dati payroll non configurati per {user.get_full_name()}"
            )

        self.ccnl = self.dati_payroll.ccnl
        self.livello = self.dati_payroll.livello

        if not self.ccnl or not self.livello:
            raise ValueError(
                f"CCNL e Livello non configurati per {user.get_full_name()}"
            )

    def _applica_scaglioni_irpef(self, reddito_annuo):
        """
        Applica gli scaglioni IRPEF progressivi a un reddito annuo.

        Per reddito di €30.000:
        - Primi €15.000 al 23% = €3.450
        - Da €15.001 a €28.000 (€13.000) al 25% = €3.250
        - Da €28.001 a €30.000 (€2.000) al 35% = €700
        - TOTALE IRPEF = €7.400
        """
        irpef_totale = Decimal("0")
        residuo = reddito_annuo
        scaglione_precedente = Decimal("0")

        for limite_superiore, aliquota in self.SCAGLIONI_IRPEF:
            if residuo <= 0:
                break

            if limite_superiore == float("inf"):
                limite_dec = residuo + scaglione_precedente
            else:
                limite_dec = Decimal(str(limite_superiore))

            scaglione_corrente = min(residuo, limite_dec - scaglione_precedente)
            irpef_scaglione = scaglione_corrente * (aliquota / Decimal("100"))
            irpef_totale += irpef_scaglione

            residuo -= scaglione_corrente
            scaglione_precedente = limite_dec

        return irpef_totale.quantize(Decimal("0.01"))

    @transaction.atomic
    def calcola_busta_paga(self, ore_ordinarie, ore_straordinari=None, assenze=None):
        """
        Calcola la busta paga completa.

        Args:
            ore_ordinarie: ore lavorate normali
            ore_straordinari: dict con chiavi 'feriale', 'festivo', 'notturno'
            assenze: dict con chiavi 'ferie', 'rol', 'permessi', 'malattia'

        Returns:
            BustaPaga: istanza della busta paga creata
        """
        ore_straordinari = ore_straordinari or {}
        assenze = assenze or {}

        try:
            busta = BustaPaga.objects.get(
                user=self.user, mese=self.mese, anno=self.anno
            )
            busta.voci.all().delete()
        except BustaPaga.DoesNotExist:
            busta = BustaPaga.objects.create(
                user=self.user,
                mese=self.mese,
                anno=self.anno,
            )

        busta.ore_ordinarie = ore_ordinarie
        busta.ore_straordinario_feriale = ore_straordinari.get("feriale", 0)
        busta.ore_straordinario_festivo = ore_straordinari.get("festivo", 0)
        busta.ore_straordinario_notturno = ore_straordinari.get("notturno", 0)
        busta.ore_ferie = assenze.get("ferie", 0)
        busta.ore_rol = assenze.get("rol", 0)
        busta.ore_permessi = assenze.get("permessi", 0)
        busta.ore_malattia = assenze.get("malattia", 0)

        self._calcola_competenze(busta, ore_ordinarie, ore_straordinari)
        self._calcola_mensilita_aggiuntive(busta)
        self._calcola_imponibili(busta)
        self._calcola_contributi_inps(busta)
        self._calcola_irpef(busta)
        self._calcola_detrazioni(busta)

        busta.netto_busta = (
            busta.imponibile_fiscale
            - busta.ritenute_previdenziali
            - busta.ritenute_irpef
            - busta.addizionale_regionale
            - busta.addizionale_comunale
            + busta.detrazioni_fiscali
            - busta.altre_trattenute
        )

        self._calcola_tfr(busta)
        busta.save()
        self._aggiorna_ferie_permessi(assenze)

        return busta

    def _calcola_competenze(self, busta, ore_ordinarie, ore_straordinari):
        """Calcola tutte le competenze (retribuzione lorda)"""
        paga_oraria = self.dati_payroll.calcola_paga_oraria()

        importo_base = paga_oraria * Decimal(str(ore_ordinarie))
        VoceBustaPaga.objects.create(
            busta_paga=busta,
            tipo="COMPETENZA",
            descrizione="Retribuzione ordinaria",
            quantita=Decimal(str(ore_ordinarie)),
            importo_unitario=paga_oraria,
            importo_totale=importo_base,
        )

        for tipo, ore in ore_straordinari.items():
            if ore > 0:
                if tipo == "feriale":
                    percentuale = self.ccnl.percentuale_straordinario_feriale
                    desc = "Straordinario feriale"
                elif tipo == "festivo":
                    percentuale = self.ccnl.percentuale_straordinario_festivo
                    desc = "Straordinario festivo"
                else:
                    percentuale = self.ccnl.percentuale_straordinario_notturno
                    desc = "Straordinario notturno"

                maggiorazione = paga_oraria * (percentuale / Decimal("100"))
                paga_straord = paga_oraria + maggiorazione
                importo_straord = paga_straord * Decimal(str(ore))

                VoceBustaPaga.objects.create(
                    busta_paga=busta,
                    tipo="COMPETENZA",
                    descrizione=f"{desc} (+{percentuale}%)",
                    quantita=Decimal(str(ore)),
                    importo_unitario=paga_straord,
                    importo_totale=importo_straord,
                )

        for elemento in self.ccnl.elementi_retributivi.filter(attivo=True):
            importo = self._calcola_elemento_retributivo(elemento, importo_base)
            if importo > 0:
                VoceBustaPaga.objects.create(
                    busta_paga=busta,
                    tipo="COMPETENZA",
                    descrizione=elemento.nome,
                    importo_totale=importo,
                    imponibile_fiscale=(
                        elemento.natura in ["IMPONIBILE", "SOLO_FISCALE"]
                    ),
                    imponibile_contributivo=(
                        elemento.natura in ["IMPONIBILE", "SOLO_CONTRIBUTIVO"]
                    ),
                )

    def _calcola_elemento_retributivo(self, elemento, paga_base):
        """Calcola singolo elemento retributivo"""
        if elemento.tipo_calcolo == "FISSO":
            return elemento.valore
        elif elemento.tipo_calcolo in ["PERCENTUALE_PAGA_BASE", "PERCENTUALE_RETRIBUZIONE"]:
            return paga_base * (elemento.valore / Decimal("100"))
        return Decimal("0")

    def _calcola_mensilita_aggiuntive(self, busta):
        """
        Aggiunge tredicesima (dicembre) e quattordicesima (mese previsto da CCNL)
        come voci di competenza, proporzionali ai mesi lavorati nell'anno.
        """
        retrib_utile = self._retribuzione_utile_mensilita()
        if retrib_utile <= 0:
            return

        if self.ccnl.ha_tredicesima and self.mese == 12:
            mesi = self._mesi_maturati(1, 12)
            importo = (retrib_utile * Decimal(str(mesi)) / Decimal("12")).quantize(Decimal("0.01"))
            if importo > 0:
                VoceBustaPaga.objects.create(
                    busta_paga=busta,
                    tipo="COMPETENZA",
                    descrizione=f"13ª mensilità ({mesi}/12 mesi)",
                    importo_totale=importo,
                    imponibile_fiscale=True,
                    imponibile_contributivo=True,
                )

        if self.ccnl.ha_quattordicesima and self.ccnl.maturazione_quattordicesima:
            mese_pag = {"GIUGNO": 6, "LUGLIO": 7, "DICEMBRE": 12}.get(
                self.ccnl.maturazione_quattordicesima
            )
            if mese_pag == self.mese:
                mese_inizio = 7 if mese_pag in (6, 7) else 1
                mesi = self._mesi_maturati(mese_inizio, mese_pag)
                importo = (retrib_utile * Decimal(str(mesi)) / Decimal("12")).quantize(Decimal("0.01"))
                if importo > 0:
                    VoceBustaPaga.objects.create(
                        busta_paga=busta,
                        tipo="COMPETENZA",
                        descrizione=f"14ª mensilità ({mesi}/12 mesi)",
                        importo_totale=importo,
                        imponibile_fiscale=True,
                        imponibile_contributivo=True,
                    )

    def _retribuzione_utile_mensilita(self):
        """Paga mensile base per mensilità aggiuntive (esclusi straordinari)."""
        paga = self.livello.paga_base_mensile + self.dati_payroll.superminimo
        n_scatti = Decimal(str(self.dati_payroll.calcola_scatti_anzianita()))
        paga += n_scatti * self.ccnl.importo_scatto
        for el in self.ccnl.elementi_retributivi.filter(attivo=True, incluso_tredicesima=True):
            paga += self._calcola_elemento_retributivo(el, paga)
        return paga.quantize(Decimal("0.01"))

    def _mesi_maturati(self, mese_inizio, mese_fine):
        """Mesi effettivamente lavorati nel range (mese_inizio→mese_fine) dell'anno."""
        data_ass = getattr(self.user, "data_assunzione", None)
        if not data_ass or data_ass.year < self.anno:
            primo_mese = mese_inizio
        elif data_ass.year == self.anno:
            primo_mese = max(mese_inizio, data_ass.month)
        else:
            return 0
        return max(0, mese_fine - primo_mese + 1)

    def _calcola_imponibili(self, busta):
        """Calcola imponibile fiscale e contributivo"""
        imponibile_fiscale = Decimal("0")
        imponibile_contributivo = Decimal("0")

        for voce in busta.voci.filter(tipo="COMPETENZA"):
            if voce.imponibile_fiscale:
                imponibile_fiscale += voce.importo_totale
            if voce.imponibile_contributivo:
                imponibile_contributivo += voce.importo_totale

        busta.imponibile_fiscale = imponibile_fiscale.quantize(Decimal("0.01"))
        busta.imponibile_contributivo = imponibile_contributivo.quantize(Decimal("0.01"))

    def _calcola_contributi_inps(self, busta):
        """Calcola contributi previdenziali a carico dipendente"""
        contributi = busta.imponibile_contributivo * (
            self.CONTRIBUTO_INPS_DIPENDENTE / Decimal("100")
        )
        busta.ritenute_previdenziali = contributi.quantize(Decimal("0.01"))

        VoceBustaPaga.objects.create(
            busta_paga=busta,
            tipo="TRATTENUTA",
            descrizione=f"Contributi INPS ({self.CONTRIBUTO_INPS_DIPENDENTE}%)",
            importo_totale=busta.ritenute_previdenziali,
            imponibile_fiscale=False,
            imponibile_contributivo=False,
        )

    def _calcola_irpef(self, busta):
        """
        Calcola IRPEF con metodo del CUMULO ANNUALE (progressivo).

        L'IRPEF va calcolata sul reddito CUMULATO da inizio anno (Art. 11 TUIR).
        Metodo: IRPEF mese = IRPEF(cumulo_tot) - IRPEF già trattenuta nei mesi prec.
        Scaglioni IRPEF 2025: ≤15k 23%, ≤28k 25%, ≤50k 35%, >50k 43%.
        """
        buste_precedenti = BustaPaga.objects.filter(
            user=self.user,
            anno=self.anno,
            mese__lt=self.mese,
            confermata=True,
        ).order_by("mese")

        reddito_cumulato = Decimal("0")
        irpef_gia_pagata = Decimal("0")

        for busta_prec in buste_precedenti:
            imponibile_prec = busta_prec.imponibile_fiscale - busta_prec.ritenute_previdenziali
            reddito_cumulato += imponibile_prec
            irpef_gia_pagata += busta_prec.ritenute_irpef

        imponibile_corrente = busta.imponibile_fiscale - busta.ritenute_previdenziali
        reddito_cumulato += imponibile_corrente

        irpef_cumulata = self._applica_scaglioni_irpef(reddito_cumulato)
        busta.ritenute_irpef = (irpef_cumulata - irpef_gia_pagata).quantize(Decimal("0.01"))

        if busta.ritenute_irpef < 0:
            busta.ritenute_irpef = Decimal("0")

        VoceBustaPaga.objects.create(
            busta_paga=busta,
            tipo="TRATTENUTA",
            descrizione="IRPEF",
            importo_totale=busta.ritenute_irpef,
            imponibile_fiscale=False,
            imponibile_contributivo=False,
        )

        # Addizionale Regionale
        busta.addizionale_regionale = (
            imponibile_corrente
            * (self.dati_payroll.aliquota_addizionale_regionale / Decimal("100"))
        ).quantize(Decimal("0.01"))

        if busta.addizionale_regionale > 0:
            VoceBustaPaga.objects.create(
                busta_paga=busta,
                tipo="TRATTENUTA",
                descrizione=f"Addizionale Regionale ({self.dati_payroll.aliquota_addizionale_regionale}%)",
                importo_totale=busta.addizionale_regionale,
                imponibile_fiscale=False,
                imponibile_contributivo=False,
            )

        # Addizionale Comunale
        busta.addizionale_comunale = (
            imponibile_corrente
            * (self.dati_payroll.aliquota_addizionale_comunale / Decimal("100"))
        ).quantize(Decimal("0.01"))

        if busta.addizionale_comunale > 0:
            VoceBustaPaga.objects.create(
                busta_paga=busta,
                tipo="TRATTENUTA",
                descrizione=f"Addizionale Comunale ({self.dati_payroll.aliquota_addizionale_comunale}%)",
                importo_totale=busta.addizionale_comunale,
                imponibile_fiscale=False,
                imponibile_contributivo=False,
            )

    def _calcola_detrazioni(self, busta):
        """
        Calcola detrazioni fiscali per lavoro dipendente.
        Formula semplificata (Art. 13 TUIR).
        """
        if not self.dati_payroll.detrazione_lavoro_dipendente:
            busta.detrazioni_fiscali = Decimal("0")
            return

        reddito_annuo = busta.imponibile_fiscale * Decimal("12")

        if reddito_annuo <= 15000:
            detrazione_annua = Decimal("1955")
        elif reddito_annuo <= 28000:
            detrazione_annua = Decimal("1910") + Decimal("1190") * (
                (Decimal("28000") - reddito_annuo) / Decimal("13000")
            )
        elif reddito_annuo <= 50000:
            detrazione_annua = Decimal("1910") * (
                (Decimal("50000") - reddito_annuo) / Decimal("22000")
            )
        else:
            detrazione_annua = Decimal("0")

        busta.detrazioni_fiscali = (detrazione_annua / Decimal("12")).quantize(
            Decimal("0.01")
        )

        if busta.detrazioni_fiscali > 0:
            VoceBustaPaga.objects.create(
                busta_paga=busta,
                tipo="DEDUZIONE",
                descrizione="Detrazioni lavoro dipendente",
                importo_totale=busta.detrazioni_fiscali,
                imponibile_fiscale=False,
                imponibile_contributivo=False,
            )

    def _calcola_tfr(self, busta):
        """
        Calcola TFR maturato nel mese.

        Formula: TFR = Retribuzione Utile TFR / 13.5 (Art. 2120 C.C.)
        Sono escluse le voci con imponibile_contributivo=False.
        """
        retribuzione_utile_tfr = Decimal("0")

        for voce in busta.voci.filter(tipo="COMPETENZA"):
            if voce.imponibile_contributivo:
                retribuzione_utile_tfr += voce.importo_totale

        busta.tfr_maturato = (retribuzione_utile_tfr / Decimal("13.5")).quantize(
            Decimal("0.01")
        )

    def _aggiorna_ferie_permessi(self, assenze):
        """Aggiorna i contatori di ferie e permessi utilizzati"""
        tipo_mapping = {
            "ferie": "FERIE",
            "rol": "ROL",
            "permessi": "PERMESSO_RETRIBUITO",
            "malattia": "MALATTIA",
        }

        for tipo_assenza, ore in assenze.items():
            if ore > 0 and tipo_assenza in tipo_mapping:
                fp, _ = FeriePermessiPayroll.objects.get_or_create(
                    user=self.user,
                    anno=self.anno,
                    tipo=tipo_mapping[tipo_assenza],
                )
                fp.ore_godute += Decimal(str(ore))
                fp.save()

    def matura_ferie_permessi_mensili(self):
        """Calcola la maturazione mensile di ferie e permessi"""
        ore_giornaliere = self.dati_payroll.ore_settimanali / Decimal("5")

        # Ferie
        ore_ferie_mensili = (
            Decimal(str(self.ccnl.giorni_ferie_annui))
            * ore_giornaliere
            / Decimal("12")
        )
        fp_ferie, _ = FeriePermessiPayroll.objects.get_or_create(
            user=self.user, anno=self.anno, tipo="FERIE"
        )
        fp_ferie.ore_maturate += ore_ferie_mensili
        fp_ferie.save()

        # ROL
        ore_rol_mensili = self.ccnl.ore_rol_annue / Decimal("12")
        fp_rol, _ = FeriePermessiPayroll.objects.get_or_create(
            user=self.user, anno=self.anno, tipo="ROL"
        )
        fp_rol.ore_maturate += ore_rol_mensili
        fp_rol.save()

        # Permessi Retribuiti
        ore_permessi_mensili = self.ccnl.ore_permessi_retribuiti_annui / Decimal("12")
        fp_permessi, _ = FeriePermessiPayroll.objects.get_or_create(
            user=self.user, anno=self.anno, tipo="PERMESSO_RETRIBUITO"
        )
        fp_permessi.ore_maturate += ore_permessi_mensili
        fp_permessi.save()

    def get_riepilogo_annuale(self):
        """Restituisce un riepilogo delle buste paga dell'anno corrente"""
        buste = BustaPaga.objects.filter(user=self.user, anno=self.anno).order_by("mese")

        return {
            "anno": self.anno,
            "dipendente": self.user.get_full_name(),
            "numero_buste": buste.count(),
            "totale_ore_ordinarie": sum(b.ore_ordinarie for b in buste),
            "totale_ore_straordinari": sum(
                b.ore_straordinario_feriale
                + b.ore_straordinario_festivo
                + b.ore_straordinario_notturno
                for b in buste
            ),
            "totale_imponibile_fiscale": sum(b.imponibile_fiscale for b in buste),
            "totale_imponibile_contributivo": sum(b.imponibile_contributivo for b in buste),
            "totale_ritenute_previdenziali": sum(b.ritenute_previdenziali for b in buste),
            "totale_ritenute_irpef": sum(b.ritenute_irpef for b in buste),
            "totale_netto": sum(b.netto_busta for b in buste),
            "totale_tfr": sum(b.tfr_maturato for b in buste),
        }
