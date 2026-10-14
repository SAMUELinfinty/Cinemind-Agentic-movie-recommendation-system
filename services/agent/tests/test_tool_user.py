"""Tool 4 tests: get_user_context (isolated, fakes only)."""

import json

import pytest

from app.orchestrator import run_chat
from app.tools import USER_CONTEXT_SPEC, TOOL_SPECS, create_user_context_tool
from app.user_client import UserContextError, build_user_urls, get_user_context

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
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


async def fake_search_unreachable(query, limit=5):
    from app.movies_client import MoviesServiceError

    raise MoviesServiceError("movies service unreachable: Timeout")


def test_build_user_urls_uses_approved_endpoints():
    urls = build_user_urls("http://localhost:5000/")
    assert urls == {
        "profile": "http://localhost:5000/api/users/me",
        "watchlist": "http://localhost:5000/api/watchlist",
        "ratings": "http://localhost:5000/api/ratings",
    }


async def test_user_context_trims_and_forwards_bearer():
    seen = {}

    async def fetch(url, *, headers, params, timeout_s):
        seen.setdefault("urls", []).append(url)
        seen["auth"] = headers.get("Authorization")
        assert "X-Internal-Key" not in headers
        if url.endswith("/api/users/me"):
            return FakeResponse(200, {"user": {"email": "a@b.co", "name": "A", "passwordHash": "SECRET"}})
        if url.endswith("/api/watchlist"):
            return FakeResponse(200, {"items": [{"movieId": 101}, {"movieId": 104}]})
        return FakeResponse(200, {"items": [{"movieId": 101, "score": 9}]})

    data = await get_user_context("jwt-token", base_url="http://localhost:5000", fetch=fetch)
    assert data == {
        "profile": {"email": "a@b.co", "name": "A"},
        "watchlist": [101, 104],
        "ratings": [{"movieId": 101, "score": 9}],
    }
    assert seen["auth"] == "Bearer jwt-token"
    assert len(seen["urls"]) == 3


async def test_user_context_missing_token_and_rejected_token():
    with pytest.raises(UserContextError, match="no user authentication"):
        await get_user_context(None, base_url="http://x")

    async def denied(url, *, headers, params, timeout_s):
        return FakeResponse(401, {"error": {}})

    with pytest.raises(UserContextError, match="invalid or expired"):
        await get_user_context("stale", base_url="http://x", fetch=denied)


async def test_user_context_outage_never_leaks_token():
    async def boom(url, *, headers, params, timeout_s):
        raise TimeoutError("down")

    with pytest.raises(UserContextError) as exc:
        await get_user_context("SUPERSECRET-JWT", base_url="http://x", fetch=boom)
    assert "SUPERSECRET-JWT" not in str(exc.value)


async def test_user_context_flow_with_auth():
    async def context():
        return {"profile": {"email": "a@b.co", "name": "A"}, "watchlist": [], "ratings": []}

    model = FakeChatModel(
        [
            {"content": "", "tool_calls": [{"id": "c1", "name": "get_user_context", "args": {}}]},
            {"content": "Fresh account — here are general picks.", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "pick something for me",
        chat_model=model,
        search_movies=fake_search_unreachable,
        extra_tools={"get_user_context": context},
        user_token="jwt-token",
    )
    assert ids == []  # personal ids are not catalogue recommendations
    tool_data = json.loads([m for m in model.calls[1][0] if m["role"] == "tool"][0]["content"])
    assert tool_data["watchlist"] == []
    assert "general picks" in reply


async def test_user_context_flow_without_auth_never_calls_service():
    called = []

    async def spy():
        called.append(True)
        return {}

    model = FakeChatModel(
        [
            {"content": "", "tool_calls": [{"id": "c1", "name": "get_user_context", "args": {}}]},
            {"content": "please sign in", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "for me", chat_model=model, search_movies=fake_search_unreachable,
        extra_tools={"get_user_context": spy},
    )
    assert called == [] and ids == []
    assert "sign in" in [m for m in model.calls[1][0] if m["role"] == "tool"][0]["content"]


async def test_user_context_spec_and_langchain_factory():
    assert USER_CONTEXT_SPEC["name"] == "get_user_context"
    assert USER_CONTEXT_SPEC in TOOL_SPECS

    async def context():
        return {"profile": {"email": "a@b.co"}, "watchlist": [101], "ratings": []}

    tool = create_user_context_tool(context)
    assert tool.name == "get_user_context"
    assert json.loads(await tool.ainvoke({}))["watchlist"] == [101]
