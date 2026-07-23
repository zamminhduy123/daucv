"""General-purpose helper functions.

The core extraction function now uses the layout-aware pipeline
(see ``app.services.layout_extraction``) which captures spatial
metadata, normalises extraction noise, detects reading order,
and identifies physical line continuations.
"""

from app.services.layout_extraction import extract_text_from_pdf

__all__ = ["extract_text_from_pdf"]
