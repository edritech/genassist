"""
WebSocket Service Main Application
"""

import os
import sys
import logging
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Add backend directory to Python path for shared module access
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import uvicorn
from fastapi import FastAPI, Request, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import conversations, health, broadcast, test

# Use local implementations for now (will migrate to shared incrementally)
from .cache.redis_manager import (
    initialize_redis_manager,
    shutdown_redis_manager,
    get_redis_manager,
)
from app.core.connection_manager import (
    SocketConnectionManager,
    get_connection_manager,
    set_connection_manager,
)
from app.core.config.settings import get_settings, validate_settings

# Note: To use shared modules later, update imports to:
# from shared.cache.redis_manager import RedisManager
# from shared.websocket.connection_manager import SocketConnectionManager
# Then update the lifespan function to use RedisManager().initialize() instead


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variable to track application startup time
_startup_time = None


def get_startup_time() -> float:
    """Get the application startup time timestamp."""
    global _startup_time
    return _startup_time


def calculate_uptime_seconds() -> float:
    """Calculate the uptime in seconds since application startup."""
    startup_time = get_startup_time()
    if startup_time is None:
        return 0.0
    return time.time() - startup_time


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup and shutdown events.

    Handles:
    - Redis initialization
    - WebSocket connection manager setup
    - Cleanup on shutdown
    """
    # Startup
    global _startup_time
    _startup_time = time.time()
    logger.info("Starting WebSocket service...")

    try:
        # Validate configuration
        issues = validate_settings()
        if issues:
            logger.error("Configuration validation failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            raise RuntimeError("Invalid configuration")

        # Initialize Redis manager
        logger.info("Initializing Redis manager...")
        try:
            await initialize_redis_manager()
            redis_manager = get_redis_manager()
            logger.info("Redis manager initialized successfully")
        except Exception as e:
            logger.warning(f"Redis manager initialization failed: {e}")
            logger.info("Running without Redis (single-server mode)")
            redis_manager = None

        # Initialize WebSocket connection manager
        logger.info("Initializing WebSocket connection manager...")
        connection_manager = SocketConnectionManager(redis_manager=redis_manager)
        set_connection_manager(connection_manager)

        # Initialize Redis subscriber if Redis is available
        if redis_manager:
            try:
                await connection_manager.initialize_redis_subscriber()
                logger.info("Redis Pub/Sub subscriber initialized")
            except Exception as e:
                logger.warning(f"Redis Pub/Sub not available: {e}")
                logger.info("Running in single-server mode")
        else:
            logger.info("Running in single-server mode (no Redis)")

        logger.info("WebSocket service started successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to start WebSocket service: {e}")
        raise

    # Shutdown
    logger.info("Shutting down WebSocket service...")

    try:
        # Cleanup connection manager
        connection_manager = get_connection_manager()
        if connection_manager:
            logger.info("Cleaning up WebSocket connections...")
            await connection_manager.cleanup()

        # Shutdown Redis manager
        logger.info("Shutting down Redis manager...")
        await shutdown_redis_manager()

        logger.info("WebSocket service shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()

    # Create FastAPI app with lifespan
    app = FastAPI(
        title=f"{settings.SERVICE_NAME}",
        version=f"{settings.SERVICE_VERSION}",
        description="WebSocket microservice for real-time communication for GenAssist",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add middleware
    setup_middleware(app, settings)

    # Add exception handlers
    setup_exception_handlers(app)

    # Add routers
    setup_routers(app)

    return app


def setup_middleware(app: FastAPI, settings) -> None:
    """
    Setup application middleware.

    Args:
        app: FastAPI application instance
        settings: Application settings
    """
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Trusted host middleware
    if settings.is_production():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # Configure appropriately for production
        )

    # Custom middleware for request logging and tenant resolution
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        # Log request
        logger.info(f"Request: {request.method} {request.url}")

        # Process request
        response = await call_next(request)

        # Log response
        logger.info(f"Response: {response.status_code}")

        return response


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Setup global exception handlers.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(WebSocketDisconnect)
    async def websocket_disconnect_handler(request: Request, exc: WebSocketDisconnect):
        """Handle WebSocket disconnections gracefully"""
        logger.info(f"WebSocket disconnected: {exc.code}")
        return JSONResponse(
            status_code=exc.code,
            content={"message": "WebSocket disconnected", "code": exc.code},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle value errors"""
        logger.warning(f"Value error: {exc}")
        return JSONResponse(
            status_code=400, content={"message": "Invalid request", "detail": str(exc)}
        )

    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        """Handle key errors"""
        logger.warning(f"Key error: {exc}")
        return JSONResponse(
            status_code=400,
            content={"message": "Missing required field", "detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "message": "Internal server error",
                "detail": "An unexpected error occurred",
            },
        )


def setup_routers(app: FastAPI) -> None:
    """
    Setup application routers.

    Args:
        app: FastAPI application instance
    """

    # Health check router
    app.include_router(health.router, tags=["Health"])

    # Broadcast router
    app.include_router(broadcast.router, tags=["Broadcast"])

    # WebSocket router
    app.include_router(conversations.router, tags=["WebSocket"])

    # Test router
    app.include_router(test.router, tags=["Test"])


# Create application instance
app = create_application()


@app.get("/")
async def root():
    """Root endpoint for service information"""
    settings = get_settings()
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENV,
        "status": "running",
        "endpoints": {
            "websocket": f"ws://{settings.host}:{settings.port}",
            "health": settings.health_check_path,
            "docs": "/docs",
        },
    }


@app.get("/info")
async def info():
    """Detailed service information"""
    settings = get_settings()
    manager = get_connection_manager()

    # Get connection statistics
    try:
        stats = await manager.get_connection_stats()
    except Exception as e:
        logger.warning(f"Failed to get connection stats: {e}")
        stats = {"error": "Unable to retrieve statistics"}

    return {
        "service": {
            "name": settings.SERVICE_NAME,
            "version": settings.SERVICE_VERSION,
            "environment": settings.ENV,
        },
        "configuration": {
            "multi_tenant_enabled": settings.multi_tenant_enabled,
            "redis_enabled": bool(settings.redis_url),
            "websocket_compression": settings.websocket_enable_compression,
            "max_connections_per_user": settings.max_connections_per_user,
        },
        "connections": stats,
        "endpoints": {
            "websocket": {
                "conversation": "ws://localhost:8002/api/conversations/ws/{{conversation_id}}",
                "dashboard": "ws://localhost:8002/api/conversations/dashboard/list",
            },
            "health": settings.health_check_path,
            "metrics": settings.metrics_path,
        },
    }


if __name__ == "__main__":
    # Run the application directly
    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
    )
