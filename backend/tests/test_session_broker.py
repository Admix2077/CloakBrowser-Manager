"""Runtime session broker API tests."""

from __future__ import annotations

import sys
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from backend import database as db, main


def test_runtime_live_verifier_source_exists_and_is_opt_in():
    verifier = Path(__file__).with_name("test_runtime_live.py")

    assert verifier.exists()
    source = verifier.read_text()
    assert "RUN_LIVE_RUNTIME_WORKSPACE" in source
    assert "pytest.mark.skipif" in source
    assert "test_live_runtime_workspace_env_guard_rejects_invalid_values" in source
    assert "_assert_live_runtime_workspace_env" in source
    assert "_assert_http_api_base_url" in source
    assert "_assert_optional_positive_integer_env" in source
    assert "_build_runtime_live_not_verified_report" in source
    assert "_write_runtime_live_not_verified_report" in source
    assert "test-reports" in source
    assert "RUNTIME_LIVE_WORKSPACE_E2E_READY: NOT VERIFIED" in source
    assert "RUNTIME_LIVE_WORKSPACE_PREFLIGHT=FAIL" in source
    assert "No environment values are written." in source
    assert "_assert_no_sensitive_report_text" in source
    assert "CLOAKBROWSER_RUNTIME_API_BASE_URL" in source
    assert "CLOAKBROWSER_RUNTIME_SERVICE_TOKEN" in source
    assert "/api/runtime/sessions" in source
    assert "/viewer-token" in source
    assert "/vnc?" in source
    assert "asyncio.wait_for" in source
    assert "websocket.recv()" in source
    assert "RFB " in source
    assert "finally:" in source
    assert "/terminate" in source
    assert '"confirm_terminate": True' in source
    assert "print(" not in source


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


def _runtime_audit_events() -> list[dict]:
    return [
        event
        for event in db.list_audit_events()
        if event["event_type"].startswith("runtime.")
    ]


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


