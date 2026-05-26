"""Runtime session broker API tests."""

from __future__ import annotations

import sys
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from backend import database as db, main


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


def _create_runtime_session(
    client: TestClient,
    headers: dict[str, str],
    profile_id: str,
    external_session_id: str = "pm-session-token",
) -> dict:
    with patch.object(
        main.browser_mgr,
        "launch",
        new=AsyncMock(return_value=_mock_running_profile()),
    ):
        resp = client.post(
            "/api/runtime/sessions",
            headers=headers,
            json={
                "external_session_id": external_session_id,
                "profile_id": profile_id,
                "lease_seconds": 900,
            },
        )
    assert resp.status_code == 201
    return resp.json()


def _audit_event_types() -> list[str]:
    return [event["event_type"] for event in db.list_audit_events()]


def _viewer_failure_events(session_id: str | None = None) -> list[dict]:
    return [
        event
        for event in db.list_audit_events(session_id)
        if event["event_type"] == "runtime.viewer.failed"
    ]


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


def test_runtime_viewer_token_requires_runtime_service_token(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)

    resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        json={"ttl_seconds": 60},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Runtime service token required"


def test_runtime_viewer_token_persists_hash_and_returns_short_lived_viewer_url(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)

    resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 60},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["viewer_url"].startswith(f"/api/runtime/sessions/{session['id']}/vnc?viewer_token=")
    assert data["viewer_token"]
    assert data["viewer_token"] in data["viewer_url"]
    assert data["expires_at"]
    assert "viewer_token_hash" not in data
    assert "wallet" not in data
    assert "order" not in data
    assert "billing" not in data

    stored = db.get_runtime_session(session["id"])
    assert stored is not None
    assert stored["viewer_token_hash"]
    assert stored["viewer_token_hash"] != data["viewer_token"]
    assert stored["viewer_token_expires_at"] == data["expires_at"]


def test_runtime_viewer_token_rejects_missing_session(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    resp = app_client.post(
        "/api/runtime/sessions/missing/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 60},
    )

    assert resp.status_code == 404


def test_runtime_vnc_rejects_missing_wrong_or_expired_viewer_token(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)

    with pytest.raises(Exception) as missing:
        with app_client.websocket_connect(f"/api/runtime/sessions/{session['id']}/vnc"):
            pass
    assert missing.value.code == 4401

    with pytest.raises(Exception) as wrong:
        with app_client.websocket_connect(
            f"/api/runtime/sessions/{session['id']}/vnc?viewer_token=wrong-token"
        ):
            pass
    assert wrong.value.code == 4401

    token_resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 1},
    )
    assert token_resp.status_code == 201
    db.set_runtime_session_viewer_token(
        session["id"],
        db.get_runtime_session(session["id"])["viewer_token_hash"],
        "2000-01-01T00:00:00+00:00",
    )

    with pytest.raises(Exception) as expired:
        with app_client.websocket_connect(
            token_resp.json()["viewer_url"],
            headers={"origin": "http://testserver"},
        ):
            pass
    assert expired.value.code == 4401

    failures = _viewer_failure_events(session["id"])
    assert [event["metadata"] for event in failures] == [
        {"reason_code": "viewer_credential_missing"},
        {"reason_code": "viewer_credential_invalid"},
        {"reason_code": "viewer_credential_expired"},
    ]
    assert all(event["actor_type"] == "runtime_viewer" for event in failures)
    assert all(event["runtime_session_id"] == session["id"] for event in failures)
    assert all(event["profile_id"] == profile_id for event in failures)
    assert all(event["external_session_id"] == session["external_session_id"] for event in failures)

    serialized_events = json.dumps(failures, sort_keys=True)
    assert "wrong-token" not in serialized_events
    assert token_resp.json()["viewer_token"] not in serialized_events
    assert db.get_runtime_session(session["id"])["viewer_token_hash"] not in serialized_events
    assert token_resp.json()["viewer_url"] not in serialized_events
    assert "viewer_token" not in serialized_events
    assert "runtime.viewer.connected" not in _audit_event_types()
    assert "runtime.viewer.disconnected" not in _audit_event_types()


