"""Runtime session broker API tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from backend import main


@pytest.fixture()
def runtime_headers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setattr(main, "RUNTIME_SERVICE_TOKEN", "runtime-secret", raising=False)
    return {"X-Runtime-Service-Token": "runtime-secret"}


@pytest.fixture(autouse=True)
def clear_running_profiles():
    main.browser_mgr.running.clear()
    yield
    main.browser_mgr.running.clear()


def _create_profile(client: TestClient, name: str = "Runtime Profile") -> str:
    resp = client.post("/api/profiles", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _mock_running_profile() -> SimpleNamespace:
    return SimpleNamespace(ws_port=6109, display=109, resolved_geoip=None)


def test_runtime_session_create_requires_service_token(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)

    resp = app_client.post(
        "/api/runtime/sessions",
        json={
            "external_session_id": "pm-session-1",
            "profile_id": profile_id,
            "lease_seconds": 900,
        },
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Runtime service token required"


def test_runtime_session_create_launches_profile_and_persists_session(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)

    with patch.object(
        main.browser_mgr,
        "launch",
        new=AsyncMock(return_value=_mock_running_profile()),
    ) as launch:
        create = app_client.post(
            "/api/runtime/sessions",
            headers=runtime_headers,
            json={
                "external_session_id": "pm-session-2",
                "profile_id": profile_id,
                "lease_seconds": 900,
            },
        )

    assert create.status_code == 201
    data = create.json()
    assert data["external_session_id"] == "pm-session-2"
    assert data["profile_id"] == profile_id
    assert data["status"] == "active"
    assert data["lease_expires_at"]
    assert "viewer_token_hash" not in data
    assert "wallet" not in data
    assert "order" not in data
    assert "billing" not in data
    launch.assert_awaited_once()

    get_resp = app_client.get(
        f"/api/runtime/sessions/{data['id']}",
        headers=runtime_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json() == data


def test_runtime_session_create_from_template_creates_profile_then_launches(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    template = app_client.post(
        "/api/profile-templates",
        json={
            "name": "Runtime Template",
            "platform": "macos",
            "screen_width": 1440,
            "screen_height": 900,
            "geoip": False,
        },
    )
    assert template.status_code == 201

    with patch.object(
        main.browser_mgr,
        "launch",
        new=AsyncMock(return_value=_mock_running_profile()),
    ) as launch:
        resp = app_client.post(
            "/api/runtime/sessions",
            headers=runtime_headers,
            json={
                "external_session_id": "pm-session-template",
                "template_id": template.json()["id"],
                "lease_seconds": 600,
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    created_profile = app_client.get(f"/api/profiles/{data['profile_id']}").json()
    assert created_profile["name"] == "Runtime pm-session-template"
    assert created_profile["platform"] == "macos"
    assert created_profile["screen_width"] == 1440
    assert created_profile["screen_height"] == 900
    assert created_profile["geoip"] is False
    launch.assert_awaited_once()


def test_runtime_session_create_rejects_missing_or_ambiguous_profile_source(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    missing = app_client.post(
        "/api/runtime/sessions",
        headers=runtime_headers,
        json={"external_session_id": "pm-session-missing", "lease_seconds": 300},
    )
    assert missing.status_code == 422

    profile_id = _create_profile(app_client)
    template = app_client.post("/api/profile-templates", json={"name": "Ambiguous"})
    assert template.status_code == 201

    ambiguous = app_client.post(
        "/api/runtime/sessions",
        headers=runtime_headers,
        json={
            "external_session_id": "pm-session-ambiguous",
            "profile_id": profile_id,
            "template_id": template.json()["id"],
            "lease_seconds": 300,
        },
    )
    assert ambiguous.status_code == 422


def test_runtime_session_uses_runtime_token_when_ui_auth_is_enabled(
    app_client: TestClient,
    runtime_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    profile_id = _create_profile(app_client)
    monkeypatch.setattr(main, "AUTH_TOKEN", "ui-secret", raising=False)

    with patch.object(
        main.browser_mgr,
        "launch",
        new=AsyncMock(return_value=_mock_running_profile()),
    ):
        resp = app_client.post(
            "/api/runtime/sessions",
            headers=runtime_headers,
            json={
                "external_session_id": "pm-session-auth-enabled",
                "profile_id": profile_id,
                "lease_seconds": 300,
            },
        )

    assert resp.status_code == 201
    assert resp.json()["external_session_id"] == "pm-session-auth-enabled"
