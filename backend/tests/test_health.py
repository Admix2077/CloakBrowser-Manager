"""Tests for profile fingerprint health calculation and API."""

from __future__ import annotations

import json
from urllib.parse import quote
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from starlette.testclient import TestClient

from backend import database as db, geoip
from backend.geoip import GeoIPResult
from backend.health import HEALTH_WARNING_CODES, compute_profile_health


def _profile(**overrides):
    profile = {
        "id": "profile-1",
        "proxy": None,
        "timezone": None,
        "locale": None,
        "last_geoip_ip": None,
        "last_geoip_country_code": None,
        "last_geoip_timezone": None,
        "last_geoip_locale": None,
        "last_geoip_source": None,
        "last_geoip_resolved_at": None,
    }
    profile.update(overrides)
    return profile


def _runtime(**overrides):
    runtime = {
        "status": "stopped",
        "vnc_ws_port": None,
        "automation_url": None,
    }
    runtime.update(overrides)
    return runtime


def _warning_codes(result):
    return {warning.code for warning in result.warnings}


def _health_audit_events() -> list[dict]:
    return [
        event
        for event in db.list_audit_events()
        if event["event_type"] == "profile.health_checked"
    ]


def test_health_warning_code_catalog_matches_task_contract():
    assert HEALTH_WARNING_CODES == {
        "geoip_missing",
        "geoip_stale",
        "proxy_invalid",
        "geoip_lookup_failed",
        "manual_timezone_mismatch",
        "manual_locale_mismatch",
        "runtime_vnc_missing",
        "runtime_automation_missing",
        "launch_failed",
    }


def test_health_unknown_when_geoip_missing():
    result = compute_profile_health(_profile(), _runtime(), checked_at="2026-05-25T00:00:00Z")

    assert result.status == "unknown"
    assert result.geoip is None
    assert result.manual_overrides == {"timezone": False, "locale": False}
    assert "geoip_missing" in _warning_codes(result)


def test_health_invalid_proxy_returns_error():
    result = compute_profile_health(
        _profile(proxy="ftp://proxy.example:21"),
        _runtime(),
        checked_at="2026-05-25T00:00:00Z",
    )

    assert result.status == "error"
    warnings = {warning.code: warning for warning in result.warnings}
    assert warnings["proxy_invalid"].severity == "error"
    assert warnings["proxy_invalid"].message == "Invalid proxy scheme"


def test_health_invalid_proxy_warning_uses_low_sensitive_detail():
    result = compute_profile_health(
        _profile(proxy="http://user:hiddenpass@proxy.example"),
        _runtime(),
        checked_at="2026-05-25T00:00:00Z",
    )

    warning = {item.code: item for item in result.warnings}["proxy_invalid"]
    assert warning.message == "Proxy URL missing port"
    assert "hiddenpass" not in warning.message
    assert "user:" not in warning.message
    assert "proxy.example" not in warning.message
    assert "http://proxy.example" not in warning.message


def test_health_check_invalid_proxy_warning_does_not_echo_proxy_host(
    app_client: TestClient,
):
    create = app_client.post(
        "/api/profiles",
        json={
            "name": "Bad Proxy Host",
            "proxy": "http://user:hiddenpass@health-proxy.example",
        },
    )
    pid = create.json()["id"]

    with patch("backend.main.resolve_network_geo", new=AsyncMock(side_effect=AssertionError("network"))):
        resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200
    body = resp.json()
    warning = body["warnings"][0]
    assert warning["code"] == "proxy_invalid"
    assert warning["message"] == "Proxy URL missing port"
    serialized = json.dumps(body, sort_keys=True)
    for leaked in (
        "hiddenpass",
        "user:",
        "health-proxy.example",
        "http://user:hiddenpass@health-proxy.example",
        "http://health-proxy.example",
    ):
        assert leaked not in serialized


