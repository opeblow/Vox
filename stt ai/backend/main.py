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
    auth_router, upload_router,
    ingest_router, query_router, vaults_router, admin_router,
    ws_router, comparison_router, transcribe_router,
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
    allow_credentials=False,  # cannot use credentials=True with allow_origins=["*"]
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
    # Only the health check endpoint is truly public; everything else is user-scoped.
    # Use "private" so downstream CDNs/proxies never cache authenticated user data.
    if request.method == "GET" and response.status_code == 200:
        if not response.headers.get("Cache-Control"):
            if request.url.path == "/admin/health":
                response.headers["Cache-Control"] = "public, max-age=10, s-maxage=10"
            else:
                response.headers["Cache-Control"] = "private, max-age=0, no-store"
    return response


app.include_router(auth_router, prefix="/auth")
app.include_router(upload_router, prefix="/upload")
app.include_router(ingest_router, prefix="/ingest")
app.include_router(query_router, prefix="/query")
app.include_router(vaults_router, prefix="/vaults")
app.include_router(admin_router, prefix="/admin")
app.include_router(ws_router, prefix="/ws")
app.include_router(comparison_router, prefix="/compare")
app.include_router(transcribe_router, prefix="/transcribe")


# Paths that require NO bearer token in the Swagger UI.
_PUBLIC_PATHS = {
    ("/admin/health", "get"),
    ("/auth/register", "post"),
    ("/auth/login", "post"),
}


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
    # Merge BearerAuth into whatever FastAPI already generated (keeps HTTPBearer definition).
    openapi_schema["components"].setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    # Replace the per-endpoint HTTPBearer reference with BearerAuth so the
    # Swagger UI "Authorize" button actually populates the correct header.
    for path_str, path_item in openapi_schema["paths"].items():
        for http_method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            is_public = (path_str, http_method.lower()) in _PUBLIC_PATHS
            if is_public:
                # Explicitly mark public endpoints as requiring no security.
                operation["security"] = []
            else:
                # Override whatever FastAPI generated (e.g. HTTPBearer) with BearerAuth.
                operation["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
