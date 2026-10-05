"""Log-safe one-line summaries of exceptions.

LLM-path exceptions often embed the model's input or output in their message
(for example pydantic ``ValidationError`` echoes ``input_value``, which can be
a chunk of a candidate's CV). These helpers describe an exception for logs
without copying that content.
"""

from pydantic import ValidationError

_MAX_MESSAGE_CHARS = 200
_MAX_VALIDATION_ERRORS = 5


def describe_exception(exc: BaseException) -> str:
    """Return ``"<Type>: <short message>"`` without echoing request content."""
    if isinstance(exc, ValidationError):
        details = exc.errors(include_input=False, include_url=False)
        parts = [
            f"{'.'.join(str(p) for p in d.get('loc', ())) or '<root>'}:{d.get('type')}"
            for d in details[:_MAX_VALIDATION_ERRORS]
        ]
        return f"ValidationError({exc.error_count()} errors: {', '.join(parts)})"

    message = " ".join(str(exc).split())
    if len(message) > _MAX_MESSAGE_CHARS:
        message = message[:_MAX_MESSAGE_CHARS] + "..."
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__