def test_runtime_vnc_rejects_cross_origin_even_with_valid_viewer_token(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)
    main.browser_mgr.running[profile_id] = _mock_running_profile()
    token_resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 60},
    )
    assert token_resp.status_code == 201

    with pytest.raises(Exception) as rejected:
        with app_client.websocket_connect(
            token_resp.json()["viewer_url"],
            headers={"origin": "http://evil.com"},
        ):
            pass

    assert rejected.value.code == 4403

    failures = _viewer_failure_events(session["id"])
    assert len(failures) == 1
    assert failures[0]["actor_type"] == "runtime_viewer"
    assert failures[0]["runtime_session_id"] == session["id"]
    assert failures[0]["profile_id"] is None
    assert failures[0]["external_session_id"] is None
    assert failures[0]["metadata"] == {"reason_code": "origin_not_allowed"}

    serialized_events = json.dumps(failures, sort_keys=True)
    assert "evil.com" not in serialized_events
    assert token_resp.json()["viewer_token"] not in serialized_events
    assert db.get_runtime_session(session["id"])["viewer_token_hash"] not in serialized_events
    assert token_resp.json()["viewer_url"] not in serialized_events
    assert "viewer_token" not in serialized_events
    assert "http://evil.com" not in serialized_events


def test_runtime_vnc_failure_audits_session_not_live_and_skips_missing_session(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)
    db.terminate_runtime_session(session["id"])

    with pytest.raises(Exception) as terminated:
        with app_client.websocket_connect(
            f"/api/runtime/sessions/{session['id']}/vnc?viewer_token=anything",
            headers={"origin": "http://testserver"},
        ):
            pass
    assert terminated.value.code == 4404

    failures = _viewer_failure_events(session["id"])
    assert len(failures) == 1
    assert failures[0]["actor_type"] == "runtime_viewer"
    assert failures[0]["runtime_session_id"] == session["id"]
    assert failures[0]["profile_id"] == profile_id
    assert failures[0]["external_session_id"] == session["external_session_id"]
    assert failures[0]["metadata"] == {"reason_code": "runtime_session_not_live"}

    with pytest.raises(Exception) as missing:
        with app_client.websocket_connect(
            "/api/runtime/sessions/missing/vnc?viewer_token=anything",
            headers={"origin": "http://testserver"},
        ):
            pass
    assert missing.value.code == 4404
    assert _viewer_failure_events("missing") == []


def test_runtime_vnc_failure_audits_profile_not_running(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)
    token_resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 60},
    )
    assert token_resp.status_code == 201

    with pytest.raises(Exception) as rejected:
        with app_client.websocket_connect(
            token_resp.json()["viewer_url"],
            headers={"origin": "http://testserver"},
        ):
            pass
    assert rejected.value.code == 4004

    failures = _viewer_failure_events(session["id"])
    assert len(failures) == 1
    assert failures[0]["actor_type"] == "runtime_viewer"
    assert failures[0]["runtime_session_id"] == session["id"]
    assert failures[0]["profile_id"] == profile_id
    assert failures[0]["external_session_id"] == session["external_session_id"]
    assert failures[0]["metadata"] == {"reason_code": "profile_not_running"}

    serialized_events = json.dumps(failures, sort_keys=True)
    assert token_resp.json()["viewer_token"] not in serialized_events
    assert db.get_runtime_session(session["id"])["viewer_token_hash"] not in serialized_events
    assert token_resp.json()["viewer_url"] not in serialized_events
    assert "viewer_token" not in serialized_events


