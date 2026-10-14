"""Offline prompt matrix: ~20 realistic assistant prompts through run_chat.

No live LLM key is available in this workspace, so each scenario scripts the
LLM's tool-call decision and drives the REAL orchestrator, executors, and
tool-result shaping with fake service functions. This verifies dispatch, ID
grounding, auth gating, and failure paths — not the model's wording.
"""

import json

import pytest

from app.movies_client import MoviesServiceError
from app.orchestrator import run_chat
from app.user_client import UserContextError

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


async def no_search(query, limit=5):
    raise MoviesServiceError("movies service unreachable: Timeout")


def fns(**overrides):
    base = {"search_movies": no_search}
    base.update(overrides)
    return base


async def run_scripted(message, tool_calls, final="done", functions=None, **kw):
    model = FakeChatModel(
        [
            {"content": "", "tool_calls": tool_calls},
            {"content": final, "tool_calls": []},
        ]
    )
    functions = functions or {}
    search = functions.pop("search_movies", no_search)
    reply, ids = await run_chat(
        message, chat_model=model, search_movies=search, extra_tools=functions, **kw
    )
    tools_seen = [m for m in model.calls[1][0] if m["role"] == "tool"]
    return reply, ids, tools_seen


def search_hits(items):
    async def search(query, limit=5):
        return items[:limit]

    return search


# 1. chit-chat: no tool, no ids
async def test_01_chitchat_no_tool():
    model = FakeChatModel([{"content": "Hello! How can I help?", "tool_calls": []}])
    reply, ids = await run_chat("hi there", chat_model=model, search_movies=no_search)
    assert ids == [] and "Hello" in reply and len(model.calls) == 1


# 2. space-opera recommendation -> search, ids grounded
async def test_02_search_recommendation():
    reply, ids, tools = await run_scripted(
        "suggest a space opera",
        [{"id": "c1", "name": "search_movies", "args": {"query": "space opera", "limit": 2}}],
        final="Try these.",
        functions=fns(
            search_movies=search_hits([
                {"tmdb_id": 11, "title": "Star Wars", "year": 1977, "genres": ["Sci-Fi"]},
                {"tmdb_id": 12, "title": "Dune", "year": 2021, "genres": ["Sci-Fi"]},
            ])
        ),
    )
    assert ids == [11, 12] and reply == "Try these."
    assert "Star Wars" in tools[0]["content"]


# 3. "movies like X" -> similar
async def test_03_similar_request():
    async def similar(movie_id, limit=5):
        assert movie_id == 11
        return [{"tmdb_id": 12, "title": "Dune", "year": 2021, "genres": ["Sci-Fi"]}]

    reply, ids, tools = await run_scripted(
        "movies like Star Wars",
        [{"id": "c1", "name": "find_similar_movies", "args": {"movie_id": 11}}],
        functions=fns(find_similar_movies=similar),
    )
    assert ids == [12]


# 4. specific title -> details
async def test_04_details_request():
    async def details(movie_id):
        assert movie_id == 11
        return {"tmdb_id": 11, "title": "Star Wars", "year": 1977, "genres": ["Sci-Fi"], "vote_average": 8.6}

    reply, ids, tools = await run_scripted(
        "tell me about Star Wars (id 11)",
        [{"id": "c1", "name": "get_movie_details", "args": {"movie_id": 11}}],
        functions=fns(get_movie_details=details),
    )
    assert ids == [11]
    assert json.loads(tools[0]["content"])["vote_average"] == 8.6


# 5. genre + year filter -> discover
async def test_05_discover_genre_year():
    seen = {}

    async def discover(filters, limit=5):
        seen.update(filters)
        return [{"tmdb_id": 21, "title": "Funny 2024", "year": 2024, "genres": ["Comedy"]}]

    reply, ids, _ = await run_scripted(
        "comedies from 2024",
        [{"id": "c1", "name": "discover_movies", "args": {"genre": "Comedy", "year": 2024}}],
        functions=fns(discover_movies=discover),
    )
    assert ids == [21] and seen["genre"] == "Comedy" and seen["year"] == 2024


