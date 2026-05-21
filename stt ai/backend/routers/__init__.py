from backend.routers.auth import router as auth_router
from backend.routers.payments import router as payments_router
from backend.routers.upload import router as upload_router
from backend.routers.ingest import router as ingest_router
from backend.routers.query import router as query_router
from backend.routers.vaults import router as vaults_router
from backend.routers.admin import router as admin_router
from backend.routers.ws import router as ws_router
from backend.routers.comparison import router as comparison_router

__all__ = [
    "auth_router", "payments_router", "upload_router",
    "ingest_router", "query_router", "vaults_router", "admin_router",
    "ws_router", "comparison_router",
]