def test_runtime_vnc_accepts_valid_viewer_token_and_proxies_to_profile_vnc(
    app_client: TestClient,
    runtime_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)
    token_resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 60},
    )
    assert token_resp.status_code == 201
    main.browser_mgr.running[profile_id] = _mock_running_profile()
    captured: dict[str, object] = {}

    class FakeVncWs:
        subprotocol = "binary"
        close_code = 1000

        async def send(self, data: bytes):
            captured["sent"] = data

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class FakeConnect:
        def __init__(self, url: str, **kwargs: object):
            captured["url"] = url
            captured["kwargs"] = kwargs

        async def __aenter__(self):
            return FakeVncWs()

        async def __aexit__(self, *exc: object):
            return False

    fake_websockets = MagicMock()
    fake_websockets.connect = FakeConnect
    monkeypatch.setitem(sys.modules, "websockets", fake_websockets)

    with app_client.websocket_connect(
        token_resp.json()["viewer_url"],
        headers={"origin": "http://testserver"},
        subprotocols=["binary"],
    ):
        pass

    assert captured["url"] == "ws://127.0.0.1:6109/websockify"
    kwargs = captured["kwargs"]
    assert kwargs["subprotocols"] == ["binary"]
    assert kwargs["compression"] is None
    assert kwargs["ping_interval"] is None


def test_runtime_vnc_success_writes_redacted_connect_and_disconnect_audit(
    app_client: TestClient,
    runtime_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(
        app_client,
        runtime_headers,
        profile_id,
        external_session_id="pm-session-vnc-audit",
    )
    token_resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 60},
    )
    assert token_resp.status_code == 201
    stored_with_token = db.get_runtime_session(session["id"])
    assert stored_with_token is not None
    main.browser_mgr.running[profile_id] = _mock_running_profile()

    class FakeVncWs:
        subprotocol = "binary"
        close_code = 1000

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class FakeConnect:
        def __init__(self, url: str, **kwargs: object):
            pass

        async def __aenter__(self):
            return FakeVncWs()

        async def __aexit__(self, *exc: object):
            return False

    fake_websockets = MagicMock()
    fake_websockets.connect = FakeConnect
    monkeypatch.setitem(sys.modules, "websockets", fake_websockets)

    with app_client.websocket_connect(
        token_resp.json()["viewer_url"],
        headers={"origin": "http://testserver"},
        subprotocols=["binary"],
    ):
        pass

    events = db.list_audit_events(session["id"])
    assert [event["event_type"] for event in events][-2:] == [
        "runtime.viewer.connected",
        "runtime.viewer.disconnected",
    ]
    viewer_events = events[-2:]
    assert all(event["actor_type"] == "runtime_viewer" for event in viewer_events)
    assert all(event["runtime_session_id"] == session["id"] for event in viewer_events)
    assert all(event["profile_id"] == profile_id for event in viewer_events)
    assert all(event["external_session_id"] == "pm-session-vnc-audit" for event in viewer_events)
    assert viewer_events[0]["metadata"] == {
        "subprotocol": "binary",
    }
    assert viewer_events[1]["metadata"] == {
        "close_code": 1000,
    }

    serialized_events = json.dumps(viewer_events, sort_keys=True)
    assert token_resp.json()["viewer_token"] not in serialized_events
    assert stored_with_token["viewer_token_hash"] not in serialized_events
    assert token_resp.json()["viewer_url"] not in serialized_events
    assert "viewer_token" not in serialized_events
    assert "origin" not in serialized_events.lower()


def test_runtime_vnc_backend_connect_failure_writes_redacted_failure_audit(
    app_client: TestClient,
    runtime_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)
    token_resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 60},
    )
    assert token_resp.status_code == 201
    main.browser_mgr.running[profile_id] = _mock_running_profile()

    class FailingConnect:
        def __init__(self, url: str, **kwargs: object):
            pass

        async def __aenter__(self):
            raise OSError("backend vnc unavailable")

        async def __aexit__(self, *exc: object):
            return False

    fake_websockets = MagicMock()
    fake_websockets.connect = FailingConnect
    monkeypatch.setitem(sys.modules, "websockets", fake_websockets)

    with app_client.websocket_connect(
        token_resp.json()["viewer_url"],
        headers={"origin": "http://testserver"},
        subprotocols=["binary"],
    ):
        pass

    event_types = _audit_event_types()
    assert "runtime.viewer.connected" not in event_types
    assert "runtime.viewer.disconnected" not in event_types
    failures = _viewer_failure_events(session["id"])
    assert len(failures) == 1
    assert failures[0]["actor_type"] == "runtime_viewer"
    assert failures[0]["runtime_session_id"] == session["id"]
    assert failures[0]["profile_id"] == profile_id
    assert failures[0]["external_session_id"] == session["external_session_id"]
    assert failures[0]["metadata"] == {"reason_code": "backend_vnc_unavailable"}

    serialized_events = json.dumps(failures, sort_keys=True)
    assert "backend vnc unavailable" not in serialized_events
    assert "127.0.0.1" not in serialized_events
    assert "6109" not in serialized_events
    assert token_resp.json()["viewer_token"] not in serialized_events
    assert db.get_runtime_session(session["id"])["viewer_token_hash"] not in serialized_events
    assert token_resp.json()["viewer_url"] not in serialized_events
    assert "viewer_token" not in serialized_events


