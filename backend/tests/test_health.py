"""Tests for profile fingerprint health calculation and API."""

from __future__ import annotations

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
    assert "ftp" in warnings["proxy_invalid"].message


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
