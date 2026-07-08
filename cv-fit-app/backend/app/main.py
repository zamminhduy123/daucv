"""
CVFit API — Application Factory
=================================
Creates the FastAPI application, registers middleware, and includes all routers.
This is the single source of truth for the ``app`` object.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, billing, health, jobs, sepay, user


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    application = FastAPI(title="CVFit API", version="1.0.0")

    @application.on_event("startup")
    async def startup_event():
        from app.core.db import Database

        await Database.connect()

    @application.on_event("shutdown")
    async def shutdown_event():
        from app.core.db import Database

        await Database.disconnect()

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

    # --- Logging & Request Tracing ------------------------------------------
    # Set up structured JSON logging with PII sanitization before any
    # routes/middleware are registered.  Import is lazy to avoid circular deps.
    from app.core.logging_config import setup_logging

    setup_logging()

    from app.middleware.request_logger import setup_request_logging

    setup_request_logging(application)

    # --- Routers -----------------------------------------------------------
    application.include_router(health.router)
    application.include_router(user.router)
    application.include_router(jobs.router)
    application.include_router(admin.router)
    application.include_router(billing.router)
    application.include_router(sepay.router)

    return application


app = create_app()
