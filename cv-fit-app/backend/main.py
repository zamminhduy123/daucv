"""Compatibility shim — keeps ``uvicorn main:app`` working.

All application logic lives in the ``app/`` package.
This file simply re-exports the FastAPI instance.
"""

from app.main import app  # noqa: F401

# Re-export models for backward compatibility with tests and scripts
# that import directly from ``main``.
from app.models.domain import *  # noqa: F403
from app.models.requests import *  # noqa: F403
from app.models.responses import *  # noqa: F403
