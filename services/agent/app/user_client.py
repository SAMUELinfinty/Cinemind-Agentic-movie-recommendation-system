"""Express user-context client (profile / watchlist / ratings).

Uses only approved, existing Express endpoints — no new routes needed:
  GET {EXPRESS_API_URL}/api/users/me   (Bearer) -> {user: {email, name}}
  GET {EXPRESS_API_URL}/api/watchlist  (Bearer) -> {items: [{movieId, ...}]}
  GET {EXPRESS_API_URL}/api/ratings    (Bearer) -> {items: [{movieId, score}]}

The caller's JWT is forwarded as-is; it is never logged, stored, or echoed
in error messages. Anything but success raises UserContextError.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable


class UserContextError(Exception):
    """Personal data is unavailable: missing, invalid, or expired auth, or outage."""


def build_user_urls(base_url: str) -> dict[str, str]:
    """Pure helper: endpoint URLs for the three approved calls."""
    root = base_url.rstrip("/")
    return {
        "profile": f"{root}/api/users/me",
        "watchlist": f"{root}/api/watchlist",
        "ratings": f"{root}/api/ratings",
    }


async def _fetch(url: str, *, headers: dict, params: dict, timeout_s: float) -> Any:
    import httpx  # lazy: keeps this module importable without httpx installed

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        return await client.get(url, headers=headers, params=params)


def _movie_ids(items: Any) -> list[int]:
    ids: list[int] = []
    if isinstance(items, list):
        for entry in items:
            if isinstance(entry, dict):
                mid = entry.get("movieId")
                if isinstance(mid, int) and not isinstance(mid, bool) and mid not in ids:
                    ids.append(mid)
    return ids


async def get_user_context(
    user_token: str | None,
    *,
    base_url: str,
    timeout_s: float = 10.0,
    fetch: Callable[..., Awaitable[Any]] = _fetch,
) -> dict:
    """Fetch trimmed profile + watchlist movie ids + ratings.

    Raises UserContextError when no token is supplied, the token is rejected,
    or the Express API is unreachable.
    """
    if not user_token:
        raise UserContextError("no user authentication provided")
    headers = {"Authorization": f"Bearer {user_token}"}
    urls = build_user_urls(base_url)
    try:
        responses = [
            await fetch(url, headers=headers, params={}, timeout_s=timeout_s)
            for url in (urls["profile"], urls["watchlist"], urls["ratings"])
        ]
    except Exception as exc:
        raise UserContextError(f"profile service unreachable: {type(exc).__name__}") from exc
    for response in responses:
        status = getattr(response, "status_code", 200)
        if status in (401, 403):
            raise UserContextError("user authentication is invalid or expired")
        if status != 200:
            raise UserContextError(f"profile service returned status {status}")
    try:
        profile_payload = responses[0].json()
        watchlist_payload = responses[1].json()
        ratings_payload = responses[2].json()
    except Exception as exc:
        raise UserContextError("profile service returned an unreadable response") from exc
    user = profile_payload.get("user", {}) if isinstance(profile_payload, dict) else {}
    ratings = []
    raw_ratings = ratings_payload.get("items", []) if isinstance(ratings_payload, dict) else []
    if isinstance(raw_ratings, list):
        for entry in raw_ratings:
            if isinstance(entry, dict) and isinstance(entry.get("movieId"), int):
                ratings.append({"movieId": entry["movieId"], "score": entry.get("score")})
    watchlist_items = (
        watchlist_payload.get("items", []) if isinstance(watchlist_payload, dict) else []
    )
    return {
        "profile": {"email": user.get("email"), "name": user.get("name")},
        "watchlist": _movie_ids(watchlist_items),
        "ratings": ratings,
    }
