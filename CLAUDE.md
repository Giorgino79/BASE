# CLAUDE.md — RATTUS26

> Questo file è la fonte di verità specifica del **prodotto** rattus26 (gestionale
> per aziende di disinfestazione/pest-control). Il `MANUALE_TECNICO.md` in questa
> stessa cartella è invece la documentazione del template generico **BASE**
> condiviso con altri progetti (vedi `/home/giorgio/Scrivania/APPLICAZIONI RIUTILIZZABILI/`)
> — copre solo `core`/`users`/`comunicazioni`/`corrispondenza` e va tenuto
> generico: non aggiungerci contenuti specifici di rattus26.

---

## IDENTITÀ PROGETTO

| Campo | Valore |
|-------|--------|
| **Prodotto** | rattus26 — gestionale per aziende di disinfestazione/pest-control |
| **Mercato** | Separato e non collegato a em26 (ModularBEF) — **non bridgare mai utenti tra i due prodotti** |
| **Framework** | Django 5.2 / Python 3.12 |
| **Working dir** | `/home/giorgio/Scrivania/RATTUS26/r_26/` |
| **Django project** | `config/` (settings, urls) |
| **App reali** | 15, elencate in `config/settings.py::INSTALLED_APPS` |

---

## STRUTTURA APP — MAPPA REALE (22/08/2026)

### Moduli core (obbligatori)

| App | Ruolo | Note critiche |
|-----|-------|---------------|
| `core` | Mixin, allegati, PDF, permessi, calendario, module_manager | Base per tutti gli altri |
| `users` | Auth, timbrature, ferie, permessi, payroll-adiacente | Modello User custom |
| `anagrafica_r2` | Clienti (Azienda/Privato) e Fornitori | **Namespace URL storico `anagrafica`, diverso dal vero app label `anagrafica_r2`** — vedi sotto |

### Moduli opzionali (vendibili)

`comunicazioni`, `corrispondenza`, `payroll`, `cespiti`, `acquisti`, `magazzino`, `servizi`, `installazioni`, `analysis`, `portale`, `fatturazione_attiva`, `contabilita`.

**Attenzione:** a differenza di em26, questi moduli hanno un accoppiamento reale
molto più denso (non solo incidentale). Esempio concreto: vendere solo
`servizi` + `fatturazione_attiva` trascina in automatico anche `acquisti`,
`cespiti`, `comunicazioni`, `contabilita`, `magazzino`, `portale` (11 moduli su
15 totali) — verificabile con `python manage.py package_client --modules
servizi,fatturazione_attiva --dry-run`. Prima di promettere a un cliente "solo
il modulo X", controllare sempre con `--dry-run` cosa si trascina davvero.

**`anagrafica_r2` vs namespace URL `anagrafica`:** `anagrafica_r2/urls.py`
dichiara `app_name = 'anagrafica'` (storico, usato in centinaia di
`{% url 'anagrafica:...' %}` nei template — non rinominabile senza un
refactor enorme). Il vero Django app label (usato in `INSTALLED_APPS`,
`module_manager.py`, `ModuloRegistry`) è `anagrafica_r2`. `core/middleware.py`
gestisce l'alias esplicitamente (`_URL_NAMESPACE_ALIASES`) — se si aggiungono
nuovi punti che confrontano `request.resolver_match.app_name` con l'app label
Django, ricordarsi di questo disallineamento.

---

## DIPENDENZE TRA APP

**Fonte di verità: `core/module_manager.py::MODULE_DEPENDENCIES`** — riscritto
il 22/08/2026 da un audit sistematico (import diretti + import locali/funzione
su tutti i file non-migration). Prima di questa data il file era una copia
letterale mai adattata di quello di em26: citava app inesistenti in rattus26 e
non dichiarava nessuna delle 15 app reali. Non fidarsi di grafi disegnati a
mano nella documentazione — usare sempre `python manage.py check_modules`.

