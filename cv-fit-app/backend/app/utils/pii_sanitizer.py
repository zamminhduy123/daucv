"""
PII Sanitizer — Mask personally identifiable information in log messages.

Provides ``sanitize()`` which replaces common PII patterns in arbitrary strings
with safe placeholders before the string is written to any log file.

This is a **defensive** layer — no PII should be logged intentionally, but
if a developer slips up, this utility prevents email addresses, phone numbers,
and other identifiable fields from appearing in plaintext logs.

Patterns matched (Vietnamese and international):
- Email addresses
- Vietnamese phone numbers (+84, 0xxx, 0xx.xxx)
- International phone numbers (+1-3 digit country code)
- IPv4 addresses (metadata risk)
- Vietnamese ID card patterns (CMT/CCCD: 0\\d{11}, CCCD \\d{12})
"""

import re
from typing import Any

# ---------------------------------------------------------------------------
# Pre-compiled patterns — order matters: longer/more-specific patterns first
# ---------------------------------------------------------------------------

# Vietnamese ID card / CCCD: 12 consecutive digits (often starts with 0)
_ID_CARD = re.compile(r"\b0\d{11}\b")

# Vietnamese phone: +84 xx xxx xxxx or +84-xx-xxx-xxxx or 0xx xxx xxxx or 0xx-xxx-xxxx
_PHONE_VN = re.compile(r"(?:\+84[\s.-]?|0)\d{2}[\s.-]?\d{3}[\s.-]?\d{4}\b")

# International phone: +1-3 digit country code followed by digits
# Matches: +1 555 1234, +44 20 7946, +81-3-1234-5678, etc.
_PHONE_INT = re.compile(r"\+\d{1,3}(?:[\s.-]\d{1,4}){2,6}\b")

# Email address
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

# IPv4 address (not inside a larger token)
_IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b")


# ---------------------------------------------------------------------------
# Main sanitizer
# ---------------------------------------------------------------------------

_PLACEHOLDER_PII = "[REDACTED-PII]"


def sanitize(value: Any) -> str:
    """
    Convert *value* to a string and mask all PII patterns.

    Parameters
    ----------
    value : Any
        Anything convertible to ``str`` — a message string, an exception, etc.

    Returns
    -------
    str
        The same text with all PII patterns replaced by ``[REDACTED-PII]``.

    Examples
    --------
    >>> sanitize("Contact at john@example.com for info")
    'Contact at [REDACTED-PII] for info'
    >>> sanitize("Phone: +84 90 123 4567")
    'Phone: [REDACTED-PII]'
    """
    text = str(value)

    # Apply patterns in priority order (most-specific first)
    replacements = [
        (_ID_CARD, _PLACEHOLDER_PII),
        (_PHONE_VN, _PLACEHOLDER_PII),
        (_PHONE_INT, _PLACEHOLDER_PII),
        (_EMAIL, _PLACEHOLDER_PII),
        (_IPV4, _PLACEHOLDER_PII),
    ]

    for pattern, replacement in replacements:
        text = pattern.sub(replacement, text)

    return text
