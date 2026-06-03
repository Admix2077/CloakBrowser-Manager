"""Tests for proxy provider preset storage and CRUD API."""

from __future__ import annotations

import json
from pathlib import Path

from starlette.testclient import TestClient

from backend import database as db


def test_init_db_creates_proxy_provider_presets_table(tmp_db: Path):
    with db.get_db() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {row["name"] for row in tables}
    assert "proxy_provider_presets" in names


def test_create_list_update_and_delete_proxy_provider_preset(tmp_db: Path):
    preset = db.create_proxy_provider_preset(
        name="Japan mobile default",
        provider="MobileProxy",
        country_code="JP",
        tags=[{"tag": "mobile", "color": "#0ea5e9"}],
        notes="Tokyo exit defaults",
    )

    assert preset["name"] == "Japan mobile default"
    assert preset["provider"] == "MobileProxy"
    assert preset["country_code"] == "JP"
    assert preset["tags"] == [{"tag": "mobile", "color": "#0ea5e9"}]
    assert preset["notes"] == "Tokyo exit defaults"
    assert preset["created_at"] is not None
    assert preset["updated_at"] is not None

    assert [item["id"] for item in db.list_proxy_provider_presets()] == [preset["id"]]

    updated = db.update_proxy_provider_preset(
        preset["id"],
        name="Japan mobile warmup",
        country_code=" JP ",
        tags=[{"tag": "warmup", "color": None}],
        notes=None,
    )

    assert updated is not None
    assert updated["name"] == "Japan mobile warmup"
    assert updated["provider"] == "MobileProxy"
    assert updated["country_code"] == " JP "
    assert updated["tags"] == [{"tag": "warmup", "color": None}]
    assert updated["notes"] is None

    assert db.delete_proxy_provider_preset(preset["id"]) is True
    assert db.get_proxy_provider_preset(preset["id"]) is None
    assert db.delete_proxy_provider_preset(preset["id"]) is False


def test_delete_proxy_provider_preset_does_not_delete_proxy_assets(tmp_db: Path):
    preset = db.create_proxy_provider_preset(
        name="US residential",
        provider="ProxyCo",
        country_code="US",
        tags=[{"tag": "stable", "color": "#2563eb"}],
    )
    proxy = db.create_proxy(
        name="Proxy asset",
        url="http://proxy.example:8080",
        provider="ProxyCo",
        country_code="US",
        tags=[{"tag": "stable", "color": "#2563eb"}],
    )

    assert db.delete_proxy_provider_preset(preset["id"]) is True

    remaining_proxy = db.get_proxy(proxy["id"])
    assert remaining_proxy is not None
    assert remaining_proxy["provider"] == "ProxyCo"
    assert remaining_proxy["country_code"] == "US"


