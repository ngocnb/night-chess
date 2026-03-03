import logging
import logging.handlers
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings


def _configure_logging() -> None:
    """Route structlog through stdlib; errors go to error.log, all logs to app.log."""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    all_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )

    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler(), all_handler, error_handler],
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.format_exc_info,
            structlog.processors.KeyValueRenderer(key_order=["timestamp", "level", "event"]),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)
    logger.info("startup", environment=settings.environment)
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Night Chess API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.environment != "production" else None,
    )

    # Register the error-catching middleware FIRST so that when CORSMiddleware
    # is added next (Starlette prepends each new middleware), CORS ends up
    # outermost.  Stack after both registrations:
    #   CORSMiddleware (outermost) → catch_unhandled_exceptions → routes
    # Any JSONResponse returned by catch_unhandled_exceptions flows back
    # through CORSMiddleware, which then injects the CORS headers.
    @app.middleware("http")
    async def catch_unhandled_exceptions(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(
                "unhandled_exception",
                error=str(exc),
                path=str(request.url),
                exc_info=True,
            )
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    from app.api.v1 import router as api_v1_router

    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
