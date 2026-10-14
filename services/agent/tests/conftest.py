"""Shared async-test backend (anyio ships its own pytest plugin)."""

import pytest


@pytest.fixture()
def anyio_backend():
    return "asyncio"
