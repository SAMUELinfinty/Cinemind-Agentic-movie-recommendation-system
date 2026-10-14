"""Agent orchestration: user message -> optional tool call -> grounded reply.

Dependency-free core. The chat model behind the ``ChatModel`` protocol can be
the LangChain adapter (app/llm.py) or a test fake. Message dicts use plain
roles: system / user / assistant / tool.

Movie IDs in the response come ONLY from tool results (never parsed from
free text), so the agent cannot invent IDs.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable, Protocol

from .movies_client import MoviesServiceError
from .tools import (
    DETAILS_SPEC,
    DISCOVER_SPEC,
    SIMILAR_SPEC,
    SYSTEM_PROMPT,
    TOOL_SPEC,
    TOOL_SPECS,
    USER_CONTEXT_SPEC,
    trim_results,
)
from .user_client import UserContextError

SEARCH_TOOL = "search_movies"
DETAILS_TOOL = "get_movie_details"
DISCOVER_TOOL = "discover_movies"
SIMILAR_TOOL = "find_similar_movies"
USER_TOOL = "get_user_context"
MAX_TOOL_CALLS = 3


class LLMError(Exception):
    """The language model call failed or timed out."""


class ChatModel(Protocol):
    async def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        """Return {"content": str, "tool_calls": [{"id", "name", "args": dict}]}."""
        ...


def collect_movie_ids(items: list[dict]) -> list[int]:
    """Deduped tmdb_id list in first-seen order."""
    ids: list[int] = []
    for item in items:
        value = item.get("tmdb_id")
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value not in ids:
            ids.append(value)
    return ids


async def _execute_search(args: dict, ctx: dict) -> tuple[str, list[int]]:
    """Run one search_movies call. Returns (tool content, movie ids)."""
    query = args.get("query") or ctx["message"]
    try:
        limit = int(args.get("limit", ctx["default_limit"]))
    except (TypeError, ValueError):
        limit = ctx["default_limit"]
    limit = min(max(limit, 1), 10)
    try:
        items = await ctx["fns"][SEARCH_TOOL](str(query), limit)
        ctx["seen"].extend(trim_results(items))
        return json.dumps(trim_results(items)), collect_movie_ids(items)
    except MoviesServiceError:
        return json.dumps({"error": "movie search is temporarily unavailable"}), []


async def _execute_details(args: dict, ctx: dict) -> tuple[str, list[int]]:
    """Run one get_movie_details call. Returns (tool content, movie ids)."""
    try:
        movie_id = int(args.get("movie_id"))
    except (TypeError, ValueError):
        return json.dumps({"error": "movie_id must be a positive integer"}), []
    try:
        doc = await ctx["fns"][DETAILS_TOOL](movie_id)
    except MoviesServiceError:
        return json.dumps({"error": "movie details are temporarily unavailable"}), []
    if doc is None:
        return json.dumps({"error": f"movie {movie_id} not found"}), []
    ctx["seen"].extend(trim_results([doc]))
    return json.dumps(trim_results([doc])[0]), collect_movie_ids([doc])


async def _execute_discover(args: dict, ctx: dict) -> tuple[str, list[int]]:
    """Run one discover_movies call. Returns (tool content, movie ids)."""
    filters = {k: args.get(k) for k in ("genre", "year", "language", "min_vote")}
    try:
        limit = int(args.get("limit", ctx["default_limit"]))
    except (TypeError, ValueError):
        limit = ctx["default_limit"]
    limit = min(max(limit, 1), 10)
    try:
        items = await ctx["fns"][DISCOVER_TOOL](filters, limit)
        ctx["seen"].extend(trim_results(items))
        return json.dumps(trim_results(items)), collect_movie_ids(items)
    except MoviesServiceError:
        return json.dumps({"error": "movie discovery is temporarily unavailable"}), []


async def _execute_similar(args: dict, ctx: dict) -> tuple[str, list[int]]:
    """Run one find_similar_movies call. Returns (tool content, movie ids)."""
    try:
        movie_id = int(args.get("movie_id"))
    except (TypeError, ValueError):
        return json.dumps({"error": "movie_id must be a positive integer"}), []
    try:
        limit = int(args.get("limit", ctx["default_limit"]))
    except (TypeError, ValueError):
        limit = ctx["default_limit"]
    limit = min(max(limit, 1), 10)
    try:
        items = await ctx["fns"][SIMILAR_TOOL](movie_id, limit)
        ctx["seen"].extend(trim_results(items))
        return json.dumps(trim_results(items)), collect_movie_ids(items)
    except MoviesServiceError as exc:
        message = str(exc)
        if "not found" in message:
            return json.dumps({"error": message}), []
        return json.dumps({"error": "similar movies are temporarily unavailable"}), []


async def _execute_user_context(args: dict, ctx: dict) -> tuple[str, list[int]]:
    """Run one get_user_context call. Auth-gated; never invents preferences."""
    if not ctx.get("user_token"):
        return (
            json.dumps({"error": "no user authentication provided; ask the user to sign in"}),
            [],
        )
    try:
        data = await ctx["fns"][USER_TOOL]()
        return json.dumps(data), []
    except UserContextError as exc:
        return json.dumps({"error": str(exc)}), []


EXECUTORS = {
    SEARCH_TOOL: _execute_search,
    DETAILS_TOOL: _execute_details,
    DISCOVER_TOOL: _execute_discover,
    SIMILAR_TOOL: _execute_similar,
    USER_TOOL: _execute_user_context,
}


def fallback_reply(seen: list[dict], movie_ids: list[int]) -> str:
    """Template reply from grounded tool results.

    Small/weak models sometimes return empty content on the tool-result turn.
    This guarantees the user still gets an answer built ONLY from catalogue
    data the tools actually returned — never invented titles or IDs.
    """
    picks: list[str] = []
    used: set[int] = set()
    for item in seen:
        mid = item.get("tmdb_id")
        if mid in movie_ids and mid not in used:
            used.add(mid)
            title = item.get("title") or f"Movie {mid}"
            year = f" ({item['year']})" if item.get("year") else ""
            picks.append(f"{title}{year} [tmdb:{mid}]")
    if not picks:
        return ""
    lines = "\n".join(f"- {pick}" for pick in picks)
    return f"Here are my picks from the catalogue:\n{lines}"


async def run_chat(
    message: str,
    *,
    chat_model: ChatModel,
    search_movies: Callable[..., Awaitable[list[dict]]],
    extra_tools: dict[str, Callable] | None = None,
    user_token: str | None = None,
    system_prompt: str = SYSTEM_PROMPT,
    default_limit: int = 5,
    llm_timeout_s: float = 30.0,
) -> tuple[str, list[int]]:
    """Run one turn. Returns (reply_text, movie_ids)."""
    fns: dict[str, Callable] = {"search_movies": search_movies, **(extra_tools or {})}
    specs = [spec for spec in TOOL_SPECS if spec["name"] in fns]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]
    try:
        first = await asyncio.wait_for(
            chat_model.chat(messages, specs), timeout=llm_timeout_s
        )
    except (asyncio.TimeoutError, TimeoutError) as exc:
        raise LLMError("language model timed out") from exc
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"language model failed: {type(exc).__name__}") from exc

    calls = [c for c in (first.get("tool_calls") or [])][:MAX_TOOL_CALLS]
    if not calls:
        return first.get("content") or "", []

    messages.append(
        {
            "role": "assistant",
            "content": first.get("content") or "",
            "tool_calls": calls,
        }
    )
    all_ids: list[int] = []
    ctx = {"message": message, "default_limit": default_limit, "user_token": user_token, "fns": fns, "seen": []}
    for call in calls:
        name = call.get("name", "")
        executor = EXECUTORS.get(name)
        if executor is None or name not in fns:
            content, ids = json.dumps({"error": f"tool {name or '?'} is not available"}), []
        else:
            content, ids = await executor(call.get("args") or {}, ctx)
        for mid in ids:
            if mid not in all_ids:
                all_ids.append(mid)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "name": name,
                "content": content,
            }
        )

    try:
        final = await asyncio.wait_for(
            chat_model.chat(messages, specs), timeout=llm_timeout_s
        )
    except (asyncio.TimeoutError, TimeoutError) as exc:
        raise LLMError("language model timed out") from exc
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"language model failed: {type(exc).__name__}") from exc
    reply = final.get("content") or ""
    if not reply.strip():
        reply = fallback_reply(ctx["seen"], all_ids)
    return reply, all_ids
