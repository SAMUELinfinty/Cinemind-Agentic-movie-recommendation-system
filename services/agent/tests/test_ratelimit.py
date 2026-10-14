"""Rate-limit middleware: 429s over the limit, health stays open."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ratelimit import RateLimitMiddleware

pytestmark = pytest.mark.anyio


@pytest.fixture()
def anyio_backend():
    return "asyncio"


def make_client(max_requests=2):
    clock = {"t": 0.0}
    inner = FastAPI()
    inner.add_middleware(
        RateLimitMiddleware, max_requests=max_requests, window_s=60.0, clock=lambda: clock["t"]
    )

    @inner.get("/health")
    async def health():
        return {"status": "ok"}

    @inner.post("/chat")
    async def chat():
        return {"response": "hi", "movie_ids": [], "model": "test"}

    return TestClient(inner), clock


def test_over_limit_returns_429_json():
    client, _ = make_client()
    assert client.post("/chat", json={}).status_code == 200
    assert client.post("/chat", json={}).status_code == 200
    resp = client.post("/chat", json={})
    assert resp.status_code == 429
    assert resp.json() == {"detail": "Rate limit exceeded"}


def test_window_reset_allows_again():
    client, clock = make_client(max_requests=1)
    assert client.post("/chat", json={}).status_code == 200
    assert client.post("/chat", json={}).status_code == 429
    clock["t"] = 61.0
    assert client.post("/chat", json={}).status_code == 200


def test_health_is_exempt():
    client, _ = make_client(max_requests=1)
    client.post("/chat", json={})
    for _ in range(3):
        assert client.get("/health").status_code == 200
