"""
Management command: genera il dataset comuni italiani.

Con connessione internet scarica i ~8000 comuni da GitHub.
Senza connessione genera il seed con i 110 capoluoghi di provincia.

Uso:  python manage.py importa_comuni
      python manage.py importa_comuni --solo-seed
"""

import json
import urllib.request
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

SOURCE_URL = (
    "https://raw.githubusercontent.com/matteocontrini/comuni-json"
    "/master/comuni.json"
)
OUTPUT_PATH = Path(settings.BASE_DIR) / "static" / "js" / "comuni_italiani.json"

# Seed: tutti i capoluoghi di provincia italiani
# formato: [nome, cap, sigla_provincia, regione]
CAPOLUOGHI_SEED = [
    ["Agrigento","92100","AG","Sicilia"],
    ["Alessandria","15100","AL","Piemonte"],
    ["Ancona","60121","AN","Marche"],
    ["Aosta","11100","AO","Valle d'Aosta"],
    ["Arezzo","52100","AR","Toscana"],
    ["Ascoli Piceno","63100","AP","Marche"],
    ["Asti","14100","AT","Piemonte"],
    ["Avellino","83100","AV","Campania"],
    ["Bari","70121","BA","Puglia"],
    ["Barletta","76121","BT","Puglia"],
    ["Belluno","32100","BL","Veneto"],
    ["Benevento","82100","BN","Campania"],
    ["Bergamo","24121","BG","Lombardia"],
    ["Biella","13900","BI","Piemonte"],
    ["Bologna","40121","BO","Emilia-Romagna"],
    ["Bolzano","39100","BZ","Trentino-Alto Adige"],
    ["Brescia","25121","BS","Lombardia"],
    ["Brindisi","72100","BR","Puglia"],
    ["Cagliari","09121","CA","Sardegna"],
    ["Caltanissetta","93100","CL","Sicilia"],
    ["Campobasso","86100","CB","Molise"],
    ["Caserta","81100","CE","Campania"],
    ["Catania","95121","CT","Sicilia"],
    ["Catanzaro","88100","CZ","Calabria"],
    ["Chieti","66100","CH","Abruzzo"],
    ["Como","22100","CO","Lombardia"],
    ["Cosenza","87100","CS","Calabria"],
    ["Cremona","26100","CR","Lombardia"],
    ["Crotone","88900","KR","Calabria"],
    ["Cuneo","12100","CN","Piemonte"],
    ["Enna","94100","EN","Sicilia"],
    ["Fermo","63900","FM","Marche"],
    ["Ferrara","44121","FE","Emilia-Romagna"],
    ["Firenze","50121","FI","Toscana"],
    ["Foggia","71121","FG","Puglia"],
    ["Forlì","47121","FC","Emilia-Romagna"],
    ["Frosinone","03100","FR","Lazio"],
    ["Genova","16121","GE","Liguria"],
    ["Gorizia","34170","GO","Friuli-Venezia Giulia"],
    ["Grosseto","58100","GR","Toscana"],
    ["Imperia","18100","IM","Liguria"],
    ["Isernia","86170","IS","Molise"],
    ["L'Aquila","67100","AQ","Abruzzo"],
    ["La Spezia","19121","SP","Liguria"],
    ["Latina","04100","LT","Lazio"],
    ["Lecce","73100","LE","Puglia"],
    ["Lecco","23900","LC","Lombardia"],
    ["Livorno","57121","LI","Toscana"],
    ["Lodi","26900","LO","Lombardia"],
    ["Lucca","55100","LU","Toscana"],
    ["Macerata","62100","MC","Marche"],
    ["Mantova","46100","MN","Lombardia"],
    ["Massa","54100","MS","Toscana"],
    ["Matera","75100","MT","Basilicata"],
    ["Messina","98121","ME","Sicilia"],
    ["Milano","20121","MI","Lombardia"],
    ["Modena","41121","MO","Emilia-Romagna"],
    ["Monza","20900","MB","Lombardia"],
    ["Napoli","80121","NA","Campania"],
    ["Novara","28100","NO","Piemonte"],
    ["Nuoro","08100","NU","Sardegna"],
    ["Oristano","09170","OR","Sardegna"],
    ["Padova","35121","PD","Veneto"],
    ["Palermo","90121","PA","Sicilia"],
    ["Parma","43121","PR","Emilia-Romagna"],
    ["Pavia","27100","PV","Lombardia"],
    ["Perugia","06121","PG","Umbria"],
    ["Pesaro","61121","PU","Marche"],
    ["Pescara","65121","PE","Abruzzo"],
    ["Piacenza","29121","PC","Emilia-Romagna"],
    ["Pisa","56121","PI","Toscana"],
    ["Pistoia","51100","PT","Toscana"],
    ["Pordenone","33170","PN","Friuli-Venezia Giulia"],
    ["Potenza","85100","PZ","Basilicata"],
    ["Prato","59100","PO","Toscana"],
    ["Ragusa","97100","RG","Sicilia"],
    ["Ravenna","48121","RA","Emilia-Romagna"],
    ["Reggio Calabria","89121","RC","Calabria"],
    ["Reggio Emilia","42121","RE","Emilia-Romagna"],
    ["Rieti","02100","RI","Lazio"],
    ["Rimini","47921","RN","Emilia-Romagna"],
    ["Roma","00100","RM","Lazio"],
    ["Rovigo","45100","RO","Veneto"],
    ["Salerno","84121","SA","Campania"],
    ["Sassari","07100","SS","Sardegna"],
    ["Savona","17100","SV","Liguria"],
    ["Siena","53100","SI","Toscana"],
    ["Siracusa","96100","SR","Sicilia"],
    ["Sondrio","23100","SO","Lombardia"],
    ["Taranto","74121","TA","Puglia"],
    ["Teramo","64100","TE","Abruzzo"],
    ["Terni","05100","TR","Umbria"],
    ["Torino","10121","TO","Piemonte"],
    ["Trapani","91100","TP","Sicilia"],
    ["Trento","38121","TN","Trentino-Alto Adige"],
    ["Treviso","31100","TV","Veneto"],
    ["Trieste","34121","TS","Friuli-Venezia Giulia"],
    ["Udine","33100","UD","Friuli-Venezia Giulia"],
    ["Varese","21100","VA","Lombardia"],
    ["Venezia","30121","VE","Veneto"],
    ["Verbania","28921","VB","Piemonte"],
    ["Vercelli","13100","VC","Piemonte"],
    ["Verona","37121","VR","Veneto"],
    ["Vibo Valentia","89900","VV","Calabria"],
    ["Vicenza","36100","VI","Veneto"],
    ["Viterbo","01100","VT","Lazio"],
]