def test_health_warns_on_manual_timezone_and_locale_mismatch():
    result = compute_profile_health(
        _profile(
            timezone="America/New_York",
            locale="en-US",
            last_geoip_ip="203.0.113.20",
            last_geoip_country_code="JP",
            last_geoip_timezone="Asia/Tokyo",
            last_geoip_locale="ja-JP",
            last_geoip_source="ipwho.is",
            last_geoip_resolved_at="2026-05-25T00:00:00Z",
        ),
        _runtime(),
        checked_at="2026-05-25T00:05:00Z",
    )

    assert result.status == "warning"
    assert result.manual_overrides == {"timezone": True, "locale": True}
    assert {"manual_timezone_mismatch", "manual_locale_mismatch"} <= _warning_codes(result)
    assert result.geoip is not None
    assert result.geoip.timezone == "Asia/Tokyo"
    assert result.geoip.locale == "ja-JP"


def test_health_manual_mismatch_warning_does_not_echo_manual_values():
    sensitive_timezone = "https://timezone.example/?token=super-secret Authorization=Bearer super-secret"
    sensitive_locale = "Bearer super-secret"
    result = compute_profile_health(
        _profile(
            timezone=sensitive_timezone,
            locale=sensitive_locale,
            last_geoip_ip="203.0.113.20",
            last_geoip_country_code="JP",
            last_geoip_timezone="Asia/Tokyo",
            last_geoip_locale="ja-JP",
            last_geoip_source="ipwho.is",
            last_geoip_resolved_at="2026-05-25T00:00:00Z",
        ),
        _runtime(),
        checked_at="2026-05-25T00:05:00Z",
    )

    warnings = {warning.code: warning for warning in result.warnings}
    assert warnings["manual_timezone_mismatch"].message == "手动 timezone 与当前出口建议不一致。"
    assert warnings["manual_locale_mismatch"].message == "手动 locale 与当前出口建议不一致。"
    serialized = result.model_dump_json()
    for leaked in (
        sensitive_timezone,
        sensitive_locale,
        "timezone.example",
        "super-secret",
        "Authorization",
        "Bearer",
    ):
        assert leaked not in serialized


def test_health_warns_when_running_runtime_urls_are_missing():
    result = compute_profile_health(
        _profile(
            last_geoip_ip="23.144.4.92",
            last_geoip_country_code="US",
            last_geoip_timezone="America/Los_Angeles",
            last_geoip_locale="en-US",
            last_geoip_source="ip-api",
            last_geoip_resolved_at="2026-05-25T00:00:00Z",
        ),
        _runtime(status="running", vnc_ws_port=None, automation_url=None),
        checked_at="2026-05-25T00:05:00Z",
    )

    assert result.status == "warning"
    assert {"runtime_vnc_missing", "runtime_automation_missing"} <= _warning_codes(result)


