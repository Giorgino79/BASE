from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()
EMAIL = "danigioloso@gmail.com"


class Command(BaseCommand):
    help = "Carica dati di test: aziende, privati, tecnici, assistenti, automezzo, stabilimento, prodotti"

    def handle(self, *args, **options):
        self._tecnici = self._crea_tecnici()
        self._assistenti = self._crea_assistenti()
        self._crea_aziende()
        self._crea_privati()
        self._crea_automezzo()
        self._crea_stabilimento()
        self._crea_prodotti()
        self.stdout.write(self.style.SUCCESS("✓ Dati di test caricati correttamente."))

    # ------------------------------------------------------------------
    def _crea_tecnici(self):
        dati = [
            {"username": "tecnico1", "first_name": "Marco",  "last_name": "Bianchi",  "codice_dipendente": "101"},
            {"username": "tecnico2", "first_name": "Luca",   "last_name": "Ferretti", "codice_dipendente": "102"},
        ]
        utenti = []
        for d in dati:
            u, created = User.objects.get_or_create(
                username=d["username"],
                defaults=dict(
                    first_name=d["first_name"],
                    last_name=d["last_name"],
                    email=EMAIL,
                    codice_dipendente=d["codice_dipendente"],
                    qualifica="Tecnico",
                    stato="attivo",
                    is_staff=True,
                ),
            )
            if created:
                u.set_password("password123")
                u.save()
                self.stdout.write(f"  + Tecnico: {u.get_full_name()}")
            utenti.append(u)
        return utenti

    def _crea_assistenti(self):
        dati = [
            {"username": "assistente1", "first_name": "Sara",   "last_name": "Conti",    "codice_dipendente": "201"},
            {"username": "assistente2", "first_name": "Giulia", "last_name": "Martini",  "codice_dipendente": "202"},
        ]
        utenti = []
        for d in dati:
            u, created = User.objects.get_or_create(
                username=d["username"],
                defaults=dict(
                    first_name=d["first_name"],
                    last_name=d["last_name"],
                    email=EMAIL,
                    codice_dipendente=d["codice_dipendente"],
                    qualifica="Assistente",
                    stato="attivo",
                ),
            )
            if created:
                u.set_password("password123")
                u.save()
                self.stdout.write(f"  + Assistente: {u.get_full_name()}")
            utenti.append(u)
        return utenti

    # ------------------------------------------------------------------
    def _crea_aziende(self):
        from anagrafica_r2.models import Azienda
        clienti = [
            ("Condominio Il Cedro",        "Via Roma 12",          "Roma",       "Centro",   "00100", "12345670012"),
            ("Condominio Le Querce",        "Via Nazionale 45",     "Milano",     "Nord",     "20100", "23456781023"),
            ("Palazzo Moretti Srl",         "Corso Vittorio 8",     "Torino",     "Centro",   "10100", "34567892034"),
            ("Immobiliare Rossi Spa",       "Via Garibaldi 100",    "Napoli",     "Sud",      "80100", "45678903045"),
            ("Condominio Aurora",           "Via Mazzini 22",       "Bologna",    "Centro",   "40100", "56789014056"),
            ("Residenza La Pineta",         "Viale Europa 5",       "Firenze",    "Centro",   "50100", "67890125067"),
            ("Condominio Primavera",        "Via Dante 33",         "Venezia",    "Nord-Est", "30100", "78901236078"),
            ("Palazzo San Giorgio Srl",     "Via Verdi 77",         "Genova",     "Nord-Ovest","16100","89012347089"),
            ("Immobiliare Blu Srl",         "Via Leopardi 14",      "Bari",       "Sud",      "70100", "90123458090"),
            ("Condominio Monte Verde",      "Via Pascoli 3",        "Catania",    "Sud",      "95100", "01234569001"),
        ]
        for rs, ind, cit, zona, cap, piva in clienti:
            obj, created = Azienda.objects.get_or_create(
                ragione_sociale=rs,
                defaults=dict(
                    indirizzo=ind,
                    citta=cit,
                    zona=zona,
                    cap=cap,
                    partita_iva=piva,
                    pec=EMAIL,
                    telefono="0612345678",
                    email_operativo=EMAIL,
                    email_direzione=EMAIL,
                    email_amministrazione=EMAIL,
                    tipo_pagamento="30_gg",
                    attivo=True,
                ),
            )
            if created:
                self.stdout.write(f"  + Azienda: {rs}")

    # ------------------------------------------------------------------
    def _crea_privati(self):
        from anagrafica_r2.models import Privato
        dati = [
            ("Mario",     "Rossi",      "Via Salaria 10",       "Roma",     "Centro"),
            ("Francesca", "Bianchi",    "Via Po 22",            "Torino",   "Nord"),
            ("Antonio",   "Verde",      "Via Toledo 5",         "Napoli",   "Centro"),
            ("Elena",     "Marino",     "Corso Como 18",        "Milano",   "Centro"),
            ("Roberto",   "Esposito",   "Via Appia Nuova 88",   "Roma",     "Sud"),
        ]
        for nome, cognome, ind, cit, zona in dati:
            obj, created = Privato.objects.get_or_create(
                nome=nome, cognome=cognome,
                defaults=dict(
                    telefono="3331234567",
                    indirizzo=ind,
                    citta=cit,
                    zona=zona,
                    cap="00100",
                    email=EMAIL,
                    attivo=True,
                ),
            )
            if created:
                self.stdout.write(f"  + Privato: {cognome} {nome}")

    # ------------------------------------------------------------------
    def _crea_automezzo(self):
        from cespiti.models import Automezzo
        obj, created = Automezzo.objects.get_or_create(
            targa="AA123BB",
            defaults=dict(
                numero_mezzo=1,
                marca="Fiat",
                modello="Ducato",
                anno_immatricolazione=2020,
                chilometri_attuali=45000,
                attivo=True,
                disponibile=True,
                assegnato_a=self._tecnici[0] if self._tecnici else None,
            ),
        )
        if created:
            self.stdout.write(f"  + Automezzo: {obj}")

    # ------------------------------------------------------------------
    def _crea_stabilimento(self):
        from cespiti.models import Stabilimento
        superuser = User.objects.filter(is_superuser=True).first()
        creato_da = superuser or (self._tecnici[0] if self._tecnici else User.objects.first())
        obj, created = Stabilimento.objects.get_or_create(
            codice_stabilimento="SEDE01",
            defaults=dict(
                nome="Sede Operativa Roma",
                indirizzo="Via della Lavorazione 1",
                cap="00100",
                citta="Roma",
                provincia="RM",
                telefono="0612345678",
                email_filiale=EMAIL,
                responsabile_operativo=self._tecnici[0] if self._tecnici else None,
                creato_da=creato_da,
                superficie_mq=500,
                attivo=True,
            ),
        )
        if created:
            self.stdout.write(f"  + Stabilimento: {obj}")

    # ------------------------------------------------------------------
    def _crea_prodotti(self):
        from magazzino.models import Categoria, Prodotto
        cat, _ = Categoria.objects.get_or_create(nome="Prodotti Generici")

        prodotti = [
            ("Esca rodenticida Block",      "pz",   "ROD-001"),
            ("Gel anti-blatta",             "conf", "GEL-001"),
            ("Insetticida concentrato",     "lt",   "INS-001"),
            ("Rodenticida liquido",         "lt",   "ROD-002"),
            ("Trappola a colla topi",       "pz",   "TRA-001"),
            ("Schiuma insetticida 500ml",   "ml",   "SCH-001"),
            ("Polvere acaricida",           "gr",   "POL-001"),
            ("Granulato lumachicida",       "kg",   "GRA-001"),
            ("Repellente ultrasuoni",       "pz",   "REP-001"),
            ("Disinfettante superfici 5lt", "lt",   "DIS-001"),
        ]
        for nome, um, cod in prodotti:
            obj, created = Prodotto.objects.get_or_create(
                codice_interno=cod,
                defaults=dict(
                    categoria=cat,
                    nome_prodotto=nome,
                    unita_misura=um,
                    attivo=True,
                    scorta_minima=5,
                ),
            )
            if created:
                self.stdout.write(f"  + Prodotto: {nome} ({um})")