Diverse coppie sono bidirezionali di proposito (`acquisti`↔`magazzino`,
`acquisti`↔`contabilita`, `cespiti`↔`magazzino`, `cespiti`↔`servizi`,
`magazzino`↔`servizi`, `comunicazioni`↔`servizi`, `servizi`↔`portale`): il
dizionario esprime "vanno installati insieme", non un grafo aciclico — un
ciclo qui non è un bug, è stato verificato che entrambi i lati usano import
locali (nessun rischio di ImportError circolare Python).

`users/views.py::dashboard_view` e `anagrafica_r2/views.py::PrivatoDetailView`
leggono da `comunicazioni`/`servizi` (moduli opzionali) ma sono protetti da
try/except con degradazione elegante (0/liste vuote se il modulo non è
installato) — per questo `comunicazioni` e `servizi` NON sono dichiarati come
dipendenze di `users`/`anagrafica_r2` in `module_manager.py`: dichiararli
renderebbe quei moduli opzionali obbligatori per sempre, dato che `users` e
`anagrafica_r2` sono core.

---

## SISTEMA GATING MODULI (attivazione/disattivazione a runtime)

Stesso sistema introdotto in em26 il 22/08/2026, portato qui lo stesso giorno:

- **`core/models_legacy.py::ModuloRegistry`** — modello DB (esisteva già,
  copiato da em26, era orfano) con `codice`, `app_name`, `attivo`,
  `obbligatorio`, `dipendenze`. Fonte di verità per "questo modulo è attivo su
  QUESTA installazione".
- **`core/module_gating.py::get_active_modules()`/`is_module_active(app_name)`**
  — cache 5 min. **Se `ModuloRegistry` non ha righe, ritorna `None` = nessun
  filtro, tutto attivo**: default di sicurezza, zero cambi di comportamento
  finché nessuno cura il registry esplicitamente.
- **`core/middleware.py::ModuleGatingMiddleware`** — blocca (404) le richieste
  verso app disattivate. **Attiva solo se `settings.MODULE_GATING_ENABLED` è
  `True`** (env var, default `False`). Gestisce l'alias `anagrafica` →
  `anagrafica_r2` (vedi sopra) per non bloccare per errore il modulo clienti.
- `core/sidebar.py::get_sections()` e `core/search.py::SearchRegistry.search_all()`
  filtrano automaticamente le voci/risultati delle app disattivate (fail-open).
  `core/calendario_registry.py::CalendarioRegistry.register()` ha un parametro
  opzionale `app_name` per lo stesso filtro — nessun provider lo passa ancora
  oggi, quindi il calendario non filtra nulla finché non viene aggiunto ai
  singoli `register()` esistenti.
- **`python manage.py sync_module_registry [--database X]`** — crea le righe
  mancanti in `ModuloRegistry` (`attivo=True` di default). Idempotente, non
  tocca mai `attivo` su righe esistenti.
- **`python manage.py package_client --modules mod1,mod2,... [--database X] [--dry-run]`**
  — dato l'elenco moduli acquistati da un cliente, calcola le dipendenze
  transitive (vedi sopra: possono essere molte più del previsto) e aggiorna
  `ModuloRegistry` sul DB target. **Non fa** branding, packaging, o deploy —
  solo lo stato dei moduli.

**Prima di attivare `MODULE_GATING_ENABLED=True` su un'installazione reale**,
verificare su un dump locale/ambiente non di produzione — stesso avvertimento
dato per em26.

---

## TEST

Al 22/08/2026 il progetto ha un solo test (`core.tests.ModuleDependencyGraphTest`,
aggiunto in questa sessione) — nessuna copertura preesistente su nessuna delle
15 app di business. Non è un problema introdotto da questo lavoro, è lo stato
di partenza: da tenere presente prima di refactoring futuri, non c'è una rete
di sicurezza automatica oltre a `python manage.py check` e `check_modules`.

---

*Ultima modifica: 22/08/2026*
