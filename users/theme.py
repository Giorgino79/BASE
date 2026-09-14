"""
Tema per-utente — genera il blocco :root delle variabili colore in base
alle preferenze salvate su User (palette + a quale ruolo — sidebar,
navbar, accento primario/secondario — è assegnato ciascuno dei 4 colori
della famiglia scelta).

La parte strutturale del CSS (card, tabelle, bottoni...) è invece un file
statico normale (static/css/main-structure.css), identica per tutti — usa
sempre le stesse variabili (--color-1, --sidebar-bg, --navbar-bg, ...),
qui generate dinamicamente invece che fisse per file.
"""

import colorsys

# Le 4 famiglie di colori confermate — stessi valori di
# BASE/static/css/palettes/main-palette-*.css. Ordine = ordine mostrato
# nel selettore ruoli (slot 1..4).
PALETTE_FAMIGLIE = {
    "1": {"nome": "Blu",        "colori": ["#5585b5", "#53a8b6", "#79c2d0", "#bbe4e9"]},
    "2": {"nome": "Verde",      "colori": ["#3bba83", "#3baea0", "#118a7e", "#1f6f78"]},
    "3": {"nome": "Marroncino", "colori": ["#8b855b", "#537791", "#e7e6e1", "#f7f6e7"]},
    "4": {"nome": "Lavanda",    "colori": ["#c3bef0", "#cca8e9", "#cadefc", "#defcf9"]},
}

RUOLI = ["sidebar_role", "navbar_role", "accento_role", "accento2_role"]


def _hex_to_hsl(hexcol):
    hexcol = hexcol.lstrip("#")
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s * 100, l * 100


def _hsl_to_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, max(0, min(100, l)) / 100, max(0, min(100, s)) / 100)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def _blend_bianco(hexcol, rapporto):
    hexcol = hexcol.lstrip("#")
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (0, 2, 4))
    r = r * (1 - rapporto) + rapporto
    g = g * (1 - rapporto) + rapporto
    b = b * (1 - rapporto) + rapporto
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def _accento_dark(hexcol):
    h, s, l = _hex_to_hsl(hexcol)
    return _hsl_to_hex(h, s + 3, l - 12)


def _accento_light(hexcol):
    h, s, l = _hex_to_hsl(hexcol)
    return _hsl_to_hex(h, s + 13, l + 38)


def _barra_scura(hexcol):
    """Sfondo/hover/testo per una barra scura (sidebar o navbar) a partire
    da un colore qualsiasi della palette — stessa formula HSL usata per
    tutte le palette confermate il 28/08/2026."""
    h, s, l = _hex_to_hsl(hexcol)
    return {
        "bg": _hsl_to_hex(h + 3, s + 10, l - 18),
        "active": _hsl_to_hex(h + 4, s + 13, l - 27),
        "hover": _hsl_to_hex(h + 5, s + 14, l - 21),
        "text": _hsl_to_hex(h, s + 8, l + 25),
    }


def get_ruoli_utente(user):
    """Ritorna (palette_id, {ruolo: slot}) con default sensati se l'utente
    non ha ancora scelto nulla."""
    palette_id = getattr(user, "palette", None) or "1"
    if palette_id not in PALETTE_FAMIGLIE:
        palette_id = "1"
    ruoli = {
        "sidebar_role": getattr(user, "sidebar_role", None) or "1",
        "navbar_role": getattr(user, "navbar_role", None) or "1",
        "accento_role": getattr(user, "accento_role", None) or "1",
        "accento2_role": getattr(user, "accento2_role", None) or "2",
    }
    return palette_id, ruoli


def genera_root_css(palette_id, ruoli):
    """ruoli: dict con chiavi sidebar_role/navbar_role/accento_role/accento2_role,
    valori '1'..'4' (indice 1-based nella famiglia scelta)."""
    famiglia = PALETTE_FAMIGLIE.get(palette_id, PALETTE_FAMIGLIE["1"])["colori"]

    def slot(ruolo_key):
        idx = int(ruoli.get(ruolo_key, "1")) - 1
        idx = max(0, min(3, idx))
        return famiglia[idx]

    accento = slot("accento_role")
    accento2 = slot("accento2_role")
    color3 = famiglia[2]
    color4 = famiglia[3]

    sidebar = _barra_scura(slot("sidebar_role"))
    navbar = _barra_scura(slot("navbar_role"))

    indigo_100 = _blend_bianco(accento, 0.45)
    indigo_200 = _blend_bianco(accento, 0.15)

    h3, s3, l3 = _hex_to_hsl(color3)
    color3_light = _hsl_to_hex(h3, s3 + 10, min(95, l3 + 15))

    return f""":root {{
  --color-1:       {accento};
  --color-1-dark:  {_accento_dark(accento)};
  --color-1-light: {_accento_light(accento)};
  --color-2:       {accento2};
  --color-2-dark:  {_accento_dark(accento2)};
  --color-2-light: {_accento_light(accento2)};
  --color-3:       {color3};
  --color-3-light: {color3_light};
  --color-4:       {color4};

  --indigo-50:  var(--color-1-light);
  --indigo-100: {indigo_100};
  --indigo-200: {indigo_200};
  --indigo-500: var(--color-1);
  --indigo-600: var(--color-1);
  --indigo-700: var(--color-1-dark);

  --slate-50:  #f8fafc;
  --slate-100: #f1f5f9;
  --slate-200: #e2e8f0;
  --slate-300: #cbd5e1;
  --slate-400: #94a3b8;
  --slate-500: #64748b;
  --slate-600: #475569;
  --slate-700: #334155;
  --slate-800: #1e293b;
  --slate-900: #0f172a;

  --sidebar-width:       260px;
  --sidebar-bg:          {sidebar['bg']};
  --sidebar-active:      {sidebar['active']};
  --sidebar-hover:       {sidebar['hover']};
  --sidebar-text:        {sidebar['text']};
  --sidebar-text-active: #ffffff;
  --sidebar-accent:      var(--color-4);
  --navbar-bg:           {navbar['bg']};
  --navbar-text:         {navbar['text']};
  --navbar-text-active:  #ffffff;
  --topbar-height:       60px;
  --content-bg:          var(--slate-100);

  --card-shadow:        0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.06);
  --card-shadow-hover:  0 4px 12px rgba(0,0,0,.12);
  --shadow-sm:          0 .125rem .25rem rgba(0,0,0,.075);
  --shadow-md:          0 .5rem 1rem rgba(0,0,0,.15);

  --spacing-xs: .25rem;
  --spacing-sm: .5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 3rem;

  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
}}
"""
