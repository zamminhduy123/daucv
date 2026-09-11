import io
import logging

import fitz
from PIL import Image

logger = logging.getLogger(__name__)


def generate_pdf_thumbnail(
    pdf_bytes: bytes,
    target_width: int = 680,
    quality: int = 82,
    output_format: str = "webp",
) -> bytes | None:
    """Render the first page of a PDF to high-quality WebP (or JPEG) bytes.

    Args:
        pdf_bytes: Raw bytes of the PDF document.
        target_width: Approximate width in pixels for the generated thumbnail.
                      Defaults to 680px for crisp retina display on 2x/3x screens.
        quality: Compression quality (1-100). Defaults to 82 for WebP.
        output_format: 'webp' (default, lightweight and sharp) or 'jpg'.

    Returns:
        Image bytes (WebP or JPEG), or None if the PDF cannot be opened or is empty.
        Never raises exceptions to callers.
    """
    if not pdf_bytes:
        return None

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if len(doc) == 0:
                return None

            page = doc[0]
            rect = page.rect
            if rect.width <= 0 or rect.height <= 0:
                return None

            scale = min(3.5, max(0.2, target_width / rect.width))
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            if output_format.lower() == "webp":
                try:
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    buf = io.BytesIO()
                    img.save(buf, format="WEBP", quality=quality, method=5)
                    return buf.getvalue()
                except Exception as img_err:
                    logger.warning(
                        "Pillow WebP encoding failed, falling back to JPEG: %s", img_err
                    )

            return pix.tobytes("jpg")
    except (fitz.FileDataError, Exception) as exc:
        logger.warning("Failed to generate PDF thumbnail: %s", exc)
        return None