def _converti_raw(raw):
    """Adatta il formato di matteocontrini/comuni-json.
    'c' è sempre una lista: ['00100'] oppure ['00100','00118',...].
    """
    comuni = []
    for c in raw:
        cap = c.get("cap", [])
        comuni.append({
            "n": c["nome"],
            "c": cap,          # lista completa — il widget gestisce la scelta
            "p": c.get("sigla", ""),
            "r": c.get("regione", {}).get("nome", ""),
        })
    comuni.sort(key=lambda x: x["n"])
    return comuni


def _genera_seed():
    return [
        {"n": r[0], "c": [r[1]], "p": r[2], "r": r[3]}
        for r in sorted(CAPOLUOGHI_SEED, key=lambda x: x[0])
    ]


class Command(BaseCommand):
    help = "Genera/scarica il dataset comuni italiani in static/js/comuni_italiani.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--solo-seed",
            action="store_true",
            help="Usa solo il seed integrato (110 capoluoghi), senza download",
        )

    def handle(self, *args, **options):
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

        if options["solo_seed"]:
            comuni = _genera_seed()
            self._salva(comuni, "seed integrato")
            return

        self.stdout.write(f"Download da {SOURCE_URL} …")
        try:
            req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = json.loads(resp.read())
            comuni = _converti_raw(raw)
            self._salva(comuni, f"download ({len(comuni)} comuni)")
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f"Download fallito ({e}). Uso seed integrato (110 capoluoghi)."
            ))
            comuni = _genera_seed()
            self._salva(comuni, "seed integrato")

    def _salva(self, comuni, fonte):
        OUTPUT_PATH.write_text(
            json.dumps(comuni, ensure_ascii=False, separators=(",", ":"))
        )
        size_kb = OUTPUT_PATH.stat().st_size // 1024
        self.stdout.write(self.style.SUCCESS(
            f"Salvato {OUTPUT_PATH} — {len(comuni)} voci da {fonte}, {size_kb} KB"
        ))
