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
from .tools import SYSTEM_PROMPT, TOOL_SPEC, trim_results

TOOL_NAME = "search_movies"
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


async def run_chat(
    message: str,
    *,
    chat_model: ChatModel,
    search_movies: Callable[..., Awaitable[list[dict]]],
    system_prompt: str = SYSTEM_PROMPT,
    default_limit: int = 5,
    llm_timeout_s: float = 30.0,
) -> tuple[str, list[int]]:
    """Run one turn. Returns (reply_text, movie_ids)."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]
    try:
        first = await asyncio.wait_for(
            chat_model.chat(messages, [TOOL_SPEC]), timeout=llm_timeout_s
        )
    except (asyncio.TimeoutError, TimeoutError) as exc:
        raise LLMError("language model timed out") from exc
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"language model failed: {type(exc).__name__}") from exc

    calls = [c for c in (first.get("tool_calls") or []) if c.get("name") == TOOL_NAME][
        :MAX_TOOL_CALLS
    ]
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
    for call in calls:
        args = call.get("args") or {}
        query = args.get("query") or message
        try:
            limit = int(args.get("limit", default_limit))
        except (TypeError, ValueError):
            limit = default_limit
        limit = min(max(limit, 1), 10)
        try:
            items = await search_movies(str(query), limit)
            content = json.dumps(trim_results(items))
            for mid in collect_movie_ids(items):
                if mid not in all_ids:
                    all_ids.append(mid)
        except MoviesServiceError:
            content = json.dumps({"error": "movie search is temporarily unavailable"})
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "name": TOOL_NAME,
                "content": content,
            }
        )

    try:
        final = await asyncio.wait_for(
            chat_model.chat(messages, [TOOL_SPEC]), timeout=llm_timeout_s
        )
    except (asyncio.TimeoutError, TimeoutError) as exc:
        raise LLMError("language model timed out") from exc
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"language model failed: {type(exc).__name__}") from exc
    return final.get("content") or "", all_ids
