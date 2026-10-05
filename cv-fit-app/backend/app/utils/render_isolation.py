"""Isolation helpers for rendering HTML in server-side Playwright.

Defense in depth for untrusted HTML (the WYSIWYG export renders markup sent by
the client): the browser itself refuses every sub-resource except inline
styles and data: images/fonts, so ``url(file:///...)`` in CSS,
``<svg><image href>``, ``<video>`` and similar cannot read local files or reach
the network even if a sanitizer pattern misses them.
"""

import re
from typing import Any

NO_SUBRESOURCE_CSP_META = (
    '<meta http-equiv="Content-Security-Policy" content="'
    "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:"
    '">'
)
_HEAD_OPEN = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
_HTML_OPEN = re.compile(r"<html\b[^>]*>", re.IGNORECASE)


def inject_no_subresource_csp(html: str) -> str:
    """Insert the CSP meta tag as the first element of <head> (or after <html>)."""
    for pattern in (_HEAD_OPEN, _HTML_OPEN):
        match = pattern.search(html)
        if match:
            end = match.end()
            return html[:end] + NO_SUBRESOURCE_CSP_META + html[end:]
    return NO_SUBRESOURCE_CSP_META + html


def is_allowed_render_request(url: str) -> bool:
    """Only inline data: and about: URLs may load while rendering."""
    return url.startswith(("data:", "about:"))


async def block_non_inline_requests(route: Any) -> None:
    """Playwright route handler: abort everything except data:/about: URLs.

    Replaces the old ``url.startswith("http")`` check, which let file:// and
    every other scheme through.
    """
    if is_allowed_render_request(route.request.url):
        await route.continue_()
    else:
        await route.abort()
