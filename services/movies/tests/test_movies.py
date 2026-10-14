"""Tests for the movies service endpoints (in-memory fake collection, no Mongo)."""

import re

import pytest
from fastapi.testclient import TestClient

import app.routes.movies as movies_routes
from app.main import app


def make_doc(tmdb_id, title, genres, popularity, vote_average, year, language):
    return {
        "_id": f"tmdb-{tmdb_id}",
        "tmdb_id": tmdb_id,
        "title": title,
        "original_title": title,
        "original_language": language,
        "year": year,
        "genres": genres,
        "popularity": popularity,
        "vote_average": vote_average,
    }


FIXTURES = [
    make_doc(101, "Alpha Dawn", ["Action", "Sci-Fi"], 90.0, 8.0, 2024, "en"),
    make_doc(102, "Beta Night", ["Action", "Drama"], 80.0, 7.5, 2023, "en"),
    make_doc(103, "Gamma Ray", ["Comedy"], 95.0, 6.0, 2024, "fr"),
    make_doc(104, "Alpha Returns", ["Action", "Sci-Fi", "Drama"], 70.0, 8.5, 2022, "en"),
    make_doc(105, "Delta Quiet", [], 10.0, 5.0, 2020, "en"),
]


def _match(doc, filt):
    for key, cond in filt.items():
        if key == "$or":
            if not any(_match(doc, sub) for sub in cond):
                return False
            continue
        value = doc.get(key)
        if isinstance(cond, dict):
            if "$regex" in cond:
                flags = re.IGNORECASE if cond.get("$options") == "i" else 0
                # MongoDB semantics: regex tests each array element.
                candidates = value if isinstance(value, list) else [value or ""]
                if not any(re.search(cond["$regex"], str(v or ""), flags) for v in candidates):
                    return False
            elif "$in" in cond:
                actual = value if isinstance(value, list) else [value]
                if not any(v in cond["$in"] for v in actual):
                    return False
            elif "$ne" in cond:
                if value == cond["$ne"]:
                    return False
            elif "$gte" in cond:
                if value is None or value < cond["$gte"]:
                    return False
            else:
                raise AssertionError(f"unsupported operator in tests: {cond}")
        elif isinstance(value, list):
            # MongoDB semantics: scalar equality matches array contents.
            if cond not in value:
                return False
        elif value != cond:
            return False
    return True


def _sort_key(doc, field):
    value = doc.get(field)
    if isinstance(value, bool):
        return (0, int(value), "")
    if isinstance(value, (int, float)):
        return (0, value, "")
    if isinstance(value, str):
        return (0, 0, value)
    if isinstance(value, list):
        return (0, 0, ",".join(value))
    return (1, 0, "")  # None / missing sorts last


class FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, key, direction=None):
        pairs = [(key, direction)] if isinstance(key, str) else list(key)
        for field, order in reversed(pairs):
            self._docs.sort(key=lambda d: _sort_key(d, field), reverse=(order == -1))
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        docs = self._docs if length is None else self._docs[:length]
        return [dict(d) for d in docs]


class FakeCollection:
    def __init__(self, docs):
        self._docs = [dict(d) for d in docs]

    def _apply_projection(self, doc, projection):
        if projection:
            excluded = {k for k, v in projection.items() if v == 0}
            return {k: v for k, v in doc.items() if k not in excluded}
        return dict(doc)

    async def count_documents(self, filt):
        return sum(1 for d in self._docs if _match(d, filt))

    def find(self, filt, projection=None):
        return FakeCursor(self._apply_projection(d, projection) for d in self._docs if _match(d, filt))

    async def find_one(self, filt, projection=None):
        for doc in self._docs:
            if _match(doc, filt):
                return self._apply_projection(doc, projection)
        return None


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(movies_routes, "get_collection", lambda: FakeCollection(FIXTURES))
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "service": "movies"}


def test_list_movies(client):
    body = client.get("/movies").json()
    assert body["total"] == 5
    assert [m["title"] for m in body["items"]] == [
        "Alpha Dawn", "Alpha Returns", "Beta Night", "Delta Quiet", "Gamma Ray",
    ]


def test_list_pagination(client):
    body = client.get("/movies", params={"page": 2, "limit": 2}).json()
    assert body["page"] == 2 and body["total"] == 5
    assert [m["title"] for m in body["items"]] == ["Beta Night", "Delta Quiet"]


def test_list_invalid_params(client):
    assert client.get("/movies", params={"page": 0}).status_code == 422
    assert client.get("/movies", params={"limit": 101}).status_code == 422


def test_search_match(client):
    body = client.get("/movies/search", params={"q": "alpha"}).json()
    assert body["total"] == 2
    assert body["items"][0]["title"] == "Alpha Dawn"  # higher popularity first


def test_search_no_match(client):
    body = client.get("/movies/search", params={"q": "zzz"}).json()
    assert body == {"items": [], "page": 1, "limit": 20, "total": 0}


def test_search_multi_word_uses_or_semantics(client):
    body = client.get("/movies/search", params={"q": "alpha night"}).json()
    assert body["total"] == 3
    assert [m["title"] for m in body["items"]] == ["Alpha Dawn", "Beta Night", "Alpha Returns"]


def test_search_matches_genre_words(client):
    body = client.get("/movies/search", params={"q": "comedy"}).json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Gamma Ray"


def test_search_bad_query(client):
    assert client.get("/movies/search").status_code == 422
    assert client.get("/movies/search", params={"q": ""}).status_code == 422


def test_details_found(client):
    body = client.get("/movies/101").json()
    assert body["tmdb_id"] == 101 and body["title"] == "Alpha Dawn"


def test_details_not_found(client):
    resp = client.get("/movies/999")
    assert resp.status_code == 404


def test_details_non_int_id(client):
    assert client.get("/movies/abc").status_code == 422


def test_discover_genre(client):
    body = client.get("/discover", params={"genre": "Action"}).json()
    assert body["total"] == 3


def test_discover_year_and_language(client):
    body = client.get("/discover", params={"year": 2024, "language": "en"}).json()
    assert body["total"] == 1 and body["items"][0]["title"] == "Alpha Dawn"


def test_discover_min_vote(client):
    body = client.get("/discover", params={"min_vote": 8}).json()
    assert {m["title"] for m in body["items"]} == {"Alpha Dawn", "Alpha Returns"}


def test_discover_no_match(client):
    body = client.get("/discover", params={"genre": "Horror"}).json()
    assert body["total"] == 0 and body["items"] == []


def test_trending_order_and_meta(client):
    body = client.get("/trending", params={"limit": 3}).json()
    assert [m["title"] for m in body["items"]] == ["Gamma Ray", "Alpha Dawn", "Beta Night"]
    assert body["limit"] == 3 and "popularity" in body["ranking"]


def test_similar_overlap_order(client):
    body = client.get("/movies/101/similar").json()
    assert body["movie_id"] == 101
    assert [m["tmdb_id"] for m in body["items"]] == [104, 102]  # 2 vs 1 shared genres
    assert "genre" in body["rule"]


def test_similar_unknown_source(client):
    assert client.get("/movies/999/similar").status_code == 404


def test_similar_source_without_genres(client):
    body = client.get("/movies/105/similar").json()
    assert body["items"] == []
