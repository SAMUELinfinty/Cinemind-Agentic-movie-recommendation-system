"""Tests for the agent service (fakes only; no network, no real LLM)."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

import app.routes.chat as chat_route

pytestmark = pytest.mark.anyio


@pytest.fixture()
def anyio_backend():
    return "asyncio"
from app.config import settings
from app.main import app
from app.movies_client import MoviesServiceError, build_search_request, search_movies
from app.orchestrator import LLMError, collect_movie_ids, run_chat
from app.tools import SYSTEM_PROMPT, TOOL_SPEC, create_search_tool, trim_results


class FakeChatModel:
    """Scripted ChatModel; records (messages, tools) per call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def chat(self, messages, tools):
        self.calls.append((messages, tools))
        if not self.responses:
            raise AssertionError("unexpected extra chat call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


async def fake_search_ok(query, limit=5):
    assert isinstance(query, str) and query
    return [
        {"tmdb_id": 101, "title": "Alpha Dawn", "year": 2024, "genres": ["Action"]},
        {"tmdb_id": 104, "title": "Alpha Returns", "year": 2022, "genres": ["Action"]},
    ][:limit]


async def test_direct_answer_without_tool():
    model = FakeChatModel([{"content": "Hello!", "tool_calls": []}])
    reply, ids = await run_chat("hi", chat_model=model, search_movies=fake_search_ok)
    assert reply == "Hello!"
    assert ids == []
    assert len(model.calls) == 1  # no second LLM call


async def test_search_flow_returns_movie_ids():
    model = FakeChatModel(
        [
            {
                "content": "",
                "tool_calls": [{"id": "c1", "name": "search_movies", "args": {"query": "space opera", "limit": 2}}],
            },
            {"content": "Try Alpha Dawn (101).", "tool_calls": []},
        ]
    )
    seen = {}

    async def search(query, limit=5):
        seen.update(query=query, limit=limit)
        return await fake_search_ok(query, limit)

    reply, ids = await run_chat("suggest a space opera", chat_model=model, search_movies=search)
    assert seen == {"query": "space opera", "limit": 2}
    assert ids == [101, 104]
    assert reply == "Try Alpha Dawn (101)."
    # The model saw tool results containing the IDs it must cite.
    tool_msgs = [m for m in model.calls[1][0] if m["role"] == "tool"]
    assert len(tool_msgs) == 1
    assert "101" in tool_msgs[0]["content"]


async def test_tool_args_fall_back_to_user_message():
    model = FakeChatModel(
        [
            {"content": "", "tool_calls": [{"id": "c1", "name": "search_movies", "args": {}}]},
            {"content": "done", "tool_calls": []},
        ]
    )
    seen = {}

    async def search(query, limit=5):
        seen["query"] = query
        return []

    await run_chat("comedy night", chat_model=model, search_movies=search)
    assert seen["query"] == "comedy night"


async def test_tool_failure_degrades_gracefully():
    async def failing_search(query, limit=5):
        raise MoviesServiceError("movies service unreachable: Timeout")

    model = FakeChatModel(
        [
            {"content": "", "tool_calls": [{"id": "c1", "name": "search_movies", "args": {"query": "x"}}]},
            {"content": "Search is down, tell me more.", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat("anything", chat_model=model, search_movies=failing_search)
    assert ids == []
    assert "down" in reply
    tool_content = [m for m in model.calls[1][0] if m["role"] == "tool"][0]["content"]
    assert "unavailable" in tool_content


async def test_llm_failure_raises():
    model = FakeChatModel([LLMError("boom")])
    with pytest.raises(LLMError):
        await run_chat("hi", chat_model=model, search_movies=fake_search_ok)


async def test_llm_timeout_raises():
    class Slow:
        async def chat(self, messages, tools):
            await asyncio.sleep(5)
            return {"content": "late", "tool_calls": []}

    with pytest.raises(LLMError):
        await run_chat("hi", chat_model=Slow(), search_movies=fake_search_ok, llm_timeout_s=0.05)


def test_collect_movie_ids_dedupes_and_skips_junk():
    assert collect_movie_ids(
        [{"tmdb_id": 1}, {"tmdb_id": 2}, {"tmdb_id": 1}, {"tmdb_id": "x"}, {}, {"tmdb_id": True}]
    ) == [1, 2]


def test_tool_spec_and_prompt_are_sane():
    assert TOOL_SPEC["name"] == "search_movies"
    assert "query" in TOOL_SPEC["parameters"]["required"]
    assert "recommend" in TOOL_SPEC["description"].lower()
    assert "never invent" in SYSTEM_PROMPT.lower()


def test_trim_results_keeps_small_schema():
    trimmed = trim_results([{"tmdb_id": 1, "title": "T", "overview": "long...", "budget_usd": 5}])
    assert trimmed == [{"tmdb_id": 1, "title": "T", "year": None, "genres": [], "vote_average": None}]


async def test_real_langchain_tool_invokes_search():
    tool = create_search_tool(fake_search_ok)
    assert tool.name == "search_movies"
    raw = await tool.ainvoke({"query": "alpha", "limit": 1})
    assert json.loads(raw)[0]["tmdb_id"] == 101


def test_build_search_request_uses_existing_contract_and_key():
    url, params, headers = build_search_request("http://localhost:8002/", "sekret", "alpha", 5)
    assert url == "http://localhost:8002/movies/search"
    assert params == {"q": "alpha", "limit": 5}
    assert headers == {"X-Internal-Key": "sekret"}


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"items": [], "total": 0}

    def json(self):
        return self._payload


async def test_search_movies_success():
    seen = {}

    async def fetch(url, *, headers, params, timeout_s):
        seen.update(url=url, headers=headers, params=params, timeout_s=timeout_s)
        return FakeResponse(200, {"items": [{"tmdb_id": 7}], "total": 1})

    items = await search_movies(
        "alpha", 3, base_url="http://m:8002", internal_key="k", timeout_s=4.0, fetch=fetch
    )
    assert items == [{"tmdb_id": 7}]
    assert seen["headers"] == {"X-Internal-Key": "k"}
    assert seen["timeout_s"] == 4.0


async def test_search_movies_errors_never_leak_key():
    async def boom(url, *, headers, params, timeout_s):
        raise TimeoutError("slow")

    with pytest.raises(MoviesServiceError) as exc:
        await search_movies("a", 1, base_url="http://m:8002", internal_key="SUPERSECRET", fetch=boom)
    assert "SUPERSECRET" not in str(exc.value)

    async def bad_status(url, *, headers, params, timeout_s):
        return FakeResponse(500, {})

    with pytest.raises(MoviesServiceError):
        await search_movies("a", 1, base_url="http://m:8002", internal_key="k", fetch=bad_status)


@pytest.fixture()
def authed_client(monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", "test-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "test-model")
    return TestClient(app)


def test_health_is_open(authed_client):
    assert authed_client.get("/health").json() == {"status": "ok", "service": "agent"}


def test_chat_requires_internal_key(authed_client):
    assert authed_client.post("/chat", json={"message": "hi"}).status_code == 401
    bad = authed_client.post("/chat", json={"message": "hi"}, headers={"X-Internal-Key": "wrong"})
    assert bad.status_code == 401


def test_chat_rejects_empty_message(authed_client):
    resp = authed_client.post("/chat", json={"message": ""}, headers={"X-Internal-Key": "test-key"})
    assert resp.status_code == 422


def test_chat_success_returns_ids_and_model(authed_client, monkeypatch):
    async def search(query, limit=5):
        return [{"tmdb_id": 101, "title": "Alpha Dawn", "year": 2024, "genres": ["Action"]}]

    class Scripted:
        def __init__(self):
            self.n = 0

        async def chat(self, messages, tools):
            self.n += 1
            if self.n == 1:
                return {
                    "content": "",
                    "tool_calls": [{"id": "c1", "name": "search_movies", "args": {"query": "alpha"}}],
                }
            return {"content": "Try Alpha Dawn.", "tool_calls": []}

    monkeypatch.setattr(
        chat_route, "get_agent_deps", lambda user_token=None: {"chat_model": Scripted(), "search": search}
    )
    resp = authed_client.post(
        "/chat", json={"message": "something fun", "limit": 3}, headers={"X-Internal-Key": "test-key"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"response": "Try Alpha Dawn.", "movie_ids": [101], "model": "test-model"}


def test_chat_llm_failure_is_502(authed_client, monkeypatch):
    class Broken:
        async def chat(self, messages, tools):
            raise LLMError("language model timed out")

    async def search(query, limit=5):
        return []

    monkeypatch.setattr(
        chat_route, "get_agent_deps", lambda user_token=None: {"chat_model": Broken(), "search": search}
    )
    resp = authed_client.post(
        "/chat", json={"message": "hi"}, headers={"X-Internal-Key": "test-key"}
    )
    assert resp.status_code == 502
