"""Internal-service authentication (X-Internal-Key)."""

import hmac

from fastapi import HTTPException, Request

from .config import settings


async def require_internal_key(request: Request) -> None:
    """Reject requests without the shared internal key (401, no details leaked)."""
    expected = settings.INTERNAL_API_KEY
    if not expected:
        raise HTTPException(status_code=500, detail="Service misconfigured")
    provided = request.headers.get("x-internal-key", "")
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
