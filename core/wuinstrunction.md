# Istruzioni: aggiornamento funzione WhatsApp/Email (Bottone INVIA)

Questo file guida Claude Code nell'applicare la feature **bottone INVIA** (WhatsApp + Email)
da BASE verso un progetto figlio già esistente.

---

## Contesto

BASE è il progetto starter da cui derivano tutti i progetti gestionali.
La feature "bottone INVIA" permette di inviare documenti (testo o PDF) via WhatsApp Web
e/o email direttamente dai template Django, tramite un modal Bootstrap riusabile.

Il codice sorgente di riferimento è sempre in BASE:
`/home/giorgio/Scrivania/BASE/`

---

## Prima di iniziare — verifica stato

Esegui questi comandi nella root del progetto figlio:

```bash
grep -r "invia_documento" core/urls.py 2>/dev/null && echo "GIA PRESENTE" || echo "DA AGGIUNGERE"
grep -r "InvioLog" core/models/__init__.py 2>/dev/null && echo "GIA PRESENTE" || echo "DA AGGIUNGERE"
pip show pywhatkit 2>/dev/null && echo "INSTALLATO" || echo "MANCANTE"
```

Se tutto è "GIA PRESENTE", la feature è già installata — nessuna azione necessaria.

---

## Step 1 — Copia i file nuovi da BASE

Copia questi file esattamente come sono (non modificarli):

| Sorgente in BASE | Destinazione nel progetto figlio |
|---|---|
| `core/whatsapp_sender.py` | `core/whatsapp_sender.py` |
| `core/models/invia_log.py` | `core/models/invia_log.py` |
| `core/views_invia.py` | `core/views_invia.py` |
| `core/templates/core/modal_invia.html` | `core/templates/core/modal_invia.html` |
| `core/templatetags/invia_tags.py` | `core/templatetags/invia_tags.py` |

Comando bash (eseguilo dalla root di BASE, sostituisci `$PROGETTO`):

```bash
PROGETTO=/path/al/progetto-figlio

cp core/whatsapp_sender.py               $PROGETTO/core/
cp core/models/invia_log.py              $PROGETTO/core/models/
cp core/views_invia.py                   $PROGETTO/core/
cp core/templates/core/modal_invia.html  $PROGETTO/core/templates/core/
cp core/templatetags/invia_tags.py       $PROGETTO/core/templatetags/
```

---

## Step 2 — Modifica `core/models/__init__.py`

Aggiungi l'import di `InvioLog` **dopo** le import esistenti:

```python
from .invia_log import InvioLog
```

Aggiungi `"InvioLog"` alla lista `__all__`:

```python
__all__ = [
    "BaseModel",
    "BaseModelWithCode",
    "BaseModelSimple",
    "EventoCalendario",
    "InvioLog",           # <-- aggiunta
    "PermissionTemplate",
]
```

---

## Step 3 — Modifica `core/urls.py`

Aggiungi l'import **insieme agli altri import di views**:

```python
from .views_invia import invia_documento
```

Aggiungi il path **in `urlpatterns`**, nella sezione TOOLS o alla fine:

```python
# ========== INVIA (WhatsApp / Email) ==========
path("invia/", invia_documento, name="invia_documento"),
```

---

## Step 4 — Modifica `config/settings.py`

Aggiungi in fondo al file (prima dell'eventuale blocco produzione):

```python
# WhatsApp sender
WHATSAPP_MIN_DELAY = int(os.environ.get("WHATSAPP_MIN_DELAY", 20))
WHATSAPP_WAIT_TIME = int(os.environ.get("WHATSAPP_WAIT_TIME", 12))
```

---

## Step 5 — Dipendenze

```bash
pip install pywhatkit==5.4
```

Aggiungi a `requirements.txt`:

```
pywhatkit==5.4
```

---

## Step 6 — Migration

```bash
python manage.py makemigrations core --name invia_log
python manage.py migrate
```

Verifica che l'output contenga `Create model InvioLog` e `OK`.

---

## Step 7 — Verifica rapida

```bash
python manage.py check
```

Nessun errore = installazione corretta.

---

## Uso nei template del progetto figlio

### Caso 1 — Solo testo (nessun PDF)

```django
{% load invia_tags %}

{% bottone_invia
    phone=dipendente.telefono
    email=dipendente.email
    oggetto="Comunicazione importante"
    messaggio="Gentile dipendente, in allegato..."
    destinatario_nome=dipendente.get_full_name
%}
```

### Caso 2 — Con PDF (URL Django)

```django
{% load invia_tags %}

{% bottone_invia
    phone=dipendente.telefono
    email=dipendente.email
    oggetto="Busta paga Gennaio 2026"
    pdf_url=pdf_url
    destinatario_nome=dipendente.get_full_name
    label="Invia busta paga"
    btn_class="btn-success"
%}
```

### Parametri disponibili

| Parametro | Tipo | Default | Descrizione |
|---|---|---|---|
| `phone` | str | `""` | Numero WhatsApp (es. `"+393331234567"` o `"3331234567"`) |
| `email` | str | `""` | Email destinatario |
| `oggetto` | str | `""` | Oggetto / titolo documento |
| `messaggio` | str | `""` | Testo del messaggio |
| `pdf_url` | str | `""` | URL relativa Django del PDF (es. `/media/buste/file.pdf`) |
| `pdf_path` | str | `""` | Percorso assoluto del PDF (alternativa a `pdf_url`) |
| `destinatario_nome` | str | `""` | Nome del destinatario (mostrato nel log) |
| `label` | str | `"Invia"` | Testo del bottone |
| `btn_class` | str | `"btn-primary"` | Classe Bootstrap del bottone |
| `btn_size` | str | `""` | `"btn-sm"` / `"btn-lg"` / `""` |

---

## Prerequisiti a runtime per WhatsApp

- **Browser aperto** con WhatsApp Web (`web.whatsapp.com`) già loggato
- **Display grafico disponibile** (macchina locale, non server headless)
- Il delay minimo tra invii è 20 secondi + jitter random (configurabile via `WHATSAPP_MIN_DELAY`)
- Tutti gli invii vengono registrati nel modello `InvioLog` (admin Django: *Core → Log invii*)

---

## Troubleshooting

| Errore | Causa | Soluzione |
|---|---|---|
| `DisplayConnectionError` all'avvio | pywhatkit carica pyautogui che cerca il display | Già gestito con import lazy — se persiste, verifica che la variabile `DISPLAY` sia settata |
| `pywhatkit non disponibile` | Library non installata o display mancante | `pip install pywhatkit` e assicurarsi di avere un display attivo |
| Il browser non si apre | WhatsApp non è loggato su Web | Aprire `web.whatsapp.com` e fare login con QR code |
| `File non trovato` | `pdf_url` non corrisponde a un file in MEDIA_ROOT | Verificare che il PDF sia in `/media/` e che `MEDIA_ROOT` sia corretto |
| Email non inviata | `EMAIL_BACKEND` punta a console | Configurare SMTP in `.env`: `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` |

---

## Versione feature

- Introdotta in BASE commit: `feat: WhatsApp/Email bottone INVIA`
- Compatibile con: Django 5.x, pywhatkit 5.4, Bootstrap 5
