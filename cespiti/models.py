"""
App ritirata dal catalogo prodotto il 26/08/2026 — ex contenitore di
Automezzo/Manutenzione/Rifornimento/EventoAutomezzo (-> app 'automezzi') e
Stabilimento/CostiStabilimento/DocStabilimento (-> app 'stabilimenti').

Resta in INSTALLED_APPS SOLO come ancora storica per le migrazioni: le
migrazioni di automezzi, magazzino, servizi e stabilimenti dipendono dalla
cronologia di migrazione di questa app (i dati reali sono nelle tabelle
rinominate automezzi_*/stabilimenti_*/magazzino_*, vedi
automezzi/migrations/0001_initial.py e stabilimenti/migrations/0001_...py).
Nessun modello, nessuna URL, nessuna voce sidebar: non fa parte del
catalogo vendibile (non e' in core/module_manager.py).

Gli alias sotto servono alle vecchie migrazioni 0001/0002 di cespiti, che
referenziano queste funzioni per import path diretto (non stringa).
"""

from automezzi.models import (
    libretto_upload_path, assicurazione_upload_path, scontrino_upload_path,
    allegati_manutenzione_path, allegato_evento_path,
)