# 6. quality filter -> discover min_vote
async def test_06_discover_min_vote():
    async def discover(filters, limit=5):
        assert filters["min_vote"] == 8
        return []

    reply, ids, tools = await run_scripted(
        "highly rated sci-fi",
        [{"id": "c1", "name": "discover_movies", "args": {"genre": "Sci-Fi", "min_vote": 8}}],
        final="Nothing matched — tell me more.",
        functions=fns(discover_movies=discover),
    )
    assert ids == [] and json.loads(tools[0]["content"]) == []


# 7. personal picks with token -> context + search in one turn
async def test_07_personal_picks_with_token():
    async def context():
        return {"profile": {"email": "a@b.co", "name": "A"}, "watchlist": [12], "ratings": [{"movieId": 11, "score": 9}]}

    reply, ids, tools = await run_scripted(
        "pick something for me",
        [
            {"id": "c1", "name": "get_user_context", "args": {}},
            {"id": "c2", "name": "search_movies", "args": {"query": "sci-fi"}},
        ],
        functions=fns(
            get_user_context=context,
            search_movies=search_hits([{"tmdb_id": 12, "title": "Dune", "year": 2021}]),
        ),
        user_token="jwt",
    )
    assert ids == [12]  # catalogue ids only; watchlist ids are not recommendations
    assert json.loads(tools[0]["content"])["ratings"] == [{"movieId": 11, "score": 9}]


# 8. personal picks without token -> auth gate, service untouched
async def test_08_personal_picks_without_token():
    called = []

    async def spy():
        called.append(True)
        return {}

    reply, ids, tools = await run_scripted(
        "pick something for me",
        [{"id": "c1", "name": "get_user_context", "args": {}}],
        functions=fns(get_user_context=spy),
    )
    assert called == [] and ids == []
    assert "sign in" in tools[0]["content"]


# 9. empty profile -> general fallback signal, no invented tastes
async def test_09_empty_profile_falls_back_to_general():
    async def context():
        return {"profile": {"email": "a@b.co", "name": None}, "watchlist": [], "ratings": []}

    reply, ids, tools = await run_scripted(
        "recommend based on my taste",
        [{"id": "c1", "name": "get_user_context", "args": {}}],
        final="Fresh account — here are popular picks.",
        functions=fns(get_user_context=context),
        user_token="jwt",
    )
    data = json.loads(tools[0]["content"])
    assert data == {"profile": {"email": "a@b.co", "name": None}, "watchlist": [], "ratings": []}
    assert ids == []


# 10. unknown movie id -> not found, no ids
async def test_10_details_unknown_id():
    async def missing(movie_id):
        return None

    reply, ids, tools = await run_scripted(
        "tell me about movie 999999",
        [{"id": "c1", "name": "get_movie_details", "args": {"movie_id": 999999}}],
        functions=fns(get_movie_details=missing),
    )
    assert ids == [] and "not found" in tools[0]["content"]


# 11. similar for unknown source -> not found message
async def test_11_similar_unknown_source():
    async def missing(movie_id, limit=5):
        raise MoviesServiceError(f"movie {movie_id} not found")

    reply, ids, tools = await run_scripted(
        "more like movie 999999",
        [{"id": "c1", "name": "find_similar_movies", "args": {"movie_id": 999999}}],
        functions=fns(find_similar_movies=missing),
    )
    assert ids == [] and "999999" in tools[0]["content"]


# 12. malformed details args -> validation without service call
async def test_12_details_malformed_args():
    called = []

    async def spy(movie_id):
        called.append(movie_id)
        return {}

    reply, ids, tools = await run_scripted(
        "details please",
        [{"id": "c1", "name": "get_movie_details", "args": {"movie_id": "abc"}}],
        functions=fns(get_movie_details=spy),
    )
    assert called == [] and ids == [] and "movie_id" in tools[0]["content"]


