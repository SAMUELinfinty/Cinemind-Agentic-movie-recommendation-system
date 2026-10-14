"""Dataset accuracy: real CSV rows through the seed validator and ranking.

Grounds the audit's movie-accuracy claim in tmdb_top1000_movies.csv itself:
every ID the pipeline cites must exist, be unique, and rank sanely.
"""

from pathlib import Path

from app.recommendations import TRENDING_SORT, rank_similar

import seed as seed_module

CSV_PATH = Path(__file__).resolve().parent.parent.parent.parent / "tmdb_top1000_movies.csv"


def load_documents():
    documents, skipped, total = seed_module.load_rows(CSV_PATH)
    return documents, skipped, total


def test_csv_row_counts_are_stable():
    documents, skipped, total = load_documents()
    assert total == 1000
    assert len(documents) == 1000
    assert skipped == []


def test_tmdb_ids_are_unique_and_present():
    documents, _, _ = load_documents()
    ids = [doc["tmdb_id"] for doc in documents]
    assert len(set(ids)) == 1000
    assert all(isinstance(i, int) and i > 0 for i in ids)
    by_id = {doc["tmdb_id"]: doc for doc in documents}
    # Spot-check a known row straight from the file.
    assert by_id[1115544]["title"] == "Mike & Nick & Nick & Alice"
    assert "Comedy" in by_id[1115544]["genres"]


def test_similar_ranking_on_real_docs_shares_genres():
    documents, _, _ = load_documents()
    source = next(d for d in documents if "Action" in d["genres"] and len(d["genres"]) >= 2)
    ranked = rank_similar(source, [d for d in documents if d["tmdb_id"] != source["tmdb_id"]], 5)
    assert len(ranked) == 5
    source_genres = set(source["genres"])
    overlaps = [len(source_genres & set(c["genres"])) for c in ranked]
    assert all(o >= 1 for o in overlaps)
    assert overlaps == sorted(overlaps, reverse=True)
    assert source["tmdb_id"] not in [c["tmdb_id"] for c in ranked]


def test_trending_sort_contract_matches_repo_order():
    assert TRENDING_SORT == [("popularity", -1), ("vote_average", -1)]
    documents, _, _ = load_documents()
    top = sorted(
        documents,
        key=lambda d: (-(d["popularity"] or 0.0), -(d["vote_average"] or 0.0)),
    )[:3]
    assert all(t["popularity"] for t in top)
    assert top[0]["popularity"] >= top[1]["popularity"] >= top[2]["popularity"]
