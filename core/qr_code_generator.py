from io import BytesIO
import qrcode
from django.core.files import File
from PIL import Image, ImageDraw



def generate_qr_code(data, box_size=10, border=4, fill_color="black", back_color="white"):
    """
    Genera un QR Code dai dati forniti.
    
    Args:
        data: Stringa o URL da codificare
        box_size: Dimensione di ogni singolo quadrato del QR
        border: Spessore del bordo
        fill_color: Colore del QR
        back_color: Colore dello sfondo
        
    Returns:
        BytesIO: Buffer contenente l'immagine PNG
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