def test_runtime_session_create_rejects_extra_business_and_secret_fields(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    leak_marker = "runtime-create-extra-secret"

    resp = app_client.post(
        "/api/runtime/sessions",
        headers=runtime_headers,
        json={
            "external_session_id": "pm-session-extra-fields",
            "profile_id": profile_id,
            "lease_seconds": 900,
            "order_id": f"order-{leak_marker}",
            "wallet_id": f"wallet-{leak_marker}",
            "viewer_token": f"viewer-{leak_marker}",
            "runtime_service_token": f"runtime-{leak_marker}",
            "cookie": f"sid={leak_marker}",
            "proxy_password": leak_marker,
        },
    )

    assert resp.status_code == 422
    serialized_response = json.dumps(resp.json(), sort_keys=True)
    assert leak_marker not in serialized_response
    assert "viewer_token" not in serialized_response
    assert db.count_live_runtime_sessions() == 0
    assert "runtime.session.created" not in _audit_event_types()
    serialized_events = json.dumps(db.list_audit_events(), sort_keys=True)
    assert leak_marker not in serialized_events


def test_runtime_session_response_sanitizes_persisted_status(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    leak_marker = "runtime-status-leak-marker"
    session = db.create_runtime_session(
        profile_id=profile_id,
        external_session_id="pm-session-persisted-status",
        lease_seconds=900,
        status=f"active {leak_marker}",
    )

    resp = app_client.get(
        f"/api/runtime/sessions/{session['id']}",
        headers=runtime_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unknown"
    assert leak_marker not in json.dumps(data, sort_keys=True)


def test_runtime_session_response_sanitizes_persisted_timestamp_fields(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    leak_marker = "runtime-timestamp-secret"
    session = db.create_runtime_session(
        profile_id=profile_id,
        external_session_id="pm-session-persisted-timestamps",
        lease_seconds=900,
    )
    with db.get_db() as conn:
        conn.execute(
            """UPDATE runtime_sessions
               SET lease_expires_at = ?, created_at = ?, updated_at = ?
               WHERE id = ?""",
            (
                f"2026-06-03T00:00:00+00:00 token={leak_marker}",
                f"created Authorization=Bearer {leak_marker}",
                f"https://runtime.example/updated?token={leak_marker}",
                session["id"],
            ),
        )
        conn.commit()

    resp = app_client.get(
        f"/api/runtime/sessions/{session['id']}",
        headers=runtime_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["lease_expires_at"] == "unknown"
    assert data["created_at"] == "unknown"
    assert data["updated_at"] == "unknown"
    serialized = json.dumps(data, sort_keys=True)
    assert leak_marker not in serialized
    assert "Authorization" not in serialized
    assert "Bearer" not in serialized
    assert "runtime.example" not in serialized


def test_runtime_session_response_sanitizes_persisted_external_session_id(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    leak_marker = "runtime-external-session-secret"
    session = db.create_runtime_session(
        profile_id=profile_id,
        external_session_id=(
            f"https://runtime.example/session?token={leak_marker} "
            f"Authorization=Bearer {leak_marker}"
        ),
        lease_seconds=900,
    )

    resp = app_client.get(
        f"/api/runtime/sessions/{session['id']}",
        headers=runtime_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["external_session_id"] == "unknown"
    serialized = json.dumps(data, sort_keys=True)
    for leaked in (
        leak_marker,
        "runtime.example",
        "Authorization",
        "Bearer",
        "token=",
    ):
        assert leaked not in serialized


def test_runtime_session_response_omits_sensitive_external_session_id_markers(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    sensitive_ids = [
        "api_key-runtime-external-marker",
        "x-api-key-runtime-external-marker",
        "access_token-runtime-external-marker",
        "refresh_token-runtime-external-marker",
        "session_id-runtime-external-marker",
        "client_secret-runtime-external-marker",
        "private_key-runtime-external-marker",
        "api-key-runtime-external-marker",
        "client-secret-runtime-external-marker",
        "session-id-runtime-external-marker",
        "private-key-runtime-external-marker",
        "runtime_service_token_runtime_external_marker",
        "service_token_runtime_external_marker",
    ]
    sensitive_sessions = [
        db.create_runtime_session(
            profile_id=profile_id,
            external_session_id=external_session_id,
            lease_seconds=900,
        )
        for external_session_id in sensitive_ids
    ]
    public_session = db.create_runtime_session(
        profile_id=profile_id,
        external_session_id="pm-session-runtime-public-marker",
        lease_seconds=900,
    )

    sensitive_responses = []
    for session in sensitive_sessions:
        resp = app_client.get(
            f"/api/runtime/sessions/{session['id']}",
            headers=runtime_headers,
        )
        assert resp.status_code == 200
        sensitive_responses.append(resp.json())

    public_resp = app_client.get(
        f"/api/runtime/sessions/{public_session['id']}",
        headers=runtime_headers,
    )

    assert [data["external_session_id"] for data in sensitive_responses] == ["unknown"] * 13
    assert public_resp.status_code == 200
    assert public_resp.json()["external_session_id"] == "pm-session-runtime-public-marker"
    serialized_responses = json.dumps(sensitive_responses, sort_keys=True)
    for external_session_id in sensitive_ids:
        assert external_session_id not in serialized_responses


def test_runtime_session_response_omits_viewer_and_auth_token_external_session_markers(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    sensitive_ids = [
        "auth_token-runtime-external-marker",
        "auth-token-runtime-external-marker",
        "viewer_token-runtime-external-marker",
        "viewer-token-runtime-external-marker",
    ]
    sessions = [
        db.create_runtime_session(
            profile_id=profile_id,
            external_session_id=external_session_id,
            lease_seconds=900,
        )
        for external_session_id in sensitive_ids
    ]
    public_session = db.create_runtime_session(
        profile_id=profile_id,
        external_session_id="pm-session-token",
        lease_seconds=900,
    )

    sensitive_responses = []
    for session in sessions:
        resp = app_client.get(
            f"/api/runtime/sessions/{session['id']}",
            headers=runtime_headers,
        )
        assert resp.status_code == 200
        sensitive_responses.append(resp.json())

    public_resp = app_client.get(
        f"/api/runtime/sessions/{public_session['id']}",
        headers=runtime_headers,
    )

    assert [data["external_session_id"] for data in sensitive_responses] == ["unknown"] * 4
    assert public_resp.status_code == 200
    assert public_resp.json()["external_session_id"] == "pm-session-token"
    serialized_responses = json.dumps(sensitive_responses, sort_keys=True)
    for external_session_id in sensitive_ids:
        assert external_session_id not in serialized_responses


def test_runtime_session_response_sanitizes_persisted_profile_id(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    leak_marker = "runtime-profile-id-secret"
    profile_id = _create_profile(app_client)
    polluted_profile_id = (
        f"https://runtime-profile.example/profile?token={leak_marker} "
        f"Authorization=Bearer {leak_marker}"
    )
    with db.get_db() as conn:
        conn.execute("UPDATE profiles SET id = ? WHERE id = ?", (polluted_profile_id, profile_id))
        conn.commit()
    session = db.create_runtime_session(
        profile_id=polluted_profile_id,
        external_session_id="pm-session-persisted-profile-id",
        lease_seconds=900,
    )

    resp = app_client.get(
        f"/api/runtime/sessions/{session['id']}",
        headers=runtime_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["profile_id"] == "unknown"
    serialized = json.dumps(data, sort_keys=True)
    for leaked in (
        leak_marker,
        "runtime-profile.example",
        "Authorization",
        "Bearer",
        "token=",
    ):
        assert leaked not in serialized


def test_runtime_session_response_sanitizes_persisted_session_id(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    leak_marker = "runtime-session-id-secret"
    profile_id = _create_profile(app_client)
    session = db.create_runtime_session(
        profile_id=profile_id,
        external_session_id="pm-session-persisted-session-id",
        lease_seconds=900,
    )
    polluted_session_id = (
        f"runtime-session-id {leak_marker} "
        f"token={leak_marker} Authorization=Bearer {leak_marker}"
    )
    with db.get_db() as conn:
        conn.execute(
            "UPDATE runtime_sessions SET id = ? WHERE id = ?",
            (polluted_session_id, session["id"]),
        )
        conn.commit()

    resp = app_client.get(
        f"/api/runtime/sessions/{quote(polluted_session_id, safe='')}",
        headers=runtime_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "unknown"
    read_events = [
        event
        for event in _runtime_audit_events()
        if event["event_type"] == "runtime.session.read"
    ]
    assert len(read_events) == 1
    assert read_events[0]["runtime_session_id"] is None
    serialized = json.dumps({"response": data, "audit": read_events}, sort_keys=True)
    for leaked in (
        leak_marker,
        "Authorization",
        "Bearer",
        "token=",
    ):
        assert leaked not in serialized


def test_runtime_viewer_token_response_sanitizes_persisted_session_id(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    leak_marker = "viewer-token-session-id-secret"
    profile_id = _create_profile(app_client)
    session = db.create_runtime_session(
        profile_id=profile_id,
        external_session_id="pm-session-viewer-token-session-id",
        lease_seconds=900,
    )
    polluted_session_id = (
        f"viewer-token-session-id {leak_marker} "
        f"token={leak_marker} Authorization=Bearer {leak_marker}"
    )
    with db.get_db() as conn:
        conn.execute(
            "UPDATE runtime_sessions SET id = ? WHERE id = ?",
            (polluted_session_id, session["id"]),
        )
        conn.commit()

    resp = app_client.post(
        f"/api/runtime/sessions/{quote(polluted_session_id, safe='')}/viewer-token",
        headers=runtime_headers,
        json={"ttl_seconds": 60},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["viewer_url"].startswith("/api/runtime/sessions/unknown/vnc?viewer_token=")
    token_events = [
        event
        for event in _runtime_audit_events()
        if event["event_type"] == "runtime.viewer_token.created"
    ]
    assert len(token_events) == 1
    assert token_events[0]["runtime_session_id"] is None
    serialized = json.dumps({"response": data, "audit": token_events}, sort_keys=True)
    for leaked in (
        leak_marker,
        "Authorization",
        "Bearer",
    ):
        assert leaked not in serialized


def test_runtime_viewer_failure_audit_omits_sensitive_external_session_id(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    leak_marker = "viewer-external-session-secret"
    session = db.create_runtime_session(
        profile_id=profile_id,
        external_session_id=(
            f"https://viewer.example/session?token={leak_marker} "
            f"Authorization=Bearer {leak_marker}"
        ),
        lease_seconds=900,
    )

    with pytest.raises(Exception) as rejected:
        with app_client.websocket_connect(
            f"/api/runtime/sessions/{session['id']}/vnc?viewer_token=wrong-token",
            headers={"origin": "http://testserver"},
        ):
            pass

    assert rejected.value.code == 4401
    failures = _viewer_failure_events(session["id"])
    assert len(failures) == 1
    assert failures[0]["external_session_id"] is None
    serialized = json.dumps(failures, sort_keys=True)
    for leaked in (
        leak_marker,
        "viewer.example",
        "Authorization",
        "Bearer",
        "token=",
        "wrong-token",
    ):
        assert leaked not in serialized


def test_runtime_viewer_failure_audit_omits_sensitive_profile_id(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    leak_marker = "viewer-profile-id-secret"
    profile_id = _create_profile(app_client)
    polluted_profile_id = (
        f"https://viewer-profile.example/profile?token={leak_marker} "
        f"Authorization=Bearer {leak_marker}"
    )
    with db.get_db() as conn:
        conn.execute("UPDATE profiles SET id = ? WHERE id = ?", (polluted_profile_id, profile_id))
        conn.commit()
    session = db.create_runtime_session(
        profile_id=polluted_profile_id,
        external_session_id="pm-session-persisted-profile-id",
        lease_seconds=900,
    )

    with pytest.raises(Exception) as rejected:
        with app_client.websocket_connect(
            f"/api/runtime/sessions/{session['id']}/vnc?viewer_token=wrong-token",
            headers={"origin": "http://testserver"},
        ):
            pass

    assert rejected.value.code == 4401
    failures = _viewer_failure_events(session["id"])
    assert len(failures) == 1
    assert failures[0]["profile_id"] is None
    assert failures[0]["external_session_id"] == "pm-session-persisted-profile-id"
    serialized = json.dumps(failures, sort_keys=True)
    for leaked in (
        leak_marker,
        "viewer-profile.example",
        "Authorization",
        "Bearer",
        "token=",
        "wrong-token",
    ):
        assert leaked not in serialized


def test_runtime_viewer_origin_failure_audit_omits_sensitive_session_id(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    leak_marker = "viewer-session-id-secret"
    polluted_session_id = (
        f"viewer-session-id {leak_marker} "
        f"token={leak_marker} Authorization=Bearer {leak_marker}"
    )

    with pytest.raises(Exception) as rejected:
        with app_client.websocket_connect(
            f"/api/runtime/sessions/{quote(polluted_session_id, safe='')}/vnc"
            f"?viewer_token={leak_marker}",
            headers={"origin": "http://evil.com"},
        ):
            pass

    assert rejected.value.code == 4403
    failures = _viewer_failure_events()
    assert len(failures) == 1
    assert failures[0]["runtime_session_id"] is None
    assert failures[0]["profile_id"] is None
    assert failures[0]["external_session_id"] is None
    assert failures[0]["metadata"] == {"reason_code": "origin_not_allowed"}
    serialized = json.dumps(failures, sort_keys=True)
    for leaked in (
        leak_marker,
        "evil.com",
        "Authorization",
        "Bearer",
        "token=",
        "viewer_token",
    ):
        assert leaked not in serialized


def test_runtime_session_create_respects_max_running_profiles(
    app_client: TestClient,
    runtime_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("MAX_RUNNING_PROFILES", "1")
    existing_profile_id = _create_profile(app_client, "Existing Runtime")
    target_profile_id = _create_profile(app_client, "Blocked Runtime")
    main.browser_mgr.running[existing_profile_id] = _mock_running_profile()

    with patch.object(
        main.browser_mgr.vnc,
        "allocate",
        new=AsyncMock(side_effect=AssertionError("must not allocate VNC when max running profiles is reached")),
    ) as allocate:
        resp = app_client.post(
            "/api/runtime/sessions",
            headers=runtime_headers,
            json={
                "external_session_id": "pm-session-limit",
                "profile_id": target_profile_id,
                "lease_seconds": 900,
            },
        )

    assert resp.status_code == 409
    assert resp.json() == {"detail": "Maximum running profiles reached"}
    allocate.assert_not_awaited()
    assert target_profile_id not in main.browser_mgr.running
    assert "runtime.session.created" not in _audit_event_types()


def test_runtime_session_create_resource_limit_detail_does_not_echo_exception_text(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client, "Sensitive Runtime Limit")

    with patch.object(
        main.browser_mgr,
        "launch",
        new=AsyncMock(
            side_effect=main.BrowserResourceLimitError(
                "Maximum running profiles reached for "
                "http://user:hiddenpass@runtime-limit.example:8080 token=super-secret"
            )
        ),
    ):
        resp = app_client.post(
            "/api/runtime/sessions",
            headers=runtime_headers,
            json={
                "external_session_id": "pm-session-sensitive-limit",
                "profile_id": profile_id,
                "lease_seconds": 900,
            },
        )

    assert resp.status_code == 409
    assert resp.json() == {"detail": "Maximum running profiles reached"}
    serialized = str(resp.json())
    assert "hiddenpass" not in serialized
    assert "super-secret" not in serialized
    assert "runtime-limit.example" not in serialized
    assert "user:" not in serialized
    assert "runtime.session.created" not in _audit_event_types()


def test_runtime_session_create_redacts_sensitive_launch_value_error_detail(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client, "Sensitive Runtime Launch")

    with patch.object(
        main.browser_mgr,
        "launch",
        new=AsyncMock(
            side_effect=ValueError(
                "Proxy URL invalid port: "
                "http://user:hiddenpass@runtime-launch.example:99999 token=super-secret"
            )
        ),
    ):
        resp = app_client.post(
            "/api/runtime/sessions",
            headers=runtime_headers,
            json={
                "external_session_id": "pm-session-sensitive-launch",
                "profile_id": profile_id,
                "lease_seconds": 900,
            },
        )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "Proxy URL invalid port"}
    serialized = str(resp.json())
    assert "hiddenpass" not in serialized
    assert "super-secret" not in serialized
    assert "runtime-launch.example" not in serialized
    assert "user:" not in serialized
    assert "runtime.session.created" not in _audit_event_types()


def test_runtime_session_create_launch_failure_log_omits_sensitive_profile_id(
    app_client: TestClient,
    runtime_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
):
    leak_marker = "runtime-launch-profile-id-secret"
    profile_id = _create_profile(app_client)
    polluted_profile_id = (
        f"runtime-launch-profile-id {leak_marker} "
        f"token={leak_marker} Authorization=Bearer {leak_marker}"
    )
    with db.get_db() as conn:
        conn.execute("UPDATE profiles SET id = ? WHERE id = ?", (polluted_profile_id, profile_id))
        conn.commit()

    with caplog.at_level("ERROR", logger="invisible_browser.manager"):
        with patch.object(
            main.browser_mgr,
            "launch",
            new=AsyncMock(side_effect=RuntimeError(f"runtime launch failure {leak_marker}")),
        ):
            resp = app_client.post(
                "/api/runtime/sessions",
                headers=runtime_headers,
                json={
                    "external_session_id": "pm-session-sensitive-launch-log",
                    "profile_id": polluted_profile_id,
                    "lease_seconds": 900,
                },
            )

    assert resp.status_code == 500
    assert resp.json() == {"detail": "Failed to launch browser"}
    assert "Failed to launch runtime session profile unknown error_type=RuntimeError" in caplog.text
    for leaked in (
        leak_marker,
        "Authorization",
        "Bearer",
        "token=",
    ):
        assert leaked not in caplog.text
    assert "runtime.session.created" not in _audit_event_types()


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


def test_runtime_session_create_from_template_sanitizes_generated_profile_name(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    leak_marker = "runtime-template-name-secret"
    template = app_client.post(
        "/api/profile-templates",
        json={
            "name": "Runtime Template",
            "platform": "windows",
            "geoip": False,
        },
    )
    assert template.status_code == 201

    with patch.object(
        main.browser_mgr,
        "launch",
        new=AsyncMock(return_value=_mock_running_profile()),
    ):
        resp = app_client.post(
            "/api/runtime/sessions",
            headers=runtime_headers,
            json={
                "external_session_id": (
                    f"https://runtime-template.example/session?token={leak_marker} "
                    f"Authorization=Bearer {leak_marker}"
                ),
                "template_id": template.json()["id"],
                "lease_seconds": 600,
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["external_session_id"] == "unknown"
    created_profile = app_client.get(f"/api/profiles/{data['profile_id']}").json()
    assert created_profile["name"] == "Runtime session"
    serialized = json.dumps({"session": data, "profile": created_profile}, sort_keys=True)
    for leaked in (
        leak_marker,
        "runtime-template.example",
        "Authorization",
        "Bearer",
        "token=",
    ):
        assert leaked not in serialized


def test_runtime_session_create_from_template_sanitizes_template_identity_before_launch(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    leak_marker = "runtime-template-identity-secret"
    template = db.create_profile_template(
        name="Historical polluted runtime template",
        platform=f"linux-{leak_marker}",
        screen_width=f"1920\nAuthorization: Bearer {leak_marker}",
        screen_height=f"1080?token={leak_marker}",
        gpu_vendor=f"Google Inc. (NVIDIA)\nAuthorization: Bearer {leak_marker}",
        gpu_renderer=f"ANGLE (NVIDIA) https://runtime-template.invalid/?token={leak_marker}",
        hardware_concurrency=f"8 cookie={leak_marker}",
        color_scheme=f"dark-{leak_marker}",
        human_preset=f"careful-{leak_marker}",
        launch_args=[
            "--private-window",
            f"--user-agent={leak_marker}",
            f"Bearer {leak_marker}",
        ],
    )

    with patch.object(
        main.browser_mgr,
        "launch",
        new=AsyncMock(return_value=_mock_running_profile()),
    ) as launch:
        resp = app_client.post(
            "/api/runtime/sessions",
            headers=runtime_headers,
            json={
                "external_session_id": "pm-session-template-sanitized",
                "template_id": template["id"],
                "lease_seconds": 600,
            },
        )

    assert resp.status_code == 201
    launch.assert_awaited_once()
    launched_profile = launch.await_args.args[0]
    assert launched_profile["platform"] == "windows"
    assert launched_profile["screen_width"] == 1920
    assert launched_profile["screen_height"] == 1080
    assert launched_profile["gpu_vendor"] is None
    assert launched_profile["gpu_renderer"] is None
    assert launched_profile["hardware_concurrency"] is None
    assert launched_profile["color_scheme"] is None
    assert launched_profile["human_preset"] == "default"
    assert launched_profile["launch_args"] == ["--private-window"]
    serialized = json.dumps({"session": resp.json(), "profile": launched_profile}, sort_keys=True)
    for leaked in (
        leak_marker,
        "runtime-template.invalid",
        "Authorization",
        "Bearer",
        "token=",
        "cookie=",
    ):
        assert leaked not in serialized


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


def test_ui_auth_token_cannot_create_runtime_session(
    app_client: TestClient,
    runtime_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    profile_id = _create_profile(app_client)
    monkeypatch.setattr(main, "AUTH_TOKEN", "ui-secret", raising=False)

    resp = app_client.post(
        "/api/runtime/sessions",
        headers={"Authorization": "Bearer ui-secret"},
        json={
            "external_session_id": "pm-session-ui-token-rejected",
            "profile_id": profile_id,
            "lease_seconds": 300,
        },
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Runtime service token required"


def test_ui_auth_cookie_cannot_create_runtime_session(
    app_client: TestClient,
    runtime_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    profile_id = _create_profile(app_client)
    monkeypatch.setattr(main, "AUTH_TOKEN", "ui-secret", raising=False)
    app_client.cookies.set("auth_token", "ui-secret")

    resp = app_client.post(
        "/api/runtime/sessions",
        json={
            "external_session_id": "pm-session-ui-cookie-rejected",
            "profile_id": profile_id,
            "lease_seconds": 300,
        },
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Runtime service token required"


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


def test_runtime_viewer_token_rejects_extra_business_and_secret_fields(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(app_client, runtime_headers, profile_id)
    leak_marker = "runtime-viewer-token-extra-secret"

    resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/viewer-token",
        headers=runtime_headers,
        json={
            "ttl_seconds": 60,
            "order_id": f"order-{leak_marker}",
            "wallet_id": f"wallet-{leak_marker}",
            "viewer_token": f"viewer-{leak_marker}",
            "runtime_service_token": f"runtime-{leak_marker}",
            "cookie": f"sid={leak_marker}",
            "proxy_password": leak_marker,
        },
    )

    assert resp.status_code == 422
    serialized_response = json.dumps(resp.json(), sort_keys=True)
    assert leak_marker not in serialized_response
    assert "viewer_token" not in serialized_response
    stored = db.get_runtime_session(session["id"])
    assert stored is not None
    assert stored["viewer_token_hash"] is None
    assert stored["viewer_token_expires_at"] is None
    serialized_events = json.dumps(db.list_audit_events(), sort_keys=True)
    assert "runtime.viewer_token.created" not in _audit_event_types()
    assert leak_marker not in serialized_events


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


def test_runtime_viewer_disconnect_audit_sanitizes_non_integer_close_code(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(
        app_client,
        runtime_headers,
        profile_id,
        external_session_id="pm-session-vnc-close-code",
    )
    stored_session = db.get_runtime_session(session["id"])
    assert stored_session is not None
    leak_marker = "runtime-close-code-secret"

    main._audit_runtime_viewer_event(
        "runtime.viewer.disconnected",
        stored_session,
        {
            "close_code": (
                f"1000 token={leak_marker} "
                f"Authorization=Bearer {leak_marker}"
            ),
        },
    )

    [event] = [
        event
        for event in db.list_audit_events(session["id"])
        if event["event_type"] == "runtime.viewer.disconnected"
    ]
    assert event["metadata"] == {"close_code": None}
    serialized = json.dumps(event, sort_keys=True)
    for leaked in (
        leak_marker,
        "token=",
        "Authorization",
        "Bearer",
    ):
        assert leaked not in serialized


def test_runtime_viewer_connected_audit_allows_only_public_subprotocol_metadata(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(
        app_client,
        runtime_headers,
        profile_id,
        external_session_id="pm-session-vnc-subprotocol",
    )
    stored_session = db.get_runtime_session(session["id"])
    assert stored_session is not None
    leak_marker = "runtime-subprotocol-secret"

    main._audit_runtime_viewer_event(
        "runtime.viewer.connected",
        stored_session,
        {
            "subprotocol": (
                f"binary token={leak_marker} "
                f"Authorization=Bearer {leak_marker}"
            ),
            "origin": f"https://viewer.example?token={leak_marker}",
            "viewer_url": f"/api/runtime/sessions/{session['id']}/vnc?viewer_token={leak_marker}",
        },
    )

    [event] = [
        event
        for event in db.list_audit_events(session["id"])
        if event["event_type"] == "runtime.viewer.connected"
    ]
    assert event["metadata"] == {"subprotocol": None}
    serialized = json.dumps(event, sort_keys=True)
    for leaked in (
        leak_marker,
        "token=",
        "Authorization",
        "Bearer",
        "origin",
        "viewer_url",
        "viewer.example",
        "viewer_token",
    ):
        assert leaked not in serialized


def test_runtime_viewer_audit_handles_non_dict_metadata_without_leaking(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(
        app_client,
        runtime_headers,
        profile_id,
        external_session_id="pm-session-vnc-non-dict-metadata",
    )
    stored_session = db.get_runtime_session(session["id"])
    assert stored_session is not None
    leak_marker = "runtime-viewer-non-dict-metadata-secret"

    main._audit_runtime_viewer_event(
        "runtime.viewer.connected",
        stored_session,
        f"subprotocol=binary token={leak_marker} Authorization=Bearer {leak_marker}",
    )
    main._audit_runtime_viewer_event(
        "runtime.viewer.disconnected",
        stored_session,
        [f"close_code=1000 token={leak_marker}"],
    )

    events = [
        event
        for event in db.list_audit_events(session["id"])
        if event["event_type"] in {"runtime.viewer.connected", "runtime.viewer.disconnected"}
    ]
    assert [event["metadata"] for event in events] == [
        {"subprotocol": None},
        {"close_code": None},
    ]
    serialized = json.dumps(events, sort_keys=True)
    for leaked in (
        leak_marker,
        "token=",
        "Authorization",
        "Bearer",
        "subprotocol=binary",
        "close_code=1000",
    ):
        assert leaked not in serialized


def test_runtime_viewer_failure_audit_sanitizes_reason_code_metadata(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(
        app_client,
        runtime_headers,
        profile_id,
        external_session_id="pm-session-vnc-failure-reason",
    )
    stored_session = db.get_runtime_session(session["id"])
    assert stored_session is not None
    leak_marker = "runtime-viewer-failure-reason-secret"

    main._audit_runtime_viewer_failure(
        (
            f"backend_vnc_unavailable token={leak_marker} "
            f"Authorization=Bearer {leak_marker}"
        ),
        session=stored_session,
    )

    [event] = _viewer_failure_events(session["id"])
    assert event["metadata"] == {"reason_code": "unknown"}
    serialized = json.dumps(event, sort_keys=True)
    for leaked in (
        leak_marker,
        "token=",
        "Authorization",
        "Bearer",
    ):
        assert leaked not in serialized


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


def test_runtime_session_terminate_requires_explicit_confirmation_without_side_effects(
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
    assert stored_before["status"] == "active"
    assert stored_before["viewer_token_hash"]

    for payload in ({}, {"confirm_terminate": False}, {"confirm_terminate": "true"}):
        resp = app_client.post(
            f"/api/runtime/sessions/{session['id']}/terminate",
            headers=runtime_headers,
            json=payload,
        )
        assert resp.status_code == 422
        assert resp.json() == {
            "detail": "Runtime session terminate requires explicit confirmation"
        }

    stored_after = db.get_runtime_session(session["id"])
    assert stored_after is not None
    assert stored_after["status"] == "active"
    assert stored_after["viewer_token_hash"] == stored_before["viewer_token_hash"]
    assert stored_after["viewer_token_expires_at"] == stored_before["viewer_token_expires_at"]
    assert "runtime.session.terminated" not in _audit_event_types()


def test_runtime_session_terminate_rejects_extra_business_and_secret_fields(
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
    leak_marker = "runtime-terminate-extra-secret"

    resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/terminate",
        headers=runtime_headers,
        json={
            "confirm_terminate": True,
            "order_id": f"order-{leak_marker}",
            "wallet_id": f"wallet-{leak_marker}",
            "viewer_token": f"viewer-{leak_marker}",
            "runtime_service_token": f"runtime-{leak_marker}",
            "cookie": f"sid={leak_marker}",
            "proxy_password": leak_marker,
        },
    )

    assert resp.status_code == 422
    serialized_response = json.dumps(resp.json(), sort_keys=True)
    assert leak_marker not in serialized_response
    assert "viewer_token" not in serialized_response
    stored_after = db.get_runtime_session(session["id"])
    assert stored_after is not None
    assert stored_after["status"] == stored_before["status"]
    assert stored_after["viewer_token_hash"] == stored_before["viewer_token_hash"]
    assert stored_after["viewer_token_expires_at"] == stored_before["viewer_token_expires_at"]
    assert "runtime.session.terminated" not in _audit_event_types()
    serialized_events = json.dumps(db.list_audit_events(), sort_keys=True)
    assert leak_marker not in serialized_events


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
        json={"confirm_terminate": True},
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
        json={"confirm_terminate": True},
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


def test_runtime_session_renew_rejects_extra_business_and_secret_fields(
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
    leak_marker = "runtime-renew-extra-secret"

    resp = app_client.post(
        f"/api/runtime/sessions/{session['id']}/renew",
        headers=runtime_headers,
        json={
            "lease_seconds": 1800,
            "order_id": f"order-{leak_marker}",
            "wallet_id": f"wallet-{leak_marker}",
            "viewer_token": f"viewer-{leak_marker}",
            "runtime_service_token": f"runtime-{leak_marker}",
            "cookie": f"sid={leak_marker}",
            "proxy_password": leak_marker,
        },
    )

    assert resp.status_code == 422
    serialized_response = json.dumps(resp.json(), sort_keys=True)
    assert leak_marker not in serialized_response
    assert "viewer_token" not in serialized_response
    stored_after = db.get_runtime_session(session["id"])
    assert stored_after is not None
    assert stored_after["lease_expires_at"] == stored_before["lease_expires_at"]
    assert stored_after["viewer_token_hash"] == stored_before["viewer_token_hash"]
    assert stored_after["viewer_token_expires_at"] == stored_before["viewer_token_expires_at"]
    assert "runtime.session.renewed" not in _audit_event_types()
    serialized_events = json.dumps(db.list_audit_events(), sort_keys=True)
    assert leak_marker not in serialized_events


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
        json={"confirm_terminate": True},
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
        json={"confirm_terminate": True},
    )
    assert terminate.status_code == 200

    events = _runtime_audit_events()
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


def test_runtime_service_audit_allows_only_public_metadata_shapes(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(
        app_client,
        runtime_headers,
        profile_id,
        external_session_id="pm-session-runtime-audit-shape",
    )
    stored_session = db.get_runtime_session(session["id"])
    assert stored_session is not None
    leak_marker = "runtime-service-metadata-secret"

    main._audit_runtime_event(
        "runtime.session.created",
        stored_session,
        {
            "profile_source": (
                f"profile_id token={leak_marker} "
                f"Authorization=Bearer {leak_marker}"
            ),
            "lease_seconds": f"900 token={leak_marker}",
            "wallet": f"wallet-{leak_marker}",
        },
    )
    main._audit_runtime_event(
        "runtime.viewer_token.created",
        stored_session,
        {
            "ttl_seconds": f"60 token={leak_marker}",
            "viewer_token_expires_at": f"2026-06-03T00:00:00+00:00 token={leak_marker}",
            "viewer_url": f"/api/runtime/sessions/{session['id']}/vnc?viewer_token={leak_marker}",
        },
    )
    main._audit_runtime_event(
        "runtime.session.renewed",
        stored_session,
        {
            "lease_seconds": f"1800 token={leak_marker}",
            "lease_expires_at": f"2026-06-03T00:30:00+00:00 token={leak_marker}",
            "order": f"order-{leak_marker}",
        },
    )
    main._audit_runtime_event(
        "runtime.session.read",
        stored_session,
        {
            "viewer_url": f"/api/runtime/sessions/{session['id']}/vnc?viewer_token={leak_marker}",
            "billing": f"billing-{leak_marker}",
        },
    )

    events = [
        event
        for event in db.list_audit_events(session["id"])
        if event["created_at"] >= stored_session["created_at"]
    ][-4:]
    assert [event["event_type"] for event in events] == [
        "runtime.session.created",
        "runtime.viewer_token.created",
        "runtime.session.renewed",
        "runtime.session.read",
    ]
    assert events[0]["metadata"] == {
        "profile_source": "unknown",
        "lease_seconds": None,
    }
    assert events[1]["metadata"] == {
        "ttl_seconds": None,
        "viewer_token_expires_at": "unknown",
    }
    assert events[2]["metadata"] == {
        "lease_seconds": None,
        "lease_expires_at": "unknown",
    }
    assert events[3]["metadata"] == {}

    serialized_events = json.dumps(events, sort_keys=True)
    for leaked in (
        leak_marker,
        "token=",
        "Authorization",
        "Bearer",
        "viewer_url",
        "viewer_token=",
        "/vnc?",
        "wallet",
        "order",
        "billing",
    ):
        assert leaked not in serialized_events


def test_runtime_service_audit_handles_non_dict_metadata_without_leaking(
    app_client: TestClient,
    runtime_headers: dict[str, str],
):
    profile_id = _create_profile(app_client)
    session = _create_runtime_session(
        app_client,
        runtime_headers,
        profile_id,
        external_session_id="pm-session-runtime-non-dict-metadata",
    )
    stored_session = db.get_runtime_session(session["id"])
    assert stored_session is not None
    leak_marker = "runtime-service-non-dict-metadata-secret"

    main._audit_runtime_event(
        "runtime.session.created",
        stored_session,
        f"profile_source=profile_id token={leak_marker} Authorization=Bearer {leak_marker}",
    )
    main._audit_runtime_event(
        "runtime.viewer_token.created",
        stored_session,
        [f"viewer_token_expires_at=2026-06-03T00:00:00+00:00 token={leak_marker}"],
    )
    main._audit_runtime_event(
        "runtime.session.renewed",
        stored_session,
        (f"lease_seconds=900 token={leak_marker}",),
    )

    events = [
        event
        for event in db.list_audit_events(session["id"])
        if event["event_type"] in {
            "runtime.session.created",
            "runtime.viewer_token.created",
            "runtime.session.renewed",
        }
    ][-3:]
    assert [event["metadata"] for event in events] == [
        {"profile_source": "unknown", "lease_seconds": None},
        {"ttl_seconds": None, "viewer_token_expires_at": "unknown"},
        {"lease_seconds": None, "lease_expires_at": "unknown"},
    ]
    serialized = json.dumps(events, sort_keys=True)
    for leaked in (
        leak_marker,
        "token=",
        "Authorization",
        "Bearer",
        "profile_source=profile_id",
        "viewer_token_expires_at=",
        "lease_seconds=900",
    ):
        assert leaked not in serialized


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
    assert _runtime_audit_events() == []


def test_audit_metadata_sanitizer_removes_sensitive_fields(tmp_db):
    leak_marker = "audit-key-marker"
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
            "viewer-token-hash": "hashed-hyphen-viewer-token",
            "viewer-url": "http://viewer-user:viewer-pass@viewer.example.test/vnc",
            "runtime_service_token": "runtime-secret",
            "runtime-service-token": "runtime-hyphen-secret",
            "service-token": "service-hyphen-secret",
            "proxy_url": "http://user:proxy-pass@example.test:8080",
            "proxy-url": "http://hyphen-user:hyphen-proxy-pass@example.test:8080",
            "api_key": "plain-api-key",
            "x-api-key": "plain-header-api-key",
            "access_token": "plain-access-token",
            "refresh_token": "plain-refresh-token",
            "session_id": "plain-session-id",
            "client_secret": "plain-client-secret",
            "private_key": "plain-private-key",
            "message": (
                "proxy http://user:message-pass@example.test:8080 failed "
                "token=message-secret Authorization=Bearer bearer-secret "
                "api_key=message-api-key x-api-key: message-header-api-key "
                "api-key=message-hyphen-api-key client-secret=message-hyphen-client-secret "
                "access_token=message-access-token refresh_token=message-refresh-token "
                "session_id=message-session-id session-id=message-hyphen-session-id "
                "client_secret=message-client-secret private_key=message-private-key "
                "private-key=message-hyphen-private-key "
                "api_key-audit-message-marker x-api-key-audit-message-marker "
                "session_id-audit-message-marker private_key-audit-message-marker "
                "/data/profiles/profile-secret /tmp/xvnc-secret.log /home/jeff/profile-secret "
                r"C:\Users\Jeff\AppData\Local\CloakBrowser\profile-secret"
            ),
            "url_message": (
                "opened https://audit.example.test/account/check?session_id=audit-query-secret#private "
                "through socks5://user:pass@proxy.example:1080/path?token=audit-query-secret#frag"
            ),
            "ip_message": (
                "exit ip 203.0.113.45 via 198.51.100.20:8080 "
                "and ipv6 2001:db8::45 via [2001:db8::46]:443"
            ),
            "path_list": [
                "kept",
                "/data/runtime/profile-secret/state.json",
                {"path_message": "failed at /tmp/runtime-profile-secret/socket"},
                {"windows_path": "D:/profiles/profile-secret/state.json"},
                {"ip_message": "candidate 192.0.2.44 selected"},
                {"ipv6_message": "candidate 2001:db8::44 selected"},
            ],
            f"Authorization: Bearer {leak_marker}": "header-key",
            f"token={leak_marker}": "token-key",
            f"api_key={leak_marker}": "top-level-api-value",
            f"api-key={leak_marker}": "top-level-hyphen-api-value",
            f"x-api-key: {leak_marker}": "top-level-header-value",
            f"session_id={leak_marker}": "top-level-session-value",
            f"session-id={leak_marker}": "top-level-hyphen-session-value",
            f"client-secret={leak_marker}": "top-level-hyphen-client-value",
            f"private_key={leak_marker}": "top-level-private-value",
            f"private-key={leak_marker}": "top-level-hyphen-private-value",
            f"/data/audit/{leak_marker}": "path-key",
            "203.0.113.99": "ipv4-key",
            "client_2001:db8::99": "ipv6-key",
            "[2001:db8::98]": "bracketed-ipv6-key",
            "nested": {
                "cookie": "session-cookie",
                "safe_nested": "also-kept",
                f"Bearer {leak_marker}": "nested-header-key",
                "peer_198.51.100.99": "nested-ipv4-key",
                "peer_2001:db8::97": "nested-ipv6-key",
            },
        },
    )

    events = db.list_audit_events()
    assert len(events) == 1
    assert events[0]["metadata"] == {
        "safe": "kept",
        "message": (
            "proxy http://example.test:8080 failed "
            "token=[redacted] Authorization=[redacted] "
            "api_key=[redacted] x-api-key=[redacted] "
            "api-key=[redacted] client-secret=[redacted] "
            "access_token=[redacted] refresh_token=[redacted] "
            "session_id=[redacted] session-id=[redacted] "
            "client_secret=[redacted] private_key=[redacted] "
            "private-key=[redacted] "
            "[redacted] [redacted] [redacted] [redacted] "
            "[redacted-path] [redacted-path] [redacted-path] "
            "[redacted-path]"
        ),
        "url_message": (
            "opened https://audit.example.test/account/check "
            "through socks5://proxy.example:1080/path"
        ),
        "ip_message": (
            "exit ip [redacted-ip] via [redacted-ip]:8080 "
            "and ipv6 [redacted-ip] via [redacted-ip]:443"
        ),
        "path_list": [
            "kept",
            "[redacted-path]",
            {"path_message": "failed at [redacted-path]"},
            {"windows_path": "[redacted-path]"},
            {"ip_message": "candidate [redacted-ip] selected"},
            {"ipv6_message": "candidate [redacted-ip] selected"},
        ],
        "nested": {"safe_nested": "also-kept"},
    }
    serialized_events = json.dumps(events, sort_keys=True)
    assert "plain-viewer-token" not in serialized_events
    assert "hashed-viewer-token" not in serialized_events
    assert "hashed-hyphen-viewer-token" not in serialized_events
    assert "viewer-pass" not in serialized_events
    assert "runtime-secret" not in serialized_events
    assert "runtime-hyphen-secret" not in serialized_events
    assert "service-hyphen-secret" not in serialized_events
    assert "hyphen-proxy-pass" not in serialized_events
    assert "plain-api-key" not in serialized_events
    assert "plain-header-api-key" not in serialized_events
    assert "plain-access-token" not in serialized_events
    assert "plain-refresh-token" not in serialized_events
    assert "plain-session-id" not in serialized_events
    assert "plain-client-secret" not in serialized_events
    assert "plain-private-key" not in serialized_events
    assert "message-secret" not in serialized_events
    assert "bearer-secret" not in serialized_events
    assert "message-api-key" not in serialized_events
    assert "message-header-api-key" not in serialized_events
    assert "message-hyphen-api-key" not in serialized_events
    assert "message-hyphen-client-secret" not in serialized_events
    assert "message-access-token" not in serialized_events
    assert "message-refresh-token" not in serialized_events
    assert "message-session-id" not in serialized_events
    assert "message-hyphen-session-id" not in serialized_events
    assert "message-client-secret" not in serialized_events
    assert "message-private-key" not in serialized_events
    assert "message-hyphen-private-key" not in serialized_events
    assert "api_key-audit-message-marker" not in serialized_events
    assert "x-api-key-audit-message-marker" not in serialized_events
    assert "session_id-audit-message-marker" not in serialized_events
    assert "private_key-audit-message-marker" not in serialized_events
    assert leak_marker not in serialized_events
    assert "header-key" not in serialized_events
    assert "token-key" not in serialized_events
    assert "top-level-api-value" not in serialized_events
    assert "top-level-hyphen-api-value" not in serialized_events
    assert "top-level-header-value" not in serialized_events
    assert "top-level-session-value" not in serialized_events
    assert "top-level-hyphen-session-value" not in serialized_events
    assert "top-level-hyphen-client-value" not in serialized_events
    assert "top-level-private-value" not in serialized_events
    assert "top-level-hyphen-private-value" not in serialized_events
    assert "path-key" not in serialized_events
    assert "nested-header-key" not in serialized_events
    assert "ipv4-key" not in serialized_events
    assert "ipv6-key" not in serialized_events
    assert "bracketed-ipv6-key" not in serialized_events
    assert "nested-ipv4-key" not in serialized_events
    assert "nested-ipv6-key" not in serialized_events
    assert "Authorization: Bearer" not in serialized_events
    assert "/data/audit" not in serialized_events
    assert "/data/profiles" not in serialized_events
    assert "/data/runtime" not in serialized_events
    assert "/tmp/xvnc-secret.log" not in serialized_events
    assert "/tmp/runtime-profile-secret" not in serialized_events
    assert "/home/jeff" not in serialized_events
    assert "C:\\Users\\Jeff" not in serialized_events
    assert "D:/profiles" not in serialized_events
    assert "203.0.113.45" not in serialized_events
    assert "198.51.100.20" not in serialized_events
    assert "192.0.2.44" not in serialized_events
    assert "2001:db8::45" not in serialized_events
    assert "2001:db8::46" not in serialized_events
    assert "2001:db8::44" not in serialized_events
    assert "203.0.113.99" not in serialized_events
    assert "198.51.100.99" not in serialized_events
    assert "2001:db8::99" not in serialized_events
    assert "2001:db8::98" not in serialized_events
    assert "2001:db8::97" not in serialized_events
    assert "proxy-pass" not in serialized_events
    assert "user:" not in serialized_events
    assert "message-pass" not in serialized_events
    assert "audit-query-secret" not in serialized_events
    assert "session_id=audit-query-secret" not in serialized_events
    assert "?token" not in serialized_events
    assert "#private" not in serialized_events
    assert "#frag" not in serialized_events
    assert "session-cookie" not in serialized_events


def test_audit_metadata_sanitizer_sanitizes_tuple_values_before_persistence(tmp_db):
    leak_marker = "audit-tuple-secret"
    event = db.create_audit_event(
        event_type="runtime.test",
        actor_type="runtime_service",
        metadata={
            "tuple_values": (
                "kept",
                f"token={leak_marker}",
                {
                    "viewer_token": f"viewer-{leak_marker}",
                    "message": f"Authorization=Bearer {leak_marker}",
                },
            ),
            "nested": {
                "tuple_values": (
                    f"runtime_service_token_{leak_marker}",
                    "safe",
                )
            },
        },
    )

    with db.get_db() as conn:
        raw_metadata = conn.execute(
            "SELECT metadata FROM audit_events WHERE id = ?",
            (event["id"],),
        ).fetchone()[0]

    persisted = json.loads(raw_metadata)
    assert persisted == {
        "nested": {"tuple_values": ["[redacted]", "safe"]},
        "tuple_values": [
            "kept",
            "token=[redacted]",
            {"message": "Authorization=[redacted]"},
        ],
    }
    serialized_raw = json.dumps(persisted, sort_keys=True)
    assert leak_marker not in serialized_raw
    assert "viewer-" not in serialized_raw
    assert "Authorization=Bearer" not in serialized_raw
    assert "runtime_service_token" not in serialized_raw


def test_audit_metadata_sanitizer_collapses_malformed_url_without_credentials(tmp_db):
    leak_marker = "audit-malformed-url-secret"

    event = db.create_audit_event(
        event_type="runtime.test",
        actor_type="runtime_service",
        metadata={
            "message": (
                "proxy "
                f"http://audit-user:audit-pass@[2001:db8::1/path?token={leak_marker}#frag "
                "failed"
            )
        },
    )

    assert event["metadata"] == {"message": "proxy http://unknown failed"}
    events = db.list_audit_events()
    assert events[0]["metadata"] == {"message": "proxy http://unknown failed"}
    serialized_events = json.dumps(events, sort_keys=True)
    assert "audit-user" not in serialized_events
    assert "audit-pass" not in serialized_events
    assert "2001:db8" not in serialized_events
    assert leak_marker not in serialized_events
    assert "?token" not in serialized_events
    assert "#frag" not in serialized_events


def test_audit_event_reader_omits_sensitive_external_session_id_markers(tmp_db):
    sensitive_ids = [
        "api_key-audit-external-marker",
        "x-api-key-audit-external-marker",
        "access_token-audit-external-marker",
        "refresh_token-audit-external-marker",
        "auth_token-audit-external-marker",
        "auth-token-audit-external-marker",
        "session_id-audit-external-marker",
        "client_secret-audit-external-marker",
        "private_key-audit-external-marker",
        "api-key-audit-external-marker",
        "client-secret-audit-external-marker",
        "session-id-audit-external-marker",
        "private-key-audit-external-marker",
        "runtime_service_token_audit_external_marker",
        "service_token_audit_external_marker",
        "viewer_token-audit-external-marker",
        "viewer-token-audit-external-marker",
    ]
    for external_session_id in sensitive_ids:
        db.create_audit_event(
            event_type="runtime.test",
            actor_type="runtime_service",
            external_session_id=external_session_id,
            metadata={"safe": "kept"},
        )
    db.create_audit_event(
        event_type="runtime.test",
        actor_type="runtime_service",
        external_session_id="pm-session-public-marker",
        metadata={"safe": "kept"},
    )

    events = db.list_audit_events()

    assert len(events) == 18
    assert [event["external_session_id"] for event in events[:-1]] == [None] * 17
    assert events[-1]["external_session_id"] == "pm-session-public-marker"
    serialized_events = json.dumps(events, sort_keys=True)
    for external_session_id in sensitive_ids:
        assert external_session_id not in serialized_events


def test_audit_event_reader_omits_sensitive_event_type_markers(tmp_db):
    sensitive_event_types = [
        "api_key.audit",
        "access_token.audit",
        "session_id.audit",
        "private_key.audit",
        "x_api_key.audit",
        "runtime.api_key",
        "viewer_token.audit",
    ]
    with db.get_db() as conn:
        for index, event_type in enumerate(sensitive_event_types, start=1):
            conn.execute(
                """INSERT INTO audit_events (
                    id, event_type, actor_type, runtime_session_id, profile_id,
                    external_session_id, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"00000000-0000-4000-8000-0000000000{index:02d}",
                    event_type,
                    "runtime_service",
                    None,
                    None,
                    None,
                    json.dumps({"safe": "kept"}),
                    f"2026-06-04T00:00:0{index}+00:00",
                ),
            )
        conn.execute(
            """INSERT INTO audit_events (
                id, event_type, actor_type, runtime_session_id, profile_id,
                external_session_id, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "00000000-0000-4000-8000-000000000099",
                "runtime.test",
                "runtime_service",
                None,
                None,
                None,
                json.dumps({"safe": "kept"}),
                "2026-06-04T00:00:09+00:00",
            ),
        )
        conn.commit()

    events = db.list_audit_events()

    assert len(events) == 8
    assert [event["event_type"] for event in events[:-1]] == ["unknown"] * 7
    assert events[-1]["event_type"] == "runtime.test"
    serialized_events = json.dumps(events, sort_keys=True)
    for event_type in sensitive_event_types:
        assert event_type not in serialized_events


def test_audit_event_reader_sanitizes_historical_top_level_fields_and_metadata(tmp_db):
    leak_marker = "audit-reader-secret"
    polluted_event_id = (
        f"audit-id {leak_marker} "
        f"token={leak_marker} Authorization=Bearer {leak_marker}"
    )
    polluted_runtime_session_id = (
        f"runtime-id {leak_marker} "
        f"token={leak_marker} Authorization=Bearer {leak_marker}"
    )
    polluted_profile_id = (
        f"profile-id {leak_marker} "
        f"token={leak_marker} Authorization=Bearer {leak_marker}"
    )
    polluted_external_session_id = f"https://external.example/session?token={leak_marker}"
    polluted_created_at = f"2026-06-03T00:00:00+00:00 token={leak_marker}"
    with db.get_db() as conn:
        conn.execute(
            """INSERT INTO audit_events (
                id, event_type, actor_type, runtime_session_id, profile_id,
                external_session_id, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                polluted_event_id,
                f"runtime.test token={leak_marker}",
                f"runtime_service token={leak_marker}",
                polluted_runtime_session_id,
                polluted_profile_id,
                polluted_external_session_id,
                json.dumps(
                    {
                        "safe": "kept",
                        "viewer_token": f"viewer-{leak_marker}",
                        "message": f"token={leak_marker} Bearer {leak_marker}",
                    }
                ),
                polluted_created_at,
            ),
        )
        conn.commit()

    listed = db.list_audit_events()
    fetched = db.get_audit_event(polluted_event_id)

    assert len(listed) == 1
    for event in (listed[0], fetched):
        assert event is not None
        assert event["id"] == "unknown"
        assert event["event_type"] == "unknown"
        assert event["actor_type"] == "unknown"
        assert event["runtime_session_id"] is None
        assert event["profile_id"] is None
        assert event["external_session_id"] is None
        assert event["created_at"] == "unknown"
        assert event["metadata"] == {
            "safe": "kept",
            "message": "token=[redacted] Bearer [redacted]",
        }

    serialized_events = json.dumps({"listed": listed, "fetched": fetched}, sort_keys=True)
    assert leak_marker not in serialized_events
    assert "viewer-" not in serialized_events
    assert "external.example" not in serialized_events
    assert "runtime-id" not in serialized_events
    assert "profile-id" not in serialized_events