def test_proxy_provider_preset_crud_api(app_client: TestClient):
    create = app_client.post(
        "/api/proxy-provider-presets",
        json={
            "name": "Japan mobile default",
            "provider": "MobileProxy",
            "country_code": "JP",
            "tags": [{"tag": "jp", "color": "#0ea5e9"}],
            "notes": "Tokyo exit defaults",
        },
    )

    assert create.status_code == 201
    data = create.json()
    assert data["id"]
    assert data["name"] == "Japan mobile default"
    assert data["provider"] == "MobileProxy"
    assert data["country_code"] == "JP"
    assert data["tags"] == [{"tag": "jp", "color": "#0ea5e9"}]
    assert data["notes"] == "Tokyo exit defaults"

    listed = app_client.get("/api/proxy-provider-presets")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [data["id"]]

    get = app_client.get(f"/api/proxy-provider-presets/{data['id']}")
    assert get.status_code == 200
    assert get.json()["provider"] == "MobileProxy"

    update = app_client.put(
        f"/api/proxy-provider-presets/{data['id']}",
        json={
            "name": "Japan mobile warmup",
            "tags": [{"tag": "priority", "color": None}],
            "notes": None,
        },
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Japan mobile warmup"
    assert update.json()["provider"] == "MobileProxy"
    assert update.json()["tags"] == [{"tag": "priority", "color": None}]
    assert update.json()["notes"] is None

    delete = app_client.request(
        "DELETE",
        f"/api/proxy-provider-presets/{data['id']}",
        json={"confirm_delete": True},
    )
    assert delete.status_code == 200
    assert delete.json() == {"ok": True}
    assert app_client.get(f"/api/proxy-provider-presets/{data['id']}").status_code == 404


def test_proxy_provider_preset_api_sanitizes_persisted_malformed_tags(
    app_client: TestClient,
):
    preset = app_client.post(
        "/api/proxy-provider-presets",
        json={
            "name": "Malformed tags",
            "provider": "ProxyCo",
            "tags": [{"tag": "valid", "color": "#0ea5e9"}],
        },
    ).json()
    db.update_proxy_provider_preset(
        preset["id"],
        tags=[
            {"color": "#ef4444"},
            {"tag": 123, "color": "#22c55e"},
            {"tag": "kept", "color": 123},
            {"tag": "colored", "color": "#0ea5e9"},
        ],
    )

    get = app_client.get(f"/api/proxy-provider-presets/{preset['id']}")
    listed = app_client.get("/api/proxy-provider-presets")

    assert get.status_code == 200
    assert get.json()["tags"] == [
        {"tag": "kept", "color": None},
        {"tag": "colored", "color": "#0ea5e9"},
    ]
    assert listed.status_code == 200
    assert listed.json()[0]["tags"] == get.json()["tags"]


def test_proxy_provider_preset_api_redacts_persisted_sensitive_selection_fields(
    app_client: TestClient,
):
    preset = app_client.post(
        "/api/proxy-provider-presets",
        json={
            "name": "Sensitive selection fields",
            "provider": "ProxyCo",
            "country_code": "JP",
        },
    ).json()
    leak_marker = "preset-selection-secret"

    updated = db.update_proxy_provider_preset(
        preset["id"],
        provider=f"Authorization=Bearer {leak_marker}",
        country_code=f"JP?token={leak_marker}",
    )
    assert updated is not None

    get = app_client.get(f"/api/proxy-provider-presets/{preset['id']}")
    listed = app_client.get("/api/proxy-provider-presets")

    assert get.status_code == 200
    assert listed.status_code == 200
    for data in (get.json(), listed.json()[0]):
        assert data["provider"] is None
        assert data["country_code"] is None
        serialized = json.dumps(data, sort_keys=True)
        for leaked in (leak_marker, "Authorization", "Bearer", "token="):
            assert leaked not in serialized


def test_proxy_provider_preset_crud_writes_low_sensitive_audit_events(
    app_client: TestClient,
):
    create = app_client.post(
        "/api/proxy-provider-presets",
        json={
            "name": "Preset https://provider.example/?token=super-secret",
            "provider": "Authorization=Bearer super-secret",
            "country_code": "JP",
            "tags": [{"tag": "mobile-token-super-secret", "color": "#0ea5e9"}],
            "notes": "notes token=super-secret provider.example",
        },
    )
    assert create.status_code == 201
    preset_id = create.json()["id"]

    update = app_client.put(
        f"/api/proxy-provider-presets/{preset_id}",
        json={
            "name": "Updated https://provider.example/?token=new-secret",
            "provider": "token=new-secret",
            "tags": [{"tag": "priority-secret", "color": None}],
            "notes": "Authorization=Bearer new-secret",
        },
    )
    assert update.status_code == 200

    delete = app_client.request(
        "DELETE",
        f"/api/proxy-provider-presets/{preset_id}",
        json={"confirm_delete": True},
    )
    assert delete.status_code == 200

    events = db.list_audit_events()
    assert [event["event_type"] for event in events] == [
        "proxy.provider_preset.created",
        "proxy.provider_preset.updated",
        "proxy.provider_preset.deleted",
    ]
    assert all(event["actor_type"] == "local_admin" for event in events)
    assert events[0]["metadata"] == {
        "preset_id": preset_id,
        "tag_count": 1,
    }
    assert events[1]["metadata"] == {
        "preset_id": preset_id,
        "updated_fields": ["name", "notes", "provider", "tags"],
        "tag_count": 1,
    }
    assert events[2]["metadata"] == {
        "preset_id": preset_id,
        "tag_count": 1,
    }

    serialized_events = json.dumps(events, sort_keys=True)
    for leaked in (
        "provider.example",
        "super-secret",
        "new-secret",
        "Authorization",
        "Bearer",
        "mobile-token-super-secret",
        "priority-secret",
    ):
        assert leaked not in serialized_events


def test_delete_proxy_provider_preset_requires_explicit_confirmation_without_side_effects(
    app_client: TestClient,
):
    create = app_client.post(
        "/api/proxy-provider-presets",
        json={
            "name": "Japan mobile default",
            "provider": "MobileProxy",
            "country_code": "JP",
            "tags": [{"tag": "jp", "color": "#0ea5e9"}],
        },
    )
    assert create.status_code == 201
    preset_id = create.json()["id"]

    for payload in ({}, {"confirm_delete": False}, {"confirm_delete": "true"}):
        resp = app_client.request(
            "DELETE",
            f"/api/proxy-provider-presets/{preset_id}",
            json=payload,
        )
        assert resp.status_code == 422
        assert resp.json() == {
            "detail": "Proxy provider preset delete requires explicit confirmation"
        }

    get = app_client.get(f"/api/proxy-provider-presets/{preset_id}")
    assert get.status_code == 200
    assert get.json()["id"] == preset_id


def test_proxy_provider_preset_api_rejects_empty_name(app_client: TestClient):
    resp = app_client.post(
        "/api/proxy-provider-presets",
        json={
            "name": "",
            "provider": "ProxyCo",
        },
    )

    assert resp.status_code == 422
    assert app_client.get("/api/proxy-provider-presets").json() == []


def test_proxy_provider_preset_api_ignores_credential_and_billing_fields(app_client: TestClient):
    resp = app_client.post(
        "/api/proxy-provider-presets",
        json={
            "name": "Provider metadata only",
            "provider": "ProxyCo",
            "country_code": "US",
            "api_key": "secret-api-key",
            "password": "secret-password",
            "billing_account": "acct_123",
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert "api_key" not in data
    assert "password" not in data
    assert "billing_account" not in data

    listed = app_client.get("/api/proxy-provider-presets").json()
    assert listed == [data]
    assert "secret-api-key" not in str(listed)
    assert "secret-password" not in str(listed)


def test_proxy_provider_preset_api_not_found(app_client: TestClient):
    assert app_client.get("/api/proxy-provider-presets/missing").status_code == 404
    assert app_client.put("/api/proxy-provider-presets/missing", json={"name": "x"}).status_code == 404
    assert app_client.request(
        "DELETE",
        "/api/proxy-provider-presets/missing",
        json={"confirm_delete": True},
    ).status_code == 404
