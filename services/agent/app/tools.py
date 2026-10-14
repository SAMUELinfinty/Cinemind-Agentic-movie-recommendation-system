"""The agent's movie tools (one per supported service endpoint).

Each *_SPEC is a plain OpenAI-function-style dict (no LangChain import needed)
so the orchestrator stays dependency-free. create_*_tool() builds the real
LangChain StructuredTool for production wiring (lazy import).
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable
import json

TOOL_SPEC: dict = {
    "name": "search_movies",
    "description": (
        "Search the CineMind movie catalogue by title or keywords. "
        "Use this when the user asks for recommendations, suggestions, "
        "movies like a given title, or anything they want to watch. "
        "Do NOT use it for general chit-chat. "
        "Args: query (short title/keywords string, required), "
        "limit (max results, 1-10, default 5). "
        "Returns a JSON list of {tmdb_id, title, year, genres}."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Short title or keywords to search for"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
        },
        "required": ["query"],
    },
}

DETAILS_SPEC: dict = {
    "name": "get_movie_details",
    "description": (
        "Fetch full details for one movie by its numeric tmdb_id. "
        "Use this when the user asks about a specific movie or you need "
        "verified data (year, genres, rating, overview) before recommending it. "
        "Args: movie_id (integer tmdb_id, required). "
        "Returns the movie object, or an error when the id is unknown."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "movie_id": {"type": "integer", "description": "Numeric tmdb_id of the movie"},
        },
        "required": ["movie_id"],
    },
}

DISCOVER_SPEC: dict = {
    "name": "discover_movies",
    "description": (
        "Discover movies by metadata filters from the catalogue. "
        "Use this when the user names a genre, year, language, or minimum "
        "rating (e.g. 'comedies from 2024', 'highly rated sci-fi'). "
        "All filter args are optional; pass only what the user stated — "
        "never invent preferences. "
        "Returns a JSON list of {tmdb_id, title, year, genres}."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "genre": {"type": "string", "description": "Genre name, e.g. Comedy"},
            "year": {"type": "integer", "description": "Release year, e.g. 2024"},
            "language": {"type": "string", "description": "Original language code, e.g. en"},
            "min_vote": {"type": "number", "description": "Minimum vote average 0-10"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
        },
    },
}

TOOL_SPECS: list[dict] = [TOOL_SPEC, DETAILS_SPEC, DISCOVER_SPEC]

SIMILAR_SPEC: dict = {
    "name": "find_similar_movies",
    "description": (
        "Find movies similar to one movie by tmdb_id (shared-genre overlap). "
        "Use this when the user asks for 'movies like X' or 'more like this'. "
        "Args: movie_id (integer tmdb_id, required), limit (1-10, default 5). "
        "Returns a JSON list of {tmdb_id, title, year, genres}."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "movie_id": {"type": "integer", "description": "Numeric tmdb_id of the source movie"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
        },
        "required": ["movie_id"],
    },
}

TOOL_SPECS: list[dict] = [TOOL_SPEC, DETAILS_SPEC, DISCOVER_SPEC, SIMILAR_SPEC]

USER_CONTEXT_SPEC: dict = {
    "name": "get_user_context",
    "description": (
        "Fetch the signed-in user's profile, watchlist movie ids, and ratings "
        "from the approved Express endpoints. Use this ONLY when the user asks "
        "for personal or tailored picks ('for me', 'my watchlist', 'based on my "
        "ratings'). Takes no arguments; authentication comes from the request "
        "context, never from the conversation. If it reports no authentication, "
        "ask the user to sign in instead of guessing. If the watchlist and "
        "ratings are empty, fall back to general catalogue recommendations. "
        "Returns {profile, watchlist, ratings}."
    ),
    "parameters": {"type": "object", "properties": {}},
}

TOOL_SPECS: list[dict] = [TOOL_SPEC, DETAILS_SPEC, DISCOVER_SPEC, SIMILAR_SPEC, USER_CONTEXT_SPEC]

SYSTEM_PROMPT = (
    "You are CineMind, a concise movie-recommendation assistant for a catalogue of 1000 films. "
    "TOOL POLICY — follow strictly: "
    "recommendation or search requests ('suggest', 'find', genre, mood, or year mentions) "
    "-> search_movies with 2-4 SHORT keywords (e.g. 'sci-fi comedy', never full sentences); "
    "'movies like X' or 'more like this' -> find_similar_movies with X's tmdb_id "
    "(search first if you do not know it); "
    "'tell me about X' -> get_movie_details with X's tmdb_id; "
    "genre/year/language/rating requests ('comedies from 2024', 'highly rated horror') "
    "-> discover_movies, passing ONLY filters the user stated; "
    "'for me', 'my watchlist', or 'my ratings' -> get_user_context first "
    "(it needs a signed-in user; if it reports no authentication, ask the user to sign in); "
    "chit-chat, greetings, and questions answerable without data -> answer directly, no tools. "
    "Chain tools when useful (search to identify a film, then similar for more like it). "
    "GROUNDING — non-negotiable: recommend ONLY movies returned by tools in this turn "
    "and cite their tmdb_id values exactly; never invent titles, IDs, ratings, years, "
    "or user preferences and history. "
    "If tools return nothing or fail, say so in one sentence and ask ONE clarifying question. "
    "If the watchlist and ratings are empty, give general catalogue picks and say so. "
    "STYLE: conversational and brief, 3-5 picks with title, year, and a one-line reason each, "
    "plain text, under ~150 words unless the user asks for more."
)


def trim_results(items: list[dict], limit: int = 10) -> list[dict]:
    """Keep only the fields the model needs (small, stable context)."""
    trimmed = []
    for item in items[:limit]:
        trimmed.append(
            {
                "tmdb_id": item.get("tmdb_id"),
                "title": item.get("title"),
                "year": item.get("year"),
                "genres": item.get("genres", []),
                "vote_average": item.get("vote_average"),
            }
        )
    return trimmed


def create_search_tool(
    search_fn: Callable[..., Awaitable[list[dict]]],
):
    """Build the real LangChain tool around an async search function."""
    from langchain_core.tools import StructuredTool  # lazy: langchain only needed in production

    async def _run(query: str, limit: int = 5) -> str:
        items = await search_fn(query, limit=min(max(limit, 1), 10))
        return json.dumps(trim_results(items))

    return StructuredTool.from_function(
        func=None,
        coroutine=_run,
        name=TOOL_SPEC["name"],
        description=TOOL_SPEC["description"],
    )


def create_details_tool(
    details_fn: Callable[..., Awaitable[dict | None]],
):
    """Build the real LangChain tool around an async details function."""
    from langchain_core.tools import StructuredTool  # lazy: langchain only needed in production

    async def _run(movie_id: int) -> str:
        doc = await details_fn(int(movie_id))
        if doc is None:
            return json.dumps({"error": f"movie {movie_id} not found"})
        return json.dumps(trim_results([doc])[0])

    return StructuredTool.from_function(
        func=None,
        coroutine=_run,
        name=DETAILS_SPEC["name"],
        description=DETAILS_SPEC["description"],
    )


def create_discover_tool(
    discover_fn: Callable[..., Awaitable[list[dict]]],
):
    """Build the real LangChain tool around an async discover function."""
    from langchain_core.tools import StructuredTool  # lazy: langchain only needed in production

    async def _run(
        genre: str | None = None,
        year: int | None = None,
        language: str | None = None,
        min_vote: float | None = None,
        limit: int = 5,
    ) -> str:
        filters = {"genre": genre, "year": year, "language": language, "min_vote": min_vote}
        items = await discover_fn(filters, limit=min(max(limit, 1), 10))
        return json.dumps(trim_results(items))

    return StructuredTool.from_function(
        func=None,
        coroutine=_run,
        name=DISCOVER_SPEC["name"],
        description=DISCOVER_SPEC["description"],
    )


def create_similar_tool(
    similar_fn: Callable[..., Awaitable[list[dict]]],
):
    """Build the real LangChain tool around an async similar-movies function."""
    from langchain_core.tools import StructuredTool  # lazy: langchain only needed in production

    async def _run(movie_id: int, limit: int = 5) -> str:
        items = await similar_fn(int(movie_id), limit=min(max(limit, 1), 10))
        return json.dumps(trim_results(items))

    return StructuredTool.from_function(
        func=None,
        coroutine=_run,
        name=SIMILAR_SPEC["name"],
        description=SIMILAR_SPEC["description"],
    )


def create_user_context_tool(
    context_fn: Callable[..., Awaitable[dict]],
):
    """Build the real LangChain tool around an async user-context function."""
    from langchain_core.tools import StructuredTool  # lazy: langchain only needed in production

    async def _run() -> str:
        return json.dumps(await context_fn())

    return StructuredTool.from_function(
        func=None,
        coroutine=_run,
        name=USER_CONTEXT_SPEC["name"],
        description=USER_CONTEXT_SPEC["description"],
    )