def test_runtime_session_terminate_requires_runtime_service_token(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)

    resp = app_client.post(f"/api/runtime/sessions/{session['id']}/terminate")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Runtime service token required"


def test_runtime_session_terminate_marks_session_inactive_and_revokes_viewer_token(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)
    main.browser_mgr.running[profile_id] = _mock_running_profile()
    token_resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 60},
    )
    assert token_resp.status_code == 201

    terminate = app_client.post(
        f"/api/runtime/sessions/{session['id']}/terminate",
        headers=runtime_headers,
    )

    assert terminate.status_code == 200
    data = terminate.json()
    assert data["id"] == session["id"]
    assert data["status"] == "terminated"
    assert "viewer_token_hash" not in data
    stored = db.get_runtime_session(session["id"])
    assert stored is not None
    assert stored["status"] == "terminated"
    assert stored["viewer_token_hash"] is None
    assert stored["viewer_token_expires_at"] is None

    with pytest.raises(Exception) as rejected:
        with app_client.websocket_connect(
            token_resp.json()["viewer_url"],
            headers={"origin": "http://testserver"},
        ):
            pass

    assert rejected.value.code == 4404


def test_runtime_session_terminate_rejects_missing_session(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    resp = app_client.post(
        "/api/runtime/sessions/missing/terminate",
        headers=runtime_headers,
    )

    assert resp.status_code == 404


def test_runtime_session_renew_requires_runtime_service_token(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)

    resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/renew",
        json={"lease_seconds": 1800},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Runtime service token required"


def test_runtime_session_renew_extends_active_session_and_keeps_short_lived_viewer_token(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)
    token_resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 60},
    )
    assert token_resp.status_code == 201
    stored_before = db.get_runtime_session(session["id"])
    assert stored_before is not None
    assert stored_before["viewer_token_hash"]

    renew = app_client.post(
        f"/api/runtime/sessions/{session['id']}/renew",
        headers=runtime_headers,
        json={"lease_seconds": 1800},
    )

    assert renew.status_code == 200
    data = renew.json()
    assert data["id"] == session["id"]
    assert data["status"] == "active"
    assert data["lease_expires_at"] > stored_before["lease_expires_at"]
    assert "viewer_token_hash" not in data

    stored_after = db.get_runtime_session(session["id"])
    assert stored_after is not None
    assert stored_after["viewer_token_hash"] == stored_before["viewer_token_hash"]
    assert stored_after["viewer_token_expires_at"] == stored_before["viewer_token_expires_at"]


def test_runtime_session_renew_rejects_missing_or_terminated_session(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    missing = app_client.post(
        "/api/runtime/sessions/missing/renew",
        headers=runtime_headers,
        json={"lease_seconds": 1800},
    )
    assert missing.status_code == 404

    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)
    terminate = app_client.post(
        f"/api/runtime/sessions/{session['id']}/terminate",
        headers=runtime_headers,
    )
    assert terminate.status_code == 200

    renew = app_client.post(
        f"/api/runtime/sessions/{session['id']}/renew",
        headers=runtime_headers,
        json={"lease_seconds": 1800},
    )

    assert renew.status_code == 409
    assert renew.json()["detail"] == "Runtime session is not active"


