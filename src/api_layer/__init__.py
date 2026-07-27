"""API Layer Package and Application Factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api_layer.rest.routes import router as rest_router
from src.api_layer.websocket.gateway import ws_router
from src.api_layer.middleware.error_handler import jarvis_exception_handler
from src.shared.exceptions.base import JarvisException
from config.settings import settings


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Jarvis Autonomous AI Assistant Microservices API",
        debug=settings.debug
    )

    # CORS Middleware Setup
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    app.add_exception_handler(JarvisException, jarvis_exception_handler)

    # Include Routers
    app.include_router(rest_router)
    app.include_router(ws_router)

    return app


app = create_app()

__all__ = [
    "create_app",
    "app",
]
