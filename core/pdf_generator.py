"""
CORE PDF GENERATOR - ModularBEF
================================

Sistema universale per generazione PDF.
Supporta ReportLab per PDF professionali con tabelle e stili.
Supporta xhtml2pdf per generazione PDF da HTML.
"""

from io import BytesIO
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass, field
import tempfile
import urllib.request

from django.http import HttpResponse
from django.utils import timezone

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfgen import canvas

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from xhtml2pdf import pisa

    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False


@dataclass
class PDFConfig:
    """Configurazione per la generazione PDF da HTML."""

    filename: str = "document.pdf"
    page_size: str = "A4"
    orientation: str = "portrait"
    margin_top: str = "1cm"
    margin_bottom: str = "1cm"
    margin_left: str = "1cm"
    margin_right: str = "1cm"


def generate_pdf_from_html(
    html_content: str,
    config: PDFConfig = None,
    output_type: str = "response",
) -> Optional[BytesIO | HttpResponse]:
    """
    Genera un PDF da contenuto HTML usando xhtml2pdf.

    Args:
        html_content: Stringa HTML da convertire in PDF
        config: Configurazione PDFConfig (opzionale)
        output_type: "response" per HttpResponse, "buffer" per BytesIO

    Returns:
        HttpResponse o BytesIO con il PDF, None se errore
    """
    if not XHTML2PDF_AVAILABLE:
        raise ImportError("xhtml2pdf non installato. Run: pip install xhtml2pdf")

    if config is None:
        config = PDFConfig()

    # Crea buffer
    buffer = BytesIO()

    # Genera PDF
    pisa_status = pisa.CreatePDF(html_content, dest=buffer)

    if pisa_status.err:
        return None

    buffer.seek(0)

    if output_type == "buffer":
        return buffer

    # Response
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{config.filename}"'
    return response