def test_runtime_service_actions_write_redacted_audit_events(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(
        app_client,
        runtime_headers,
        profile_id,
        external_session_id="pm-session-audit",
    )

    get_resp = app_client.get(
        f"/api/runtime/sessions/{session['id']}",
        headers=runtime_headers,
    )
    assert get_resp.status_code == 200

    token_resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 60},
    )
    assert token_resp.status_code == 201
    stored_with_token = db.get_runtime_session(session["id"])
    assert stored_with_token is not None

    renew = app_client.post(
        f"/api/runtime/sessions/{session['id']}/renew",
        headers=runtime_headers,
        json={"lease_seconds": 1800},
    )
    assert renew.status_code == 200

    terminate = app_client.post(
        f"/api/runtime/sessions/{session['id']}/terminate",
        headers=runtime_headers,
    )
    assert terminate.status_code == 200

    events = db.list_audit_events()
    assert [event["event_type"] for event in events] == [
        "runtime.session.created",
        "runtime.session.read",
        "runtime.viewer_token.created",
        "runtime.session.renewed",
        "runtime.session.terminated",
    ]
    assert all(event["actor_type"] == "runtime_service" for event in events)
    assert all(event["runtime_session_id"] == session["id"] for event in events)
    assert all(event["profile_id"] == profile_id for event in events)
    assert all(event["external_session_id"] == "pm-session-audit" for event in events)
    assert events[0]["metadata"] == {
        "profile_source": "profile_id",
        "lease_seconds": 900,
    }
    assert events[2]["metadata"] == {
        "ttl_seconds": 60,
        "viewer_token_expires_at": token_resp.json()["expires_at"],
    }
    assert events[3]["metadata"] == {
        "lease_seconds": 1800,
        "lease_expires_at": renew.json()["lease_expires_at"],
    }

    serialized_events = json.dumps(events, sort_keys=True)
    assert token_resp.json()["viewer_token"] not in serialized_events
    assert stored_with_token["viewer_token_hash"] not in serialized_events
    assert runtime_headers["X-Runtime-Service-Token"] not in serialized_events
    assert "viewer_url" not in serialized_events
    assert "wallet" not in serialized_events
    assert "order" not in serialized_events
    assert "billing" not in serialized_events


def test_runtime_audit_ignores_unauthenticated_runtime_requests(
    app_client: TestClient,
):
    profile_id = _create_profile(app_client)

    resp = app_client.post(
        "/api/runtime/sessions",
        headers={"X-Runtime-Service-Token": "wrong-runtime-secret"},
        json={
            "external_session_id": "pm-session-not-audited",
            "profile_id": profile_id,
            "lease_seconds": 900,
            "viewer_token": "plain-viewer-token",
            "cookie": "session-cookie",
        },
    )

    assert resp.status_code == 401
    assert _audit_event_types() == []


def test_audit_metadata_sanitizer_removes_sensitive_fields(tmp_db):
    db.create_audit_event(
        event_type="runtime.test",
        actor_type="runtime_service",
        runtime_session_id="session-1",
        profile_id="profile-1",
        external_session_id="external-1",
        metadata={
            "safe": "kept",
            "viewer_token": "plain-viewer-token",
            "viewer_token_hash": "hashed-viewer-token",
            "runtime_service_token": "runtime-secret",
            "proxy_url": "http://user:proxy-pass@example.test:8080",
            "message": "proxy http://user:message-pass@example.test:8080 failed",
            "nested": {
                "cookie": "session-cookie",
                "safe_nested": "also-kept",
            },
        },
    )

    events = db.list_audit_events()
    assert len(events) == 1
    assert events[0]["metadata"] == {
        "safe": "kept",
        "message": "proxy http://example.test:8080 failed",
        "nested": {"safe_nested": "also-kept"},
    }
    serialized_events = json.dumps(events, sort_keys=True)
    assert "plain-viewer-token" not in serialized_events
    assert "hashed-viewer-token" not in serialized_events
    assert "runtime-secret" not in serialized_events
    assert "proxy-pass" not in serialized_events
    assert "user:" not in serialized_events
    assert "message-pass" not in serialized_events
    assert "session-cookie" not in serialized_events
