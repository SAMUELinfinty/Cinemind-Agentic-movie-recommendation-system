"""Health endpoint (no auth, no DB requirement to report healthy)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "movies"}
