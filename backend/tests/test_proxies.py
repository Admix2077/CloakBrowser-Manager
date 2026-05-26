"""Tests for proxy asset storage and CRUD API."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from backend import database as db, main
from backend.geoip import GeoIPResult


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

    delete = app_client.delete(f"/api/proxies/{data['id']}")
    assert delete.status_code == 200
    assert delete.json() == {"ok": True}
    assert app_client.get(f"/api/proxies/{data['id']}").status_code == 404


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


def test_proxy_api_not_found(app_client: TestClient):
    assert app_client.get("/api/proxies/missing").status_code == 404
    assert app_client.put("/api/proxies/missing", json={"name": "x"}).status_code == 404
    assert app_client.delete("/api/proxies/missing").status_code == 404
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
    assert "http://proxy.example:8080" in data["last_check_error"]
    assert "hiddenpass" not in data["last_check_error"]
    assert "hiddenpass" not in str(data)

    stored = db.get_proxy(proxy_id)
    assert stored is not None
    assert stored["last_check_status"] == "error"
    assert "hiddenpass" not in stored["last_check_error"]


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
        json={"proxy_ids": [good["id"], broken["id"], "missing"]},
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
    assert "http://broken.example:8080" in broken_result["error"]
    assert "hiddenpass" not in broken_result["error"]
    assert broken_result["proxy"]["url"] == "http://broken.example:8080"
    assert broken_result["proxy"]["last_check_status"] == "error"
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
    assert "hiddenpass" not in stored_broken["last_check_error"]


def test_proxy_bulk_check_requires_at_least_one_proxy_id(app_client: TestClient):
    resp = app_client.post("/api/proxies/bulk/check", json={"proxy_ids": []})

    assert resp.status_code == 422
