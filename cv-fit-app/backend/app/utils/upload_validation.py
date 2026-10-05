"""Content checks for uploaded files (don't trust the client's Content-Type)."""

from fastapi import HTTPException

PDF_MAGIC = b"%PDF-"
# PDF readers accept the "%PDF-" header anywhere in the first 1024 bytes, and
# some generators emit a BOM or a few junk bytes first, so scan that window.
_HEADER_SCAN_BYTES = 1024


def looks_like_pdf(data: bytes) -> bool:
    """Return True when the PDF header ``%PDF-`` appears in the first 1 KB."""
    return PDF_MAGIC in data[:_HEADER_SCAN_BYTES]


def require_pdf_bytes(data: bytes) -> None:
    """Raise HTTP 415 unless ``data`` carries a PDF header."""
    if not looks_like_pdf(data):
        raise HTTPException(
            status_code=415,
            detail="Only PDF files are accepted.",
        )
