"""CineMind movies service (FastAPI, port 8002)."""

from fastapi import FastAPI

from .config import settings
from .ratelimit import RateLimitMiddleware
from .routes import health, movies

app = FastAPI(title="CineMind Movies Service")
app.add_middleware(RateLimitMiddleware, max_requests=300, window_s=60.0)
app.include_router(health.router)
app.include_router(movies.router)


@app.get("/")
async def root() -> dict:
    return {"service": "movies", "health": "/health"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT)
