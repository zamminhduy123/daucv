"""
CVFit API — Application Factory
=================================
Creates the FastAPI application, registers middleware, and includes all routers.
This is the single source of truth for the ``app`` object.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, health, jobs, user


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    application = FastAPI(title="CVFit API", version="1.0.0")

    # --- CORS (explicit origin allowlist -- dev and prod) -------------------
    # Never use allow_origins=["*"] with allow_credentials=True — violates CORS spec.
    from app.core.config import CORS_ALLOWED_ORIGINS

    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers -----------------------------------------------------------
    application.include_router(health.router)
    application.include_router(user.router)
    application.include_router(jobs.router)
    application.include_router(admin.router)

    return application


app = create_app()