def generate_pdf_response(
    data: List[Dict[str, Any]],
    filename: str,
    title: str = "Report",
    headers: List[str] = None,
    landscape: bool = False,
    totals: Dict[str, Any] = None,
) -> HttpResponse:
    """
    Genera un file PDF con tabella e lo ritorna come HttpResponse.

    Args:
        data: Lista di dizionari con i dati
        filename: Nome del file (senza estensione)
        title: Titolo del documento
        headers: Lista headers personalizzati (opzionale)
        landscape: Se True usa orientamento orizzontale (utile per molte colonne)

    Returns:
        HttpResponse con il file PDF
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab non installato. Run: pip install reportlab")

    from reportlab.lib.pagesizes import landscape as _landscape
    page_size = _landscape(A4) if landscape else A4

    # Crea buffer
    buffer = BytesIO()

    margin = 1.5 * cm
    # Crea documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    # Elementi del documento
    elements = []

    # Stili
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#5585b5"),
        spaceAfter=30,
        alignment=1,  # Center
    )

    # Titolo
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 12))

    # Info generazione
    info_text = f"Generato il {timezone.now().strftime('%d/%m/%Y alle %H:%M')}"
    info_style = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        alignment=2,  # Right
    )
    elements.append(Paragraph(info_text, info_style))
    elements.append(Spacer(1, 20))

    if not data:
        elements.append(Paragraph("Nessun dato disponibile", styles["Normal"]))
    else:
        # Headers
        if headers is None:
            headers = list(data[0].keys())

        # Prepara dati tabella
        table_data = [headers]

        for row_data in data:
            row = []
            for header in headers:
                value = row_data.get(header, "")

                # Formatta valore
                if isinstance(value, (datetime, date)):
                    formatted = (
                        value.strftime("%d/%m/%Y %H:%M")
                        if isinstance(value, datetime)
                        else value.strftime("%d/%m/%Y")
                    )
                elif isinstance(value, Decimal):
                    formatted = f"{float(value):.2f}"
                elif value is None:
                    formatted = "-"
                else:
                    formatted = str(value)

                row.append(formatted)

            table_data.append(row)

        # Riga totali
        if totals:
            totals_row = []
            for header in headers:
                val = totals.get(header, "")
                if val == "" or val is None:
                    totals_row.append("")
                elif isinstance(val, float):
                    totals_row.append(f"{val:.2f}")
                else:
                    totals_row.append(str(val))
            table_data.append(totals_row)

        # Distribuisce le colonne su tutta la larghezza utile
        n_cols = len(headers)
        usable_w = page_size[0] - 2 * margin
        col_w = usable_w / n_cols

        # Font adattivo: meno spazio → caratteri più piccoli
        body_font = max(6, min(9, int(usable_w / (n_cols * 8))))
        head_font = body_font + 1

        # Crea tabella
        table = Table(table_data, colWidths=[col_w] * n_cols, repeatRows=1)

        # Stile tabella
        table_style = TableStyle(
            [
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5585b5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), head_font),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                # Dati
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), body_font),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                # Bordi
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#5585b5")),
                # Alternating row colors
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f8f9fa")],
                ),
            ]
        )

        if totals:
            last = len(table_data) - 1
            table_style.add("BACKGROUND",   (0, last), (-1, last), colors.HexColor("#dce8f5"))
            table_style.add("FONTNAME",     (0, last), (-1, last), "Helvetica-Bold")
            table_style.add("TEXTCOLOR",    (0, last), (-1, last), colors.HexColor("#1a3a5c"))
            table_style.add("TOPPADDING",   (0, last), (-1, last), 6)
            table_style.add("BOTTOMPADDING",(0, last), (-1, last), 6)

        table.setStyle(table_style)
        elements.append(table)

    # Build PDF
    doc.build(elements)

    # Ottieni PDF
    pdf = buffer.getvalue()
    buffer.close()

    # Response
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'

    return response


# ===========================================================================
# TESSERINO DIPENDENTE (formato badge 85.6mm x 54mm)
# ===========================================================================


def get_image_path(file_field):
    """
    Ottiene il path locale di un'immagine, scaricandola se è su storage remoto.

    Restituisce il path stringa oppure None se non disponibile.
    """
    if not file_field:
        return None
    try:
        return file_field.path
    except (NotImplementedError, AttributeError):
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            urllib.request.urlretrieve(file_field.url, temp_file.name)
            return temp_file.name
        except Exception:
            return None


def generate_tesserino_pdf(user, logo_path: str = None) -> HttpResponse:
    """
    Genera il tesserino dipendente in formato badge (85.6mm x 54mm, fronte/retro).

    - Fronte: logo, foto/iniziale, nome, qualifica, matricola, reparto, QR
    - Retro: dati anagrafici e contributivi
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab non installato. Run: pip install reportlab")

    badge_width = 85.6 * mm
    badge_height = 54 * mm

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="tesserino_{user.username}.pdf"'

    c = canvas.Canvas(response, pagesize=(badge_width, badge_height))

    # ──────────────────────────────────────────────
    # FRONTE
    # ──────────────────────────────────────────────

    # Sfondo blu brand
    c.setFillColor(colors.HexColor('#5585b5'))
    c.rect(0, 0, badge_width, badge_height, fill=1, stroke=0)

    # Logo aziendale in alto a sinistra
    if logo_path:
        try:
            if logo_path.startswith('http'):
                temp_logo = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                urllib.request.urlretrieve(logo_path, temp_logo.name)
                logo_path = temp_logo.name
            c.drawImage(logo_path, 5 * mm, badge_height - 10 * mm,
                        width=20 * mm, height=7 * mm,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # "TESSERINO DIPENDENTE" in alto a destra
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 6)
    c.drawRightString(badge_width - 5 * mm, badge_height - 7 * mm, "TESSERINO")
    c.drawRightString(badge_width - 5 * mm, badge_height - 10 * mm, "DIPENDENTE")

    # Card bianca centrale
    c.setFillColor(colors.white)
    c.roundRect(3 * mm, 3 * mm, badge_width - 6 * mm, badge_height - 16 * mm,
                2 * mm, fill=1, stroke=0)

    # Foto profilo (o iniziale)
    y_start = 25 * mm
    foto_path = get_image_path(user.foto_profilo) if user.foto_profilo else None
    if foto_path:
        try:
            c.drawImage(foto_path, badge_width / 2 - 7 * mm, y_start,
                        width=14 * mm, height=14 * mm,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            foto_path = None

    if not foto_path:
        c.setFillColor(colors.HexColor('#5585b5'))
        c.rect(badge_width / 2 - 7 * mm, y_start, 14 * mm, 14 * mm, fill=1, stroke=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 12)
        initial = (user.get_full_name() or user.username)[0].upper()
        c.drawCentredString(badge_width / 2, y_start + 7 * mm, initial)

    # Nome completo
    y_pos = y_start - 5 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(badge_width / 2, y_pos, (user.get_full_name() or user.username)[:20])

    # Qualifica
    y_pos -= 5 * mm
    c.setFillColor(colors.HexColor('#5585b5'))
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(badge_width / 2, y_pos, (user.qualifica or "N/D")[:24])

    # Matricola
    y_pos -= 5 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 6)
    c.drawCentredString(badge_width / 2, y_pos, f"Mat: {user.codice_dipendente}")

    # Reparto
    y_pos -= 4.5 * mm
    c.setFont("Helvetica", 6)
    c.drawCentredString(badge_width / 2, y_pos, (user.reparto or "N/D")[:25])

    # QR code (se disponibile)
    qr_badge = user.get_badge_qr()
    if qr_badge and hasattr(qr_badge, 'file'):
        qr_path = get_image_path(qr_badge.file)
        if qr_path:
            try:
                c.drawImage(qr_path, badge_width - 15 * mm, 4 * mm,
                            width=11 * mm, height=11 * mm,
                            preserveAspectRatio=True)
            except Exception:
                pass

    # Data emissione in basso a sinistra
    c.setFillColor(colors.HexColor('#5585b5'))
    c.setFont("Helvetica", 5)
    c.drawString(4 * mm, 1.5 * mm, f"Em: {date.today().strftime('%d/%m/%Y')}")

    # ──────────────────────────────────────────────
    # RETRO
    # ──────────────────────────────────────────────
    c.showPage()

    # Sfondo bianco
    c.setFillColor(colors.white)
    c.rect(0, 0, badge_width, badge_height, fill=1, stroke=0)

    # Header blu
    c.setFillColor(colors.HexColor('#5585b5'))
    c.rect(0, badge_height - 10 * mm, badge_width, 10 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(badge_width / 2, badge_height - 6 * mm, "DATI IDENTIFICATIVI")

    y_pos = badge_height - 14 * mm
    lh = 5.5 * mm  # line height

    def riga(label, valore):
        nonlocal y_pos
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 6)
        c.drawString(5 * mm, y_pos, label)
        c.setFont("Helvetica", 6)
        c.drawString(28 * mm, y_pos, str(valore) if valore else "N/D")
        y_pos -= lh

    riga("Nato il:", user.data_nascita.strftime('%d/%m/%Y') if user.data_nascita else None)
    riga("Luogo:", (user.luogo_nascita or None) and user.luogo_nascita[:30])
    riga("Assunto il:", user.data_assunzione.strftime('%d/%m/%Y') if user.data_assunzione else None)
    riga("Contratto:", user.data_cessazione.strftime('%d/%m/%Y') if user.data_cessazione else "Indeterminato")

    y_pos -= 1 * mm  # piccola spaziatura prima di INPS/INAIL

    # INPS e INAIL con font leggermente più piccolo per il valore
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(5 * mm, y_pos, "INPS:")
    c.setFont("Helvetica", 5)
    c.drawString(28 * mm, y_pos, (user.posizione_inps or "Non disponibile")[:35])
    y_pos -= lh

    c.setFont("Helvetica-Bold", 6)
    c.drawString(5 * mm, y_pos, "INAIL:")
    c.setFont("Helvetica", 5)
    c.drawString(28 * mm, y_pos, (user.posizione_inail or "Non disponibile")[:35])

    # Footer blu
    c.setFillColor(colors.HexColor('#5585b5'))
    c.rect(0, 0, badge_width, 5 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 5)
    c.drawCentredString(badge_width / 2, 1.5 * mm, "Documento valido per controlli esterni")

    c.save()
    return response
