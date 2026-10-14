"""MongoDB access layer (connection + indexes; no seeding logic here).

The motor import is deferred to get_client() so modules (and tests with a
fake collection) import cleanly when motor is not installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import settings

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

_client: Any = None

COLLECTION_NAME = settings.MONGODB_COLLECTION


def get_client() -> Any:
    """Return a shared Motor client built from environment configuration."""
    global _client
    if _client is None:
        from motor.motor_asyncio import AsyncIOMotorClient

        _client = AsyncIOMotorClient(settings.MONGODB_URI)
    return _client


def get_db() -> Any:
    """Return the configured MongoDB database handle."""
    return get_client()[settings.MONGODB_DB]


def get_collection() -> Any:
    """Return the movies collection handle."""
    return get_db()[COLLECTION_NAME]


async def ensure_indexes() -> None:
    """Create lookup/search indexes. Idempotent; mirrors seed.py index specs."""
    collection = get_collection()
    await collection.create_index("tmdb_id", unique=True)
    await collection.create_index("title")
    await collection.create_index([("year", -1)])
    await collection.create_index("genres")
    try:
        await collection.create_index(
            [("title", "text"), ("original_title", "text"), ("overview", "text")],
            name="movie_text_search",
        )
    except Exception:
        pass  # a conflicting text index already exists; leave it alone


async def check_connection() -> bool:
    """Ping MongoDB. Returns False instead of raising, for health reporting."""
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False
