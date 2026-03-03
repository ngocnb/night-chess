from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings

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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def catch_unhandled_exceptions(request: Request, call_next):
        # This middleware sits INSIDE CORSMiddleware in the stack, so any
        # JSONResponse returned here will have CORS headers added by the time
        # it reaches the client — unlike @app.exception_handler(Exception),
        # which registers with ServerErrorMiddleware (outside CORS).
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error("unhandled_exception", error=str(exc), path=str(request.url))
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    from app.api.v1 import router as api_v1_router

    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