def test_get_profile_health_does_not_perform_network_lookup(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Health GET"})
    pid = create.json()["id"]

    with patch("backend.main.resolve_network_geo", new=AsyncMock(side_effect=AssertionError("network"))):
        resp = app_client.get(f"/api/profiles/{pid}/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "unknown"
    assert resp.json()["warnings"][0]["code"] == "geoip_missing"


def test_health_check_success_persists_geoip_without_overwriting_manual_fields(
    app_client: TestClient,
):
    create = app_client.post(
        "/api/profiles",
        json={
            "name": "Health POST",
            "timezone": "America/New_York",
            "locale": "en-US",
        },
    )
    pid = create.json()["id"]

    with patch(
        "backend.main.resolve_network_geo",
        new=AsyncMock(
            return_value=GeoIPResult(
                timezone="Asia/Tokyo",
                locale="ja-JP",
                ip="203.0.113.20",
                country_code="JP",
                source="ipwho.is",
            )
        ),
    ) as resolve:
        resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200
    assert resp.json()["status"] == "warning"
    assert {"manual_timezone_mismatch", "manual_locale_mismatch"} <= {
        item["code"] for item in resp.json()["warnings"]
    }
    resolve.assert_awaited_once_with(None)

    profile = db.get_profile(pid)
    assert profile is not None
    assert profile["timezone"] == "America/New_York"
    assert profile["locale"] == "en-US"
    assert profile["last_geoip_ip"] == "203.0.113.20"
    assert profile["last_geoip_country_code"] == "JP"
    assert profile["last_geoip_timezone"] == "Asia/Tokyo"
    assert profile["last_geoip_locale"] == "ja-JP"
    assert profile["last_geoip_source"] == "ipwho.is"


def test_health_check_redacts_sensitive_geoip_source(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Health Sensitive Source"})
    pid = create.json()["id"]
    sensitive_source = (
        "https://geo.example/check?token=super-secret "
        "Authorization=Bearer super-secret"
    )

    with patch(
        "backend.main.resolve_network_geo",
        new=AsyncMock(
            return_value=GeoIPResult(
                timezone="Asia/Tokyo",
                locale="ja-JP",
                ip="203.0.113.20",
                country_code="JP",
                source=sensitive_source,
            )
        ),
    ):
        resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200
    body = resp.json()
    assert body["geoip"]["source"] == "unknown"
    for leaked in ("geo.example", "super-secret", "Authorization", "Bearer", sensitive_source):
        assert leaked not in json.dumps(body, sort_keys=True)

    profile = db.get_profile(pid)
    assert profile is not None
    assert profile["last_geoip_source"] == "unknown"
    for leaked in ("geo.example", "super-secret", "Authorization", "Bearer", sensitive_source):
        assert leaked not in json.dumps(dict(profile), sort_keys=True)

    events = _health_audit_events()
    assert len(events) == 1
    assert events[0]["metadata"]["geoip_source"] == "unknown"
    for leaked in ("geo.example", "super-secret", "Authorization", "Bearer", sensitive_source):
        assert leaked not in json.dumps(events[0], sort_keys=True)


def test_health_check_redacts_sensitive_geoip_success_fields(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Health Sensitive Geo Fields"})
    pid = create.json()["id"]
    sensitive_ip = "https://ip.example/check?token=health-geoip-secret"
    sensitive_timezone = "https://timezone.example/check?token=health-geoip-secret"
    sensitive_locale = "Authorization=Bearer health-geoip-secret"
    sensitive_country = "JP?token=health-geoip-secret"

    with patch(
        "backend.main.resolve_network_geo",
        new=AsyncMock(
            return_value=GeoIPResult(
                timezone=sensitive_timezone,
                locale=sensitive_locale,
                ip=sensitive_ip,
                country_code=sensitive_country,
                source="qa",
            )
        ),
    ):
        resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200
    body = resp.json()
    assert body["geoip"]["ip"] is None
    assert body["geoip"]["country_code"] is None
    assert body["geoip"]["timezone"] is None
    assert body["geoip"]["locale"] is None
    assert body["geoip"]["source"] == "qa"
    for leaked in (
        "timezone.example",
        "health-geoip-secret",
        "Authorization",
        "Bearer",
        "ip.example",
        sensitive_ip,
        sensitive_timezone,
        sensitive_locale,
        sensitive_country,
    ):
        assert leaked not in json.dumps(body, sort_keys=True)

    profile = db.get_profile(pid)
    assert profile is not None
    assert profile["last_geoip_ip"] is None
    assert profile["last_geoip_country_code"] is None
    assert profile["last_geoip_timezone"] is None
    assert profile["last_geoip_locale"] is None
    assert profile["last_geoip_source"] == "qa"
    for leaked in (
        "timezone.example",
        "health-geoip-secret",
        "Authorization",
        "Bearer",
        "ip.example",
        sensitive_ip,
        sensitive_timezone,
        sensitive_locale,
        sensitive_country,
    ):
        assert leaked not in json.dumps(dict(profile), sort_keys=True)

    events = _health_audit_events()
    assert len(events) == 1
    assert events[0]["metadata"].get("geoip_source") == "qa"
    assert "geoip_country_code" not in events[0]["metadata"]
    for leaked in (
        "timezone.example",
        "health-geoip-secret",
        "Authorization",
        "Bearer",
        "ip.example",
        sensitive_ip,
        sensitive_timezone,
        sensitive_locale,
        sensitive_country,
    ):
        assert leaked not in json.dumps(events[0], sort_keys=True)


def test_health_get_redacts_persisted_sensitive_geoip_source(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Health Existing Source"})
    pid = create.json()["id"]
    sensitive_source = (
        "https://geo.example/check?token=super-secret "
        "Authorization=Bearer super-secret"
    )
    db.update_profile_geoip_result(
        pid,
        {
            "ip": "203.0.113.20",
            "country_code": "JP",
            "timezone": "Asia/Tokyo",
            "locale": "ja-JP",
            "source": sensitive_source,
        },
    )

    resp = app_client.get(f"/api/profiles/{pid}/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["geoip"]["source"] == "unknown"
    for leaked in ("geo.example", "super-secret", "Authorization", "Bearer", sensitive_source):
        assert leaked not in json.dumps(body, sort_keys=True)


def test_health_get_redacts_persisted_sensitive_geoip_fields(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Health Existing Geo Fields"})
    pid = create.json()["id"]
    sensitive_ip = "https://ip.example/check?token=stored-geoip-secret"
    sensitive_timezone = "https://timezone.example/check?token=stored-geoip-secret"
    sensitive_locale = "Authorization=Bearer stored-geoip-secret"
    sensitive_country = "JP?token=stored-geoip-secret"
    db.update_profile_geoip_result(
        pid,
        {
            "ip": sensitive_ip,
            "country_code": sensitive_country,
            "timezone": sensitive_timezone,
            "locale": sensitive_locale,
            "source": "qa",
        },
    )

    resp = app_client.get(f"/api/profiles/{pid}/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["geoip"]["ip"] is None
    assert body["geoip"]["country_code"] is None
    assert body["geoip"]["timezone"] is None
    assert body["geoip"]["locale"] is None
    assert body["geoip"]["source"] == "qa"
    for leaked in (
        "timezone.example",
        "stored-geoip-secret",
        "Authorization",
        "Bearer",
        "ip.example",
        sensitive_ip,
        sensitive_timezone,
        sensitive_locale,
        sensitive_country,
    ):
        assert leaked not in json.dumps(body, sort_keys=True)


def test_health_check_success_writes_redacted_audit_event(app_client: TestClient):
    create = app_client.post(
        "/api/profiles",
        json={
            "name": "Health Audit Success",
            "proxy": "http://audit-user:secret-proxy-password@audit-proxy.example:8080",
            "timezone": "America/New_York",
            "locale": "en-US",
        },
    )
    pid = create.json()["id"]

    with patch(
        "backend.main.resolve_network_geo",
        new=AsyncMock(
            return_value=GeoIPResult(
                timezone="Asia/Tokyo",
                locale="ja-JP",
                ip="203.0.113.20",
                country_code="JP",
                source="ipwho.is",
            )
        ),
    ):
        resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200

    events = _health_audit_events()
    assert len(events) == 1
    event = events[0]
    assert event["actor_type"] == "local_admin"
    assert event["profile_id"] == pid
    assert event["runtime_session_id"] is None
    assert event["metadata"] == {
        "status": "warning",
        "warning_codes": ["manual_timezone_mismatch", "manual_locale_mismatch"],
        "warning_count": 2,
        "lookup_attempted": True,
        "lookup_result": "success",
        "geoip_source": "ipwho.is",
        "geoip_country_code": "JP",
        "manual_timezone_override": True,
        "manual_locale_override": True,
        "runtime_status": "stopped",
    }

    serialized_event = json.dumps(event, sort_keys=True)
    assert "secret-proxy-password" not in serialized_event
    assert "audit-user" not in serialized_event
    assert "audit-proxy.example" not in serialized_event
    assert "203.0.113.20" not in serialized_event
    assert "America/New_York" not in serialized_event
    assert "Asia/Tokyo" not in serialized_event
    assert "en-US" not in serialized_event
    assert "ja-JP" not in serialized_event
    assert "token" not in serialized_event.lower()
    assert "automation_url" not in serialized_event
    assert "vnc_ws_port" not in serialized_event


def test_health_check_fallback_success_persists_last_geoip(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    create = app_client.post("/api/profiles", json={"name": "Health Fallback"})
    pid = create.json()["id"]
    hosts: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host or "")
        if request.url.host == "ip-api.com":
            return httpx.Response(200, json={"status": "fail", "message": "rate limited"})
        return httpx.Response(
            200,
            json={
                "ip": "198.51.100.25",
                "country_code": "DE",
                "timezone": "Europe/Berlin",
                "languages": "de-DE,en",
            },
        )

    monkeypatch.setattr(geoip, "_transport_for_tests", httpx.MockTransport(handler))
    geoip.clear_geoip_cache()

    resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200
    assert resp.json()["status"] == "good"
    assert hosts[:2] == ["ip-api.com", "ipapi.co"]
    profile = db.get_profile(pid)
    assert profile is not None
    assert profile["last_geoip_ip"] == "198.51.100.25"
    assert profile["last_geoip_country_code"] == "DE"
    assert profile["last_geoip_timezone"] == "Europe/Berlin"
    assert profile["last_geoip_locale"] == "de-DE"
    assert profile["last_geoip_source"] == "ipapi.co"


def test_health_check_normalizes_proxy_for_geoip_lookup(app_client: TestClient):
    create = app_client.post(
        "/api/profiles",
        json={"name": "Health Proxy", "proxy": "proxy.example:8080"},
    )
    pid = create.json()["id"]

    with patch(
        "backend.main.resolve_network_geo",
        new=AsyncMock(
            return_value=GeoIPResult(
                timezone="Europe/Berlin",
                locale="de-DE",
                ip="198.51.100.25",
                country_code="DE",
                source="ipapi.co",
            )
        ),
    ) as resolve:
        resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200
    assert resp.json()["status"] == "good"
    resolve.assert_awaited_once_with("http://proxy.example:8080")


def test_health_check_invalid_proxy_returns_health_error_without_lookup(app_client: TestClient):
    create = app_client.post(
        "/api/profiles",
        json={"name": "Bad Proxy", "proxy": "ftp://proxy.example:21"},
    )
    pid = create.json()["id"]

    with patch("backend.main.resolve_network_geo", new=AsyncMock(side_effect=AssertionError("network"))):
        resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200
    assert resp.json()["status"] == "error"
    assert resp.json()["warnings"][0]["code"] == "proxy_invalid"


def test_health_check_invalid_proxy_writes_redacted_audit_without_lookup(app_client: TestClient):
    create = app_client.post(
        "/api/profiles",
        json={"name": "Bad Proxy Audit", "proxy": "ftp://proxy-secret.example:21"},
    )
    pid = create.json()["id"]

    with patch("backend.main.resolve_network_geo", new=AsyncMock(side_effect=AssertionError("network"))):
        resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200

    events = _health_audit_events()
    assert len(events) == 1
    assert events[0]["metadata"] == {
        "status": "error",
        "warning_codes": ["proxy_invalid", "geoip_missing"],
        "warning_count": 2,
        "lookup_attempted": False,
        "lookup_result": "skipped_invalid_proxy",
        "manual_timezone_override": False,
        "manual_locale_override": False,
        "runtime_status": "stopped",
    }
    serialized_event = json.dumps(events[0], sort_keys=True)
    assert "proxy-secret.example" not in serialized_event
    assert "ftp://proxy-secret.example:21" not in serialized_event


def test_health_check_lookup_failure_keeps_existing_last_geoip(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Health Failure Keeps Cache"})
    pid = create.json()["id"]
    db.update_profile_geoip_result(
        pid,
        {
            "ip": "23.144.4.92",
            "country_code": "US",
            "timezone": "America/Los_Angeles",
            "locale": "en-US",
            "source": "ip-api",
        },
    )

    with patch(
        "backend.main.resolve_network_geo",
        new=AsyncMock(side_effect=RuntimeError("provider unavailable")),
    ):
        resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200
    assert resp.json()["status"] == "warning"
    assert "geoip_lookup_failed" in {item["code"] for item in resp.json()["warnings"]}
    profile = db.get_profile(pid)
    assert profile is not None
    assert profile["last_geoip_ip"] == "23.144.4.92"
    assert profile["last_geoip_country_code"] == "US"
    assert profile["last_geoip_timezone"] == "America/Los_Angeles"
    assert profile["last_geoip_locale"] == "en-US"
    assert profile["last_geoip_source"] == "ip-api"


def test_health_check_lookup_failure_writes_redacted_audit_event(app_client: TestClient):
    create = app_client.post(
        "/api/profiles",
        json={
            "name": "Health Audit Failure",
            "proxy": "http://audit-user:secret-proxy-password@audit-failure.example:8080",
        },
    )
    pid = create.json()["id"]

    with patch(
        "backend.main.resolve_network_geo",
        new=AsyncMock(side_effect=RuntimeError("provider unavailable secret-token")),
    ):
        resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200

    events = _health_audit_events()
    assert len(events) == 1
    assert events[0]["metadata"] == {
        "status": "error",
        "warning_codes": ["geoip_lookup_failed", "geoip_missing"],
        "warning_count": 2,
        "lookup_attempted": True,
        "lookup_result": "failed",
        "manual_timezone_override": False,
        "manual_locale_override": False,
        "runtime_status": "stopped",
    }
    serialized_event = json.dumps(events[0], sort_keys=True)
    assert "secret-proxy-password" not in serialized_event
    assert "audit-failure.example" not in serialized_event
    assert "provider unavailable" not in serialized_event
    assert "secret-token" not in serialized_event


def test_health_check_lookup_failure_logs_error_type_without_raw_exception(
    app_client: TestClient,
    caplog: pytest.LogCaptureFixture,
):
    create = app_client.post(
        "/api/profiles",
        json={
            "name": "Health Log Failure",
            "proxy": "http://audit-user:secret-proxy-password@health-log.example:8080",
        },
    )
    pid = create.json()["id"]
    caplog.set_level("WARNING", logger="invisible_browser.manager")

    with patch(
        "backend.main.resolve_network_geo",
        new=AsyncMock(
            side_effect=RuntimeError(
                "provider-token-super-secret via http://health-log.example:8080/path",
            ),
        ),
    ):
        resp = app_client.post(f"/api/profiles/{pid}/health/check")

    assert resp.status_code == 200
    assert (
        f"action=profile.health_geoip_lookup_failed profile_id={pid} "
        "error_type=RuntimeError"
    ) in caplog.text
    assert "provider-token-super-secret" not in caplog.text
    assert "secret-proxy-password" not in caplog.text
    assert "health-log.example" not in caplog.text


def test_health_check_audit_and_logs_sanitize_persisted_profile_id(
    app_client: TestClient,
    caplog: pytest.LogCaptureFixture,
):
    leak_marker = "health-audit-profile-id-secret"
    create = app_client.post(
        "/api/profiles",
        json={"name": "Health polluted profile id"},
    )
    original_id = create.json()["id"]
    polluted_profile_id = (
        f"health-profile {leak_marker} "
        f"token={leak_marker} Authorization=Bearer {leak_marker}"
    )
    with db.get_db() as conn:
        conn.execute("UPDATE profiles SET id = ? WHERE id = ?", (polluted_profile_id, original_id))
        conn.commit()
    caplog.set_level("WARNING", logger="invisible_browser.manager")

    with patch(
        "backend.main.resolve_network_geo",
        new=AsyncMock(side_effect=RuntimeError(f"provider failed {leak_marker}")),
    ):
        resp = app_client.post(
            f"/api/profiles/{quote(polluted_profile_id, safe='')}/health/check"
        )

    assert resp.status_code == 200
    events = _health_audit_events()
    assert len(events) == 1
    assert events[0]["profile_id"] is None
    assert "action=profile.health_geoip_lookup_failed profile_id=unknown" in caplog.text

    serialized = json.dumps({"event": events[0], "logs": caplog.text}, sort_keys=True)
    for leaked in (
        leak_marker,
        "Authorization",
        "Bearer",
        "token=",
    ):
        assert leaked not in serialized


def test_get_profile_health_does_not_write_audit(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Health GET Audit"})
    pid = create.json()["id"]

    resp = app_client.get(f"/api/profiles/{pid}/health")

    assert resp.status_code == 200
    assert _health_audit_events() == []


def test_health_check_missing_profile_does_not_write_audit(app_client: TestClient):
    resp = app_client.post("/api/profiles/missing-health-profile/health/check")

    assert resp.status_code == 404
    assert _health_audit_events() == []
