"""Shared test fixtures for backend tests."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock invisible_playwright BEFORE any backend module is imported.
# browser_manager.py imports InvisiblePlaywright at module level, and tests
# assert how Manager maps profile fields into that launcher.
# ---------------------------------------------------------------------------


class _MockInvisiblePlaywright:
    """Async context manager test double for invisible_playwright."""

    instances: list["_MockInvisiblePlaywright"] = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.closed = False
        self.context = MagicMock()
        self.context.pages = []
        self.context.add_init_script = AsyncMock()
        self.context.set_extra_http_headers = AsyncMock()
        self.context.close = AsyncMock()
        self.context.on = MagicMock()
        self.__class__.instances.append(self)

    async def __aenter__(self):
        return self.context

    async def __aexit__(self, *exc):
        self.closed = True
        await self.context.close()


_mock_invisible = types.ModuleType("invisible_playwright")
_mock_invisible_async = types.ModuleType("invisible_playwright.async_api")
_mock_invisible_async.InvisiblePlaywright = _MockInvisiblePlaywright  # type: ignore[attr-defined]
_mock_invisible.InvisiblePlaywright = _MockInvisiblePlaywright  # type: ignore[attr-defined]

sys.modules.setdefault("invisible_playwright", _mock_invisible)
sys.modules.setdefault("invisible_playwright.async_api", _mock_invisible_async)

from backend import database as db  # noqa: E402


@pytest.fixture()
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point database module at a temp directory and init schema."""
    db_file = tmp_path / "profiles.db"
    monkeypatch.setattr(db, "DB_PATH", db_file)
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    db.init_db()
    return tmp_path


@pytest.fixture()
def mock_invisible_playwright():
    """Expose the invisible_playwright test double and reset captured launches."""
    _MockInvisiblePlaywright.instances.clear()
    yield _MockInvisiblePlaywright
    _MockInvisiblePlaywright.instances.clear()


@pytest.fixture()
def sample_profile(tmp_db: Path):
    """Create and return a sample profile dict."""
    return db.create_profile(name="Test Profile", fingerprint_seed=12345)


@pytest.fixture()
def app_client(tmp_db: Path, monkeypatch: pytest.MonkeyPatch):
    """FastAPI TestClient with mocked DB and browser manager."""
    from backend import main

    # Patch lifespan-called methods to avoid subprocess calls (pkill, Xvnc)
    monkeypatch.setattr(main.browser_mgr, "cleanup_stale", AsyncMock())
    monkeypatch.setattr(main.browser_mgr, "cleanup_all", AsyncMock())
    monkeypatch.setattr(main.browser_mgr.vnc, "cleanup_stale", AsyncMock())

    from starlette.testclient import TestClient

    with TestClient(main.app) as client:
        yield client
