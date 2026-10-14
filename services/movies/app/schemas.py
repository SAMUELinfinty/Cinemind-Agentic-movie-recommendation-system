"""Response schemas for the movies service.

Proposed contract (docs/API_CONTRACTS.md does not exist yet; per
PROJECT_PLAN.md it will become the source of truth once written):

- GET /movies?page&limit            -> PaginatedMovies
- GET /movies/search?q&page&limit   -> PaginatedMovies
- GET /movies/{movie_id}            -> Movie (404 when unknown)
- GET /discover?genre&year&language&min_vote&page&limit -> PaginatedMovies
- GET /trending?limit               -> TrendingResponse
- GET /movies/{movie_id}/similar?limit -> SimilarResponse (404 when source unknown)

``movie_id`` is the numeric TMDB id (``tmdb_id``), the stable identifier
written by seed.py. List responses use a consistent envelope
``{items, page, limit, total}``.
"""

from __future__ import annotations

from pydantic import BaseModel


class Movie(BaseModel):
    tmdb_id: int
    title: str
    imdb_id: str | None = None
    original_title: str | None = None
    original_language: str | None = None
    release_date: str | None = None
    year: int | None = None
    runtime_min: int | None = None
    genres: list[str] = []
    popularity: float | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    budget_usd: int | None = None
    revenue_usd: int | None = None
    overview: str | None = None
    tagline: str | None = None
    director: str | None = None
    top_cast: list[str] = []
    production_companies: list[str] = []
    production_countries: list[str] = []
    us_rating: str | None = None
    keywords: list[str] = []
    poster_path: str | None = None
    tmdb_url: str | None = None


class PaginatedMovies(BaseModel):
    items: list[Movie]
    page: int
    limit: int
    total: int


class TrendingResponse(BaseModel):
    items: list[Movie]
    limit: int
    ranking: str


class SimilarResponse(BaseModel):
    items: list[Movie]
    movie_id: int
    rule: str
