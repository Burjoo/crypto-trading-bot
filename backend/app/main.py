"""
CryptoBot Pro — FastAPI Application Entry Point.

Configures middleware, routes, WebSocket endpoints,
startup/shutdown events, and health checks.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.db.session import engine, init_db
from app.websockets.manager import ws_manager

# ─── Structured Logging ──────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("🚀 CryptoBot Pro starting up", version=settings.APP_VERSION, env=settings.ENVIRONMENT)

    # Initialize database tables
    await init_db()
    logger.info("✅ Database initialized")

    # Initialize Sentry (if configured)
    if settings.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
        )
        logger.info("✅ Sentry initialized")

    yield

    logger.info("🛑 CryptoBot Pro shutting down")
    await engine.dispose()


# ─── Application Factory ──────────────────────────────────────────────────────

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Professional automated cryptocurrency trading platform. "
            "Connect exchanges, run strategies, backtest, and manage risk."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{elapsed:.4f}s"
        return response

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    # ── WebSocket Endpoints ───────────────────────────────────────────────────
    from fastapi import WebSocket
    from app.websockets.manager import handle_price_feed, handle_portfolio_feed
    from app.core.dependencies import get_current_user_ws

    @app.websocket("/ws/prices")
    async def ws_prices(websocket: WebSocket):
        """Public real-time price feed for all connected clients."""
        await handle_price_feed(websocket)

    @app.websocket("/ws/portfolio")
    async def ws_portfolio(websocket: WebSocket, token: str = ""):
        """Authenticated per-user portfolio / PnL feed."""
        user_id = await get_current_user_ws(token)
        if not user_id:
            await websocket.close(code=4001, reason="Unauthorized")
            return
        await handle_portfolio_feed(websocket, user_id)

    # ── Health & Metrics ─────────────────────────────────────────────────────
    @app.get("/health", tags=["System"], status_code=status.HTTP_200_OK)
    async def health_check():
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "ws_connections": ws_manager.connection_count(),
        }

    @app.get("/health/db", tags=["System"])
    async def health_db():
        """Check database connectivity."""
        from sqlalchemy import text
        from app.db.session import AsyncSessionLocal
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "ok", "database": "connected"}
        except Exception as exc:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "error", "database": str(exc)},
            )

    # ── Exception Handlers ────────────────────────────────────────────────────
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={"detail": f"Path {request.url.path!r} not found"},
        )

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        logger.error("Unhandled error", path=request.url.path, error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # ── Prometheus Metrics ────────────────────────────────────────────────────
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app)
    except ImportError:
        pass

    return app


app = create_application()
