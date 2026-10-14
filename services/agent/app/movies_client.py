"""Movies-service client (the agent's only data source).

Uses the existing movies-service contract — no contract change needed:
  GET {MOVIES_SERVICE_URL}/movies/search?q=<query>&limit=<n>
  -> {items: [{tmdb_id, title, ...}], page, limit, total}

Every request carries X-Internal-Key. Failures raise MoviesServiceError
with status info only — the API key is never included in messages or logs.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable


class MoviesServiceError(Exception):
    """The movies service is unreachable, timed out, or returned an error."""


def build_search_request(base_url: str, internal_key: str, query: str, limit: int) -> tuple[str, dict, dict]:
    """Pure helper: URL, query params, and headers for a search call."""
    return (
        f"{base_url.rstrip('/')}/movies/search",
        {"q": query, "limit": limit},
        {"X-Internal-Key": internal_key},
    )


async def _fetch(url: str, *, headers: dict, params: dict, timeout_s: float) -> Any:
    import httpx  # lazy: keeps this module importable without httpx installed

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        return await client.get(url, headers=headers, params=params)


async def search_movies(
    query: str,
    limit: int = 5,
    *,
    base_url: str,
    internal_key: str,
    timeout_s: float = 10.0,
    fetch: Callable[..., Awaitable[Any]] = _fetch,
) -> list[dict]:
    """Search movies; returns raw item dicts (may be empty)."""
    url, params, headers = build_search_request(base_url, internal_key, query, limit)
    try:
        response = await fetch(url, headers=headers, params=params, timeout_s=timeout_s)
    except Exception as exc:
        raise MoviesServiceError(f"movies service unreachable: {type(exc).__name__}") from exc
    status = getattr(response, "status_code", 200)
    if status != 200:
        raise MoviesServiceError(f"movies service returned status {status}")
    try:
        payload = response.json() if callable(getattr(response, "json", None)) else response
        items = payload.get("items", []) if isinstance(payload, dict) else []
    except Exception as exc:
        raise MoviesServiceError("movies service returned an unreadable response") from exc
    return [item for item in items if isinstance(item, dict)]
