"""
CVFit API — Application Factory
=================================
Creates the FastAPI application, registers middleware, and includes all routers.
This is the single source of truth for the ``app`` object.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, health, user


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    application = FastAPI(title="CVFit API", version="1.0.0")

    # --- CORS (allow Next.js frontend — dev and prod) ----------------------
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers -----------------------------------------------------------
    application.include_router(health.router)
    application.include_router(user.router)
    application.include_router(admin.router)

    return application


app = create_app()
