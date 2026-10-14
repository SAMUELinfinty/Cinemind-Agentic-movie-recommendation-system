"""MongoDB data access for movies (query logic only, no HTTP concerns)."""

from __future__ import annotations

import re

from .recommendations import TRENDING_SORT, rank_similar

PROJECTION = {"_id": 0}


def serialize(doc: dict) -> dict:
    """Drop the internal Mongo _id before returning a document."""
    return {k: v for k, v in doc.items() if k != "_id"}


async def list_movies(collection, page: int, limit: int) -> tuple[list[dict], int]:
    total = await collection.count_documents({})
    cursor = collection.find({}, PROJECTION).sort("title", 1).skip((page - 1) * limit).limit(limit)
    return [serialize(d) for d in await cursor.to_list(length=limit)], total


async def search_movies(collection, q: str, page: int, limit: int) -> tuple[list[dict], int]:
    """Case-insensitive substring match on title / original_title."""
    pattern = {"$regex": re.escape(q.strip()), "$options": "i"}
    filt = {"$or": [{"title": pattern}, {"original_title": pattern}]}
    total = await collection.count_documents(filt)
    cursor = (
        collection.find(filt, PROJECTION)
        .sort("popularity", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    return [serialize(d) for d in await cursor.to_list(length=limit)], total


async def get_movie(collection, tmdb_id: int) -> dict | None:
    doc = await collection.find_one({"tmdb_id": tmdb_id}, PROJECTION)
    return serialize(doc) if doc else None


async def discover_movies(
    collection,
    genre: str | None,
    year: int | None,
    language: str | None,
    min_vote: float | None,
    page: int,
    limit: int,
) -> tuple[list[dict], int]:
    filt: dict = {}
    if genre:
        filt["genres"] = genre
    if year is not None:
        filt["year"] = year
    if language:
        filt["original_language"] = language
    if min_vote is not None:
        filt["vote_average"] = {"$gte": min_vote}
    total = await collection.count_documents(filt)
    cursor = (
        collection.find(filt, PROJECTION)
        .sort("popularity", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    return [serialize(d) for d in await cursor.to_list(length=limit)], total


async def trending_movies(collection, limit: int) -> list[dict]:
    cursor = collection.find({}, PROJECTION).sort(TRENDING_SORT).limit(limit)
    return [serialize(d) for d in await cursor.to_list(length=limit)]


async def similar_movies(collection, tmdb_id: int, limit: int) -> tuple[list[dict] | None, dict | None]:
    """Returns (items, source); items is None when the source movie is unknown."""
    source = await collection.find_one({"tmdb_id": tmdb_id}, PROJECTION)
    if source is None:
        return None, None
    source = serialize(source)
    if not source.get("genres"):
        return [], source
    cursor = collection.find(
        {"tmdb_id": {"$ne": tmdb_id}, "genres": {"$in": source["genres"]}},
        PROJECTION,
    )
    candidates = [serialize(d) for d in await cursor.to_list(length=1000)]
    return rank_similar(source, candidates, limit), source
