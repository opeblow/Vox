import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.routers import (
    auth_router, payments_router, upload_router,
    ingest_router, query_router, vaults_router, admin_router,
    ws_router, comparison_router,
)
from backend.database import Base, engine
from backend.models import *
from backend.utils.rate_limit import limiter
from ml.models.registry import ModelRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s",
)
logger = logging.getLogger("vaultai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("VAULTAI ENGINE STARTING")
    logger.info("=" * 60)

    Base.metadata.create_all(bind=engine)

    if not os.environ.get("VAULTAI_SKIP_WARMUP"):
        try:
            ModelRegistry.warmup()
        except Exception as e:
            logger.warning(f"Model warmup skipped (will lazy-load): {e}")
    else:
        logger.info("Model warmup skipped (VAULTAI_SKIP_WARMUP set)")

    yield

    logger.info("VAULTAI ENGINE SHUTTING DOWN")
    ModelRegistry.clear()


app = FastAPI(
    title="VaultAI - Podcast Intelligence Platform",
    description="AI-powered podcast processing, transcription, summarization, and Q&A. "
    "Enterprise-grade features: multi-speaker diarization, RAG Q&A, chapter detection, "
    "key moment extraction, sentiment analysis, multi-format export, cross-podcast search, "
    "real-time WebSocket streaming.",
    version="2.1.0",
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time-Ms"] = str(round(elapsed * 1000, 2))
    if elapsed > 1.0:
        logger.warning(f"SLOW REQUEST [{round(elapsed, 2)}s] {request.method} {request.url.path}")
    return response


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.method == "GET" and response.status_code == 200:
        if not response.headers.get("Cache-Control"):
            response.headers["Cache-Control"] = "public, max-age=60, s-maxage=120"
    return response


app.include_router(auth_router, prefix="/auth")
app.include_router(payments_router, prefix="/payments")
app.include_router(upload_router, prefix="/upload")
app.include_router(ingest_router, prefix="/ingest")
app.include_router(query_router, prefix="/query")
app.include_router(vaults_router, prefix="/vaults")
app.include_router(admin_router, prefix="/admin")
app.include_router(ws_router, prefix="/ws")
app.include_router(comparison_router, prefix="/compare")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="VaultAI - Podcast Intelligence Platform",
        version="2.1.0",
        description="AI-powered podcast processing, transcription, summarization, and Q&A. "
        "Enterprise-grade features: multi-speaker diarization, RAG Q&A, chapter detection, "
        "key moment extraction, sentiment analysis, multi-format export, cross-podcast search, "
        "real-time WebSocket streaming.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            if method.get("operationId") not in (
                "health_check", "register", "login", "paystack_webhook",
                "verify_payment", "ws_transcribe",
            ):
                method.setdefault("security", [{"BearerAuth": []}])
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
