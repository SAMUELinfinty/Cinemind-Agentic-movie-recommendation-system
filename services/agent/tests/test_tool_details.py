"""Tool 1 tests: get_movie_details (isolated, fakes only)."""

import json

import pytest

from app.movies_client import MoviesServiceError, get_movie_details
from app.orchestrator import run_chat
from app.tools import DETAILS_SPEC, TOOL_SPECS, create_details_tool

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
        self._payload = payload

    def json(self):
        return self._payload


async def fake_details_ok(movie_id):
    assert movie_id == 101
    return {"tmdb_id": 101, "title": "Alpha Dawn", "year": 2024, "genres": ["Action"]}


async def test_details_client_returns_doc_and_none_on_404():
    async def fetch(url, *, headers, params, timeout_s):
        assert url.endswith("/movies/101")
        assert headers == {"X-Internal-Key": "k"}
        return FakeResponse(200, {"tmdb_id": 101, "title": "Alpha Dawn"})

    doc = await get_movie_details(101, base_url="http://m:8002", internal_key="k", fetch=fetch)
    assert doc == {"tmdb_id": 101, "title": "Alpha Dawn"}

    async def missing(url, *, headers, params, timeout_s):
        return FakeResponse(404, {"detail": "movie 101 not found"})

    assert await get_movie_details(101, base_url="http://m:8002", internal_key="k", fetch=missing) is None


async def test_details_client_errors_stay_clean():
    async def boom(url, *, headers, params, timeout_s):
        raise TimeoutError("slow")

    with pytest.raises(MoviesServiceError) as exc:
        await get_movie_details(1, base_url="http://m", internal_key="SUPERSECRET", fetch=boom)
    assert "SUPERSECRET" not in str(exc.value)


async def test_details_flow_returns_id():
    model = FakeChatModel(
        [
            {"content": "", "tool_calls": [{"id": "c1", "name": "get_movie_details", "args": {"movie_id": 101}}]},
            {"content": "Alpha Dawn (2024).", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "tell me about 101",
        chat_model=model,
        search_movies=fake_search_unreachable,
        extra_tools={"get_movie_details": fake_details_ok},
    )
    assert ids == [101]
    assert reply == "Alpha Dawn (2024)."
    tool_content = json.loads([m for m in model.calls[1][0] if m["role"] == "tool"][0]["content"])
    assert tool_content["movie"]["tmdb_id"] == 101
    assert tool_content["similar"] == []


async def test_details_flow_attaches_similar_films():
    async def similar(movie_id, limit=5):
        assert movie_id == 101
        return [{"tmdb_id": 104, "title": "Alpha Returns", "year": 2022, "genres": ["Action"]}]

    model = FakeChatModel(
        [
            {"content": "", "tool_calls": [{"id": "c1", "name": "get_movie_details", "args": {"movie_id": 101}}]},
            {"content": "Alpha Dawn plus one like it.", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "tell me about 101 and suggest similar films",
        chat_model=model,
        search_movies=fake_search_unreachable,
        extra_tools={"get_movie_details": fake_details_ok, "find_similar_movies": similar},
    )
    assert ids == [101, 104]
    tool_content = json.loads([m for m in model.calls[1][0] if m["role"] == "tool"][0]["content"])
    assert tool_content["movie"]["tmdb_id"] == 101
    assert [s["tmdb_id"] for s in tool_content["similar"]] == [104]


async def fake_search_unreachable(query, limit=5):
    raise MoviesServiceError("movies service unreachable: Timeout")


async def test_details_unknown_id_reports_not_found():
    async def missing(movie_id):
        return None

    model = FakeChatModel(
        [
            {"content": "", "tool_calls": [{"id": "c1", "name": "get_movie_details", "args": {"movie_id": 999}}]},
            {"content": "not found", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "tell me about 999",
        chat_model=model,
        search_movies=fake_search_unreachable,
        extra_tools={"get_movie_details": missing},
    )
    assert ids == []
    tool_content = [m for m in model.calls[1][0] if m["role"] == "tool"][0]["content"]
    assert "999" in tool_content and "not found" in tool_content


async def test_details_rejects_bad_id_without_calling_service():
    called = []

    async def spy(movie_id):
        called.append(movie_id)
        return {}

    model = FakeChatModel(
        [
            {"content": "", "tool_calls": [{"id": "c1", "name": "get_movie_details", "args": {}}]},
            {"content": "need an id", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "details please", chat_model=model, search_movies=fake_search_unreachable,
        extra_tools={"get_movie_details": spy},
    )
    assert ids == [] and called == []
    assert "movie_id" in [m for m in model.calls[1][0] if m["role"] == "tool"][0]["content"]


async def test_details_tool_spec_and_langchain_factory():
    assert DETAILS_SPEC["name"] == "get_movie_details"
    assert "movie_id" in DETAILS_SPEC["parameters"]["required"]
    assert DETAILS_SPEC in TOOL_SPECS
    tool = create_details_tool(fake_details_ok)
    assert tool.name == "get_movie_details"
    assert json.loads(await tool.ainvoke({"movie_id": 101}))["movie"]["title"] == "Alpha Dawn"
    async def missing(mid):
        return None

    assert "not found" in await create_details_tool(missing).ainvoke({"movie_id": 5})
