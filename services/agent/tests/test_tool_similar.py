"""Tool 3 tests: find_similar_movies (isolated, fakes only)."""

import json

import pytest

from app.movies_client import MoviesServiceError, find_similar_movies
from app.orchestrator import run_chat
from app.tools import SIMILAR_SPEC, TOOL_SPECS, create_similar_tool

pytestmark = pytest.mark.anyio


class FakeChatModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def chat(self, messages, tools):
        self.calls.append((messages, tools))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"items": []}

    def json(self):
        return self._payload


async def fake_search_unreachable(query, limit=5):
    raise MoviesServiceError("movies service unreachable: Timeout")


async def test_similar_client_hits_existing_endpoint():
    seen = {}

    async def fetch(url, *, headers, params, timeout_s):
        seen.update(url=url, params=params, headers=headers)
        return FakeResponse(200, {"items": [{"tmdb_id": 104}]})

    items = await find_similar_movies(101, 2, base_url="http://m:8002/", internal_key="k", fetch=fetch)
    assert items == [{"tmdb_id": 104}]
    assert seen["url"] == "http://m:8002/movies/101/similar"
    assert seen["params"] == {"limit": 2}
    assert seen["headers"] == {"X-Internal-Key": "k"}


async def test_similar_client_unknown_source_and_clean_errors():
    async def missing(url, *, headers, params, timeout_s):
        return FakeResponse(404, {"detail": "movie 999 not found"})

    with pytest.raises(MoviesServiceError) as exc:
        await find_similar_movies(999, 5, base_url="http://m", internal_key="k", fetch=missing)
    assert "999" in str(exc.value)

    async def boom(url, *, headers, params, timeout_s):
        raise TimeoutError("slow")

    with pytest.raises(MoviesServiceError) as exc2:
        await find_similar_movies(1, 5, base_url="http://m", internal_key="SUPERSECRET", fetch=boom)
    assert "SUPERSECRET" not in str(exc2.value)


async def test_similar_flow_collects_ids():
    async def similar(movie_id, limit=5):
        assert (movie_id, limit) == (101, 2)
        return [{"tmdb_id": 104, "title": "Alpha Returns", "year": 2022, "genres": ["Action"]}]

    model = FakeChatModel(
        [
            {
                "content": "",
                "tool_calls": [{"id": "c1", "name": "find_similar_movies", "args": {"movie_id": 101, "limit": 2}}],
            },
            {"content": "More like Alpha Dawn.", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "more like Alpha Dawn",
        chat_model=model,
        search_movies=fake_search_unreachable,
        extra_tools={"find_similar_movies": similar},
    )
    assert ids == [104] and reply == "More like Alpha Dawn."


async def test_similar_unknown_source_reports_not_found():
    async def missing(movie_id, limit=5):
        raise MoviesServiceError(f"movie {movie_id} not found")

    model = FakeChatModel(
        [
            {"content": "", "tool_calls": [{"id": "c1", "name": "find_similar_movies", "args": {"movie_id": 999}}]},
            {"content": "unknown", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "like 999", chat_model=model, search_movies=fake_search_unreachable,
        extra_tools={"find_similar_movies": missing},
    )
    assert ids == []
    assert "999" in [m for m in model.calls[1][0] if m["role"] == "tool"][0]["content"]


async def test_similar_spec_and_langchain_factory():
    assert SIMILAR_SPEC["name"] == "find_similar_movies"
    assert "movie_id" in SIMILAR_SPEC["parameters"]["required"]
    assert SIMILAR_SPEC in TOOL_SPECS

    async def similar(movie_id, limit=5):
        return [{"tmdb_id": 104, "title": "Alpha Returns", "year": 2022, "genres": ["Action"]}]

    tool = create_similar_tool(similar)
    assert tool.name == "find_similar_movies"
    assert json.loads(await tool.ainvoke({"movie_id": 101}))[0]["tmdb_id"] == 104
