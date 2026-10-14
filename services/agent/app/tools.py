"""The agent's single tool: movie search.

TOOL_SPEC is a plain OpenAI-function-style dict (no LangChain import needed)
so the orchestrator stays dependency-free. create_search_tool() builds the
real LangChain StructuredTool for production wiring (lazy import).
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

SYSTEM_PROMPT = (
    "You are CineMind, a concise movie-recommendation assistant. "
    "When the user asks for suggestions, recommendations, movies like a title, "
    "or anything to watch, call the search_movies tool with a short query. "
    "Base picks only on tool results and cite their tmdb_id values; never invent IDs. "
    "Reply conversationally: a few picks with title, year, and a one-line reason each. "
    "If the tool returns nothing or fails, say so briefly and ask a clarifying question. "
    "For non-movie chit-chat, answer directly without tools."
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
