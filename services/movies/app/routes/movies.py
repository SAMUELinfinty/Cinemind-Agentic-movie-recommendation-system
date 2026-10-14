"""Movie endpoints (thin HTTP layer; queries live in movies_repo)."""

from fastapi import APIRouter, HTTPException, Query

from ..db import get_collection
from .. import movies_repo
from ..recommendations import SIMILAR_RULE, TRENDING_DESCRIPTION
from ..schemas import Movie, PaginatedMovies, SimilarResponse, TrendingResponse

router = APIRouter()


@router.get("/movies", response_model=PaginatedMovies)
async def list_movies(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await movies_repo.list_movies(get_collection(), page, limit)
    return {"items": items, "page": page, "limit": limit, "total": total}


@router.get("/movies/search", response_model=PaginatedMovies)
async def search_movies(
    q: str = Query(min_length=1),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await movies_repo.search_movies(get_collection(), q, page, limit)
    return {"items": items, "page": page, "limit": limit, "total": total}


@router.get("/movies/{movie_id}", response_model=Movie)
async def get_movie_details(movie_id: int) -> dict:
    doc = await movies_repo.get_movie(get_collection(), movie_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"movie {movie_id} not found")
    return doc


@router.get("/discover", response_model=PaginatedMovies)
async def discover_movies(
    genre: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=1888, le=2100),
    language: str | None = Query(default=None),
    min_vote: float | None = Query(default=None, ge=0, le=10),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await movies_repo.discover_movies(
        get_collection(), genre, year, language, min_vote, page, limit
    )
    return {"items": items, "page": page, "limit": limit, "total": total}


@router.get("/trending", response_model=TrendingResponse)
async def trending_movies(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    items = await movies_repo.trending_movies(get_collection(), limit)
    return {"items": items, "limit": limit, "ranking": TRENDING_DESCRIPTION}


@router.get("/movies/{movie_id}/similar", response_model=SimilarResponse)
async def similar_movies(
    movie_id: int,
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    items, _source = await movies_repo.similar_movies(get_collection(), movie_id, limit)
    if items is None:
        raise HTTPException(status_code=404, detail=f"movie {movie_id} not found")
    return {"items": items, "movie_id": movie_id, "rule": SIMILAR_RULE}
