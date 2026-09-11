from unittest.mock import patch

import fitz

from app.services.pdf_thumbnail import generate_pdf_thumbnail


def test_generate_pdf_thumbnail_valid_pdf():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), "Test CV Header")
    pdf_bytes = doc.tobytes()
    doc.close()

    # Default output should be high-quality WebP
    thumb = generate_pdf_thumbnail(pdf_bytes)
    assert thumb is not None
    assert len(thumb) > 0
    # WebP magic container header: 'RIFF' .... 'WEBP'
    assert thumb[:4] == b"RIFF"
    assert thumb[8:12] == b"WEBP"

    # Optional JPEG output format
    thumb_jpg = generate_pdf_thumbnail(pdf_bytes, output_format="jpg")
    assert thumb_jpg is not None
    assert thumb_jpg[:3] == b"\xff\xd8\xff"


def test_generate_pdf_thumbnail_empty_bytes():
    assert generate_pdf_thumbnail(b"") is None


def test_generate_pdf_thumbnail_corrupt_bytes():
    assert generate_pdf_thumbnail(b"corrupt-non-pdf-bytes-12345") is None


def test_generate_pdf_thumbnail_zero_page_doc():
    doc = fitz.open()
    with patch("fitz.open", return_value=doc):
        assert generate_pdf_thumbnail(b"dummy") is None
