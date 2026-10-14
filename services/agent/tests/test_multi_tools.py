"""Multi-tool tests: one turn using search + similar + user context together."""

import json

import pytest
from fastapi.testclient import TestClient

import app.routes.chat as chat_route
from app.config import settings
from app.main import app

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


async def fake_search(query, limit=5):
    return [
        {"tmdb_id": 101, "title": "Alpha Dawn", "year": 2024, "genres": ["Action", "Sci-Fi"]},
        {"tmdb_id": 102, "title": "Beta Night", "year": 2023, "genres": ["Action"]},
    ][:limit]


async def fake_details(movie_id):
    return {"tmdb_id": 101, "title": "Alpha Dawn", "year": 2024, "genres": ["Action", "Sci-Fi"]}


async def fake_discover(filters, limit=5):
    return [{"tmdb_id": 103, "title": "Gamma Ray", "year": 2024, "genres": ["Comedy"]}]


async def fake_similar(movie_id, limit=5):
    assert movie_id == 101
    return [{"tmdb_id": 101, "title": "Alpha Dawn", "year": 2024, "genres": ["Action"]}]


async def fake_context():
    return {"profile": {"email": "a@b.co", "name": "A"}, "watchlist": [102], "ratings": []}


def tools():
    from app.orchestrator import run_chat as _  # noqa: F401 (keeps import honest)

    return {
        "get_movie_details": fake_details,
        "discover_movies": fake_discover,
        "find_similar_movies": fake_similar,
        "get_user_context": fake_context,
    }


async def test_multi_tool_turn_combines_ids_once():
    from app.orchestrator import run_chat

    model = FakeChatModel(
        [
            {
                "content": "checking",
                "tool_calls": [
                    {"id": "c1", "name": "search_movies", "args": {"query": "action", "limit": 2}},
                    {"id": "c2", "name": "find_similar_movies", "args": {"movie_id": 101}},
                    {"id": "c3", "name": "get_user_context", "args": {}},
                ],
            },
            {"content": "For you: Alpha Dawn.", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "action picks for me",
        chat_model=model,
        search_movies=fake_search,
        extra_tools=tools(),
        user_token="jwt",
    )
    # 101 appears in both search and similar -> deduped, first-seen order.
    assert ids == [101, 102]
    assert reply == "For you: Alpha Dawn."
    assert len(model.calls) == 2  # existing flow: one tool round, one final call
    advertised = [t["name"] for t in model.calls[0][1]]
    assert advertised == [
        "search_movies",
        "get_movie_details",
        "discover_movies",
        "find_similar_movies",
        "get_user_context",
    ]
    tool_msgs = [m for m in model.calls[1][0] if m["role"] == "tool"]
    assert len(tool_msgs) == 3
    assert json.loads(tool_msgs[2]["content"])["watchlist"] == [102]


async def test_unknown_tool_name_is_handled():
    from app.orchestrator import run_chat

    model = FakeChatModel(
        [
            {"content": "", "tool_calls": [{"id": "c9", "name": "teleport_movies", "args": {}}]},
            {"content": "can't do that", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "teleport me", chat_model=model, search_movies=fake_search, extra_tools=tools()
    )
    assert ids == []
    assert "not available" in [m for m in model.calls[1][0] if m["role"] == "tool"][0]["content"]
    assert reply == "can't do that"


@pytest.fixture()
def authed_client(monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", "test-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "test-model")
    return TestClient(app)


def test_chat_forwards_user_token_to_personal_tool(authed_client, monkeypatch):
    seen = {}

    async def context():
        seen["called"] = True
        return {"profile": {"email": "a@b.co"}, "watchlist": [], "ratings": []}

    class Scripted:
        def __init__(self):
            self.n = 0

        async def chat(self, messages, tools):
            self.n += 1
            names = [t["name"] for t in tools]
            assert set(names) == {"search_movies", "get_user_context"}
            if self.n == 1:
                return {"content": "", "tool_calls": [{"id": "c1", "name": "get_user_context", "args": {}}]}
            return {"content": "general picks", "tool_calls": []}

    captured = {}

    def fake_deps(user_token=None):
        captured["user_token"] = user_token

        async def search(query, limit=5):
            return []

        async def user_context():
            assert user_token == "jwt-abc"
            return await context()

        return {
            "chat_model": Scripted(),
            "search": search,
            "extra_tools": {"get_user_context": user_context},
        }

    monkeypatch.setattr(chat_route, "get_agent_deps", fake_deps)
    resp = authed_client.post(
        "/chat",
        json={"message": "for me", "user_token": "jwt-abc"},
        headers={"X-Internal-Key": "test-key"},
    )
    assert resp.status_code == 200
    assert captured["user_token"] == "jwt-abc"
    assert seen == {"called": True}
    assert resp.json()["movie_ids"] == []
