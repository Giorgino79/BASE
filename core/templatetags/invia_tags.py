"""
Template tag per il bottone INVIA (WhatsApp / Email).

Uso:
    {% load invia_tags %}
    {% bottone_invia phone="+393331234567" email="x@y.it" oggetto="Busta paga" pdf_url=pdf_url %}

Parametri:
    phone            — numero WhatsApp (es. "+393331234567" o "3331234567")
    email            — email destinatario
    oggetto          — oggetto / titolo documento
    messaggio        — testo opzionale del messaggio
    pdf_url          — URL Django relativa del PDF (es. /media/buste/file.pdf)
    pdf_path         — percorso assoluto del PDF (alternativa a pdf_url)
    destinatario_nome — nome del destinatario (opzionale)
    label            — testo del bottone (default "Invia")
    btn_class        — classe Bootstrap (default "btn-primary")
    btn_size         — "btn-sm" / "btn-lg" / "" (default "")
"""

import uuid
from django import template

register = template.Library()


@register.inclusion_tag("core/modal_invia.html", takes_context=True)
def bottone_invia(
    context,
    phone="",
    email="",
    oggetto="",
    messaggio="",
    pdf_url="",
    pdf_path="",
    destinatario_nome="",
    label="Invia",
    btn_class="btn-primary",
    btn_size="",
):
    return {
        "modal_id": f"modalInvia{uuid.uuid4().hex[:8]}",
        "phone": phone,
        "email": email,
        "oggetto": oggetto,
        "messaggio": messaggio,
        "pdf_url": pdf_url,
        "pdf_path": pdf_path,
        "destinatario_nome": destinatario_nome,
        "label": label,
        "btn_class": btn_class,
        "btn_size": btn_size,
        "request": context.get("request"),
    }
