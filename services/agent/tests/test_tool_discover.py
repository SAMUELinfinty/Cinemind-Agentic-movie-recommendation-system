"""Tool 2 tests: discover_movies (isolated, fakes only)."""

import json

import pytest

from app.movies_client import MoviesServiceError, discover_movies
from app.orchestrator import run_chat
from app.tools import DISCOVER_SPEC, TOOL_SPECS, create_discover_tool

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


async def test_discover_client_forwards_only_supported_filters():
    seen = {}

    async def fetch(url, *, headers, params, timeout_s):
        seen.update(url=url, params=params, headers=headers)
        return FakeResponse(200, {"items": [{"tmdb_id": 3}]})

    items = await discover_movies(
        {"genre": "Comedy", "year": 2024, "bogus": "x", "language": None},
        4,
        base_url="http://m:8002/",
        internal_key="k",
        fetch=fetch,
    )
    assert items == [{"tmdb_id": 3}]
    assert seen["url"] == "http://m:8002/discover"
    assert seen["params"] == {"genre": "Comedy", "year": 2024, "limit": 4}
    assert seen["headers"] == {"X-Internal-Key": "k"}


async def test_discover_client_errors_stay_clean():
    async def boom(url, *, headers, params, timeout_s):
        raise ConnectionError("down")

    with pytest.raises(MoviesServiceError) as exc:
        await discover_movies({}, 1, base_url="http://m", internal_key="SUPERSECRET", fetch=boom)
    assert "SUPERSECRET" not in str(exc.value)


async def test_discover_flow_collects_ids():
    async def discover(filters, limit=5):
        assert filters == {"genre": "Comedy", "year": 2024, "language": None, "min_vote": None}
        assert limit == 3
        return [{"tmdb_id": 103, "title": "Gamma Ray", "year": 2024, "genres": ["Comedy"]}]

    model = FakeChatModel(
        [
            {
                "content": "",
                "tool_calls": [
                    {"id": "c1", "name": "discover_movies", "args": {"genre": "Comedy", "year": 2024, "limit": 3}}
                ],
            },
            {"content": "Try Gamma Ray.", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "comedies from 2024",
        chat_model=model,
        search_movies=fake_search_unreachable,
        extra_tools={"discover_movies": discover},
    )
    assert ids == [103] and reply == "Try Gamma Ray."


async def test_discover_outage_degrades():
    async def down(filters, limit=5):
        raise MoviesServiceError("movies service returned status 500")

    model = FakeChatModel(
        [
            {"content": "", "tool_calls": [{"id": "c1", "name": "discover_movies", "args": {"genre": "Horror"}}]},
            {"content": "later", "tool_calls": []},
        ]
    )
    reply, ids = await run_chat(
        "horror please", chat_model=model, search_movies=fake_search_unreachable,
        extra_tools={"discover_movies": down},
    )
    assert ids == []
    assert "unavailable" in [m for m in model.calls[1][0] if m["role"] == "tool"][0]["content"]


async def test_discover_spec_and_langchain_factory():
    assert DISCOVER_SPEC["name"] == "discover_movies"
    assert DISCOVER_SPEC in TOOL_SPECS
    tool = create_discover_tool(
        lambda filters, limit=5: fake_discover(filters, limit)
    )
    assert tool.name == "discover_movies"
    raw = await tool.ainvoke({"genre": "Comedy"})
    assert json.loads(raw)[0]["tmdb_id"] == 103


async def fake_discover(filters, limit=5):
    assert filters["genre"] == "Comedy"
    return [{"tmdb_id": 103, "title": "Gamma Ray", "year": 2024, "genres": ["Comedy"]}]
