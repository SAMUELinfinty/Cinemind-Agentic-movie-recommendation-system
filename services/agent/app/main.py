"""CineMind agent service (FastAPI, port 8001)."""

from fastapi import FastAPI

from .config import settings
from .routes import chat, health

app = FastAPI(title="CineMind Agent Service")
app.include_router(health.router)
app.include_router(chat.router)


@app.get("/")
async def root() -> dict:
    return {"service": "agent", "health": "/health"}


if __name__ == "__main__":
    import uvicorn

    if not settings.INTERNAL_API_KEY:
        raise RuntimeError("INTERNAL_API_KEY is required")
    if not settings.OPENROUTER_API_KEY or not settings.OPENROUTER_MODEL:
        raise RuntimeError("OPENROUTER_API_KEY and OPENROUTER_MODEL are required")
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT)