# 13. search outage -> graceful degradation
async def test_13_search_outage():
    reply, ids, tools = await run_scripted(
        "something fun",
        [{"id": "c1", "name": "search_movies", "args": {"query": "fun" }}],
        final="Search is down — tell me a genre.",
        functions=fns(),
    )
    assert ids == [] and "unavailable" in tools[0]["content"]


# 14. discover outage -> graceful degradation
async def test_14_discover_outage():
    async def down(filters, limit=5):
        raise MoviesServiceError("movies service returned status 500")

    reply, ids, tools = await run_scripted(
        "horror movies",
        [{"id": "c1", "name": "discover_movies", "args": {"genre": "Horror" }}],
        functions=fns(discover_movies=down),
    )
    assert ids == [] and "unavailable" in tools[0]["content"]


# 15. similar outage (non-404) -> graceful degradation
async def test_15_similar_outage():
    async def down(movie_id, limit=5):
        raise MoviesServiceError("movies service returned status 500")

    reply, ids, tools = await run_scripted(
        "more like Dune",
        [{"id": "c1", "name": "find_similar_movies", "args": {"movie_id": 12}}],
        functions=fns(find_similar_movies=down),
    )
    assert ids == [] and "unavailable" in tools[0]["content"]


# 16. expired user token -> clear message, no ids
async def test_16_expired_user_token():
    async def denied():
        raise UserContextError("user authentication is invalid or expired")

    reply, ids, tools = await run_scripted(
        "my watchlist picks",
        [{"id": "c1", "name": "get_user_context", "args": {}}],
        functions=fns(get_user_context=denied),
        user_token="stale",
    )
    assert ids == [] and "expired" in tools[0]["content"]


# 17. search + details + similar in one turn -> deduped ids
async def test_17_multi_tool_dedupe():
    async def similar(movie_id, limit=5):
        return [
            {"tmdb_id": 11, "title": "Star Wars", "year": 1977},
            {"tmdb_id": 12, "title": "Dune", "year": 2021},
        ]

    async def details(movie_id):
        return {"tmdb_id": 11, "title": "Star Wars", "year": 1977}

    reply, ids, tools = await run_scripted(
        "sci-fi like Star Wars, and tell me about it",
        [
            {"id": "c1", "name": "search_movies", "args": {"query": "sci-fi", "limit": 1}},
            {"id": "c2", "name": "get_movie_details", "args": {"movie_id": 11}},
            {"id": "c3", "name": "find_similar_movies", "args": {"movie_id": 11}},
        ],
        functions=fns(
            search_movies=search_hits([{"tmdb_id": 11, "title": "Star Wars"}]),
            get_movie_details=details,
            find_similar_movies=similar,
        ),
    )
    assert ids == [11, 12] and len(tools) == 3


# 18. unknown tool name -> handled, no crash
async def test_18_unknown_tool():
    reply, ids, tools = await run_scripted(
        "book my tickets",
        [{"id": "c9", "name": "book_tickets", "args": {}}],
        functions=fns(),
    )
    assert ids == [] and "not available" in tools[0]["content"]


# 19. limit clamping: model asks 99 -> service gets 10
async def test_19_limit_clamped():
    seen = {}

    async def search(query, limit=5):
        seen["limit"] = limit
        return []

    await run_scripted(
        "everything",
        [{"id": "c1", "name": "search_movies", "args": {"query": "x", "limit": 99}}],
        functions=fns(search_movies=search),
    )
    assert seen["limit"] == 10


# 20. empty catalogue results -> empty ids, model informed
async def test_20_empty_results():
    reply, ids, tools = await run_scripted(
        "martian cooking documentaries",
        [{"id": "c1", "name": "search_movies", "args": {"query": "martian cooking" }}],
        final="No matches — try another craving.",
        functions=fns(search_movies=search_hits([])),
    )
    assert ids == [] and json.loads(tools[0]["content"]) == []
