# Manuale Tecnico — Progetto Django BASE

**Versione:** 1.1  
**Compatibilità:** Django 5.2, Python 3.12  
**Ultimo aggiornamento:** 2026-05-18

---

## Indice

1. [Requisiti di sistema](#1-requisiti-di-sistema)
2. [Installazione e primo avvio](#2-installazione-e-primo-avvio)
3. [Variabili d'ambiente](#3-variabili-dambiente)
4. [Architettura del progetto](#4-architettura-del-progetto)
5. [Sistema di permessi](#5-sistema-di-permessi)
6. [CalendarioRegistry](#6-calendarioregistry)
7. [Sistema allegati](#7-sistema-allegati)
8. [Generazione PDF](#8-generazione-pdf)
9. [Come agganciare una nuova app](#9-come-agganciare-una-nuova-app)
10. [Management commands](#10-management-commands)
11. [Deploy su Heroku](#11-deploy-su-heroku)
12. [Convenzioni di codice](#12-convenzioni-di-codice)
13. [Dress code UI — Regole ferree](#13-dress-code-ui--regole-ferree)
14. [Template dettaglio oggetto](#14-template-dettaglio-oggetto)

---

## 1. Requisiti di sistema

| Componente | Versione minima | Note |
|---|---|---|
| Python | 3.11 | Consigliata 3.12 |
| pip | 23.0 | |
| git | 2.x | |
| SQLite | 3.35 | Solo per sviluppo locale |
| PostgreSQL | 14 | Per produzione/Heroku |

Verificare le versioni installate:

```bash
python --version
pip --version
git --version
```

---

## 2. Installazione e primo avvio

### 2.1 Clonare il repository

```bash
git clone <url-repository> BASE
cd BASE
```

### 2.2 Creare e attivare l'ambiente virtuale

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2.3 Installare le dipendenze

```bash
pip install -r requirements.txt
```

### 2.4 Creare il file `.env`

Copiare il file di esempio e compilare i valori:

```bash
cp .env.example .env
```

Aprire `.env` e impostare almeno le variabili obbligatorie (vedere la tabella nella sezione 3).

### 2.5 Applicare le migrazioni

```bash
python manage.py migrate
```

### 2.6 Configurare i permessi base

```bash
python manage.py setup_permissions
```

Questo comando crea i gruppi di default e assegna i permessi CRUD definiti nei `PermissionTemplate` di ogni app.

### 2.7 Creare il superutente

```bash
python manage.py createsuperuser
```

### 2.8 Raccogliere i file statici (opzionale in sviluppo)

```bash
python manage.py collectstatic
```

In sviluppo Django serve i file statici automaticamente. In produzione questo passaggio è obbligatorio.

### 2.9 Avviare il server di sviluppo

```bash
python manage.py runserver
```

L'applicazione sarà disponibile su `http://127.0.0.1:8000/`.

---

## 3. Variabili d'ambiente

Il progetto legge la configurazione da un file `.env` nella root del progetto (caricato tramite `python-dotenv` o equivalente).

| Variabile | Obbligatoria | Default | Descrizione |
|---|---|---|---|
| `SECRET_KEY` | Si | — | Chiave segreta Django. Generare con `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | No | `False` | Impostare `True` solo in sviluppo |
| `ALLOWED_HOSTS` | Si (prod) | `[]` | Lista di host separati da virgola, es. `myapp.herokuapp.com,localhost` |
| `DATABASE_URL` | No | SQLite locale | URL database nel formato `postgres://user:pass@host:port/dbname` |
| `STATIC_ROOT` | No | `staticfiles/` | Percorso dove `collectstatic` deposita i file |
| `MEDIA_ROOT` | No | `media/` | Percorso dove vengono salvati gli upload (foto profilo, allegati) |
| `MEDIA_URL` | No | `/media/` | URL pubblico per accedere ai media |
| `EMAIL_HOST` | No | — | Server SMTP per invio email |
| `EMAIL_PORT` | No | `587` | Porta SMTP |
| `EMAIL_HOST_USER` | No | — | Username SMTP |
| `EMAIL_HOST_PASSWORD` | No | — | Password SMTP |
| `EMAIL_USE_TLS` | No | `True` | Abilitare TLS per SMTP |
| `DEFAULT_FROM_EMAIL` | No | — | Indirizzo mittente default per le email |

Esempio di file `.env` minimo per lo sviluppo locale:

```dotenv
SECRET_KEY=cambia-questa-chiave-con-una-vera
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## 4. Architettura del progetto

### 4.1 Struttura delle directory

```
BASE/
├── config/
│   ├── settings.py          # Configurazione Django
│   ├── urls.py              # URL dispatcher principale
│   └── wsgi.py              # Entry point WSGI
├── core/                    # App di utilità condivise
│   ├── models.py            # EventoCalendario, Allegato, PermissionTemplate
│   ├── views.py             # Views generiche (calcolatrice, ecc.)
│   ├── calendario_registry.py  # CalendarioRegistry
│   ├── modulo_registry.py   # ModuloRegistry
│   ├── pdf_utils.py         # genera_pdf_da_template, genera_pdf_da_html
│   ├── mixins.py            # AllegatiMixin
│   └── management/commands/ # setup_permissions, create_module, check_modules
├── users/                   # App gestione dipendenti
│   ├── models.py            # User, Timbratura, GiornataLavorativa, ecc.
│   ├── views.py
│   └── urls.py
├── comunicazioni/           # App messaggistica interna
│   ├── models.py            # Promemoria, ChatConversazione, ChatMessaggio
│   ├── views.py
│   └── urls.py
├── corrispondenza/          # App lettere formali
│   ├── models.py            # TipoCorrispondenza, Corrispondenza
│   ├── views.py
│   └── urls.py
├── templates/
│   ├── base.html            # Template base (navbar, sidebar, footer)
│   ├── login.html
│   └── dashboard.html
├── static/
│   ├── css/
│   ├── js/
│   └── img/
├── requirements.txt
├── Procfile                 # Per Heroku
├── manage.py
└── .env.example
```

### 4.2 App Django e loro responsabilità

#### `core`

App fondamentale da cui tutte le altre dipendono. Non deve mai dipendere da `users`, `comunicazioni` o `corrispondenza`. Fornisce:

- **CalendarioRegistry**: aggregatore di eventi calendario da provider multipli
- **EventoCalendario**: modello generico per gli eventi visualizzati nel calendario aziendale
- **PermissionTemplate**: sistema dichiarativo per la gestione dei permessi CRUD per gruppi
- **AllegatiMixin / Allegato**: sistema di allegati riutilizzabile
- **PDF utils**: generazione di PDF tramite xhtml2pdf
- **QR code**: generazione di QR code
- **ModuloRegistry**: registro dei moduli installati
- **Calcolatrice**: view statica con interfaccia JS

#### `users`

Dipende da `core`. Gestisce tutto il ciclo di vita dei dipendenti:

- Modello `User` esteso da `AbstractUser` con campi aziendali
- Sistema di timbratura (ingresso/uscita, turni mattina/pomeriggio/notte)
- Calcolo automatico delle `GiornataLavorativa` (ore ordinarie e straordinarie)
- Gestione richieste ferie e permessi con workflow di approvazione
- Lettere di richiamo (con allegati tramite `AllegatiMixin`)
- Calendario personale (`EventoPersonale`) integrato nel `CalendarioRegistry`

#### `comunicazioni`

Dipende da `core` e `users`. Gestisce la comunicazione interna:

- **Promemoria**: task con priorità, scadenze e stati
- **Chat**: conversazioni dirette e di gruppo con polling AJAX ogni 3 secondi

#### `corrispondenza`

Dipende da `core` e `users`. Gestisce le lettere formali:

- Protocollazione automatica nel formato `CORyyyyNNNN`
- Workflow bozza → inviata → archiviata (stati non reversibili una volta inviata)
- Destinatari interni (utenti del sistema) o esterni (dati anagrafici liberi)
- Generazione PDF della lettera
- Permessi granulari: `corrispondenza.can_view_all`, `corrispondenza.can_send`

### 4.3 Dipendenze tra app

```
core  (nessuna dipendenza interna)
  ↑
users (dipende da core)
  ↑
comunicazioni (dipende da core, users)
corrispondenza (dipende da core, users)
```

Regola fondamentale: `core` non deve mai importare da altre app del progetto. Ogni altra app può importare da `core`. Le app allo stesso livello (es. `comunicazioni` e `corrispondenza`) non devono dipendere l'una dall'altra.

### 4.4 Stack tecnologico

| Componente | Tecnologia | Versione |
|---|---|---|
| Framework web | Django | 5.2 |
| Linguaggio | Python | 3.12 |
| Frontend CSS | Bootstrap | 5.3 |
| Icone | Bootstrap Icons | 1.11 |
| Form rendering | crispy-forms + crispy-bootstrap5 | — |
| Autocomplete/Select | django-select2 | — |
| File statici (prod) | whitenoise | — |
| Database (dev) | SQLite | — |
| Database (prod) | PostgreSQL | — |
| Config database URL | dj-database-url | — |
| Calendario | FullCalendar | 6.1.11 (CDN) |
| Generazione PDF | xhtml2pdf | — |

---

## 5. Sistema di permessi

### 5.1 Panoramica

BASE utilizza un sistema a due livelli:

1. **Permessi Django standard** (`add_`, `change_`, `delete_`, `view_`): generati automaticamente da Django per ogni modello.
2. **Permessi custom**: definiti manualmente in `Meta.permissions` nei modelli (es. `can_view_all`, `can_send`).

### 5.2 PermissionTemplate

`PermissionTemplate` è un sistema dichiarativo che mappa i gruppi utente ai permessi CRUD. È definito in `core` e ogni app può registrare i propri template.

Struttura di un template:

```python
# Esempio in users/apps.py o users/permissions.py
from core.models import PermissionTemplate

PERMISSION_TEMPLATES = [
    PermissionTemplate(
        group_name="Responsabile HR",
        permissions=[
            "users.add_user",
            "users.change_user",
            "users.view_user",
            "users.add_richiestavacanza",
            "users.change_richiestavacanza",
            "users.delete_richiestavacanza",
            "users.view_richiestavacanza",
        ]
    ),
    PermissionTemplate(
        group_name="Dipendente",
        permissions=[
            "users.view_user",
            "users.add_richiestavacanza",
            "users.view_richiestavacanza",
        ]
    ),
]
```

Il command `setup_permissions` legge tutti i `PermissionTemplate` registrati e crea i gruppi con i permessi corrispondenti.

### 5.3 Applicare i permessi nelle view

Nelle view basate su funzioni:

```python
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required("corrispondenza.can_send", raise_exception=True)
def invia_corrispondenza(request, pk):
    ...
```

Nelle view basate su classi:

```python
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

class InviaCorrispondenzaView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "corrispondenza.can_send"
    ...
```

Nei template:

```django
{% if perms.corrispondenza.can_send %}
    <a href="{% url 'corrispondenza:invia' pk=obj.pk %}">Invia</a>
{% endif %}
```

### 5.4 Permessi custom per una nuova app

Per aggiungere permessi custom a un modello della nuova app:

```python
class MioModello(models.Model):
    ...

    class Meta:
        permissions = [
            ("can_approve", "Può approvare"),
            ("can_export", "Può esportare dati"),
        ]
```

Dopo aver aggiunto i permessi, eseguire le migrazioni e poi `setup_permissions` per assegnarli ai gruppi.

---

## 6. CalendarioRegistry

### 6.1 Panoramica

`CalendarioRegistry` è un pattern provider che permette a qualsiasi app di contribuire eventi al calendario aziendale senza che `core` debba conoscere le altre app. Funziona tramite registrazione esplicita di provider.

### 6.2 Struttura di un provider

Un provider è una classe con un metodo `get_eventi(user, start, end)` che restituisce una lista di `EventoCalendario` o dizionari compatibili con FullCalendar:

```python
# magazzino/calendario_provider.py
from core.calendario_registry import registro_calendario
from core.models import EventoCalendario


class MagazzinoCalendarioProvider:
    """Provider che espone le scadenze inventario nel calendario aziendale."""

    def get_eventi(self, user, start, end):
        from magazzino.models import ScadenzaInventario

        eventi = []
        scadenze = ScadenzaInventario.objects.filter(
            data__range=(start, end)
        )
        for scadenza in scadenze:
            eventi.append(EventoCalendario(
                titolo=f"Inventario: {scadenza.reparto}",
                data_inizio=scadenza.data,
                data_fine=scadenza.data,
                visibilita="pubblica",
                provider="magazzino",
                url=scadenza.get_absolute_url(),
                colore="#28a745",
            ))
        return eventi
```

### 6.3 Registrare il provider

La registrazione deve avvenire nel metodo `ready()` dell'`AppConfig` dell'app:

```python
# magazzino/apps.py
from django.apps import AppConfig


class MagazzinoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "magazzino"
    verbose_name = "Magazzino"

    def ready(self):
        from core.calendario_registry import registro_calendario
        from magazzino.calendario_provider import MagazzinoCalendarioProvider

        registro_calendario.registra("magazzino", MagazzinoCalendarioProvider())
```

### 6.4 Come funziona il calendario nelle view

La view del calendario in `core` chiama il registro per ottenere tutti gli eventi:

```python
# core/views.py (semplificato)
from core.calendario_registry import registro_calendario

def get_eventi_calendario(request):
    start = request.GET.get("start")
    end = request.GET.get("end")
    eventi = registro_calendario.get_tutti_gli_eventi(
        user=request.user,
        start=start,
        end=end,
    )
    return JsonResponse(eventi, safe=False)
```

### 6.5 EventoCalendario e FullCalendar

Il modello `EventoCalendario` espone il metodo `to_fullcalendar()` che trasforma l'oggetto nel formato JSON atteso da FullCalendar 6.x:

```python
evento = EventoCalendario(...)
data = evento.to_fullcalendar()
# Restituisce un dict con: id, title, start, end, url, color, ...
```

---

## 7. Sistema allegati

### 7.1 Panoramica

`AllegatiMixin` è un mixin Django che aggiunge il supporto agli allegati a qualsiasi modello, senza dover ridefinire la logica di upload e gestione file.

### 7.2 Il modello Allegato

```
Allegato
├── content_type (FK a ContentType)
├── object_id    (PositiveIntegerField)
├── content_object (GenericForeignKey)
├── file         (FileField)
├── nome         (CharField)
├── dimensione   (IntegerField, bytes)
├── caricato_da  (FK User)
└── caricato_il  (DateTimeField)
```

Usa le `GenericForeignKey` di Django per collegarsi a qualsiasi modello.

### 7.3 Aggiungere allegati a un modello esistente

```python
# magazzino/models.py
from core.mixins import AllegatiMixin
from django.db import models


class Documento(AllegatiMixin, models.Model):
    titolo = models.CharField(max_length=200)
    data_documento = models.DateField()
    # AllegatiMixin aggiunge automaticamente il supporto agli allegati
    # Non serve aggiungere campi extra al modello
```

Il mixin espone i seguenti metodi sull'istanza del modello:

```python
documento = Documento.objects.get(pk=1)

# Ottenere tutti gli allegati
allegati = documento.get_allegati()

# Aggiungere un allegato
documento.aggiungi_allegato(file_object, nome="contratto.pdf", utente=request.user)

# Rimuovere un allegato
documento.rimuovi_allegato(allegato_id)
```

### 7.4 Mostrare gli allegati in un template

Includere il partial template fornito da `core`:

```django
{% include "core/partials/allegati.html" with oggetto=documento %}
```

Il partial mostra la lista degli allegati esistenti con link al download e un form per il caricamento di nuovi file.

### 7.5 Gestire gli allegati nella view

```python
# magazzino/views.py
from core.mixins import AllegatiMixin
from django.views.generic import DetailView
from magazzino.models import Documento


class DocumentoDetailView(DetailView):
    model = Documento
    template_name = "magazzino/documento_detail.html"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if "upload_allegato" in request.POST:
            file = request.FILES.get("allegato")
            if file:
                obj.aggiungi_allegato(file, utente=request.user)
        return redirect(obj.get_absolute_url())
```

---

## 8. Generazione PDF

### 8.1 Panoramica

La generazione PDF avviene tramite `xhtml2pdf`, una libreria che converte HTML/CSS in PDF. Le funzioni di utilità si trovano in `core/pdf_utils.py`.

### 8.2 Funzioni disponibili

#### `genera_pdf_da_template(template_path, context, filename)`

Genera un PDF a partire da un template Django e restituisce una `HttpResponse` con content-type `application/pdf`.

```python
from core.pdf_utils import genera_pdf_da_template

def stampa_lettera(request, pk):
    lettera = get_object_or_404(Corrispondenza, pk=pk)
    context = {
        "lettera": lettera,
        "data_stampa": date.today(),
    }
    return genera_pdf_da_template(
        template_path="corrispondenza/pdf/lettera.html",
        context=context,
        filename=f"lettera_{lettera.numero_protocollo}.pdf",
    )
```

#### `genera_pdf_da_html(html_string, filename)`

Genera un PDF a partire da una stringa HTML già renderizzata.

```python
from core.pdf_utils import genera_pdf_da_html
from django.template.loader import render_to_string

html = render_to_string("magazzino/pdf/report.html", context)
return genera_pdf_da_html(html, filename="report_magazzino.pdf")
```

### 8.3 Struttura di un template PDF

I template PDF devono essere HTML valido con CSS inline o in un tag `<style>`. Le risorse esterne (immagini, font) devono essere referenziate con percorsi assoluti sul filesystem, non URL relativi.

```html
<!-- magazzino/templates/magazzino/pdf/report.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Helvetica, Arial, sans-serif; font-size: 12px; }
        .intestazione { border-bottom: 2px solid #333; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; }
        td, th { border: 1px solid #ccc; padding: 6px; }
    </style>
</head>
<body>
    <div class="intestazione">
        <h1>Report Magazzino</h1>
        <p>Data: {{ data_stampa }}</p>
    </div>
    ...
</body>
</html>
```

### 8.4 Salvare il PDF su file invece di restituirlo come risposta

```python
from core.pdf_utils import genera_pdf_da_template
import io

# Ottenere i byte del PDF senza restituire una response HTTP
response = genera_pdf_da_template(template_path, context, filename)
pdf_bytes = response.content

# Salvare su un campo FileField del modello
from django.core.files.base import ContentFile
oggetto.pdf.save(filename, ContentFile(pdf_bytes), save=True)
```

---

## 9. Come agganciare una nuova app

Questa checklist descrive i passi necessari per integrare una nuova app modulare (es. `magazzino`) nel progetto BASE.

### 9.1 Creare l'app

```bash
python manage.py startapp magazzino
```

### 9.2 Registrare in INSTALLED_APPS

Aprire `config/settings.py` e aggiungere l'app alla lista:

```python
INSTALLED_APPS = [
    # ... app Django built-in ...
    "core",
    "users",
    "comunicazioni",
    "corrispondenza",
    "magazzino",          # <-- aggiungere qui
]
```

### 9.3 Configurare AppConfig

Assicurarsi che `magazzino/apps.py` sia correttamente configurato:

```python
# magazzino/apps.py
from django.apps import AppConfig


class MagazzinoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "magazzino"
    verbose_name = "Magazzino"

    def ready(self):
        # Registrazioni opzionali (provider calendario, segnali, ecc.)
        pass
```

E che `magazzino/__init__.py` punti all'AppConfig:

```python
# magazzino/__init__.py
default_app_config = "magazzino.apps.MagazzinoConfig"
```

### 9.4 Aggiungere gli URL

Creare `magazzino/urls.py`:

```python
# magazzino/urls.py
from django.urls import path
from . import views

app_name = "magazzino"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("<int:pk>/", views.DetailView.as_view(), name="detail"),
    # ...
]
```

Includere gli URL nel dispatcher principale:

```python
# config/urls.py
urlpatterns = [
    # ... URL esistenti ...
    path("magazzino/", include("magazzino.urls", namespace="magazzino")),
]
```

### 9.5 Creare i modelli e le migrazioni

```bash
python manage.py makemigrations magazzino
python manage.py migrate
```

### 9.6 Definire i permessi

In `magazzino/models.py` aggiungere i permessi custom nel `Meta`:

```python
class Meta:
    permissions = [
        ("can_export", "Può esportare l'inventario"),
        ("can_approve_order", "Può approvare gli ordini"),
    ]
```

Creare i `PermissionTemplate` in `magazzino/permissions.py` e registrarli nel management command `setup_permissions`.

### 9.7 (Opzionale) Registrare un CalendarioProvider

Vedere la sezione 6 per i dettagli. Aggiungere la registrazione nel metodo `ready()` dell'`AppConfig`.

### 9.8 (Opzionale) Registrarsi nel ModuloRegistry

```python
# magazzino/apps.py
def ready(self):
    from core.modulo_registry import registro_moduli

    registro_moduli.registra(
        nome="magazzino",
        label="Magazzino",
        url_namespace="magazzino",
        icona="bi-box-seam",
        descrizione="Gestione magazzino e inventario",
    )
```

### 9.9 Creare i template

Struttura consigliata per i template della nuova app:

```
templates/
└── magazzino/
    ├── base_magazzino.html      # Template base dell'app (estende base.html)
    ├── index.html
    ├── detail.html
    ├── form.html
    └── pdf/
        └── report.html
```

### 9.10 Checklist riepilogativa

- [ ] App creata con `startapp`
- [ ] Aggiunta a `INSTALLED_APPS` in `config/settings.py`
- [ ] `AppConfig` configurato in `apps.py`
- [ ] URL definiti in `magazzino/urls.py`
- [ ] URL inclusi in `config/urls.py`
- [ ] Modelli creati con permessi custom nel `Meta`
- [ ] Migrazioni create e applicate
- [ ] `PermissionTemplate` definiti e registrati
- [ ] `setup_permissions` eseguito
- [ ] Template HTML creati
- [ ] (Opzionale) `CalendarioProvider` registrato
- [ ] (Opzionale) App registrata nel `ModuloRegistry`

---

## 10. Management commands

BASE fornisce i seguenti management commands personalizzati, tutti nella app `core`.

### `setup_permissions`

Crea i gruppi Django definiti nei `PermissionTemplate` e assegna i permessi corrispondenti. Idempotente: può essere eseguito più volte senza problemi.

```bash
python manage.py setup_permissions
```

Opzioni:

```bash
# Mostrare le operazioni senza eseguirle (dry run)
python manage.py setup_permissions --dry-run

# Resettare tutti i permessi dei gruppi prima di riassegnarli
python manage.py setup_permissions --reset
```

### `create_module`

Scaffolding per la creazione di una nuova app modulare con la struttura standard del progetto BASE.

```bash
python manage.py create_module nome_modulo
```

Crea automaticamente:
- La directory dell'app con i file standard
- `apps.py` con `AppConfig` preconfigurato
- `urls.py` con `app_name` impostato
- Template base nell'app
- File `permissions.py` con struttura di esempio

### `check_modules`

Verifica l'integrità di tutti i moduli registrati nel `ModuloRegistry`: controlla che gli URL namespace esistano, che le migrazioni siano applicate, e che i `PermissionTemplate` siano consistenti.

```bash
python manage.py check_modules
```

Output di esempio:

```
[OK] core - Tutti i controlli superati
[OK] users - Tutti i controlli superati
[WARN] magazzino - Migrazioni in attesa: 0002_auto_20260510
[OK] comunicazioni - Tutti i controlli superati
```

---

## 11. Deploy su Heroku

### 11.1 Prerequisiti

- Account Heroku attivo
- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) installata
- Git configurato nel progetto

### 11.2 Creare l'app su Heroku

```bash
heroku login
heroku create nome-della-tua-app
```

### 11.3 Aggiungere il database PostgreSQL

```bash
heroku addons:create heroku-postgresql:essential-0
```

Heroku imposta automaticamente la variabile `DATABASE_URL`. `dj-database-url` la legge da `settings.py`.

### 11.4 Configurare le variabili d'ambiente su Heroku

```bash
heroku config:set SECRET_KEY="chiave-segreta-lunga-e-casuale"
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS="nome-della-tua-app.herokuapp.com"
```

### 11.5 Verificare il Procfile

Il `Procfile` nella root del progetto deve contenere:

```
web: gunicorn config.wsgi --log-file -
```

Assicurarsi che `gunicorn` sia in `requirements.txt`.

### 11.6 Verificare la configurazione di whitenoise

In `config/settings.py` whitenoise deve essere configurato correttamente:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # Subito dopo SecurityMiddleware
    # ... altri middleware ...
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
```

### 11.7 Fare il deploy

```bash
git add .
git commit -m "Configurazione per il deploy su Heroku"
git push heroku main
```

### 11.8 Eseguire le migrazioni e i setup post-deploy

```bash
heroku run python manage.py migrate
heroku run python manage.py setup_permissions
heroku run python manage.py createsuperuser
heroku run python manage.py collectstatic --noinput
```

### 11.9 Aprire l'applicazione

```bash
heroku open
```

### 11.10 Verificare i log in caso di errori

```bash
heroku logs --tail
```

### 11.11 Riepilogo checklist deploy

- [ ] App Heroku creata
- [ ] Add-on PostgreSQL aggiunto
- [ ] Variabili d'ambiente configurate (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`)
- [ ] `Procfile` presente e corretto
- [ ] `gunicorn` in `requirements.txt`
- [ ] `whitenoise` configurato nel middleware
- [ ] Push su Heroku completato
- [ ] `migrate` eseguito
- [ ] `setup_permissions` eseguito
- [ ] `createsuperuser` eseguito
- [ ] `collectstatic` eseguito

---

## 12. Convenzioni di codice

### 12.1 Nomi degli URL

Ogni app deve definire un `app_name` nel proprio `urls.py` (namespace). I nomi degli URL seguono la convenzione `<azione>` o `<modello>-<azione>`:

```python
app_name = "magazzino"

urlpatterns = [
    path("",                  views.IndexView.as_view(),  name="index"),
    path("prodotti/",         views.ProdottoList.as_view(),  name="prodotto-list"),
    path("prodotti/nuovo/",   views.ProdottoCreate.as_view(), name="prodotto-create"),
    path("prodotti/<int:pk>/",        views.ProdottoDetail.as_view(), name="prodotto-detail"),
    path("prodotti/<int:pk>/modifica/", views.ProdottoUpdate.as_view(), name="prodotto-update"),
    path("prodotti/<int:pk>/elimina/",  views.ProdottoDelete.as_view(), name="prodotto-delete"),
]
```

Nei template, sempre referenziare gli URL con il namespace:

```django
{% url 'magazzino:prodotto-detail' pk=prodotto.pk %}
{% url 'magazzino:prodotto-create' %}
```

### 12.2 Nomi dei template

I template seguono la convenzione `<app>/<modello>_<azione>.html`:

```
magazzino/
├── prodotto_list.html
├── prodotto_detail.html
├── prodotto_form.html        # Usato sia per create che per update
└── prodotto_confirm_delete.html
```

I template delle view generiche di Django (es. `ListView`, `DetailView`) cercano automaticamente i template con questa convenzione se non si specifica `template_name`.

### 12.3 Struttura delle view

Per operazioni CRUD standard, preferire le class-based views:

```python
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from magazzino.models import Prodotto
from magazzino.forms import ProdottoForm


class ProdottoListView(LoginRequiredMixin, ListView):
    model = Prodotto
    ordering = ["-created_at"]
    paginate_by = 20


class ProdottoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Prodotto
    form_class = ProdottoForm
    permission_required = "magazzino.add_prodotto"
    success_url = reverse_lazy("magazzino:prodotto-list")
```

Per le view che richiedono logica più complessa, usare funzioni con decoratori:

```python
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render


@login_required
@permission_required("magazzino.can_approve_order", raise_exception=True)
def approva_ordine(request, pk):
    ordine = get_object_or_404(Ordine, pk=pk)
    if request.method == "POST":
        ordine.approva(approvato_da=request.user)
        return redirect(ordine.get_absolute_url())
    return render(request, "magazzino/ordine_approva.html", {"ordine": ordine})
```

### 12.4 Modelli

- Sempre definire `__str__` e `get_absolute_url`
- Usare `verbose_name` e `verbose_name_plural` nel `Meta`
- I campi con scelte (`choices`) devono usare un `TextChoices` o `IntegerChoices` come classe interna
- I campi data/ora di creazione e modifica si chiamano `created_at` e `updated_at`

```python
class Prodotto(models.Model):

    class StatoProdotto(models.TextChoices):
        DISPONIBILE = "disponibile", "Disponibile"
        ESAURITO = "esaurito", "Esaurito"
        DISCONTINUATO = "discontinuato", "Discontinuato"

    nome = models.CharField(max_length=200, verbose_name="nome")
    codice = models.CharField(max_length=50, unique=True, verbose_name="codice")
    stato = models.CharField(
        max_length=20,
        choices=StatoProdotto.choices,
        default=StatoProdotto.DISPONIBILE,
        verbose_name="stato",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "prodotto"
        verbose_name_plural = "prodotti"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.codice} — {self.nome}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("magazzino:prodotto-detail", kwargs={"pk": self.pk})
```

### 12.5 Form

I form usano `crispy-forms` per il rendering Bootstrap 5:

```python
# magazzino/forms.py
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from magazzino.models import Prodotto


class ProdottoForm(forms.ModelForm):

    class Meta:
        model = Prodotto
        fields = ["nome", "codice", "stato"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("nome", css_class="col-md-8"),
                Column("codice", css_class="col-md-4"),
            ),
            "stato",
            Submit("submit", "Salva", css_class="btn btn-primary"),
        )
```

Nel template:

```django
{% load crispy_forms_tags %}
<form method="post">
    {% csrf_token %}
    {% crispy form %}
</form>
```

### 12.6 Messaggi all'utente

Usare il sistema di messaggi di Django per feedback post-azione:

```python
from django.contrib import messages

messages.success(request, "Prodotto salvato con successo.")
messages.error(request, "Si è verificato un errore durante il salvataggio.")
messages.warning(request, "Attenzione: il prodotto è quasi esaurito.")
messages.info(request, "Ricorda di aggiornare il listino prezzi.")
```

Il template `base.html` mostra automaticamente i messaggi in cima alla pagina usando gli alert Bootstrap.

### 12.7 Segnali Django

I segnali vanno definiti in un file `signals.py` dell'app e connessi nel metodo `ready()` dell'`AppConfig`:

```python
# magazzino/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from magazzino.models import Ordine


@receiver(post_save, sender=Ordine)
def notifica_approvazione(sender, instance, created, **kwargs):
    if not created and instance.stato == Ordine.StatoOrdine.APPROVATO:
        # Logica di notifica...
        pass
```

```python
# magazzino/apps.py
def ready(self):
    import magazzino.signals  # noqa: F401
```

---

---

## 13. Dress code UI — Regole ferree

Queste regole si applicano a **tutti** i template HTML del progetto BASE e di qualsiasi app che vi si aggancia. Non esistono eccezioni. L'obiettivo è avere un'interfaccia visivamente coerente dove ogni elemento rispetti sempre la stessa palette.

### 13.1 La palette ufficiale

Tutti i colori provengono esclusivamente dalle variabili CSS definite in `static/css/main.css`. Non si usa mai un valore esadecimale diretto.

| Variabile | Valore | Uso |
|---|---|---|
| `--color-1` | `#5585b5` | Colore brand principale (blu) — bottoni primari, accenti, bordi attivi |
| `--color-1-dark` | `#3d6a94` | Hover/focus del brand, testi su sfondi chiari |
| `--color-1-light` | `#dce8f4` | Sfondi tinted, badge positivi |
| `--color-2` | `#53a8b6` | Colore brand secondario (teal) — bottoni secondari, icone accent |
| `--color-2-dark` | `#3b8a96` | Hover del secondario |
| `--color-2-light` | `#d5eff3` | Sfondi tinted secondari, badge staff/accent |
| `--color-3` | `#79c2d0` | Decorativo, sfumature leggere |
| `--color-4` | `#bbe4e9` | Il più chiaro — badge attesa, sfondi molto tenui |
| `--slate-400` | `#94a3b8` | Etichette, label secondarie, section-title |
| `--slate-500` | `#64748b` | Testo secondario, icone |
| `--slate-600` | `#475569` | Testo normale |
| `--slate-700` | `#334155` | Testo corpo principale |
| `--slate-800` | `#1e293b` | Titoli |
| `--slate-900` | `#0f172a` | Titoli principali, intestazioni card |
| `--slate-200` | `#e2e8f0` | Bordi, divisori |
| `--slate-100` | `#f1f5f9` | Sfondi card-header neutri |
| `--slate-50` | `#f8fafc` | Sfondo pagina |

### 13.2 Bottoni — regola assoluta

**Un solo stile di bottone primario: blu con testo bianco (`btn-primary`).**

| Caso d'uso | Classe corretta | Mai usare |
|---|---|---|
| Azione principale (Salva, Invia, Conferma, Elabora) | `btn btn-primary` | `btn-success`, `btn-warning`, `btn-danger`, `btn-info` |
| Azione secondaria / alternativa | `btn btn-outline-secondary` | `btn-outline-success`, `btn-outline-warning`, `btn-outline-danger` |
| Link secondario nella palette brand | `btn btn-outline-primary` | qualsiasi `btn-outline-*` colorato |
| Export (Excel, PDF, CSV) | `btn btn-primary` o `btn btn-outline-primary` | bottoni verdi o rossi per tipo di file |
| Torna indietro / Annulla | `btn btn-outline-secondary` | — |
| Elimina (pagina di conferma) | `btn btn-primary` | `btn-danger` — anche eliminare usa il colore brand |

```django
{# CORRETTO #}
<a href="{% url 'app:oggetto-update' pk=obj.pk %}" class="btn btn-primary btn-sm">
  <i class="bi bi-pencil me-1"></i>Modifica
</a>
<a href="{% url 'app:export-excel' %}" class="btn btn-outline-primary btn-sm">
  <i class="bi bi-file-earmark-excel me-1"></i>Excel
</a>
<a href="{% url 'app:oggetto-list' %}" class="btn btn-outline-secondary btn-sm">
  <i class="bi bi-arrow-left me-1"></i>Torna alla lista
</a>

{# SBAGLIATO — vietato #}
<a href="..." class="btn btn-success btn-sm">Excel</a>
<a href="..." class="btn btn-outline-danger btn-sm">PDF</a>
<button class="btn btn-danger">Elimina</button>
```

### 13.3 Badge e etichette di stato

I badge non usano classi Bootstrap `bg-*` colorate. Usano le classi di stato definite in `main.css` oppure stili inline con variabili CSS.

**Classi disponibili in `main.css`:**

| Classe | Aspetto | Quando usarla |
|---|---|---|
| `badge-ok` | Blu chiaro / blu scuro | Approvata, Attivo, Confermata, Chiusa, Completato |
| `badge-ko` | Grigio chiaro / grigio scuro | Rifiutata, Disattivato, Annullata |
| `badge-wait` | Azzurrino / blu scuro | In attesa, Bozza, Da elaborare |
| `badge-info` | Blu chiaro / blu | Informativa, Aperta, Pomeriggio |
| `badge-staff` | Teal chiaro / teal scuro | Staff, Admin, Ruolo speciale |
| `badge-urgent` | Blu brand / bianco | Urgente, Alert, Priorità alta |
| `badge-accent` | Teal chiaro / teal scuro | Accent, Mattina, Notte (turni) |

```django
{# CORRETTO — usa le classi badge-* #}
<span class="badge badge-ok">Approvata</span>
<span class="badge badge-ko">Rifiutata</span>
<span class="badge badge-wait">In attesa</span>
<span class="badge badge-staff">Staff</span>

{# CORRETTO — stile inline solo con variabili CSS #}
<span class="badge" style="background:var(--color-1-light);color:var(--color-1-dark);font-size:.7rem;">
  Approvata
</span>

{# SBAGLIATO — vietato qualsiasi hex diretto #}
<span class="badge" style="background:#dcfce7;color:#166534;">Approvata</span>
<span class="badge bg-success">Approvata</span>
```

### 13.4 Colori inline — regola assoluta

Gli attributi `style=""` nei template possono contenere **solo** variabili CSS della palette. Zero valori esadecimali diretti.

```django
{# CORRETTO #}
<div style="color:var(--slate-500);font-size:.875rem;">Testo secondario</div>
<i class="bi bi-info-circle" style="color:var(--color-1);"></i>
<div style="background:var(--color-1-light);border:1px solid var(--color-4);">Alert info</div>

{# SBAGLIATO #}
<div style="color:#64748b;font-size:.875rem;">Testo secondario</div>
<i class="bi bi-info-circle" style="color:#3b82f6;"></i>
<div style="background:#eff6ff;border:1px solid #bfdbfe;">Alert info</div>
```

**Corrispondenze veloci** per le situazioni più comuni:

| Situazione | Variabile da usare |
|---|---|
| Testo principale di un paragrafo | `var(--slate-700)` |
| Testo secondario / caption | `var(--slate-500)` |
| Etichetta (label, th) | `var(--slate-400)` |
| Titolo card o sezione | `var(--slate-900)` |
| Icona brand | `var(--color-1)` |
| Icona accent / teal | `var(--color-2)` |
| Sfondo card-header neutro | `var(--slate-50)` |
| Bordo divisore | `var(--slate-200)` |
| Sfondo tinted brand | `var(--color-1-light)` |
| Sfondo tinted teal | `var(--color-2-light)` |
| Sfondo molto chiaro (attesa) | `var(--color-4)` |

### 13.5 Icone nei contenitori (tile e stat-card)

Usare le classi `icon-*` già definite nel CSS invece di stili inline con hex.

```django
{# CORRETTO #}
<div class="stat-card-icon icon-primary"><i class="bi bi-people"></i></div>
<div class="stat-card-icon icon-accent"><i class="bi bi-clock"></i></div>

{# CORRETTO anche inline ma solo con variabili #}
<div style="width:42px;height:42px;background:var(--color-1-light);color:var(--color-1);">
  <i class="bi bi-people"></i>
</div>

{# SBAGLIATO #}
<div style="width:42px;height:42px;background:#ede9fe;color:#7c3aed;">
  <i class="bi bi-people"></i>
</div>
```

Classi `icon-*` disponibili: `icon-primary`, `icon-accent`, `icon-sky`, `icon-emerald`, `icon-amber`, `icon-rose`, `icon-violet`, `icon-cyan`. Le ultime 6 esistono per retrocompatibilità con moduli easymod; nelle nuove app preferire `icon-primary` e `icon-accent`.

### 13.6 Titoli di sezione (section-title)

Il pattern per i titoli di sezione all'interno di una pagina (es. sopra una griglia di tile):

```django
{# Pattern standard — già usato in hr_dashboard e amministrazione_dashboard #}
<div class="hr-section-title">Nome sezione</div>
```

La classe `.hr-section-title` è definita localmente nei template che la usano tramite `{% block extra_css %}`. Per le nuove app, aggiungere la definizione nel proprio blocco CSS oppure estrarne il contenuto in `main.css` se usata in più di un'app.

### 13.7 Colori nei template PDF

I template PDF (renderizzati con xhtml2pdf) non caricano `main.css` e devono usare CSS inline nel tag `<style>`. Qui sono ammessi i valori esadecimali — ma devono comunque corrispondere ai colori della palette:

| Colore palette | Hex da usare nel PDF |
|---|---|
| `--color-1` (blu brand) | `#5585b5` |
| `--color-1-dark` | `#3d6a94` |
| `--color-1-light` | `#dce8f4` |
| `--slate-700` | `#334155` |
| `--slate-400` | `#94a3b8` |
| `--slate-200` | `#e2e8f0` |

### 13.8 Sidebar navigation

Ogni nuova app che aggiunge voci alla sidebar usa `register_nav()` nel metodo `ready()` dell'`AppConfig`. Il campo `order` determina la posizione:

| Ordine | Sezione |
|---|---|
| 5 | Amministrazione |
| 10 | Human Resource |
| 20 | Comunicazioni e Corrispondenza |
| 30+ | App aggiuntive (moduli) |

```python
# miaapp/apps.py
def ready(self):
    from core.sidebar import register_nav
    register_nav(
        section_key   = "miaapp",
        section_label = "Magazzino",
        items = [
            {
                "label": "Magazzino",
                "url":   "magazzino:index",
                "icon":  "bi-box-seam",
                "staff_only": False,
                "permission": "magazzino.view_prodotto",  # opzionale
                "active_app": "magazzino",
            },
        ],
        order = 30,
    )
```

### 13.9 Checklist dress code prima del commit

Prima di fare commit su qualsiasi template HTML rispondere:

- [ ] Nessun `btn-success`, `btn-danger`, `btn-warning`, `btn-info` nel file?
- [ ] Nessun `btn-outline-success/danger/warning/info`?
- [ ] Nessun colore esadecimale diretto in `style=""` (es. `#f59e0b`)?
- [ ] I badge di stato usano le classi `badge-*` o variabili CSS?
- [ ] Le icone brand usano `var(--color-1)`, non hex?
- [ ] I titoli e i testi grigi usano `var(--slate-*)`, non hex?

Verifica rapida da terminale (deve restituire output vuoto):

```bash
# Bottoni non conformi
grep -r "btn-success\|btn-danger\|btn-warning\|btn-outline-success\|btn-outline-danger\|btn-outline-warning" \
  --include="*.html" .

# Colori inline hex (esclude variabili CSS)
grep -r "style=" --include="*.html" . | grep "color:#\|background:#" | grep -v "var(--"
```

---

## 14. Template dettaglio oggetto

Il template di dettaglio è la pagina che mostra i dati di una singola istanza di un modello (es. un ordine, un dipendente, un documento). BASE definisce due layout standard: scegliere quello più adatto alla complessità dell'oggetto.

### 14.1 Quando usare quale layout

| Layout | Quando usarlo |
|---|---|
| **Layout A — due colonne** | Oggetti semplici con 1-3 sezioni di dati + azioni CRUD. È il default per la maggior parte delle nuove app. |
| **Layout B — header card + tab** | Oggetti complessi con molte sezioni (es. dipendente con presenze, ferie, documenti, payroll). Usarlo solo se le sezioni sono 4 o più. |

### 14.2 Layout A — due colonne (standard)

```
┌─────────────────────────────────────────────────────┐
│  Breadcrumb                                         │
│  Titolo oggetto                 [badge stato]       │
├────────────────────────────┬────────────────────────┤
│  CONTENUTO  col-lg-8       │  SIDEBAR  col-lg-4     │
│                            │                        │
│  ┌──────────────────────┐  │  ┌──────────────────┐  │
│  │ card: dati principali│  │  │ Azioni CRUD      │  │
│  └──────────────────────┘  │  │ [Modifica]       │  │
│                            │  │ [Torna alla lista]│  │
│  ┌──────────────────────┐  │  │ [Elimina]        │  │
│  │ card: sezione extra  │  │  └──────────────────┘  │
│  └──────────────────────┘  │                        │
│                            │  ┌──────────────────┐  │
│                            │  │ Metadati         │  │
│                            │  │ (creato il, da)  │  │
│                            │  └──────────────────┘  │
└────────────────────────────┴────────────────────────┘
```

**Template:**

```django
{% extends "base.html" %}

{% block title %}{{ oggetto }}{% endblock %}

{% block content %}

{# Breadcrumb #}
<nav class="mb-3" style="font-size:.8rem;">
  <a href="{% url 'miaapp:oggetto-list' %}" style="color:var(--color-1);text-decoration:none;">
    Lista oggetti
  </a>
  <i class="bi bi-chevron-right mx-1" style="color:var(--slate-400);"></i>
  <span style="color:var(--slate-500);">{{ oggetto }}</span>
</nav>

{# Intestazione #}
<div class="d-flex align-items-center justify-content-between mb-4">
  <div>
    <h4 class="fw-bold mb-1" style="color:var(--slate-900);">
      <i class="bi bi-box-seam me-2" style="color:var(--color-1);"></i>{{ oggetto }}
    </h4>
    <p class="text-muted mb-0" style="font-size:.875rem;">{{ oggetto.sottotitolo }}</p>
  </div>
  {# Badge stato — opzionale #}
  {% if oggetto.stato == 'attivo' %}
    <span class="badge badge-ok">Attivo</span>
  {% elif oggetto.stato == 'in_attesa' %}
    <span class="badge badge-wait">In attesa</span>
  {% else %}
    <span class="badge badge-ko">Chiuso</span>
  {% endif %}
</div>

<div class="row g-3">

  {# Colonna principale #}
  <div class="col-lg-8">
    <div class="card">
      <div class="card-header">
        <span class="fw-semibold" style="font-size:.875rem;color:var(--slate-900);">
          <i class="bi bi-info-circle me-2" style="color:var(--color-1);"></i>Dati principali
        </span>
      </div>
      <div class="card-body">
        <dl class="row mb-0" style="font-size:.875rem;">
          <dt class="col-sm-4" style="color:var(--slate-400);font-weight:500;">Campo 1</dt>
          <dd class="col-sm-8 mb-2" style="color:var(--slate-700);">{{ oggetto.campo1|default:"—" }}</dd>

          <dt class="col-sm-4" style="color:var(--slate-400);font-weight:500;">Campo 2</dt>
          <dd class="col-sm-8 mb-0" style="color:var(--slate-700);">{{ oggetto.campo2|default:"—" }}</dd>
        </dl>
      </div>
    </div>
  </div>

  {# Sidebar azioni #}
  <div class="col-lg-4">

    {# Card azioni CRUD #}
    <div class="card mb-3">
      <div class="card-header" style="background:var(--slate-50);">
        <span class="fw-semibold" style="font-size:.875rem;color:var(--slate-900);">Azioni</span>
      </div>
      <div class="card-body d-flex flex-column gap-2">
        {% if perms.miaapp.change_oggetto %}
        <a href="{% url 'miaapp:oggetto-update' pk=oggetto.pk %}" class="btn btn-primary btn-sm w-100">
          <i class="bi bi-pencil me-1"></i>Modifica
        </a>
        {% endif %}
        <a href="{% url 'miaapp:oggetto-list' %}" class="btn btn-outline-secondary btn-sm w-100">
          <i class="bi bi-arrow-left me-1"></i>Torna alla lista
        </a>
        {% if perms.miaapp.delete_oggetto %}
        <a href="{% url 'miaapp:oggetto-delete' pk=oggetto.pk %}" class="btn btn-outline-secondary btn-sm w-100">
          <i class="bi bi-trash me-1"></i>Elimina
        </a>
        {% endif %}
      </div>
    </div>

    {# Card metadati — opzionale, includere se il modello ha created_at #}
    <div class="card">
      <div class="card-header" style="background:var(--slate-50);">
        <span class="fw-semibold" style="font-size:.875rem;color:var(--slate-900);">Informazioni</span>
      </div>
      <div class="card-body">
        <dl class="mb-0" style="font-size:.82rem;">
          <dt style="color:var(--slate-400);font-weight:500;">Creato il</dt>
          <dd style="color:var(--slate-700);" class="mb-2">{{ oggetto.created_at|date:"d/m/Y H:i" }}</dd>
          <dt style="color:var(--slate-400);font-weight:500;">Modificato il</dt>
          <dd style="color:var(--slate-700);" class="mb-0">{{ oggetto.updated_at|date:"d/m/Y H:i" }}</dd>
        </dl>
      </div>
    </div>

  </div>
</div>

{% endblock %}
```

**View corrispondente:**

```python
# miaapp/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import DetailView
from .models import Oggetto


class OggettoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Oggetto
    template_name = "miaapp/oggetto_detail.html"
    context_object_name = "oggetto"
    permission_required = "miaapp.view_oggetto"
```

### 14.3 Layout B — header card + tab (per oggetti complessi)

Usare questo layout solo quando l'oggetto ha 4 o più sezioni distinte di dati. Il modello di riferimento in BASE è `users/templates/users/user_detail.html`.

```
┌──────────────────────────────────────────────────────────────────┐
│  HEADER — 4 card orizzontali (col-md-3 ciascuna)                 │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │ Identità   │  │ Dati rapidi│  │ Numeri/KPI │  │ Azioni     │  │
│  │ (foto/nome)│  │            │  │            │  │            │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│  TAB NAVIGATION                                                  │
│  [ Tab 1 ] [ Tab 2 ] [ Tab 3 ] [ Tab 4 ]                         │
├──────────────────────────────────────────────────────────────────┤
│  CONTENUTO DEL TAB ATTIVO (full width)                           │
└──────────────────────────────────────────────────────────────────┘
```

**Struttura di base:**

```django
{% extends "base.html" %}

{% block content %}

{# Breadcrumb #}
<nav class="mb-3" style="font-size:.8rem;">
  <a href="{% url 'miaapp:oggetto-list' %}" style="color:var(--color-1);text-decoration:none;">Lista</a>
  <i class="bi bi-chevron-right mx-1" style="color:var(--slate-400);"></i>
  <span style="color:var(--slate-500);">{{ oggetto }}</span>
</nav>

{# 4 card header #}
<div class="row g-3 mb-4 align-items-stretch">

  {# Card 1: Identità #}
  <div class="col-md-3">
    <div class="card card-body text-center h-100">
      {# avatar / icona grande / immagine #}
      <h6 class="fw-bold mb-0" style="color:var(--slate-900);">{{ oggetto }}</h6>
      <small class="text-muted">{{ oggetto.sottotitolo }}</small>
      <div class="mt-2">
        <span class="badge badge-ok">Attivo</span>
      </div>
    </div>
  </div>

  {# Card 2: Dati rapidi #}
  <div class="col-md-3">
    <div class="card card-body h-100">
      <h6 class="fw-semibold mb-3"
          style="font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:var(--slate-400);">
        Dati
      </h6>
      <div class="d-flex flex-column gap-2" style="font-size:.84rem;">
        <div class="d-flex align-items-center gap-2">
          <i class="bi bi-tag" style="color:var(--slate-400);width:16px;flex-shrink:0;"></i>
          <span style="color:var(--slate-600);">{{ oggetto.codice }}</span>
        </div>
        {# ... altri dati rapidi ... #}
      </div>
    </div>
  </div>

  {# Card 3: KPI / numeri #}
  <div class="col-md-3">
    <div class="card card-body h-100">
      <h6 class="fw-semibold mb-3"
          style="font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:var(--slate-400);">
        Statistiche
      </h6>
      <div class="d-flex flex-column gap-2" style="font-size:.84rem;">
        <div class="d-flex justify-content-between">
          <span style="color:var(--slate-500);">Voce 1</span>
          <strong style="color:var(--slate-800);">{{ valore_1 }}</strong>
        </div>
      </div>
    </div>
  </div>

  {# Card 4: Azioni #}
  <div class="col-md-3">
    <div class="card card-body h-100 d-flex flex-column justify-content-center gap-2">
      <h6 class="fw-semibold mb-1"
          style="font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:var(--slate-400);">
        Azioni
      </h6>
      {% if perms.miaapp.change_oggetto %}
      <a href="{% url 'miaapp:oggetto-update' oggetto.pk %}" class="btn btn-primary btn-sm w-100">
        <i class="bi bi-pencil me-1"></i>Modifica
      </a>
      {% endif %}
      <a href="{% url 'miaapp:oggetto-list' %}" class="btn btn-outline-secondary btn-sm w-100">
        <i class="bi bi-arrow-left me-1"></i>Torna alla lista
      </a>
    </div>
  </div>

</div>

{# Tab navigation — il tab attivo è passato dalla view come ?tab=nome #}
<ul class="nav nav-tabs mb-3" style="border-bottom:2px solid var(--slate-100);">
  <li class="nav-item">
    <a class="nav-link {% if tab == 'info' or not tab %}active{% endif %}"
       href="?tab=info" style="font-size:.875rem;">
      <i class="bi bi-info-circle me-1"></i>Informazioni
    </a>
  </li>
  <li class="nav-item">
    <a class="nav-link {% if tab == 'sezione2' %}active{% endif %}"
       href="?tab=sezione2" style="font-size:.875rem;">
      <i class="bi bi-list-ul me-1"></i>Sezione 2
    </a>
  </li>
</ul>

{# Contenuto tab #}
{% if tab == 'info' or not tab %}
<div class="row g-3">
  {# contenuto scheda info #}
</div>
{% endif %}

{% if tab == 'sezione2' %}
{# contenuto scheda sezione 2 #}
{% endif %}

{% endblock %}
```

**View per il layout B:**

```python
class OggettoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Oggetto
    template_name = "miaapp/oggetto_detail.html"
    context_object_name = "oggetto"
    permission_required = "miaapp.view_oggetto"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tab"] = self.request.GET.get("tab", "info")
        # aggiungere dati necessari per i vari tab
        return ctx
```

### 14.4 Pagina di conferma eliminazione

Ogni `confirm_delete.html` segue questo schema fisso:

```django
{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center mt-4">
  <div class="col-md-6">
    <div class="card">
      <div class="card-header">
        <span class="fw-semibold" style="color:var(--slate-900);">Conferma eliminazione</span>
      </div>
      <div class="card-body text-center py-4">
        <div class="mb-3" style="color:var(--slate-400);font-size:3rem;">
          <i class="bi bi-trash"></i>
        </div>
        <h5 class="fw-bold mb-2" style="color:var(--slate-900);">Elimina {{ object }}</h5>
        <p class="text-muted mb-4" style="font-size:.875rem;">
          Questa operazione è irreversibile.
        </p>
        <form method="post" class="d-flex justify-content-center gap-2">
          {% csrf_token %}
          <a href="{{ request.META.HTTP_REFERER|default:back_url }}"
             class="btn btn-outline-secondary">
            <i class="bi bi-x-lg me-1"></i>Annulla
          </a>
          <button type="submit" class="btn btn-primary">
            <i class="bi bi-trash me-1"></i>Sì, elimina
          </button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

Nessun `btn-danger` nemmeno nella conferma eliminazione — il dress code è uniforme ovunque.

### 14.5 Pagina lista (list view)

Schema standard per le pagine lista:

```django
{% extends "base.html" %}

{% block content %}

{# Intestazione con pulsante aggiunta #}
<div class="d-flex align-items-center justify-content-between mb-4">
  <div>
    <h4 class="fw-bold mb-1" style="color:var(--slate-900);">
      <i class="bi bi-list-ul me-2" style="color:var(--color-1);"></i>Oggetti
    </h4>
    <p class="text-muted mb-0" style="font-size:.875rem;">{{ object_list.count }} record</p>
  </div>
  {% if perms.miaapp.add_oggetto %}
  <a href="{% url 'miaapp:oggetto-create' %}" class="btn btn-primary btn-sm">
    <i class="bi bi-plus-lg me-1"></i>Nuovo
  </a>
  {% endif %}
</div>

{# Filtri (opzionale) #}
{# ... form di ricerca/filtro ... #}

{# Tabella #}
<div class="table-card">
  <div class="table-responsive">
    <table class="table mb-0">
      <thead>
        <tr>
          <th>Campo 1</th>
          <th>Stato</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {% for obj in object_list %}
        <tr>
          <td style="font-size:.875rem;">{{ obj }}</td>
          <td><span class="badge badge-ok">{{ obj.stato }}</span></td>
          <td class="text-end">
            <a href="{{ obj.get_absolute_url }}" class="btn btn-outline-secondary btn-sm">
              <i class="bi bi-eye me-1"></i>Dettaglio
            </a>
          </td>
        </tr>
        {% empty %}
        <tr>
          <td colspan="3" class="text-center py-5" style="color:var(--slate-400);">
            <i class="bi bi-inbox" style="font-size:2rem;display:block;margin-bottom:.5rem;"></i>
            Nessun elemento trovato
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

{# Paginazione (Bootstrap standard, funziona col CSS del progetto) #}
{% if is_paginated %}
<nav class="mt-3">
  <ul class="pagination pagination-sm">
    {% if page_obj.has_previous %}
    <li class="page-item">
      <a class="page-link" href="?page={{ page_obj.previous_page_number }}">‹</a>
    </li>
    {% endif %}
    {% for num in page_obj.paginator.page_range %}
    <li class="page-item {% if page_obj.number == num %}active{% endif %}">
      <a class="page-link" href="?page={{ num }}">{{ num }}</a>
    </li>
    {% endfor %}
    {% if page_obj.has_next %}
    <li class="page-item">
      <a class="page-link" href="?page={{ page_obj.next_page_number }}">›</a>
    </li>
    {% endif %}
  </ul>
</nav>
{% endif %}

{% endblock %}
```

### 14.6 Form standard

```django
{% extends "base.html" %}

{% block content %}

<div class="row justify-content-center">
  <div class="col-lg-8">

    {# Intestazione #}
    <div class="mb-4">
      <h4 class="fw-bold mb-1" style="color:var(--slate-900);">
        <i class="bi bi-pencil-square me-2" style="color:var(--color-1);"></i>
        {% if object %}Modifica{% else %}Nuovo{% endif %} oggetto
      </h4>
    </div>

    <div class="card">
      <div class="card-body">
        <form method="post" enctype="multipart/form-data" novalidate>
          {% csrf_token %}

          {% for field in form %}
          <div class="mb-3">
            <label for="{{ field.id_for_label }}" class="form-label">
              {{ field.label }}{% if field.field.required %} *{% endif %}
            </label>
            {{ field }}
            {% if field.errors %}
            <div class="invalid-feedback d-block">{{ field.errors|join:", " }}</div>
            {% endif %}
            {% if field.help_text %}
            <div class="form-text" style="color:var(--slate-400);">{{ field.help_text }}</div>
            {% endif %}
          </div>
          {% endfor %}

          <div class="d-flex gap-2 mt-4">
            <button type="submit" class="btn btn-primary">
              <i class="bi bi-check-lg me-1"></i>Salva
            </button>
            <a href="{% url 'miaapp:oggetto-list' %}" class="btn btn-outline-secondary">
              Annulla
            </a>
          </div>
        </form>
      </div>
    </div>

  </div>
</div>

{% endblock %}
```

### 14.7 Checklist template per nuova app

Prima di considerare completata l'integrazione dei template di una nuova app, verificare:

- [ ] Tutti i template estendono `base.html`
- [ ] Breadcrumb presente in `detail`, `form` e `confirm_delete`
- [ ] Intestazione pagina con icona `bi-*` e `color:var(--color-1)`
- [ ] Titoli con `color:var(--slate-900)`, testi con `color:var(--slate-700)`
- [ ] Etichette/label con `color:var(--slate-400)` o `color:var(--slate-500)`
- [ ] Nessun `btn-success / btn-danger / btn-warning` — solo `btn-primary` e `btn-outline-secondary`
- [ ] Badge di stato con classi `badge-ok / badge-ko / badge-wait` o variabili CSS
- [ ] Export (Excel/PDF) con `btn-primary` o `btn-outline-primary`
- [ ] Pagina lista con stato vuoto (`{% empty %}`) gestito visivamente
- [ ] Pagina `confirm_delete` con `btn-primary` (non `btn-danger`)
- [ ] Dress code check da terminale (sezione 13.9) restituisce output vuoto

---

*Fine del manuale tecnico. Per segnalare errori o proporre integrazioni, aprire una issue nel repository del progetto.*
