# MANUALE UTENTE — Sistema Gestionale BASE

**Versione:** 1.0  
**Destinatari:** Dipendenti e Amministratori  
**Piattaforma:** Applicazione web (Django)

---

## Indice

1. [Introduzione e accesso](#1-introduzione-e-accesso)
2. [Dashboard](#2-dashboard)
3. [Area Dipendenti](#3-area-dipendenti)
   - [Lista dipendenti (Staff)](#31-lista-dipendenti-solo-staff)
   - [Scheda dipendente](#32-scheda-dipendente)
   - [Timbrature](#33-timbrature)
   - [Ferie e Permessi](#34-ferie-e-permessi)
   - [Gestione richieste (Staff)](#35-gestione-richieste-solo-staff)
   - [Lettere di richiamo (Staff)](#36-lettere-di-richiamo-solo-staff)
4. [Calendari](#4-calendari)
   - [Calendario Aziendale](#41-calendario-aziendale)
   - [Calendario Personale](#42-calendario-personale)
5. [Promemoria](#5-promemoria)
6. [Chat](#6-chat)
7. [Corrispondenza](#7-corrispondenza)
8. [Calcolatrice](#8-calcolatrice)
9. [Profilo e Account](#9-profilo-e-account)
10. [Note per gli amministratori](#10-note-per-gli-amministratori)

---

## 1. Introduzione e Accesso

BASE è il sistema gestionale aziendale che centralizza la gestione del personale, le comunicazioni interne, il calendario aziendale e gli strumenti di lavoro quotidiano.

### Tipi di utente

Il sistema prevede due livelli di accesso:

- **Dipendente normale**: accede alle funzionalità personali — timbrature, ferie e permessi, calendario personale, chat, promemoria.
- **Staff / Amministratore**: accede a tutte le funzionalità del dipendente normale, più la gestione degli altri dipendenti, l'approvazione delle richieste, il calendario aziendale, la corrispondenza e le lettere di richiamo.

### Come accedere

1. Aprire il browser e navigare all'indirizzo fornito dall'amministratore di sistema.
2. Inserire il proprio **nome utente** e **password** nei campi della pagina di login.
3. Cliccare su **Accedi**.

Se si dimentica la password, contattare l'amministratore di sistema per il ripristino. In alternativa, se abilitata, è disponibile la funzione **"Password dimenticata?"** nella pagina di login.

### Uscita dal sistema

Per uscire in modo sicuro, cliccare sul proprio nome utente in alto a destra e selezionare **Esci** (Logout). Non chiudere semplicemente il browser senza effettuare il logout, specialmente su computer condivisi.

---

## 2. Dashboard

**Come accedere:** La dashboard è la prima schermata visualizzata dopo il login. È raggiungibile in qualsiasi momento cliccando sul logo o sulla voce **Dashboard** nel menu laterale.

### Cosa si vede

La dashboard offre una panoramica immediata dello stato del sistema con i seguenti elementi:

**Stat Cards (riquadri statistici)**

- **Dipendenti attivi**: numero totale di dipendenti attualmente attivi in azienda. Visibile solo allo staff.
- **Ore oggi**: totale ore lavorate oggi da tutti i dipendenti (staff) o le proprie ore odierne (dipendente normale).
- **Richieste in attesa**: numero di richieste ferie/permessi ancora da elaborare. Per lo staff mostra tutte le richieste; per il dipendente mostra solo le proprie.

**Timbrature di oggi**

Elenco delle timbrature registrate nella giornata corrente. Per ogni timbratura viene mostrato: dipendente, orario di ingresso, orario di uscita (se già timbrато), turno. Lo staff vede tutte le timbrature del giorno; i dipendenti vedono solo le proprie.

**Richieste in attesa**

Elenco rapido delle richieste ferie/permessi che necessitano attenzione. Per lo staff mostra le richieste da approvare o rifiutare; per il dipendente mostra le proprie richieste ancora in attesa di risposta.

**Prossimi eventi calendario**

Visualizza i prossimi eventi del calendario aziendale e personale, con data, titolo e tipo di evento.

**Accessi rapidi**

Pulsanti di scorciatoia per le operazioni più frequenti: nuova timbratura, nuova richiesta ferie, nuovo promemoria, nuova chat.

---

## 3. Area Dipendenti

### 3.1 Lista Dipendenti (solo Staff)

**Come accedere:** Menu laterale → **Dipendenti** → **Lista dipendenti**

Questa sezione è riservata allo staff e agli amministratori.

**Cosa si vede**

L'elenco completo dei dipendenti aziendali in formato tabellare con: foto profilo, nome e cognome, ruolo, reparto, stato (attivo/non attivo), data di assunzione.

**Strumenti disponibili**

- **Ricerca**: campo di testo in cima alla lista. Digitare il nome, cognome o codice fiscale per filtrare i risultati in tempo reale.
- **Filtro per stato**: selezionare **Attivi**, **Non attivi** o **Tutti** tramite i pulsanti filtro sopra la lista.
- **Paginazione**: se i dipendenti sono numerosi, la lista è suddivisa in pagine. Usare i controlli di navigazione in fondo alla pagina.

**Cosa si può fare**

- Cliccare su un dipendente per aprire la sua scheda dettaglio.
- Cliccare su **Aggiungi dipendente** per inserire un nuovo dipendente nel sistema (solo amministratori).

---

### 3.2 Scheda Dipendente

**Come accedere:** Cliccare sul nome di un dipendente dalla lista, oppure navigare su **Il mio profilo** per vedere la propria scheda.

**Cosa si vede**

La scheda è divisa in più sezioni:

- **Dati anagrafici**: nome, cognome, data di nascita, codice fiscale, indirizzo, contatti.
- **Dati lavorativi**: ruolo, reparto, data di assunzione, tipo di contratto, orario di lavoro.
- **Storico timbrature**: elenco cronologico di tutte le timbrature del dipendente con filtri per data.
- **Storico richieste**: elenco di tutte le richieste ferie/permessi con relativo stato (in attesa, approvata, rifiutata).

Lo staff ha visibilità completa su tutte le sezioni di qualsiasi dipendente. Il dipendente normale vede solo la propria scheda.

---

### 3.3 Timbrature

**Come accedere:** Menu laterale → **Timbrature**, oppure dal pulsante rapido in dashboard.

**Registrare ingresso o uscita**

1. Accedere alla sezione Timbrature.
2. Cliccare su **Timbra Ingresso** all'inizio del turno, oppure **Timbra Uscita** al termine.
3. Il sistema registra automaticamente l'orario corrente e il turno di appartenenza (mattina, pomeriggio, notte) in base all'ora di registrazione.
4. Una conferma visiva viene mostrata a schermo dopo la registrazione.

**Nota:** Non è possibile registrare due ingressi consecutivi senza un'uscita intermedia.

**Visualizzare lo storico**

Nella stessa pagina, sotto il pannello di timbratura, è presente lo storico delle timbrature personali. Sono disponibili i seguenti filtri:

- **Intervallo di date**: selezionare data inizio e data fine per visualizzare le timbrature di un periodo specifico.
- **Turno**: filtrare per mattina, pomeriggio o notte.

Per ogni timbratura vengono mostrati: data, orario ingresso, orario uscita, durata totale, turno.

**Staff:** Lo staff può visualizzare e modificare le timbrature di tutti i dipendenti dalla scheda del singolo dipendente o dalla lista timbrature generale.

---

### 3.4 Ferie e Permessi

**Come accedere:** Menu laterale → **Ferie e Permessi**, oppure dal pulsante rapido in dashboard o dal calendario personale.

**Fare una nuova richiesta**

1. Cliccare su **Nuova Richiesta**.
2. Selezionare il **tipo di richiesta**: Ferie, Permesso orario, Permesso giornaliero, Malattia, ecc.
3. Inserire la **data di inizio** e la **data di fine** (per ferie multi-giorno) oppure l'**orario** (per i permessi orari).
4. Aggiungere eventuali **note** o motivazioni nel campo testo.
5. Cliccare su **Invia Richiesta**.

La richiesta viene registrata con stato **In attesa** e sarà visibile allo staff per l'approvazione.

**Stati delle richieste**

| Stato | Descrizione |
|---|---|
| In attesa | La richiesta è stata inviata e attende valutazione dello staff |
| Approvata | La richiesta è stata accettata dall'amministratore |
| Rifiutata | La richiesta è stata respinta; consultare la motivazione indicata |

**Storico richieste**

In fondo alla pagina o nella scheda personale è disponibile l'elenco di tutte le richieste inviate con relativo stato, date e note dello staff in caso di rifiuto.

---

### 3.5 Gestione Richieste (solo Staff)

**Come accedere:** Menu laterale → **Gestione Richieste** oppure dal riquadro **Richieste in attesa** in dashboard.

**Cosa si vede**

Elenco di tutte le richieste ferie/permessi ricevute dai dipendenti, suddivise per stato. In cima vengono mostrate le richieste **In attesa** che necessitano di azione.

**Approvare una richiesta**

1. Cliccare sulla richiesta da valutare per aprire il dettaglio.
2. Verificare le informazioni: dipendente, tipo di richiesta, date, note del dipendente.
3. Cliccare su **Approva** per accettare la richiesta.
4. Il dipendente riceverà una notifica del cambio di stato.

**Rifiutare una richiesta**

1. Aprire il dettaglio della richiesta.
2. Cliccare su **Rifiuta**.
3. Inserire obbligatoriamente una **motivazione** nel campo testo: questa sarà visibile al dipendente.
4. Confermare il rifiuto.

**Nota:** Un'azione di approvazione o rifiuto non può essere annullata direttamente. Per correggere un errore, contattare l'amministratore di sistema.

---

### 3.6 Lettere di Richiamo (solo Staff)

**Come accedere:** Menu laterale → **Dipendenti** → **Lettere di Richiamo**

**Cosa si vede**

Elenco di tutte le lettere di richiamo emesse, con: data emissione, dipendente destinatario, oggetto, stato.

**Creare una nuova lettera di richiamo**

1. Cliccare su **Nuova Lettera di Richiamo**.
2. Selezionare il **dipendente** destinatario dall'elenco.
3. Inserire l'**oggetto** del richiamo.
4. Compilare il **testo** della lettera nel campo dedicato.
5. Cliccare su **Salva** per registrare la lettera.

La lettera viene associata alla scheda del dipendente e risulta visibile nello storico del dipendente interessato.

---

## 4. Calendari

### 4.1 Calendario Aziendale

**Come accedere:** Menu laterale → **Calendario** → **Calendario Aziendale**

**Cosa si vede**

Un calendario interattivo (FullCalendar) che mostra tutti gli eventi aziendali: riunioni, scadenze, eventi di team, giornate di chiusura, ecc.

Sono disponibili tre modalità di visualizzazione selezionabili in alto a destra:

- **Mese**: panoramica mensile con gli eventi del mese.
- **Settimana**: vista settimanale dettagliata con orari.
- **Lista**: elenco testuale degli eventi in ordine cronologico.

Per navigare tra i periodi usare i pulsanti **Precedente** e **Successivo**, oppure cliccare su **Oggi** per tornare alla data corrente.

**Visualizzare un evento**

Cliccare su qualsiasi evento nel calendario per aprire il pannello dettaglio con: titolo, data e ora, descrizione, autore.

**Creare un evento (solo Staff)**

1. Cliccare su un giorno del calendario (nella vista mese) oppure su una fascia oraria (nella vista settimana).
2. Si aprirà il modulo di creazione evento.
3. Compilare: titolo, data/ora inizio, data/ora fine, descrizione, colore identificativo.
4. Cliccare su **Salva evento**.

L'evento sarà immediatamente visibile a tutti gli utenti nel calendario aziendale.

**Modificare o eliminare un evento (solo Staff)**

Cliccare sull'evento esistente e selezionare **Modifica** o **Elimina** dal pannello dettaglio.

---

### 4.2 Calendario Personale

**Come accedere:** Menu laterale → **Calendario** → **Calendario Personale**

**Cosa si vede**

Un calendario personale, visibile solo all'utente proprietario, che mostra gli eventi privati creati dall'utente. Gli eventi del calendario personale non sono visibili agli altri dipendenti né allo staff.

**Aggiungere un evento personale**

1. Cliccare su un giorno nel calendario personale.
2. Compilare il modulo: titolo, data, ora, note.
3. Cliccare su **Aggiungi**.

**Link rapido richiesta ferie**

Nel calendario personale è presente un pulsante **Richiedi Ferie** che porta direttamente al modulo di richiesta ferie/permessi, precompilando le date selezionate nel calendario.

---

## 5. Promemoria

**Come accedere:** Menu laterale → **Comunicazioni** → **Promemoria**

I promemoria sono note personali o assegnate ad altri utenti, con possibilità di impostare una scadenza e un livello di priorità.

### Cosa si vede

L'elenco dei promemoria è organizzato con filtri rapidi in cima:

- **Attivi**: mostra solo i promemoria non ancora completati.
- **Completati**: mostra i promemoria contrassegnati come completati.
- **Tutti**: mostra l'intera lista senza filtri.

Per ogni promemoria vengono mostrati: titolo, priorità (con badge colorato), data di scadenza, assegnatario, stato completamento.

### Priorità e badge colorati

| Priorità | Colore badge |
|---|---|
| Bassa | Verde |
| Media | Giallo |
| Alta | Arancione |
| Urgente | Rosso |

Se la data di scadenza di un promemoria è già passata e il promemoria non è ancora completato, viene mostrato un badge **Scaduto** in rosso accanto alla data.

### Creare un nuovo promemoria

1. Cliccare su **Nuovo Promemoria**.
2. Compilare: titolo, descrizione (facoltativa), data di scadenza, livello di priorità.
3. Selezionare l'**assegnatario**: è possibile assegnare il promemoria a se stessi o a un altro utente del sistema.
4. Cliccare su **Salva**.

### Completare un promemoria

Nella lista, ogni promemoria ha una **checkbox** a sinistra. Cliccandola si alterna lo stato tra completato e non completato senza ricaricare la pagina (operazione AJAX). Un promemoria completato viene visivamente barrato o spostato nella sezione Completati.

---

## 6. Chat

**Come accedere:** Menu laterale → **Comunicazioni** → **Chat**

### Cosa si vede

La pagina principale della chat mostra l'elenco di tutte le conversazioni attive dell'utente: chat dirette (1-1) e conversazioni di gruppo. Per ogni conversazione viene mostrato: nome/partecipanti, anteprima dell'ultimo messaggio, orario, numero di messaggi non letti (badge numerico).

### Aprire una conversazione

Cliccare su una conversazione dall'elenco per aprire la finestra di chat. I messaggi vengono mostrati in ordine cronologico. I messaggi dell'utente corrente appaiono a destra; quelli degli altri partecipanti a sinistra.

### Inviare un messaggio

1. Digitare il testo nel campo di input in fondo alla finestra di chat.
2. Premere **Invio** oppure cliccare sul pulsante **Invia**.

Il messaggio viene inviato e visualizzato immediatamente nella conversazione.

### Aggiornamento automatico

La chat effettua un **polling automatico ogni 3 secondi**: i nuovi messaggi degli altri partecipanti vengono caricati e visualizzati automaticamente senza dover ricaricare la pagina.

### Creare una nuova conversazione

1. Cliccare su **Nuova Chat**.
2. Selezionare il **tipo di conversazione**:
   - **Diretta (1-1)**: conversazione privata con un singolo utente.
   - **Gruppo**: conversazione con più partecipanti.
3. Selezionare i **destinatari** dall'elenco degli utenti disponibili.
4. Per le chat di gruppo, assegnare un **nome al gruppo**.
5. Cliccare su **Crea**.

La nuova conversazione viene aperta immediatamente.

---

## 7. Corrispondenza

**Come accedere:** Menu laterale → **Corrispondenza**

La sezione Corrispondenza gestisce le lettere e comunicazioni ufficiali dell'azienda, con un sistema di protocollo automatico e workflow di approvazione.

### Cosa si vede

In cima alla pagina sono presenti **statistiche riepilogative**: numero totale lettere, lettere in bozza, lettere inviate, lettere archiviate.

L'elenco delle lettere è filtrabile tramite:

- **Stato**: Bozza, Inviata, Archiviata.
- **Priorità**: Bassa, Normale, Alta, Urgente.
- **Intervallo di date**: filtra per data di creazione o invio.
- **Ricerca testo libero**: cerca nel titolo, oggetto o contenuto della lettera.

### Creare una nuova lettera

1. Cliccare su **Nuova Lettera**.
2. Compilare i campi:
   - **Oggetto**: titolo della comunicazione.
   - **Tipo**: lettera, circolare, nota interna, ecc.
   - **Priorità**: selezionare il livello di priorità.
   - **Contenuto**: testo completo della lettera.
3. Selezionare il **destinatario**:
   - **Utente interno**: selezionare dall'elenco dei dipendenti del sistema.
   - **Esterno**: inserire manualmente nome, cognome, indirizzo e altri dati anagrafici del destinatario esterno.
4. Aggiungere eventuali **note interne** nel campo dedicato (visibili solo internamente, non incluse nel PDF stampato).
5. Cliccare su **Salva come bozza** per salvare senza inviare, oppure **Salva e Invia** per procedere direttamente all'invio.

Il sistema assegna automaticamente un **numero di protocollo** nel formato `CORyyyyNNNN` (dove `yyyy` è l'anno e `NNNN` il numero progressivo).

### Workflow della corrispondenza

Le lettere seguono un percorso di stato preciso:

```
Bozza → Inviata → Archiviata
```

- **Bozza**: la lettera è stata creata ma non ancora inviata. Può essere modificata.
- **Inviata**: la lettera è stata inviata. Non può più essere modificata direttamente.
- **Archiviata**: la lettera è stata archiviata per conservazione storica.

### Azioni disponibili

Per ogni lettera, in base al suo stato, sono disponibili le seguenti azioni:

| Azione | Disponibile quando | Descrizione |
|---|---|---|
| Modifica | Solo in stato Bozza | Apre il modulo di modifica della lettera |
| Duplica | Sempre | Crea una nuova bozza con gli stessi contenuti |
| Scarica PDF | Sempre | Genera e scarica la lettera in formato PDF (senza note interne) |
| Invia email | Sempre | Invia la lettera per email all'indirizzo del destinatario |
| Archivia | Quando Inviata | Sposta la lettera nello stato Archiviata |

**Note interne:** Il campo note interne è pensato per annotazioni a uso esclusivo del personale interno (es. "verificare con il legale prima dell'invio"). Queste note non vengono mai incluse nel PDF generato né nell'email inviata al destinatario.

---

## 8. Calcolatrice

**Come accedere:** Menu laterale → **Calcolatrice** (o dall'icona negli accessi rapidi)

La calcolatrice integrata offre quattro strumenti di calcolo utili per le operazioni quotidiane d'ufficio.

### Calcolatrice Generale

Calcolatrice standard con le quattro operazioni di base (addizione, sottrazione, moltiplicazione, divisione) e funzioni aggiuntive.

**Come usarla:**

- Cliccare sui tasti numerici e sugli operatori sullo schermo, oppure
- Usare la **tastiera fisica** del computer: i tasti numerici e gli operatori (+, -, *, /) funzionano direttamente.
- Premere **Invio** o **=** per ottenere il risultato.
- Premere **C** o **Canc** per azzerare il display.

### Calcolo IVA

Strumento per calcolare rapidamente l'IVA su un importo.

**Come usarlo:**

1. Inserire l'**imponibile** (importo prima dell'IVA) nel campo dedicato.
2. Inserire l'**aliquota IVA** manualmente, oppure cliccare su uno dei pulsanti rapidi: **4%**, **5%**, **10%**, **22%**.
3. Il sistema calcola e mostra immediatamente:
   - Importo IVA (€)
   - Totale lordo (imponibile + IVA)

### Calcolo Margine e Ricarico

Strumento per analisi di prezzo e redditività.

**Come usarlo:**

1. Inserire il **costo** del prodotto/servizio.
2. Inserire il **prezzo di vendita**.
3. Il sistema calcola automaticamente:
   - **Margine in euro** (prezzo - costo)
   - **Margine percentuale** (margine / prezzo × 100)
   - **Ricarico percentuale** (margine / costo × 100)

Nota: il margine percentuale è calcolato sul prezzo di vendita; il ricarico percentuale è calcolato sul costo.

### Conversione Ore in Giorni

Strumento per convertire un totale di ore in giorni lavorativi e ore residue.

**Come usarlo:**

1. Inserire il **totale di ore** da convertire.
2. Inserire il numero di **ore per giornata lavorativa** (tipicamente 8).
3. Il sistema calcola e mostra:
   - Numero di **giorni interi**
   - **Ore rimanenti** (resto della divisione)

Esempio: 20 ore con 8 ore/giorno = 2 giorni interi + 4 ore rimanenti.

---

## 9. Profilo e Account

**Come accedere:** Cliccare sul proprio nome o sulla foto profilo in alto a destra nel menu di navigazione, poi selezionare **Il mio profilo**.

### Visualizzare il profilo

La pagina profilo mostra:

- **Foto profilo** (se caricata)
- **Dati anagrafici**: nome, cognome, data di nascita, codice fiscale, indirizzo
- **Dati lavorativi**: ruolo, reparto, data di assunzione, tipo di contratto
- **Riepilogo presenze**:
  - Giorni di ferie approvati nell'anno corrente
  - Richieste in attesa di risposta
  - Ore di permesso utilizzate

### Modificare il profilo

1. Dalla pagina profilo cliccare su **Modifica Profilo**.
2. È possibile aggiornare:
   - **Foto profilo**: cliccare sul campo foto per caricare una nuova immagine.
   - **Numero di telefono**
   - **Indirizzo**
   - Altri dati personali modificabili
3. Cliccare su **Salva modifiche** per confermare.

**Nota:** Alcuni dati lavorativi (ruolo, reparto, data di assunzione) possono essere modificati solo dallo staff/amministratore.

### Cambiare la password

1. Dal menu del profilo selezionare **Cambia Password**.
2. Inserire la **password attuale** nel primo campo.
3. Inserire la **nuova password** nel secondo campo.
4. Ripetere la nuova password nel terzo campo di **conferma**.
5. Cliccare su **Conferma**.

La nuova password deve rispettare i requisiti minimi di sicurezza (lunghezza minima, presenza di caratteri speciali, ecc.) indicati nella pagina.

### Impostazioni

Dal menu del profilo selezionare **Impostazioni** per accedere alle preferenze personali dell'applicazione, come notifiche, lingua e altre configurazioni disponibili.

---

## 10. Note per gli Amministratori

Questa sezione riepiloga le funzionalità esclusive dello staff e alcune indicazioni operative.

### Riepilogo funzionalità riservate allo Staff

| Funzionalità | Dove si trova |
|---|---|
| Lista completa dipendenti | Menu → Dipendenti → Lista |
| Aggiunta nuovo dipendente | Menu → Dipendenti → Lista → Aggiungi |
| Visualizzazione scheda qualsiasi dipendente | Menu → Dipendenti → click su dipendente |
| Modifica timbrature altrui | Scheda dipendente → Timbrature |
| Approvazione/rifiuto richieste ferie | Menu → Gestione Richieste |
| Lettere di richiamo | Menu → Dipendenti → Lettere di Richiamo |
| Creazione eventi calendario aziendale | Calendario Aziendale → click su giorno |
| Gestione corrispondenza | Menu → Corrispondenza |

### Gestione dei nuovi dipendenti

Quando si assume un nuovo dipendente:

1. Accedere a **Dipendenti → Lista → Aggiungi dipendente**.
2. Compilare tutti i campi obbligatori: nome, cognome, codice fiscale, email, ruolo, reparto, data di assunzione.
3. Impostare lo stato su **Attivo**.
4. Il sistema crea automaticamente un account utente. Comunicare le credenziali di accesso al dipendente e invitarlo a cambiare la password al primo accesso.

### Gestione dipendente non più attivo

Quando un dipendente lascia l'azienda, non eliminare il suo account ma impostare lo stato su **Non attivo**. In questo modo lo storico di timbrature, richieste e corrispondenza rimane consultabile.

### Protocollo corrispondenza

Il numero di protocollo viene assegnato automaticamente in sequenza per anno solare. Non è possibile modificare manualmente il numero di protocollo. In caso di necessità di correzione, duplicare la lettera e archiviare quella errata.

### Approvazione richieste: buone pratiche

- Elaborare le richieste in attesa entro 48 ore dalla ricezione.
- In caso di rifiuto, inserire sempre una motivazione chiara e rispettosa che aiuti il dipendente a comprendere la decisione.
- Le richieste approvate vengono automaticamente riflesse nel calendario aziendale come assenze.

---

*Manuale utente BASE — Per assistenza tecnica contattare l'amministratore di sistema.*
