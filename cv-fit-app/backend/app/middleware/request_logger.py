"""Request Logger Middleware — adds request_id tracking and logs requests/responses.

Adds a unique ``X-Request-ID`` header to every request (or reuses one from the
client).  Logs method, path, status code, and duration — **never** request or
response bodies, headers, or cookies, to prevent PII leaks.

The request ID is stored in a ``contextvar`` so downstream code can include it
in structured log messages via ``JSONFormatter``.
"""

import uuid
from contextvars import ContextVar
from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for request-scoped request ID
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

# Log level: use WARNING for requests (not every request is logged at INFO
# to avoid filling logs with noise). Adjust via LOG_LEVEL in config.


class RequestLogger(BaseHTTPMiddleware):
    """Middleware that logs every request with PII-safe fields.

    Logged fields:
    - request_id (UUID, for correlation)
    - method (GET, POST, etc.)
    - path (/api/upload-and-match)
    - status_code (200, 404, etc.)
    - duration_ms (wall-clock time)

    Never logged:
    - Request body
    - Response body
    - Cookie headers
    - Authorization headers (only logged if explicitly set in request_id)
    - Query parameters (may contain tokens)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate or reuse request ID
        request_id = request.headers.get(
            "x-request-id",
            str(uuid.uuid4()),
        )
        token = request_id_ctx.set(request_id)

        try:
            start = perf_counter()
            response = await call_next(request)
            duration_ms = int((perf_counter() - start) * 1000)

            # Add request ID to response headers
            response.headers["x-request-id"] = request_id

            # Log the request (PII-safe)
            _log_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            return response
        finally:
            request_id_ctx.reset(token)


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------


def _log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
) -> None:
    """Log a single request event.

    Uses the application logger (set up by ``logging_config.setup_logging()``)
    with structured fields. No PII is included.
    """
    import logging

    logger = logging.getLogger("app.middleware.request_logger")
    logger.info(
        f"{method} {path} → {status_code} ({duration_ms}ms)",
        extra={
            "method": method,
            "endpoint": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
        },
    )


# Expose setup function so main.py can call it
def setup_request_logging(app) -> None:
    """Attach RequestLogger middleware to the FastAPI app."""
    app.add_middleware(RequestLogger)
