import qrcode
from qrcode.image.pil import PilImage
from io import BytesIO
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


def generate_qr_code(data: str, size: int = 10, border: int = 4) -> Optional[bytes]:
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=border,
        )

        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)

        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        return img_buffer.getvalue()

    except Exception as e:
        logger.error("Failed to generate QR code", error=str(e), data=data)
        return None


def generate_invoice_qr_code(invoice_code: str, bot_username: str) -> Optional[bytes]:
    invoice_link = f"https://t.me/{bot_username}?start={invoice_code}"

    return generate_qr_code(invoice_link)
