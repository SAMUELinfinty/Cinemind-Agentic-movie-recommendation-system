"""Request/response schemas for the agent service."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=10)
    user_token: str | None = Field(
        default=None,
        description="Optional caller JWT, forwarded as Bearer to approved user endpoints only",
    )


class ChatResponse(BaseModel):
    response: str
    movie_ids: list[int]
    model: str
