from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from core.pdf_generator import generate_pdf_from_html, PDFConfig


def invia_oda(ordine):
    """
    Invia l'ODA via email al fornitore con PDF allegato.
    Restituisce (True, None) se inviata, (False, motivo) se non inviata.
    """
    fornitore = ordine.fornitore
    destinatario = fornitore.email or fornitore.referente_email

    if not destinatario:
        return False, f"Nessun indirizzo email per il fornitore {fornitore}"

    context = {
        "ordine": ordine,
        "righe": list(ordine.righe.select_related("prodotto").all()),
        "site_url": getattr(settings, "SITE_URL", ""),
    }

    soggetto = f"Ordine di Acquisto {ordine.numero_ordine}"
    corpo_txt = render_to_string("acquisti/email/oda.txt", context)
    corpo_html = render_to_string("acquisti/email/oda.html", context)

    msg = EmailMultiAlternatives(
        subject=soggetto,
        body=corpo_txt,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario],
    )
    msg.attach_alternative(corpo_html, "text/html")

    pdf_html = render_to_string("acquisti/pdf/oda.html", context)
    pdf_buffer = generate_pdf_from_html(pdf_html, PDFConfig(filename=f"{ordine.numero_ordine}.pdf"), output_type="buffer")
    if pdf_buffer:
        msg.attach(f"{ordine.numero_ordine}.pdf", pdf_buffer.read(), "application/pdf")

    try:
        msg.send(fail_silently=False)
        return True, None
    except Exception as e:
        return False, str(e)
