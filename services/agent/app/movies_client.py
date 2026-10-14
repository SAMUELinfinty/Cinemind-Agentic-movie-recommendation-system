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


async def _fetch_json(
    url: str,
    *,
    headers: dict,
    params: dict,
    timeout_s: float,
    fetch: Callable[..., Awaitable[Any]],
    service: str,
) -> tuple[int, Any]:
    """GET and parse JSON. Returns (status, payload or None)."""
    try:
        response = await fetch(url, headers=headers, params=params, timeout_s=timeout_s)
    except Exception as exc:
        raise MoviesServiceError(f"{service} unreachable: {type(exc).__name__}") from exc
    status = getattr(response, "status_code", 200)
    if status != 200:
        return status, None
    try:
        payload = response.json() if callable(getattr(response, "json", None)) else response
    except Exception as exc:
        raise MoviesServiceError(f"{service} returned an unreadable response") from exc
    return status, payload


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
    status, payload = await _fetch_json(
        url, headers=headers, params=params, timeout_s=timeout_s, fetch=fetch,
        service="movies service",
    )
    if status != 200:
        raise MoviesServiceError(f"movies service returned status {status}")
    items = payload.get("items", []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)]


async def get_movie_details(
    movie_id: int,
    *,
    base_url: str,
    internal_key: str,
    timeout_s: float = 10.0,
    fetch: Callable[..., Awaitable[Any]] = _fetch,
) -> dict | None:
    """Fetch one movie by tmdb_id. Returns None when unknown (HTTP 404)."""
    url = f"{base_url.rstrip('/')}/movies/{movie_id}"
    headers = {"X-Internal-Key": internal_key}
    status, payload = await _fetch_json(
        url, headers=headers, params={}, timeout_s=timeout_s, fetch=fetch,
        service="movies service",
    )
    if status == 404:
        return None
    if status != 200:
        raise MoviesServiceError(f"movies service returned status {status}")
    return payload if isinstance(payload, dict) else None


async def discover_movies(
    filters: dict,
    limit: int = 5,
    *,
    base_url: str,
    internal_key: str,
    timeout_s: float = 10.0,
    fetch: Callable[..., Awaitable[Any]] = _fetch,
) -> list[dict]:
    """Discover movies by metadata filters (genre/year/language/min_vote).

    Only keys the movies service supports are forwarded; anything else is
    ignored rather than invented into the query.
    """
    allowed = ("genre", "year", "language", "min_vote")
    params = {k: v for k, v in (filters or {}).items() if k in allowed and v is not None}
    params["limit"] = limit
    url = f"{base_url.rstrip('/')}/discover"
    headers = {"X-Internal-Key": internal_key}
    status, payload = await _fetch_json(
        url, headers=headers, params=params, timeout_s=timeout_s, fetch=fetch,
        service="movies service",
    )
    if status != 200:
        raise MoviesServiceError(f"movies service returned status {status}")
    items = payload.get("items", []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)]


async def find_similar_movies(
    movie_id: int,
    limit: int = 5,
    *,
    base_url: str,
    internal_key: str,
    timeout_s: float = 10.0,
    fetch: Callable[..., Awaitable[Any]] = _fetch,
) -> list[dict]:
    """Find movies similar to one tmdb_id (genre-overlap rule, server-side)."""
    url = f"{base_url.rstrip('/')}/movies/{movie_id}/similar"
    headers = {"X-Internal-Key": internal_key}
    status, payload = await _fetch_json(
        url, headers=headers, params={"limit": limit}, timeout_s=timeout_s, fetch=fetch,
        service="movies service",
    )
    if status == 404:
        raise MoviesServiceError(f"movie {movie_id} not found")
    if status != 200:
        raise MoviesServiceError(f"movies service returned status {status}")
    items = payload.get("items", []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)]
