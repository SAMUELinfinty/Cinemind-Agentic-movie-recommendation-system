"""POST /chat — internal-only (X-Internal-Key), single-turn movie agent."""

from fastapi import APIRouter, Depends, HTTPException

from ..config import settings
from ..internal_auth import require_internal_key
from ..llm import LangChainChatModel
from ..movies_client import search_movies
from ..orchestrator import LLMError, run_chat
from ..schemas import ChatRequest, ChatResponse

router = APIRouter()


def get_agent_deps() -> dict:
    """Production wiring (monkeypatched in tests)."""
    chat_model = LangChainChatModel(
        model=settings.OPENROUTER_MODEL,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
    )

    async def search(query: str, limit: int) -> list[dict]:
        return await search_movies(
            query,
            limit,
            base_url=settings.MOVIES_SERVICE_URL,
            internal_key=settings.INTERNAL_API_KEY,
            timeout_s=settings.MOVIES_TIMEOUT_S,
        )

    return {"chat_model": chat_model, "search": search}


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_internal_key)])
async def chat(body: ChatRequest) -> dict:
    deps = get_agent_deps()
    try:
        reply, movie_ids = await run_chat(
            body.message,
            chat_model=deps["chat_model"],
            search_movies=deps["search"],
            default_limit=body.limit,
            llm_timeout_s=settings.LLM_TIMEOUT_S,
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"response": reply, "movie_ids": movie_ids, "model": settings.OPENROUTER_MODEL}
