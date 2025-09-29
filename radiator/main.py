"""Main application entry point."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from radiator.core.config import settings
from radiator.core.logging import setup_logging
from radiator.core.metrics import get_metrics, PrometheusMiddleware
# API router removed - using commands instead


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    # Setup logging
    setup_logging()
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Modern REST API with PostgreSQL backend",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware - only apply in production/development, not in tests
    if settings.ENVIRONMENT not in ["test", "testing"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS,
        )
    
    # Prometheus metrics middleware
    app.add_middleware(PrometheusMiddleware)

    # API router removed - using commands instead
    # app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "Welcome to Radiator API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "redoc": "/redoc",
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": settings.APP_NAME}
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        from fastapi.responses import Response
        return Response(
            content=get_metrics(),
            media_type="text/plain"
        )

    return app


app = create_application()


def main():
    """Main function to run the application."""
    uvicorn.run(
        "radiator.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
