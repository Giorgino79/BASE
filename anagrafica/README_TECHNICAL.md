# anagrafica - Documentazione Tecnica

## Versione
- **Versione corrente**: 1.0.0
- **Django**: 5.1.4
- **Python**: 3.9+

## Descrizione
[Descrizione tecnica del modulo]

## Architettura

### Modelli
- `Item`: [Descrizione]
  - Eredita da: `BaseModel`
  - Mixin utilizzati: [AllegatiMixin, PDFMixin, etc.]
  - Campi principali: [...]
  - Relazioni: [...]

### View
- `ItemListView`: Lista paginata con ricerca
- `ItemDetailView`: Dettaglio con allegati/QR
- `ItemCreateView`: Creazione
- `ItemUpdateView`: Modifica
- `ItemDeleteView`: Eliminazione (soft delete)

### Form
- `ItemForm`: ModelForm con validazione custom

### URL
- `anagrafica:Item_lower_list` → Lista
- `anagrafica:Item_lower_detail` → Dettaglio
- `anagrafica:Item_lower_create` → Creazione
- `anagrafica:Item_lower_update` → Modifica
- `anagrafica:Item_lower_delete` → Eliminazione

## Dipendenze
### Moduli Required
- `core` (v1.0.0+)
- `users` (v1.0.0+)

### Moduli Optional
- [Lista moduli opzionali]

## Database
### Tabelle
- `anagrafica_Item_lower`

### Migrazioni
```bash
python manage.py makemigrations anagrafica
python manage.py migrate anagrafica
```

## Configurazione

### Settings.py
```python
INSTALLED_APPS = [
    # ...
    'anagrafica',
]
```

### URLs
```python
path('anagrafica/', include('anagrafica.urls')),
```

## API Endpoints
[Se presente API REST]

## Template
- Estende: `commons_templates/base_detail.html`
- Template tag utilizzati: `{% load allegati_tags %}`

## Permessi
- `anagrafica.view_Item_lower`
- `anagrafica.add_Item_lower`
- `anagrafica.change_Item_lower`
- `anagrafica.delete_Item_lower`

## Testing
```bash
pytest anagrafica/tests/
```

## Troubleshooting
[Problemi comuni e soluzioni]

## Changelog
Vedi [CHANGELOG.md](./CHANGELOG.md)
