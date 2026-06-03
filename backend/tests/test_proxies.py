"""Tests for proxy asset storage and CRUD API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from backend import database as db, main
from backend.geoip import GeoIPResult


def _proxy_bulk_audit_events() -> list[dict]:
    return [
        event
        for event in db.list_audit_events()
        if event["event_type"] in {"proxy.bulk_checked", "proxy.assigned", "proxy.random_assigned"}
    ]


def test_init_db_creates_proxies_table(tmp_db: Path):
    with db.get_db() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {row["name"] for row in tables}
    assert "proxies" in names


def test_create_list_update_and_delete_proxy_asset(tmp_db: Path):
    proxy = db.create_proxy(
        name="US residential",
        url="http://user:hiddenpass@proxy.example:8080",
        country_code="US",
        city="New York",
        asn="AS64500",
        provider="ProxyCo",
        tags=[{"tag": "warmup", "color": "#2563eb"}],
        notes="Primary pool",
    )

    assert proxy["name"] == "US residential"
    assert proxy["url"] == "http://user:hiddenpass@proxy.example:8080"
    assert proxy["country_code"] == "US"
    assert proxy["city"] == "New York"
    assert proxy["asn"] == "AS64500"
    assert proxy["provider"] == "ProxyCo"
    assert proxy["tags"] == [{"tag": "warmup", "color": "#2563eb"}]
    assert proxy["notes"] == "Primary pool"
    assert proxy["last_check_status"] is None
    assert proxy["created_at"] is not None
    assert proxy["updated_at"] is not None

    listed = db.list_proxies()
    assert [item["id"] for item in listed] == [proxy["id"]]

    updated = db.update_proxy(
        proxy["id"],
        name="US residential updated",
        provider="BetterProxy",
        tags=[{"tag": "client-a", "color": None}],
    )
    assert updated is not None
    assert updated["name"] == "US residential updated"
    assert updated["provider"] == "BetterProxy"
    assert updated["url"] == "http://user:hiddenpass@proxy.example:8080"
    assert updated["tags"] == [{"tag": "client-a", "color": None}]

    assert db.delete_proxy(proxy["id"]) is True
    assert db.get_proxy(proxy["id"]) is None
    assert db.delete_proxy(proxy["id"]) is False


def test_delete_proxy_asset_does_not_delete_profiles(tmp_db: Path):
    proxy = db.create_proxy(name="Keep profiles", url="http://proxy.example:8080")
    profile = db.create_profile(name="Profile using same proxy text", proxy=proxy["url"])

    assert db.delete_proxy(proxy["id"]) is True

    remaining_profile = db.get_profile(profile["id"])
    assert remaining_profile is not None
    assert remaining_profile["proxy"] == "http://proxy.example:8080"


def test_create_proxy_normalizes_and_rejects_invalid_urls(tmp_db: Path):
    proxy = db.create_proxy(name="Host port", url="proxy.example:8080")
    assert proxy["url"] == "http://proxy.example:8080"

    with pytest.raises(ValueError, match="Invalid proxy scheme"):
        db.create_proxy(name="Invalid", url="ftp://user:hiddenpass@proxy.example:21")

    assert [item["name"] for item in db.list_proxies()] == ["Host port"]


def test_proxy_crud_api(app_client: TestClient):
    create = app_client.post(
        "/api/proxies",
        json={
            "name": "Japan mobile",
            "url": "socks5://user:hiddenpass@jp.proxy.example:1080",
            "country_code": "JP",
            "city": "Tokyo",
            "asn": "AS64501",
            "provider": "MobileProxy",
            "tags": [{"tag": "jp", "color": "#0ea5e9"}],
            "notes": "Tokyo exit",
        },
    )
    assert create.status_code == 201
    data = create.json()
    assert data["id"]
    assert data["name"] == "Japan mobile"
    assert data["url"] == "socks5://jp.proxy.example:1080"
    assert "hiddenpass" not in str(data)
    assert data["last_check_status"] is None

    listed = app_client.get("/api/proxies")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [data["id"]]
    assert "hiddenpass" not in str(listed.json())

    get = app_client.get(f"/api/proxies/{data['id']}")
    assert get.status_code == 200
    assert get.json()["provider"] == "MobileProxy"
    assert get.json()["url"] == "socks5://jp.proxy.example:1080"
    assert "hiddenpass" not in str(get.json())

    update = app_client.put(
        f"/api/proxies/{data['id']}",
        json={
            "name": "Japan mobile updated",
            "tags": [{"tag": "priority", "color": None}],
        },
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Japan mobile updated"
    assert update.json()["url"] == "socks5://jp.proxy.example:1080"
    assert update.json()["tags"] == [{"tag": "priority", "color": None}]

    delete = app_client.request(
        "DELETE",
        f"/api/proxies/{data['id']}",
        json={"confirm_delete": True},
    )
    assert delete.status_code == 200
    assert delete.json() == {"ok": True}
    assert app_client.get(f"/api/proxies/{data['id']}").status_code == 404


def test_proxy_response_sanitizes_persisted_malformed_tags(app_client: TestClient):
    proxy = app_client.post(
        "/api/proxies",
        json={
            "name": "Malformed proxy tags",
            "url": "http://proxy.example:8080",
            "tags": [{"tag": "valid", "color": "#0ea5e9"}],
        },
    ).json()
    db.update_proxy(
        proxy["id"],
        tags=[
            {"color": "#ef4444"},
            {"tag": 123, "color": "#22c55e"},
            {"tag": "kept", "color": 123},
            {"tag": "colored", "color": "#0ea5e9"},
        ],
    )

    get = app_client.get(f"/api/proxies/{proxy['id']}")
    listed = app_client.get("/api/proxies")

    assert get.status_code == 200
    assert get.json()["tags"] == [
        {"tag": "kept", "color": None},
        {"tag": "colored", "color": "#0ea5e9"},
    ]
    assert listed.status_code == 200
    assert listed.json()[0]["tags"] == get.json()["tags"]


def test_proxy_api_responses_redact_persisted_sensitive_last_check_fields(app_client: TestClient):
    create = app_client.post(
        "/api/proxies",
        json={
            "name": "Historical check fields",
            "url": "http://user:hiddenpass@historical-check.example:8080",
        },
    )
    assert create.status_code == 201
    proxy_id = create.json()["id"]
    leak_marker = "manual-proxy-leak-marker"

    updated = db.update_proxy(
        proxy_id,
        last_check_status=f"good {leak_marker}",
        last_check_ip=f"https://ip.invalid/{leak_marker}",
        last_check_country_code=f"JP-{leak_marker}",
        last_check_timezone=f"Asia/Tokyo/{leak_marker}",
        last_check_locale=f"ja-JP-{leak_marker}",
        last_check_source=f"https://geo.invalid/{leak_marker}",
        last_check_error=f"provider failure https://geo.invalid/{leak_marker} Bearer {leak_marker}",
        last_check_at="2026-06-03T00:00:00Z",
    )
    assert updated is not None

    detail = app_client.get(f"/api/proxies/{proxy_id}")
    listed = app_client.get("/api/proxies")

    assert detail.status_code == 200
    assert listed.status_code == 200
    detail_data = detail.json()
    list_data = listed.json()[0]
    for data in (detail_data, list_data):
        assert data["last_check_status"] == "unknown"
        assert data["last_check_ip"] is None
        assert data["last_check_country_code"] is None
        assert data["last_check_timezone"] is None
        assert data["last_check_locale"] is None
        assert data["last_check_source"] == "unknown"
        assert data["last_check_error"] == "Proxy check failed"
        for leaked in (leak_marker, "geo.invalid", "ip.invalid", "Bearer"):
            assert leaked not in json.dumps(data, sort_keys=True)


def test_proxy_api_responses_redact_persisted_sensitive_selection_fields(app_client: TestClient):
    create = app_client.post(
        "/api/proxies",
        json={
            "name": "Historical selection fields",
            "url": "http://user:hiddenpass@selection-fields.example:8080",
            "provider": "ProxyCo",
            "country_code": "JP",
        },
    )
    assert create.status_code == 201
    proxy_id = create.json()["id"]
    leak_marker = "proxy-selection-secret"

    updated = db.update_proxy(
        proxy_id,
        provider=f"Authorization=Bearer {leak_marker}",
        country_code=f"JP?token={leak_marker}",
    )
    assert updated is not None

    detail = app_client.get(f"/api/proxies/{proxy_id}")
    listed = app_client.get("/api/proxies")

    assert detail.status_code == 200
    assert listed.status_code == 200
    for data in (detail.json(), listed.json()[0]):
        assert data["provider"] is None
        assert data["country_code"] is None
        serialized = json.dumps(data, sort_keys=True)
        for leaked in (leak_marker, "Authorization", "Bearer", "token="):
            assert leaked not in serialized


def test_delete_proxy_requires_explicit_confirmation_without_side_effects(
    app_client: TestClient,
):
    create = app_client.post(
        "/api/proxies",
        json={
            "name": "Confirm delete proxy",
            "url": "http://user:hiddenpass@confirm-delete.example:8080",
        },
    )
    assert create.status_code == 201
    proxy_id = create.json()["id"]

    for payload in ({}, {"confirm_delete": False}, {"confirm_delete": "true"}):
        resp = app_client.request("DELETE", f"/api/proxies/{proxy_id}", json=payload)
        assert resp.status_code == 422
        assert resp.json() == {"detail": "Proxy delete requires explicit confirmation"}

    assert app_client.get(f"/api/proxies/{proxy_id}").status_code == 200
    assert [event["event_type"] for event in db.list_audit_events()] == ["proxy.created"]


def test_proxy_crud_api_writes_redacted_audit_events(app_client: TestClient):
    create = app_client.post(
        "/api/proxies",
        json={
            "name": "Audited proxy",
            "url": "http://user:hiddenpass@audit-proxy.example:8080",
            "country_code": "US",
            "provider": "AuditPool",
            "tags": [{"tag": "ops", "color": None}],
        },
    )
    assert create.status_code == 201
    proxy_id = create.json()["id"]

    update = app_client.put(
        f"/api/proxies/{proxy_id}",
        json={
            "name": "Audited proxy updated",
            "url": "http://user:newhiddenpass@audit-proxy.example:8080",
            "tags": [{"tag": "priority", "color": "#2563eb"}],
        },
    )
    assert update.status_code == 200

    delete = app_client.request(
        "DELETE",
        f"/api/proxies/{proxy_id}",
        json={"confirm_delete": True},
    )
    assert delete.status_code == 200

    events = db.list_audit_events()
    assert [event["event_type"] for event in events] == [
        "proxy.created",
        "proxy.updated",
        "proxy.deleted",
    ]
    assert all(event["actor_type"] == "local_admin" for event in events)
    assert [event["metadata"]["proxy_id"] for event in events] == [proxy_id, proxy_id, proxy_id]
    assert events[0]["metadata"] == {
        "proxy_id": proxy_id,
        "name": "Audited proxy",
        "provider": "AuditPool",
        "country_code": "US",
        "tag_count": 1,
    }
    assert events[1]["metadata"] == {
        "proxy_id": proxy_id,
        "updated_fields": ["name", "tags", "url"],
        "tag_count": 1,
    }
    assert events[2]["metadata"] == {
        "proxy_id": proxy_id,
        "name": "Audited proxy updated",
        "provider": "AuditPool",
        "country_code": "US",
        "tag_count": 1,
    }

    serialized_events = str(events)
    assert "hiddenpass" not in serialized_events
    assert "newhiddenpass" not in serialized_events
    assert "user:" not in serialized_events
    assert "audit-proxy.example" not in serialized_events


def test_proxy_crud_audit_omits_sensitive_name_metadata(app_client: TestClient):
    leak_marker = "proxy-audit-name-secret"
    create = app_client.post(
        "/api/proxies",
        json={
            "name": (
                f"Proxy https://proxy-audit-name.example/path?token={leak_marker} "
                f"Authorization=Bearer {leak_marker}"
            ),
            "url": "http://user:hiddenpass@audit-name-proxy.example:8080",
        },
    )
    assert create.status_code == 201
    proxy_id = create.json()["id"]

    delete = app_client.request(
        "DELETE",
        f"/api/proxies/{proxy_id}",
        json={"confirm_delete": True},
    )
    assert delete.status_code == 200

    events = db.list_audit_events()
    assert [event["event_type"] for event in events] == ["proxy.created", "proxy.deleted"]
    assert "name" not in events[0]["metadata"]
    assert "name" not in events[1]["metadata"]
    serialized_events = json.dumps(events, sort_keys=True)
    for leaked in (
        leak_marker,
        "proxy-audit-name.example",
        "audit-name-proxy.example",
        "Authorization",
        "Bearer",
        "token=",
        "hiddenpass",
    ):
        assert leaked not in serialized_events


def test_proxy_api_rejects_invalid_url_without_leaking_credentials(app_client: TestClient):
    resp = app_client.post(
        "/api/proxies",
        json={
            "name": "Invalid secret",
            "url": "ftp://user:hiddenpass@proxy.example:21",
        },
    )

    assert resp.status_code == 400
    body = resp.json()
    assert "Invalid proxy scheme" in body["detail"]
    assert "hiddenpass" not in str(body)
    assert app_client.get("/api/proxies").json() == []


def test_create_proxy_api_redacts_sensitive_storage_error_detail(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    def fail_create_proxy(**_fields):
        raise ValueError(
            "Proxy insert rejected http://user:hiddenpass@create-error.example:8080 "
            "token=super-secret"
        )

    monkeypatch.setattr(main.db, "create_proxy", fail_create_proxy)

    resp = app_client.post(
        "/api/proxies",
        json={
            "name": "Sensitive create failure",
            "url": "http://user:hiddenpass@create-error.example:8080",
        },
    )

    assert resp.status_code == 400
    body = resp.json()
    assert body == {"detail": "Invalid proxy URL"}
    serialized = str(body)
    assert "hiddenpass" not in serialized
    assert "super-secret" not in serialized
    assert "create-error.example" not in serialized
    assert "user:" not in serialized


def test_update_proxy_api_redacts_sensitive_storage_error_detail(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    proxy = db.create_proxy(name="Existing proxy", url="http://proxy.example:8080")

    def fail_update_proxy(*_args, **_fields):
        raise ValueError(
            "Proxy update rejected http://user:hiddenpass@update-error.example:8080 "
            "token=super-secret"
        )

    monkeypatch.setattr(main.db, "update_proxy", fail_update_proxy)

    resp = app_client.put(
        f"/api/proxies/{proxy['id']}",
        json={
            "url": "http://user:hiddenpass@update-error.example:8080",
        },
    )

    assert resp.status_code == 400
    body = resp.json()
    assert body == {"detail": "Invalid proxy URL"}
    serialized = str(body)
    assert "hiddenpass" not in serialized
    assert "super-secret" not in serialized
    assert "update-error.example" not in serialized
    assert "user:" not in serialized


def test_proxy_api_not_found(app_client: TestClient):
    assert app_client.get("/api/proxies/missing").status_code == 404
    assert app_client.put("/api/proxies/missing", json={"name": "x"}).status_code == 404
    assert app_client.request(
        "DELETE",
        "/api/proxies/missing",
        json={"confirm_delete": True},
    ).status_code == 404
    assert app_client.post("/api/proxies/missing/check").status_code == 404


def test_proxy_check_updates_last_check_fields(app_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    captured_proxy_urls: list[str | None] = []

    async def fake_resolve(proxy_url: str | None):
        captured_proxy_urls.append(proxy_url)
        return GeoIPResult(
            timezone="Asia/Tokyo",
            locale="ja-JP",
            ip="203.0.113.8",
            country_code="JP",
            source="qa",
        )

    monkeypatch.setattr(main, "resolve_network_geo", fake_resolve)
    create = app_client.post(
        "/api/proxies",
        json={
            "name": "Check me",
            "url": "socks5://user:hiddenpass@jp.proxy.example:1080",
        },
    )
    proxy_id = create.json()["id"]

    resp = app_client.post(f"/api/proxies/{proxy_id}/check")

    assert resp.status_code == 200
    data = resp.json()
    assert captured_proxy_urls == ["socks5://user:hiddenpass@jp.proxy.example:1080"]
    assert data["url"] == "socks5://jp.proxy.example:1080"
    assert data["last_check_status"] == "good"
    assert data["last_check_ip"] == "203.0.113.8"
    assert data["last_check_country_code"] == "JP"
    assert data["last_check_timezone"] == "Asia/Tokyo"
    assert data["last_check_locale"] == "ja-JP"
    assert data["last_check_source"] == "qa"
    assert data["last_check_error"] is None
    assert data["last_check_at"] is not None
    assert "hiddenpass" not in str(data)


def test_proxy_check_redacts_sensitive_success_source(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    sensitive_source = (
        "https://geo.example/check?token=super-secret "
        "Authorization=Bearer super-secret"
    )

    async def fake_resolve(proxy_url: str | None):
        return GeoIPResult(
            timezone="Asia/Tokyo",
            locale="ja-JP",
            ip="203.0.113.8",
            country_code="JP",
            source=sensitive_source,
        )

    monkeypatch.setattr(main, "resolve_network_geo", fake_resolve)
    create = app_client.post(
        "/api/proxies",
        json={
            "name": "Sensitive source",
            "url": "socks5://user:hiddenpass@source.proxy.example:1080",
        },
    )
    proxy_id = create.json()["id"]

    resp = app_client.post(f"/api/proxies/{proxy_id}/check")

    assert resp.status_code == 200
    data = resp.json()
    assert data["last_check_status"] == "good"
    assert data["last_check_source"] == "unknown"
    for leaked in ("geo.example", "super-secret", "Authorization", "Bearer", sensitive_source):
        assert leaked not in json.dumps(data, sort_keys=True)

    stored = db.get_proxy(proxy_id)
    assert stored is not None
    assert stored["last_check_status"] == "good"
    assert stored["last_check_source"] == "unknown"
    for leaked in ("geo.example", "super-secret", "Authorization", "Bearer", sensitive_source):
        assert leaked not in json.dumps(stored, sort_keys=True)


def test_proxy_check_redacts_sensitive_success_geoip_fields(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    sensitive_ip = "https://ip.example/check?token=proxy-geoip-secret"
    sensitive_timezone = "https://timezone.example/check?token=proxy-geoip-secret"
    sensitive_locale = "Authorization=Bearer proxy-geoip-secret"
    sensitive_country = "JP?token=proxy-geoip-secret"

    async def fake_resolve(proxy_url: str | None):
        return GeoIPResult(
            timezone=sensitive_timezone,
            locale=sensitive_locale,
            ip=sensitive_ip,
            country_code=sensitive_country,
            source="qa",
        )

    monkeypatch.setattr(main, "resolve_network_geo", fake_resolve)
    create = app_client.post(
        "/api/proxies",
        json={
            "name": "Sensitive geo fields",
            "url": "socks5://user:hiddenpass@geo-fields.proxy.example:1080",
        },
    )
    proxy_id = create.json()["id"]

    resp = app_client.post(f"/api/proxies/{proxy_id}/check")

    assert resp.status_code == 200
    data = resp.json()
    assert data["last_check_status"] == "good"
    assert data["last_check_ip"] is None
    assert data["last_check_country_code"] is None
    assert data["last_check_timezone"] is None
    assert data["last_check_locale"] is None
    assert data["last_check_source"] == "qa"
    for leaked in (
        "timezone.example",
        "proxy-geoip-secret",
        "Authorization",
        "Bearer",
        "ip.example",
        sensitive_ip,
        sensitive_timezone,
        sensitive_locale,
        sensitive_country,
    ):
        assert leaked not in json.dumps(data, sort_keys=True)

    stored = db.get_proxy(proxy_id)
    assert stored is not None
    assert stored["last_check_ip"] is None
    assert stored["last_check_country_code"] is None
    assert stored["last_check_timezone"] is None
    assert stored["last_check_locale"] is None
    for leaked in (
        "timezone.example",
        "proxy-geoip-secret",
        "Authorization",
        "Bearer",
        "ip.example",
        sensitive_ip,
        sensitive_timezone,
        sensitive_locale,
        sensitive_country,
    ):
        assert leaked not in json.dumps(stored, sort_keys=True)


def test_proxy_check_records_failure_without_leaking_credentials(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_resolve(proxy_url: str | None):
        raise RuntimeError(f"cannot connect via {proxy_url}")

    monkeypatch.setattr(main, "resolve_network_geo", fake_resolve)
    create = app_client.post(
        "/api/proxies",
        json={
            "name": "Broken",
            "url": "http://user:hiddenpass@proxy.example:8080",
        },
    )
    proxy_id = create.json()["id"]

    resp = app_client.post(f"/api/proxies/{proxy_id}/check")

    assert resp.status_code == 200
    data = resp.json()
    assert data["last_check_status"] == "error"
    assert data["last_check_error"] == "Proxy check failed"
    assert "proxy.example" not in data["last_check_error"]
    assert "hiddenpass" not in data["last_check_error"]
    assert "hiddenpass" not in str(data)

    stored = db.get_proxy(proxy_id)
    assert stored is not None
    assert stored["last_check_status"] == "error"
    assert stored["last_check_error"] == "Proxy check failed"
    assert "proxy.example" not in stored["last_check_error"]
    assert "hiddenpass" not in stored["last_check_error"]


def test_proxy_check_records_generic_failure_without_leaking_provider_details(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_resolve(proxy_url: str | None):
        raise RuntimeError(
            "provider failed https://geo.example/check?token=super-secret "
            f"Authorization=Bearer super-secret via {proxy_url}"
        )

    monkeypatch.setattr(main, "resolve_network_geo", fake_resolve)
    create = app_client.post(
        "/api/proxies",
        json={
            "name": "Provider failure",
            "url": "http://user:hiddenpass@provider-failure.example:8080",
        },
    )
    proxy_id = create.json()["id"]

    resp = app_client.post(f"/api/proxies/{proxy_id}/check")

    assert resp.status_code == 200
    data = resp.json()
    assert data["last_check_status"] == "error"
    assert data["last_check_error"] == "Proxy check failed"
    for leaked in (
        "hiddenpass",
        "super-secret",
        "geo.example",
        "Authorization",
        "Bearer",
        "provider-failure.example",
        "http://user:hiddenpass@provider-failure.example:8080",
    ):
        assert leaked not in data["last_check_error"]

    stored = db.get_proxy(proxy_id)
    assert stored is not None
    assert stored["last_check_status"] == "error"
    assert stored["last_check_error"] == "Proxy check failed"
    for leaked in (
        "hiddenpass",
        "super-secret",
        "geo.example",
        "Authorization",
        "Bearer",
        "provider-failure.example",
        "http://user:hiddenpass@provider-failure.example:8080",
    ):
        assert leaked not in stored["last_check_error"]


def test_proxy_bulk_check_records_partial_results_without_leaking_credentials(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    captured_proxy_urls: list[str | None] = []

    async def fake_resolve(proxy_url: str | None):
        captured_proxy_urls.append(proxy_url)
        if proxy_url and "broken" in proxy_url:
            raise RuntimeError(f"cannot connect via {proxy_url}")
        return GeoIPResult(
            timezone="Europe/Berlin",
            locale="de-DE",
            ip="198.51.100.25",
            country_code="DE",
            source="qa",
        )

    monkeypatch.setattr(main, "resolve_network_geo", fake_resolve)
    good = app_client.post(
        "/api/proxies",
        json={
            "name": "Good bulk",
            "url": "http://user:hiddenpass@good.example:8080",
        },
    ).json()
    broken = app_client.post(
        "/api/proxies",
        json={
            "name": "Broken bulk",
            "url": "http://user:hiddenpass@broken.example:8080",
        },
    ).json()

    resp = app_client.post(
        "/api/proxies/bulk/check",
        json={
            "proxy_ids": [good["id"], broken["id"], "missing"],
            "confirm_bulk_check": True,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["succeeded"] == 1
    assert data["failed"] == 2
    assert captured_proxy_urls == [
        "http://user:hiddenpass@good.example:8080",
        "http://user:hiddenpass@broken.example:8080",
    ]
    assert "hiddenpass" not in str(data)

    good_result, broken_result, missing_result = data["results"]
    assert good_result["proxy_id"] == good["id"]
    assert good_result["ok"] is True
    assert good_result["error"] is None
    assert good_result["proxy"]["url"] == "http://good.example:8080"
    assert good_result["proxy"]["last_check_status"] == "good"
    assert good_result["proxy"]["last_check_country_code"] == "DE"

    assert broken_result["proxy_id"] == broken["id"]
    assert broken_result["ok"] is False
    assert broken_result["error"] == "Proxy check failed"
    assert "broken.example" not in broken_result["error"]
    assert "hiddenpass" not in broken_result["error"]
    assert broken_result["proxy"]["url"] == "http://broken.example:8080"
    assert broken_result["proxy"]["last_check_status"] == "error"
    assert broken_result["proxy"]["last_check_error"] == "Proxy check failed"
    assert "broken.example" not in broken_result["proxy"]["last_check_error"]
    assert "hiddenpass" not in broken_result["proxy"]["last_check_error"]

    assert missing_result == {
        "proxy_id": "missing",
        "ok": False,
        "error": "Proxy not found",
        "proxy": None,
    }

    stored_good = db.get_proxy(good["id"])
    assert stored_good is not None
    assert stored_good["last_check_status"] == "good"
    assert stored_good["last_check_ip"] == "198.51.100.25"

    stored_broken = db.get_proxy(broken["id"])
    assert stored_broken is not None
    assert stored_broken["last_check_status"] == "error"
    assert stored_broken["last_check_error"] == "Proxy check failed"
    assert "broken.example" not in stored_broken["last_check_error"]
    assert "hiddenpass" not in stored_broken["last_check_error"]


def test_proxy_bulk_check_records_generic_failure_without_leaking_provider_details(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_resolve(proxy_url: str | None):
        raise RuntimeError(
            "provider failed https://geo.example/check?token=super-secret "
            f"Authorization=Bearer super-secret via {proxy_url}"
        )

    monkeypatch.setattr(main, "resolve_network_geo", fake_resolve)
    broken = app_client.post(
        "/api/proxies",
        json={
            "name": "Broken provider bulk",
            "url": "http://user:hiddenpass@provider-bulk.example:8080",
        },
    ).json()

    resp = app_client.post(
        "/api/proxies/bulk/check",
        json={
            "proxy_ids": [broken["id"]],
            "confirm_bulk_check": True,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["succeeded"] == 0
    assert data["failed"] == 1
    result = data["results"][0]
    assert result["proxy_id"] == broken["id"]
    assert result["ok"] is False
    assert result["error"] == "Proxy check failed"
    assert result["proxy"]["last_check_status"] == "error"
    assert result["proxy"]["last_check_error"] == "Proxy check failed"
    for leaked in (
        "hiddenpass",
        "super-secret",
        "geo.example",
        "Authorization",
        "Bearer",
        "provider-bulk.example",
        "http://user:hiddenpass@provider-bulk.example:8080",
    ):
        assert leaked not in result["error"]
        assert leaked not in result["proxy"]["last_check_error"]

    stored = db.get_proxy(broken["id"])
    assert stored is not None
    assert stored["last_check_status"] == "error"
    assert stored["last_check_error"] == "Proxy check failed"
    for leaked in (
        "hiddenpass",
        "super-secret",
        "geo.example",
        "Authorization",
        "Bearer",
        "provider-bulk.example",
        "http://user:hiddenpass@provider-bulk.example:8080",
    ):
        assert leaked not in stored["last_check_error"]


def test_proxy_bulk_check_requires_explicit_confirmation_without_side_effects(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    captured_proxy_urls: list[str | None] = []

    async def fake_resolve(proxy_url: str | None):
        captured_proxy_urls.append(proxy_url)
        return GeoIPResult(
            timezone="Europe/Berlin",
            locale="de-DE",
            ip="198.51.100.25",
            country_code="DE",
            source="qa",
        )

    monkeypatch.setattr(main, "resolve_network_geo", fake_resolve)
    proxy = app_client.post(
        "/api/proxies",
        json={
            "name": "Bulk confirm",
            "url": "http://user:hiddenpass@bulk-confirm.example:8080",
        },
    ).json()

    for payload in (
        {"proxy_ids": [proxy["id"]]},
        {"proxy_ids": []},
        {"proxy_ids": [proxy["id"]], "confirm_bulk_check": False},
        {"proxy_ids": [proxy["id"]], "confirm_bulk_check": "true"},
    ):
        resp = app_client.post("/api/proxies/bulk/check", json=payload)
        assert resp.status_code == 422
        assert resp.json() == {"detail": "Proxy bulk check requires explicit confirmation"}

    assert captured_proxy_urls == []
    stored = db.get_proxy(proxy["id"])
    assert stored is not None
    assert stored["last_check_status"] is None
    assert stored["last_check_ip"] is None
    assert stored["last_check_error"] is None
    assert _proxy_bulk_audit_events() == []


def test_proxy_bulk_check_writes_redacted_audit_event(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_resolve(proxy_url: str | None):
        if proxy_url and "broken" in proxy_url:
            raise RuntimeError(f"cannot connect via {proxy_url}")
        return GeoIPResult(
            timezone="Europe/Berlin",
            locale="de-DE",
            ip="198.51.100.25",
            country_code="DE",
            source="qa",
        )

    monkeypatch.setattr(main, "resolve_network_geo", fake_resolve)
    good = app_client.post(
        "/api/proxies",
        json={"name": "Good audit bulk", "url": "http://user:hiddenpass@good-audit.example:8080"},
    ).json()
    broken = app_client.post(
        "/api/proxies",
        json={"name": "Broken audit bulk", "url": "http://user:hiddenpass@broken-audit.example:8080"},
    ).json()

    resp = app_client.post(
        "/api/proxies/bulk/check",
        json={
            "proxy_ids": [good["id"], broken["id"], "missing"],
            "confirm_bulk_check": True,
        },
    )

    assert resp.status_code == 200
    events = _proxy_bulk_audit_events()
    assert [event["event_type"] for event in events] == ["proxy.bulk_checked"]
    assert events[0]["actor_type"] == "local_admin"
    assert events[0]["metadata"] == {
        "proxy_count": 3,
        "checked_count": 2,
        "good_count": 1,
        "error_count": 1,
        "missing_count": 1,
    }
    serialized_event = json.dumps(events[0], sort_keys=True)
    assert "hiddenpass" not in serialized_event
    assert "good-audit.example" not in serialized_event
    assert "broken-audit.example" not in serialized_event
    assert "198.51.100.25" not in serialized_event


def test_proxy_bulk_check_requires_at_least_one_proxy_id(app_client: TestClient):
    resp = app_client.post(
        "/api/proxies/bulk/check",
        json={"proxy_ids": [], "confirm_bulk_check": True},
    )

    assert resp.status_code == 422


def test_proxy_assigns_raw_url_to_profiles_without_leaking_credentials(app_client: TestClient):
    proxy = app_client.post(
        "/api/proxies",
        json={
            "name": "Assignable",
            "url": "http://user:hiddenpass@assign.example:8080",
        },
    ).json()
    first = app_client.post("/api/profiles", json={"name": "Assign A"}).json()
    second = app_client.post(
        "/api/profiles",
        json={"name": "Assign B", "proxy": "http://old.example:8080"},
    ).json()

    resp = app_client.post(
        f"/api/proxies/{proxy['id']}/assign",
        json={
            "profile_ids": [first["id"], second["id"], "missing"],
            "confirm_assign": True,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["proxy_id"] == proxy["id"]
    assert data["proxy"]["url"] == "http://assign.example:8080"
    assert data["total"] == 3
    assert data["succeeded"] == 2
    assert data["failed"] == 1
    assert "hiddenpass" not in str(data)
    assert data["results"] == [
        {"profile_id": first["id"], "ok": True, "error": None},
        {"profile_id": second["id"], "ok": True, "error": None},
        {"profile_id": "missing", "ok": False, "error": "Profile not found"},
    ]

    stored_first = db.get_profile(first["id"])
    stored_second = db.get_profile(second["id"])
    assert stored_first is not None
    assert stored_second is not None
    assert stored_first["proxy"] == "http://user:hiddenpass@assign.example:8080"
    assert stored_second["proxy"] == "http://user:hiddenpass@assign.example:8080"


def test_proxy_assign_requires_explicit_confirmation_without_side_effects(app_client: TestClient):
    proxy = app_client.post(
        "/api/proxies",
        json={
            "name": "Assignable confirm",
            "url": "http://user:hiddenpass@assign-confirm.example:8080",
        },
    ).json()
    profile = app_client.post(
        "/api/profiles",
        json={"name": "Assign Confirm", "proxy": "http://old.example:8080"},
    ).json()

    for payload in (
        {"profile_ids": [profile["id"]]},
        {"profile_ids": [profile["id"]], "confirm_assign": False},
        {"profile_ids": [profile["id"]], "confirm_assign": "true"},
    ):
        resp = app_client.post(f"/api/proxies/{proxy['id']}/assign", json=payload)
        assert resp.status_code == 422
        assert resp.json() == {"detail": "Proxy assignment requires explicit confirmation"}

    stored = db.get_profile(profile["id"])
    assert stored is not None
    assert stored["proxy"] == "http://old.example:8080"
    assert _proxy_bulk_audit_events() == []


def test_proxy_assign_writes_redacted_audit_event(app_client: TestClient):
    proxy = app_client.post(
        "/api/proxies",
        json={"name": "Assignable audit", "url": "http://user:hiddenpass@assign-audit.example:8080"},
    ).json()
    first = app_client.post("/api/profiles", json={"name": "Assign Audit A"}).json()
    second = app_client.post("/api/profiles", json={"name": "Assign Audit B"}).json()

    resp = app_client.post(
        f"/api/proxies/{proxy['id']}/assign",
        json={
            "profile_ids": [first["id"], second["id"], "missing"],
            "confirm_assign": True,
        },
    )

    assert resp.status_code == 200
    events = _proxy_bulk_audit_events()
    assert [event["event_type"] for event in events] == ["proxy.assigned"]
    assert events[0]["metadata"] == {
        "proxy_id": proxy["id"],
        "profile_count": 3,
        "assigned_count": 2,
        "missing_profile_count": 1,
    }
    serialized_event = json.dumps(events[0], sort_keys=True)
    assert "hiddenpass" not in serialized_event
    assert "assign-audit.example" not in serialized_event


def test_proxy_assign_not_found_and_empty_profiles(app_client: TestClient):
    proxy = app_client.post(
        "/api/proxies",
        json={"name": "Assignable", "url": "http://assign.example:8080"},
    ).json()

    assert app_client.post(
        "/api/proxies/missing/assign",
        json={"profile_ids": ["profile"], "confirm_assign": True},
    ).status_code == 404
    assert app_client.post(
        f"/api/proxies/{proxy['id']}/assign",
        json={"profile_ids": [], "confirm_assign": True},
    ).status_code == 422


def test_random_proxy_assignment_filters_by_country_tag_and_preset_without_leaking_credentials(
    app_client: TestClient,
):
    preset = app_client.post(
        "/api/proxy-provider-presets",
        json={
            "name": "Japan mobile default",
            "provider": "ProxyJP",
            "country_code": "JP",
            "tags": [{"tag": "mobile", "color": "#0ea5e9"}],
        },
    ).json()
    matching = app_client.post(
        "/api/proxies",
        json={
            "name": "JP mobile good",
            "url": "http://user:hiddenpass@jp-mobile.example:8080",
            "provider": "ProxyJP",
            "country_code": "JP",
            "tags": [
                {"tag": "mobile", "color": "#0ea5e9"},
                {"tag": "warmup", "color": None},
            ],
        },
    ).json()
    app_client.post(
        "/api/proxies",
        json={
            "name": "US mobile excluded",
            "url": "http://user:hiddenpass@us-mobile.example:8080",
            "provider": "ProxyJP",
            "country_code": "US",
            "tags": [{"tag": "mobile", "color": None}],
        },
    )
    first = app_client.post("/api/profiles", json={"name": "Random Assign A"}).json()
    second = app_client.post("/api/profiles", json={"name": "Random Assign B"}).json()

    resp = app_client.post(
        "/api/proxies/assign/random",
        json={
            "profile_ids": [first["id"], second["id"], "missing"],
            "provider_preset_id": preset["id"],
            "tags": ["warmup"],
            "confirm_assign": True,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy"] == "random"
    assert data["candidate_count"] == 1
    assert data["provider_preset_id"] == preset["id"]
    assert data["provider"] == "ProxyJP"
    assert data["country_code"] == "JP"
    assert data["tags"] == ["mobile", "warmup"]
    assert data["total"] == 3
    assert data["succeeded"] == 2
    assert data["failed"] == 1
    assert "hiddenpass" not in str(data)
    assert data["results"] == [
        {
            "profile_id": first["id"],
            "ok": True,
            "error": None,
            "proxy_id": matching["id"],
            "proxy": {**matching, "url": "http://jp-mobile.example:8080"},
        },
        {
            "profile_id": second["id"],
            "ok": True,
            "error": None,
            "proxy_id": matching["id"],
            "proxy": {**matching, "url": "http://jp-mobile.example:8080"},
        },
        {
            "profile_id": "missing",
            "ok": False,
            "error": "Profile not found",
            "proxy_id": None,
            "proxy": None,
        },
    ]

    stored_first = db.get_profile(first["id"])
    stored_second = db.get_profile(second["id"])
    assert stored_first is not None
    assert stored_second is not None
    assert stored_first["proxy"] == "http://user:hiddenpass@jp-mobile.example:8080"
    assert stored_second["proxy"] == "http://user:hiddenpass@jp-mobile.example:8080"


def test_random_proxy_assignment_writes_redacted_audit_event(app_client: TestClient):
    preset = app_client.post(
        "/api/proxy-provider-presets",
        json={
            "name": "Audit preset",
            "provider": "ProxyJP",
            "country_code": "JP",
            "tags": [{"tag": "mobile", "color": "#0ea5e9"}],
        },
    ).json()
    app_client.post(
        "/api/proxies",
        json={
            "name": "JP audit mobile",
            "url": "http://user:hiddenpass@jp-audit-mobile.example:8080",
            "provider": "ProxyJP",
            "country_code": "JP",
            "tags": [{"tag": "mobile", "color": "#0ea5e9"}],
        },
    ).json()
    first = app_client.post("/api/profiles", json={"name": "Random Audit A"}).json()
    second = app_client.post("/api/profiles", json={"name": "Random Audit B"}).json()

    resp = app_client.post(
        "/api/proxies/assign/random",
        json={
            "profile_ids": [first["id"], second["id"], "missing"],
            "provider_preset_id": preset["id"],
            "confirm_assign": True,
        },
    )

    assert resp.status_code == 200
    events = _proxy_bulk_audit_events()
    assert [event["event_type"] for event in events] == ["proxy.random_assigned"]
    assert events[0]["metadata"] == {
        "provider_preset_id": preset["id"],
        "provider": "ProxyJP",
        "country_code": "JP",
        "tag_count": 1,
        "candidate_count": 1,
        "profile_count": 3,
        "assigned_count": 2,
        "missing_profile_count": 1,
    }
    serialized_event = json.dumps(events[0], sort_keys=True)
    assert "hiddenpass" not in serialized_event
    assert "jp-audit-mobile.example" not in serialized_event
    assert "mobile" not in serialized_event


def test_random_proxy_assignment_redacts_persisted_sensitive_preset_selection_metadata(
    app_client: TestClient,
):
    preset = app_client.post(
        "/api/proxy-provider-presets",
        json={
            "name": "Polluted preset",
            "provider": "ProxyJP",
            "country_code": "JP",
            "tags": [{"tag": "mobile", "color": "#0ea5e9"}],
        },
    ).json()
    leak_marker = "random-selection-secret"
    updated = db.update_proxy_provider_preset(
        preset["id"],
        provider=f"Authorization=Bearer {leak_marker}",
        country_code=f"JP?token={leak_marker}",
    )
    assert updated is not None
    matching = app_client.post(
        "/api/proxies",
        json={
            "name": "Tagged mobile proxy",
            "url": "http://user:hiddenpass@tagged-mobile.example:8080",
            "provider": "ProxyJP",
            "country_code": "JP",
            "tags": [{"tag": "mobile", "color": "#0ea5e9"}],
        },
    ).json()
    profile = app_client.post("/api/profiles", json={"name": "Redacted Random"}).json()

    resp = app_client.post(
        "/api/proxies/assign/random",
        json={
            "profile_ids": [profile["id"]],
            "provider_preset_id": preset["id"],
            "confirm_assign": True,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] is None
    assert data["country_code"] is None
    assert data["tags"] == ["mobile"]
    assert data["candidate_count"] == 1
    assert data["results"][0]["proxy_id"] == matching["id"]

    events = _proxy_bulk_audit_events()
    assert [event["event_type"] for event in events] == ["proxy.random_assigned"]
    assert events[0]["metadata"] == {
        "provider_preset_id": preset["id"],
        "tag_count": 1,
        "candidate_count": 1,
        "profile_count": 1,
        "assigned_count": 1,
        "missing_profile_count": 0,
    }
    serialized = json.dumps({"response": data, "events": events}, sort_keys=True)
    for leaked in (leak_marker, "Authorization", "Bearer", "token=", "hiddenpass"):
        assert leaked not in serialized


def test_random_proxy_assignment_requires_explicit_confirmation_without_side_effects(
    app_client: TestClient,
):
    app_client.post(
        "/api/proxies",
        json={
            "name": "Random confirm",
            "url": "http://user:hiddenpass@random-confirm.example:8080",
            "country_code": "JP",
        },
    )
    profile = app_client.post(
        "/api/profiles",
        json={"name": "Random Confirm", "proxy": "http://old.example:8080"},
    ).json()

    for payload in (
        {"profile_ids": [profile["id"]], "country_code": "JP"},
        {"profile_ids": [profile["id"]], "country_code": "JP", "confirm_assign": False},
        {"profile_ids": [profile["id"]], "country_code": "JP", "confirm_assign": "true"},
    ):
        resp = app_client.post("/api/proxies/assign/random", json=payload)
        assert resp.status_code == 422
        assert resp.json() == {"detail": "Random proxy assignment requires explicit confirmation"}

    stored = db.get_profile(profile["id"])
    assert stored is not None
    assert stored["proxy"] == "http://old.example:8080"
    assert _proxy_bulk_audit_events() == []


def test_random_proxy_assignment_rejects_missing_selection(app_client: TestClient):
    profile = app_client.post("/api/profiles", json={"name": "No candidate"}).json()
    app_client.post(
        "/api/proxies",
        json={
            "name": "US only",
            "url": "http://user:hiddenpass@us.example:8080",
            "country_code": "US",
            "tags": [{"tag": "stable", "color": None}],
        },
    )

    resp = app_client.post(
        "/api/proxies/assign/random",
        json={
            "profile_ids": [profile["id"]],
            "country_code": "JP",
            "tags": ["mobile"],
            "confirm_assign": True,
        },
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "No proxy assets match selection"
    assert "hiddenpass" not in str(resp.json())
    assert db.get_profile(profile["id"])["proxy"] is None


def test_save_profile_current_proxy_as_asset_without_leaking_credentials(app_client: TestClient):
    profile = app_client.post(
        "/api/profiles",
        json={
            "name": "Profile Proxy Source",
            "proxy": "http://user:hiddenpass@profile-proxy.example:8080",
        },
    ).json()

    resp = app_client.post(
        f"/api/profiles/{profile['id']}/proxy-asset",
        json={
            "name": "Saved from profile",
            "provider": "ProfilePool",
            "tags": [{"tag": "saved", "color": "#2563eb"}],
            "notes": "Migrated from profile current proxy",
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Saved from profile"
    assert data["url"] == "http://profile-proxy.example:8080"
    assert data["provider"] == "ProfilePool"
    assert data["tags"] == [{"tag": "saved", "color": "#2563eb"}]
    assert data["notes"] == "Migrated from profile current proxy"
    assert "hiddenpass" not in str(data)

    stored = db.get_proxy(data["id"])
    assert stored is not None
    assert stored["url"] == "http://user:hiddenpass@profile-proxy.example:8080"


def test_save_profile_current_proxy_as_asset_rejects_missing_or_invalid_proxy_without_leaking_credentials(
    app_client: TestClient,
):
    no_proxy = app_client.post("/api/profiles", json={"name": "No proxy"}).json()
    missing_proxy = app_client.post(
        f"/api/profiles/{no_proxy['id']}/proxy-asset",
        json={"name": "Missing"},
    )
    assert missing_proxy.status_code == 400
    assert missing_proxy.json()["detail"] == "Profile has no proxy"

    invalid = app_client.post(
        "/api/profiles",
        json={
            "name": "Invalid profile proxy",
            "proxy": "ftp://user:hiddenpass@profile-proxy.example:21",
        },
    ).json()
    invalid_resp = app_client.post(
        f"/api/profiles/{invalid['id']}/proxy-asset",
        json={"name": "Invalid"},
    )
    assert invalid_resp.status_code == 400
    assert "Invalid proxy scheme" in invalid_resp.json()["detail"]
    assert "hiddenpass" not in str(invalid_resp.json())

    not_found = app_client.post(
        "/api/profiles/missing/proxy-asset",
        json={"name": "Missing profile"},
    )
    assert not_found.status_code == 404


def test_save_profile_current_proxy_as_asset_redacts_sensitive_storage_error_detail(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    profile = app_client.post(
        "/api/profiles",
        json={
            "name": "Sensitive profile proxy source",
            "proxy": "http://user:hiddenpass@profile-error.example:8080",
        },
    ).json()

    def fail_create_proxy(**_fields):
        raise ValueError(
            "Profile proxy save rejected "
            "http://user:hiddenpass@profile-error.example:8080 token=super-secret"
        )

    monkeypatch.setattr(main.db, "create_proxy", fail_create_proxy)

    resp = app_client.post(
        f"/api/profiles/{profile['id']}/proxy-asset",
        json={"name": "Sensitive save failure"},
    )

    assert resp.status_code == 400
    body = resp.json()
    assert body == {"detail": "Invalid proxy URL"}
    serialized = str(body)
    assert "hiddenpass" not in serialized
    assert "super-secret" not in serialized
    assert "profile-error.example" not in serialized
    assert "user:" not in serialized
