from fastapi import APIRouter

router = APIRouter(tags=["Admin"])


@router.get("/health", response_model=dict)
def health_check():
    return {"status": "healthy", "version": "2.0.0"}
