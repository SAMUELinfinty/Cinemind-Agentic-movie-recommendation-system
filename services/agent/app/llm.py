"""LangChain adapter implementing the orchestrator's ChatModel protocol.

Uses ChatOpenAI pointed at the OpenRouter base URL (OpenAI-compatible).
Imported lazily — only production wiring touches LangChain.
"""

from __future__ import annotations

from typing import Any


class LangChainChatModel:
    """Thin wrapper: plain message/tool dicts <-> LangChain types."""

    def __init__(self, model: str, api_key: str, base_url: str):
        if not api_key or not model:
            raise ValueError("OPENROUTER_API_KEY and OPENROUTER_MODEL are required")
        from langchain_openai import ChatOpenAI  # lazy

        self._chat = ChatOpenAI(model=model, api_key=api_key, base_url=base_url)

    def _to_lc_messages(self, messages: list[dict]) -> list:
        from langchain_core.messages import (  # lazy
            AIMessage,
            HumanMessage,
            SystemMessage,
            ToolMessage,
        )

        converted = []
        for msg in messages:
            role, content = msg.get("role"), msg.get("content") or ""
            if role == "system":
                converted.append(SystemMessage(content=content))
            elif role == "user":
                converted.append(HumanMessage(content=content))
            elif role == "tool":
                converted.append(
                    ToolMessage(
                        content=content,
                        tool_call_id=msg.get("tool_call_id", ""),
                        name=msg.get("name", ""),
                    )
                )
            else:  # assistant (may carry tool_calls)
                converted.append(
                    AIMessage(content=content, tool_calls=self._to_lc_calls(msg.get("tool_calls")))
                )
        return converted

    @staticmethod
    def _to_lc_calls(calls: Any) -> list:
        return [
            {"name": c.get("name", ""), "args": c.get("args") or {}, "id": c.get("id", ""), "type": "tool_call"}
            for c in (calls or [])
        ]

    async def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        from langchain_core.messages import AIMessage  # lazy

        bound = self._chat.bind_tools(
            [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"],
                    },
                }
                for t in tools
            ]
        )
        try:
            reply: AIMessage = await bound.ainvoke(self._to_lc_messages(messages))
        except Exception as exc:
            from .orchestrator import LLMError

            raise LLMError(f"language model failed: {type(exc).__name__}") from exc
        calls = []
        for call in getattr(reply, "tool_calls", None) or []:
            calls.append(
                {
                    "id": call.get("id", ""),
                    "name": call.get("name", ""),
                    "args": call.get("args") or {},
                }
            )
        content = reply.content if isinstance(reply.content, str) else ""
        return {"content": content, "tool_calls": calls}
