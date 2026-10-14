"""Transparent local-data ranking rules.

No NLP pipelines, embeddings, vector databases, or external movie APIs.
Everything here uses only fields present in the seeded dataset.

Trending: the static top-1000 CSV has no time dimension, so "trending" is a
documented proxy — most popular first, vote average as tiebreak:

    sort = popularity DESC, vote_average DESC

Similar: genre-overlap scoring. For a source movie with genres G, each
candidate scores ``|G ∩ candidate_genres|``; ties break by vote_average DESC,
then popularity DESC. Candidates sharing no genre are excluded; a source
with no genres therefore yields an empty list.
"""

from __future__ import annotations

TRENDING_SORT: list[tuple[str, int]] = [("popularity", -1), ("vote_average", -1)]

TRENDING_DESCRIPTION = (
    "local-data ranking over the seeded catalogue (no time dimension in the "
    "dataset): popularity DESC, vote_average DESC tiebreak"
)

SIMILAR_RULE = (
    "genre-overlap scoring on seeded metadata: shared-genre count DESC, "
    "vote_average DESC tiebreak, popularity DESC final tiebreak"
)


def _num(value) -> float:
    return value if isinstance(value, (int, float)) else 0.0


def similarity_key(source_genres: set[str], candidate: dict) -> tuple:
    """Sort key for one candidate (higher overlap sorts first via reverse)."""
    overlap = len(source_genres & set(candidate.get("genres") or []))
    return (overlap, _num(candidate.get("vote_average")), _num(candidate.get("popularity")))


def rank_similar(source: dict, candidates: list[dict], limit: int) -> list[dict]:
    """Order candidates by genre overlap; drop zero-overlap entries."""
    source_genres = set(source.get("genres") or [])
    if not source_genres:
        return []
    scored = [
        (similarity_key(source_genres, cand), cand)
        for cand in candidates
        if source_genres & set(cand.get("genres") or [])
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [cand for _, cand in scored[:limit]]


def find_similar_movies(source: dict, candidates: list[dict], limit: int = 10) -> list[dict]:
    """Pure helper kept for backwards compatibility; prefers rank_similar."""
    return rank_similar(source, candidates, limit)
