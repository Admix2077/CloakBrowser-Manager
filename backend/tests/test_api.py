"""Tests for FastAPI routes via TestClient."""

from __future__ import annotations

import json
import sys
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from backend import main
from backend.browser_manager import RunningProfile


def _audit_events_except(*event_types: str) -> list[dict]:
    excluded = set(event_types)
    return [
        event
        for event in main.db.list_audit_events()
        if event["event_type"] not in excluded
    ]


def _audit_events_of_type(event_type: str) -> list[dict]:
    return [
        event
        for event in main.db.list_audit_events()
        if event["event_type"] == event_type
    ]


def _automation_task_audit_events() -> list[dict]:
    return [
        event
        for event in main.db.list_audit_events()
        if event["event_type"].startswith("automation.task.")
    ]


# ── Profile CRUD ─────────────────────────────────────────────────────────────


def test_list_profiles_empty(app_client: TestClient):
    resp = app_client.get("/api/profiles")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_profile(app_client: TestClient):
    resp = app_client.post("/api/profiles", json={"name": "Test"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test"
    assert data["status"] == "stopped"
    assert "id" in data
    assert len(data["id"]) == 36  # UUID


def test_create_profile_with_all_fields(app_client: TestClient):
    resp = app_client.post("/api/profiles", json={
        "name": "Full",
        "fingerprint_seed": 42,
        "proxy": "http://host:8080",
        "platform": "macos",
        "screen_width": 2560,
        "screen_height": 1440,
        "humanize": True,
        "human_preset": "careful",
        "tags": [{"tag": "work", "color": "#ff0000"}],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["fingerprint_seed"] == 42
    assert data["platform"] == "macos"
    assert len(data["tags"]) == 1


def test_create_profile_invalid_platform(app_client: TestClient):
    resp = app_client.post("/api/profiles", json={"name": "Bad", "platform": "android"})
    assert resp.status_code == 422


def test_get_profile(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Get Me"})
    pid = create.json()["id"]
    resp = app_client.get(f"/api/profiles/{pid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Get Me"


def test_get_profile_not_found(app_client: TestClient):
    resp = app_client.get("/api/profiles/nonexistent")
    assert resp.status_code == 404


def test_update_profile(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Original"})
    pid = create.json()["id"]
    resp = app_client.put(f"/api/profiles/{pid}", json={"name": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


def test_create_update_get_profile_auto_launch_api(app_client: TestClient):
    create = app_client.post("/api/profiles", json={
        "name": "AutoLaunch",
        "auto_launch": True,
    })
    assert create.status_code == 201
    pid = create.json()["id"]
    assert create.json()["auto_launch"] is True

    get_resp = app_client.get(f"/api/profiles/{pid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["auto_launch"] is True

    update = app_client.put(f"/api/profiles/{pid}", json={"auto_launch": False})
    assert update.status_code == 200
    assert update.json()["auto_launch"] is False


def test_update_profile_not_found(app_client: TestClient):
    resp = app_client.put("/api/profiles/nonexistent", json={"name": "x"})
    assert resp.status_code == 404


def test_delete_profile(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Delete Me"})
    pid = create.json()["id"]
    resp = app_client.delete(f"/api/profiles/{pid}")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    # Confirm gone
    assert app_client.get(f"/api/profiles/{pid}").status_code == 404


def test_delete_profile_not_found(app_client: TestClient):
    resp = app_client.delete("/api/profiles/nonexistent")
    assert resp.status_code == 404


def test_profile_crud_api_writes_redacted_audit_events(app_client: TestClient):
    create = app_client.post(
        "/api/profiles",
        json={
            "name": "Audited Profile",
            "proxy": "http://user:super-secret-proxy-password@profile-audit.example:8080",
            "platform": "linux",
            "notes": "note-token-super-secret",
            "tags": [{"tag": "ops", "color": None}],
        },
    )
    assert create.status_code == 201
    profile_id = create.json()["id"]

    update = app_client.put(
        f"/api/profiles/{profile_id}",
        json={
            "name": "Audited Profile Updated",
            "proxy": "http://user:new-secret-proxy-password@profile-audit.example:8080",
            "notes": "updated-note-token-super-secret",
            "tags": [{"tag": "priority", "color": "#2563eb"}],
        },
    )
    assert update.status_code == 200

    delete = app_client.delete(f"/api/profiles/{profile_id}")
    assert delete.status_code == 200

    events = main.db.list_audit_events()
    assert [event["event_type"] for event in events] == [
        "profile.created",
        "profile.updated",
        "profile.deleted",
    ]
    assert all(event["actor_type"] == "local_admin" for event in events)
    assert [event["profile_id"] for event in events] == [profile_id, profile_id, profile_id]
    assert all(event["runtime_session_id"] is None for event in events)
    assert events[0]["metadata"] == {
        "name": "Audited Profile",
        "platform": "linux",
        "tag_count": 1,
    }
    assert events[1]["metadata"] == {
        "updated_fields": ["name", "notes", "proxy", "tags"],
        "tag_count": 1,
    }
    assert events[2]["metadata"] == {
        "name": "Audited Profile Updated",
        "platform": "linux",
        "tag_count": 1,
    }

    serialized_events = json.dumps(events, sort_keys=True)
    assert "super-secret-proxy-password" not in serialized_events
    assert "new-secret-proxy-password" not in serialized_events
    assert "user:" not in serialized_events
    assert "profile-audit.example" not in serialized_events
    assert "note-token-super-secret" not in serialized_events
    assert "updated-note-token-super-secret" not in serialized_events
    assert "user_data_dir" not in serialized_events
    serialized_metadata = json.dumps([event["metadata"] for event in events], sort_keys=True)
    assert "runtime" not in serialized_metadata
    assert "viewer" not in serialized_metadata


def test_delete_profile_stops_running(app_client: TestClient):
    """Deleting a running profile should stop it first."""
    create = app_client.post("/api/profiles", json={"name": "Running"})
    pid = create.json()["id"]

    # Inject mock running profile
    mock_running = MagicMock(spec=RunningProfile)
    mock_running.display = 100
    mock_running.ws_port = 6100
    mock_running.engine = "invisible_playwright"
    main.browser_mgr.running[pid] = mock_running
    main.browser_mgr.stop = AsyncMock()

    resp = app_client.delete(f"/api/profiles/{pid}")
    assert resp.status_code == 200
    main.browser_mgr.stop.assert_called_once_with(pid)


def test_tags_api_update_replace_and_clear(app_client: TestClient):
    create = app_client.post("/api/profiles", json={
        "name": "Tags",
        "tags": [{"tag": "old", "color": "#ef4444"}],
    })
    assert create.status_code == 201
    pid = create.json()["id"]

    update = app_client.put(f"/api/profiles/{pid}", json={
        "tags": [{"tag": "new", "color": "#22c55e"}],
    })
    assert update.status_code == 200
    assert update.json()["tags"] == [{"tag": "new", "color": "#22c55e"}]

    listed = app_client.get("/api/profiles").json()
    listed_profile = next(p for p in listed if p["id"] == pid)
    assert listed_profile["tags"] == [{"tag": "new", "color": "#22c55e"}]

    cleared = app_client.put(f"/api/profiles/{pid}", json={"tags": []})
    assert cleared.status_code == 200
    assert cleared.json()["tags"] == []


def test_export_profiles_redacts_proxy_credentials_by_default(app_client: TestClient):
    create = app_client.post(
        "/api/profiles",
        json={
            "name": "ExportProxyDefault",
            "proxy": "http://user:super-secret-proxy-password@proxy.example.com:8080",
        },
    )
    pid = create.json()["id"]

    resp = app_client.post("/api/profiles/export", json={"profile_ids": [pid]})

    assert resp.status_code == 200
    data = resp.json()
    config = data["results"][0]["config"]
    assert config["proxy"] == "http://proxy.example.com:8080"
    response_text = resp.text
    assert "super-secret-proxy-password" not in response_text
    assert "user:super-secret-proxy-password" not in response_text


def test_export_profiles_can_include_sensitive_proxy_when_explicitly_requested(app_client: TestClient):
    proxy = "http://user:super-secret-proxy-password@proxy.example.com:8080"
    create = app_client.post(
        "/api/profiles",
        json={
            "name": "ExportProxySensitive",
            "proxy": proxy,
        },
    )
    pid = create.json()["id"]

    resp = app_client.post(
        "/api/profiles/export",
        json={"profile_ids": [pid], "include_sensitive": True},
    )

    assert resp.status_code == 200
    data = resp.json()
    config = data["results"][0]["config"]
    assert config["proxy"] == proxy


def test_export_profiles_rejects_coerced_sensitive_flag(app_client: TestClient):
    create = app_client.post(
        "/api/profiles",
        json={
            "name": "ExportProxyCoercedSensitive",
            "proxy": "http://user:super-secret-proxy-password@proxy.example.com:8080",
        },
    )
    pid = create.json()["id"]

    resp = app_client.post(
        "/api/profiles/export",
        json={"profile_ids": [pid], "include_sensitive": "true"},
    )

    assert resp.status_code == 422


def test_import_profile_configs_creates_profiles_from_safe_config_without_runtime_fields(app_client: TestClient):
    resp = app_client.post(
        "/api/profiles/config/import",
        json={
            "schema_version": 1,
            "configs": [
                {
                    "name": "Imported Config",
                    "fingerprint_seed": 12345,
                    "proxy": "http://proxy.example.com:8080",
                    "platform": "linux",
                    "screen_width": 1440,
                    "screen_height": 900,
                    "gpu_vendor": "Mesa",
                    "gpu_renderer": "llvmpipe",
                    "hardware_concurrency": 8,
                    "humanize": True,
                    "human_preset": "careful",
                    "headless": False,
                    "geoip": False,
                    "clipboard_sync": False,
                    "auto_launch": True,
                    "color_scheme": "dark",
                    "launch_args": ["--private-window"],
                    "notes": "Imported notes",
                    "tags": [{"tag": "imported", "color": "#2563eb"}],
                    "cookies": [{"name": "sid", "value": "super-secret-cookie-value"}],
                    "local_storage": {"token": "super-secret-local-storage"},
                    "profile_dir": "/tmp/should-not-import",
                    "user_data_dir": "/tmp/should-not-import",
                    "runtime_session_id": "runtime-secret",
                    "viewer_token": "viewer-secret",
                    "automation_tasks": [{"id": "task-secret"}],
                    "wallet_id": "wallet-secret",
                    "order_id": "order-secret",
                    "permission": "admin",
                }
            ],
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["imported"] == 1
    assert data["failed"] == 0
    result = data["results"][0]
    assert result["ok"] is True
    assert result["errors"] == []
    profile = result["profile"]
    assert profile["name"] == "Imported Config"
    assert profile["fingerprint_seed"] == 12345
    assert profile["proxy"] == "http://proxy.example.com:8080"
    assert profile["platform"] == "linux"
    assert profile["screen_width"] == 1440
    assert profile["screen_height"] == 900
    assert profile["gpu_vendor"] == "Mesa"
    assert profile["gpu_renderer"] == "llvmpipe"
    assert profile["hardware_concurrency"] == 8
    assert profile["humanize"] is True
    assert profile["human_preset"] == "careful"
    assert profile["headless"] is False
    assert profile["geoip"] is False
    assert profile["clipboard_sync"] is False
    assert profile["auto_launch"] is True
    assert profile["color_scheme"] == "dark"
    assert profile["launch_args"] == ["--private-window"]
    assert profile["notes"] == "Imported notes"
    assert profile["tags"] == [{"tag": "imported", "color": "#2563eb"}]
    assert profile["status"] == "stopped"
    assert profile["vnc_ws_port"] is None
    assert profile["automation_url"] is None
    response_text = resp.text
    assert "super-secret-cookie-value" not in response_text
    assert "super-secret-local-storage" not in response_text
    assert "runtime-secret" not in response_text
    assert "viewer-secret" not in response_text
    assert "wallet-secret" not in response_text
    assert "order-secret" not in response_text
    assert "task-secret" not in response_text
    stored = main.db.list_profiles()
    assert len(stored) == 1
    assert stored[0]["name"] == "Imported Config"
    assert stored[0]["user_data_dir"] != "/tmp/should-not-import"


def test_import_profile_configs_reports_invalid_rows_without_creating_them(app_client: TestClient):
    resp = app_client.post(
        "/api/profiles/config/import",
        json={
            "schema_version": 1,
            "configs": [
                {"name": "Good Config", "platform": "macos"},
                {"name": "", "platform": "android"},
            ],
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["imported"] == 1
    assert data["failed"] == 1
    good, bad = data["results"]
    assert good["ok"] is True
    assert good["profile"]["name"] == "Good Config"
    assert bad["ok"] is False
    assert bad["profile"] is None
    assert any("name" in error for error in bad["errors"])
    assert any("platform" in error for error in bad["errors"])
    assert [profile["name"] for profile in app_client.get("/api/profiles").json()] == ["Good Config"]


def test_import_profile_configs_rejects_invalid_schema_without_side_effects(app_client: TestClient):
    resp = app_client.post(
        "/api/profiles/config/import",
        json={"schema_version": 2, "configs": [{"name": "Wrong Schema"}]},
    )

    assert resp.status_code == 422
    assert app_client.get("/api/profiles").json() == []


# ── Profile Status ───────────────────────────────────────────────────────────


def test_get_profile_status_stopped(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Status"})
    pid = create.json()["id"]
    resp = app_client.get(f"/api/profiles/{pid}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"


def test_get_profile_status_not_found(app_client: TestClient):
    resp = app_client.get("/api/profiles/nonexistent/status")
    assert resp.status_code == 404


# ── Launch / Stop ────────────────────────────────────────────────────────────


def test_launch_not_found(app_client: TestClient):
    resp = app_client.post("/api/profiles/nonexistent/launch")
    assert resp.status_code == 404


def test_launch_already_running(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Running"})
    pid = create.json()["id"]
    # Inject into running dict
    main.browser_mgr.running[pid] = MagicMock(spec=RunningProfile)
    resp = app_client.post(f"/api/profiles/{pid}/launch")
    assert resp.status_code == 409
    # Cleanup
    main.browser_mgr.running.pop(pid, None)


def test_launch_invalid_proxy_400(app_client: TestClient):
    """ValueError from browser_mgr.launch should map to 400."""
    create = app_client.post("/api/profiles", json={"name": "BadProxy"})
    pid = create.json()["id"]
    with patch.object(
        main.browser_mgr,
        "launch",
        new=AsyncMock(side_effect=ValueError("Invalid proxy scheme 'ftp'")),
    ):
        resp = app_client.post(f"/api/profiles/{pid}/launch")
    assert resp.status_code == 400
    assert "ftp" in resp.json()["detail"]


def test_launch_invalid_proxy_real_validation_400(app_client: TestClient):
    create = app_client.post("/api/profiles", json={
        "name": "BadProxyReal",
        "proxy": "ftp://bad:21",
    })
    pid = create.json()["id"]

    with patch.object(main.browser_mgr.vnc, "allocate", new=AsyncMock(return_value=(100, 6100))), \
         patch.object(main.browser_mgr.vnc, "start_vnc", new=AsyncMock()), \
         patch.object(main.browser_mgr.vnc, "stop_vnc", new=AsyncMock()):
        resp = app_client.post(f"/api/profiles/{pid}/launch")

    assert resp.status_code == 400
    assert "Invalid proxy scheme 'ftp'" in resp.json()["detail"]


def test_launch_failure_500(app_client: TestClient):
    """Generic exception from browser_mgr.launch should map to 500."""
    create = app_client.post("/api/profiles", json={"name": "Crash"})
    pid = create.json()["id"]
    with patch.object(
        main.browser_mgr,
        "launch",
        new=AsyncMock(side_effect=RuntimeError("Xvnc failed")),
    ):
        resp = app_client.post(f"/api/profiles/{pid}/launch")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Failed to launch browser"


def test_launch_success_response_exposes_automation_url(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "LaunchOk"})
    pid = create.json()["id"]
    running = RunningProfile(
        profile_id=pid,
        context=MagicMock(),
        display=101,
        ws_port=6101,
        engine="invisible_playwright",
    )

    with patch.object(main.browser_mgr, "launch", new=AsyncMock(return_value=running)):
        resp = app_client.post(f"/api/profiles/{pid}/launch")

    assert resp.status_code == 200
    assert resp.json() == {
        "profile_id": pid,
        "status": "running",
        "vnc_ws_port": 6101,
        "display": ":101",
        "automation_url": f"/api/profiles/{pid}/automation",
    }


def test_launch_persists_resolved_geoip_result(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "LaunchGeoIP"})
    pid = create.json()["id"]
    running = RunningProfile(
        profile_id=pid,
        context=MagicMock(),
        display=101,
        ws_port=6101,
        engine="invisible_playwright",
        resolved_geoip={
            "ip": "23.144.4.92",
            "country_code": "US",
            "timezone": "America/Los_Angeles",
            "locale": "en-US",
            "source": "ipapi.co",
        },
    )

    with patch.object(main.browser_mgr, "launch", new=AsyncMock(return_value=running)):
        resp = app_client.post(f"/api/profiles/{pid}/launch")

    assert resp.status_code == 200
    profile = app_client.get(f"/api/profiles/{pid}").json()
    assert profile["timezone"] is None
    assert profile["locale"] is None
    assert profile["last_geoip_ip"] == "23.144.4.92"
    assert profile["last_geoip_country_code"] == "US"
    assert profile["last_geoip_timezone"] == "America/Los_Angeles"
    assert profile["last_geoip_locale"] == "en-US"
    assert profile["last_geoip_source"] == "ipapi.co"
    assert profile["last_geoip_resolved_at"] is not None


def test_stop_not_running(app_client: TestClient):
    resp = app_client.post("/api/profiles/nonexistent/stop")
    assert resp.status_code == 404


def test_stop_success_calls_manager_and_returns_ok(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "StopOk"})
    pid = create.json()["id"]
    main.browser_mgr.running[pid] = MagicMock(spec=RunningProfile)

    with patch.object(main.browser_mgr, "stop", new=AsyncMock()) as stop:
        resp = app_client.post(f"/api/profiles/{pid}/stop")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    stop.assert_awaited_once_with(pid)
    main.browser_mgr.running.pop(pid, None)


# ── System Status ────────────────────────────────────────────────────────────


def test_system_status(app_client: TestClient):
    # Clear any leaked running profiles from prior tests
    main.browser_mgr.running.clear()

    # Create a profile so profiles_total > 0
    app_client.post("/api/profiles", json={"name": "Status Test"})
    resp = app_client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["running_count"] == 0
    assert data["binary_version"] == "invisible-playwright"
    assert data["profiles_total"] >= 1


# ── Launch Args ─────────────────────────────────────────────────────────────


def test_profile_launch_args_default_empty(app_client: TestClient):
    resp = app_client.post("/api/profiles", json={"name": "NoArgs"})
    assert resp.status_code == 201
    assert resp.json()["launch_args"] == []


def test_profile_launch_args_create(app_client: TestClient):
    resp = app_client.post("/api/profiles", json={
        "name": "WithArgs",
        "launch_args": ["--load-extension=/data/ext", "--disable-features=Foo"],
    })
    assert resp.status_code == 201
    assert resp.json()["launch_args"] == ["--load-extension=/data/ext", "--disable-features=Foo"]


def test_profile_launch_args_update(app_client: TestClient):
    resp = app_client.post("/api/profiles", json={"name": "UpdateArgs"})
    pid = resp.json()["id"]
    resp = app_client.put(f"/api/profiles/{pid}", json={"launch_args": ["--new-flag"]})
    assert resp.status_code == 200
    assert resp.json()["launch_args"] == ["--new-flag"]


def test_profile_launch_args_get(app_client: TestClient):
    resp = app_client.post("/api/profiles", json={
        "name": "GetArgs",
        "launch_args": ["--flag"],
    })
    pid = resp.json()["id"]
    resp = app_client.get(f"/api/profiles/{pid}")
    assert resp.json()["launch_args"] == ["--flag"]


# ── Clipboard Sync Setting ──────────────────────────────────────────────────


def test_profile_clipboard_sync_default_true(app_client: TestClient):
    """New profiles should have clipboard_sync=true by default."""
    resp = app_client.post("/api/profiles", json={"name": "Clipboard Test"})
    assert resp.status_code == 201
    assert resp.json()["clipboard_sync"] is True


def test_profile_clipboard_sync_update(app_client: TestClient):
    """clipboard_sync can be toggled per profile."""
    resp = app_client.post("/api/profiles", json={"name": "Clipboard Toggle"})
    pid = resp.json()["id"]
    resp = app_client.put(f"/api/profiles/{pid}", json={"clipboard_sync": False})
    assert resp.status_code == 200
    assert resp.json()["clipboard_sync"] is False
    resp = app_client.put(f"/api/profiles/{pid}", json={"clipboard_sync": True})
    assert resp.json()["clipboard_sync"] is True


# ── Clipboard ────────────────────────────────────────────────────────────────


def test_set_clipboard_not_running(app_client: TestClient):
    resp = app_client.post("/api/profiles/nonexistent/clipboard", json={"text": "hello"})
    assert resp.status_code == 404


def test_get_clipboard_not_running(app_client: TestClient):
    resp = app_client.get("/api/profiles/nonexistent/clipboard")
    assert resp.status_code == 404


def test_set_clipboard_success(app_client: TestClient):
    """Mock a running profile and patch xclip subprocess."""
    create = app_client.post("/api/profiles", json={"name": "Clip"})
    pid = create.json()["id"]

    # Inject mock running profile
    mock_running = MagicMock(spec=RunningProfile)
    mock_running.display = 100
    mock_running.engine = "invisible_playwright"
    main.browser_mgr.running[pid] = mock_running

    # Mock asyncio.create_subprocess_exec to avoid actual xclip
    mock_proc = AsyncMock()
    mock_proc.returncode = None
    mock_proc.stdin = MagicMock()
    mock_proc.stdin.write = MagicMock()
    mock_proc.stdin.drain = AsyncMock()
    mock_proc.stdin.close = MagicMock()

    with patch("backend.main.asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
        resp = app_client.post(f"/api/profiles/{pid}/clipboard", json={"text": "test clipboard"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    # Cleanup
    main.browser_mgr.running.pop(pid, None)


def test_get_clipboard_from_page(app_client: TestClient):
    """Mock running profile with a page that has clipboard text."""
    create = app_client.post("/api/profiles", json={"name": "ClipRead"})
    pid = create.json()["id"]

    # Mock page with clipboard text
    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value="copied text")

    mock_context = MagicMock()
    mock_context.pages = [mock_page]

    mock_running = MagicMock(spec=RunningProfile)
    mock_running.display = 100
    mock_running.engine = "invisible_playwright"
    mock_running.context = mock_context
    main.browser_mgr.running[pid] = mock_running

    resp = app_client.get(f"/api/profiles/{pid}/clipboard")
    assert resp.status_code == 200
    assert resp.json()["text"] == "copied text"

    # Cleanup
    main.browser_mgr.running.pop(pid, None)


# ── Response shape ───────────────────────────────────────────────────────────


def test_profile_response_has_status_field(app_client: TestClient):
    app_client.post("/api/profiles", json={"name": "Shape"})
    resp = app_client.get("/api/profiles")
    for profile in resp.json():
        assert "status" in profile
        assert profile["status"] in ("running", "stopped")


def test_profile_response_has_automation_url_field(app_client: TestClient):
    """Stopped profiles should have automation_url=null."""
    app_client.post("/api/profiles", json={"name": "AutomationShape"})
    resp = app_client.get("/api/profiles")
    for profile in resp.json():
        assert "automation_url" in profile
        if profile["status"] == "stopped":
            assert profile["automation_url"] is None


def test_profile_responses_do_not_expose_cdp_url(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "NoCdpSurface"})
    pid = create.json()["id"]

    list_data = app_client.get("/api/profiles").json()
    profile_data = app_client.get(f"/api/profiles/{pid}").json()
    status_data = app_client.get(f"/api/profiles/{pid}/status").json()

    assert all("cdp_url" not in profile for profile in list_data)
    assert "cdp_url" not in profile_data
    assert "cdp_url" not in status_data
    assert status_data["automation_url"] is None


def test_running_profile_exposes_automation_url_only(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationRunning"})
    pid = create.json()["id"]

    mock_running = MagicMock(spec=RunningProfile)
    mock_running.display = 100
    mock_running.ws_port = 6100
    mock_running.engine = "invisible_playwright"
    mock_running.profile_id = pid
    main.browser_mgr.running[pid] = mock_running

    resp = app_client.get(f"/api/profiles/{pid}")
    data = resp.json()
    assert data["status"] == "running"
    assert data["vnc_ws_port"] == 6100
    assert "cdp_url" not in data
    assert data["automation_url"] == f"/api/profiles/{pid}/automation"

    # Cleanup
    main.browser_mgr.running.pop(pid, None)


# ── Automation API ──────────────────────────────────────────────────────────


def _automation_running_profile(pid: str, pages: list[MagicMock] | None = None) -> MagicMock:
    context = MagicMock()
    context.pages = pages if pages is not None else []
    context.new_page = AsyncMock()
    context.add_cookies = AsyncMock()
    context.cookies = AsyncMock()

    running = MagicMock(spec=RunningProfile)
    running.profile_id = pid
    running.display = 100
    running.ws_port = 6100
    running.engine = "invisible_playwright"
    running.context = context
    running.accept_language = "en-US,en;q=0.9"
    main.browser_mgr.running[pid] = running
    return running


def _automation_page(url: str = "about:blank", title: str = "Blank") -> MagicMock:
    page = MagicMock()
    page.url = url
    page.title = AsyncMock(return_value=title)
    page.goto = AsyncMock()
    page.set_extra_http_headers = AsyncMock()
    page.evaluate = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.keyboard = MagicMock()
    page.keyboard.type = AsyncMock()
    page.on = MagicMock()
    page.screenshot = AsyncMock(return_value=b"png-bytes")
    page.close = AsyncMock()
    return page


# ── Cookie import / export ───────────────────────────────────────────────────


def test_import_cookie_json_adds_cookies_to_running_profile_without_leaking_values(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "CookieImportProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)
    cookie_value = "super-secret-cookie-value"
    cookie_domain = "sensitive.example.com"
    cookie_url = "https://example.org/account?token=hidden"

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/import",
        json={
            "format": "cloakbrowser.cookie-json.v1",
            "schema_version": 1,
            "cookies": [
                {
                    "name": "sid",
                    "value": cookie_value,
                    "domain": cookie_domain,
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                    "sameSite": "Lax",
                },
                {
                    "name": "analytics_id",
                    "value": "another-secret-cookie-value",
                    "url": cookie_url,
                    "expires": 1_893_456_000,
                },
            ],
        },
    )

    assert resp.status_code == 200
    running.context.add_cookies.assert_awaited_once_with([
        {
            "name": "sid",
            "value": cookie_value,
            "domain": cookie_domain,
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "Lax",
        },
        {
            "name": "analytics_id",
            "value": "another-secret-cookie-value",
            "url": cookie_url,
            "expires": 1_893_456_000,
            "secure": False,
            "httpOnly": False,
        },
    ])
    data = resp.json()
    assert data["profile_id"] == pid
    assert data["imported"] == 2
    assert data["summary"]["cookie_count"] == 2
    assert data["summary"]["domain_scoped_count"] == 1
    assert data["summary"]["url_scoped_count"] == 1
    response_text = str(data)
    assert cookie_value not in response_text
    assert "another-secret-cookie-value" not in response_text
    assert "sid" not in response_text
    assert "analytics_id" not in response_text
    assert cookie_domain not in response_text
    assert "token=hidden" not in response_text
    main.browser_mgr.running.pop(pid, None)


def test_import_cookie_json_requires_running_profile_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "StoppedCookieImportProfile"})
    pid = create.json()["id"]

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/import",
        json={
            "schema_version": 1,
            "cookies": [
                {
                    "name": "sid",
                    "value": "super-secret-cookie-value",
                    "domain": "sensitive.example.com",
                }
            ],
        },
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Profile not running"}
    assert "super-secret-cookie-value" not in resp.text
    assert "sensitive.example.com" not in resp.text


def test_import_cookie_json_rejects_invalid_document_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "InvalidCookieImportProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/import",
        json={
            "schema_version": 1,
            "cookies": [
                {
                    "name": "sid",
                    "value": "super-secret-cookie-value",
                }
            ],
        },
    )

    assert resp.status_code == 422
    assert resp.json() == {"detail": "Invalid cookie JSON document"}
    running.context.add_cookies.assert_not_called()
    assert "super-secret-cookie-value" not in resp.text
    assert "sid" not in resp.text
    main.browser_mgr.running.pop(pid, None)


def test_import_cookie_json_rejects_invalid_request_shape_without_echoing_input(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "InvalidCookieImportRequestShapeProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)

    for payload in (
        [],
        ["sensitive.example.com", "sid", "super-secret-cookie-value"],
        "sensitive.example.com sid super-secret-cookie-value",
    ):
        resp = app_client.post(
            f"/api/profiles/{pid}/cookies/import",
            json=payload,
        )

        assert resp.status_code == 422
        assert resp.json() == {"detail": "Invalid cookie JSON document"}

    running.context.add_cookies.assert_not_called()
    assert "super-secret-cookie-value" not in resp.text
    assert "sensitive.example.com" not in resp.text
    assert "sid" not in resp.text
    main.browser_mgr.running.pop(pid, None)


def test_import_cookie_json_add_cookies_failure_uses_fixed_error_without_leaking_payload(
    app_client: TestClient,
    caplog: pytest.LogCaptureFixture,
):
    create = app_client.post("/api/profiles", json={"name": "FailingCookieImportProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)
    running.context.add_cookies.side_effect = RuntimeError(
        "super-secret-cookie-value sensitive.example.com"
    )
    caplog.set_level("WARNING", logger="invisible_browser.manager")

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/import",
        json={
            "schema_version": 1,
            "cookies": [
                {
                    "name": "sid",
                    "value": "super-secret-cookie-value",
                    "domain": "sensitive.example.com",
                }
            ],
        },
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "Cookie import failed"}
    assert "super-secret-cookie-value" not in resp.text
    assert "sensitive.example.com" not in resp.text
    assert "super-secret-cookie-value" not in caplog.text
    assert "sensitive.example.com" not in caplog.text
    main.browser_mgr.running.pop(pid, None)


def test_import_cookie_netscape_adds_cookies_to_running_profile_without_leaking_values(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "NetscapeCookieImportProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)
    text = "\n".join(
        [
            "# Netscape HTTP Cookie File",
            ".sensitive.example.com\tTRUE\t/\tTRUE\t1893456000\tsid\tsuper-secret-cookie-value",
            "#HttpOnly_example.org\tFALSE\t/account\tFALSE\t0\tanalytics_id\tanother-secret-cookie-value",
        ]
    )

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/import/netscape",
        json={"text": text},
    )

    assert resp.status_code == 200
    running.context.add_cookies.assert_awaited_once_with([
        {
            "name": "sid",
            "value": "super-secret-cookie-value",
            "domain": ".sensitive.example.com",
            "path": "/",
            "expires": 1_893_456_000,
            "secure": True,
            "httpOnly": False,
        },
        {
            "name": "analytics_id",
            "value": "another-secret-cookie-value",
            "domain": "example.org",
            "path": "/account",
            "expires": 0,
            "secure": False,
            "httpOnly": True,
        },
    ])
    data = resp.json()
    assert data["profile_id"] == pid
    assert data["imported"] == 2
    assert data["summary"] == {
        "format": "netscape-cookie-file",
        "cookie_count": 2,
        "secure_count": 1,
        "session_cookie_count": 1,
        "persistent_cookie_count": 1,
        "http_only_count": 1,
    }
    response_text = str(data)
    assert "super-secret-cookie-value" not in response_text
    assert "another-secret-cookie-value" not in response_text
    assert "sid" not in response_text
    assert "analytics_id" not in response_text
    assert "sensitive.example.com" not in response_text
    main.browser_mgr.running.pop(pid, None)


def test_import_cookie_netscape_rejects_malformed_text_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "InvalidNetscapeCookieImportProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/import/netscape",
        json={"text": "sensitive.example.com\tTRUE\t/\tTRUE\t1893456000\tsid"},
    )

    assert resp.status_code == 422
    assert resp.json() == {"detail": "Invalid Netscape cookie document"}
    running.context.add_cookies.assert_not_called()
    assert "sensitive.example.com" not in resp.text
    assert "sid" not in resp.text
    main.browser_mgr.running.pop(pid, None)


def test_import_cookie_netscape_rejects_invalid_request_shape_without_echoing_input(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "InvalidNetscapeCookieRequestShapeProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)

    for payload in (
        {},
        {"text": ""},
        {"text": ["sensitive.example.com", "sid", "super-secret-cookie-value"]},
        {"text": {"raw": "sensitive.example.com sid super-secret-cookie-value"}},
    ):
        resp = app_client.post(
            f"/api/profiles/{pid}/cookies/import/netscape",
            json=payload,
        )

        assert resp.status_code == 422
        assert resp.json() == {"detail": "Invalid Netscape cookie document"}

    running.context.add_cookies.assert_not_called()
    assert "super-secret-cookie-value" not in resp.text
    assert "sensitive.example.com" not in resp.text
    assert "sid" not in resp.text
    main.browser_mgr.running.pop(pid, None)


def test_import_cookie_netscape_requires_running_profile_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "StoppedNetscapeCookieImportProfile"})
    pid = create.json()["id"]

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/import/netscape",
        json={
            "text": ".sensitive.example.com\tTRUE\t/\tTRUE\t1893456000\tsid\tsuper-secret-cookie-value"
        },
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Profile not running"}
    assert "super-secret-cookie-value" not in resp.text
    assert "sensitive.example.com" not in resp.text


def test_import_cookie_netscape_add_cookies_failure_uses_fixed_error_without_leaking_payload(
    app_client: TestClient,
    caplog: pytest.LogCaptureFixture,
):
    create = app_client.post("/api/profiles", json={"name": "FailingNetscapeCookieImportProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)
    running.context.add_cookies.side_effect = RuntimeError(
        "super-secret-cookie-value sensitive.example.com"
    )
    caplog.set_level("WARNING", logger="invisible_browser.manager")

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/import/netscape",
        json={
            "text": ".sensitive.example.com\tTRUE\t/\tTRUE\t1893456000\tsid\tsuper-secret-cookie-value"
        },
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "Cookie import failed"}
    assert "super-secret-cookie-value" not in resp.text
    assert "sensitive.example.com" not in resp.text
    assert "super-secret-cookie-value" not in caplog.text
    assert "sensitive.example.com" not in caplog.text
    main.browser_mgr.running.pop(pid, None)


def test_export_cookie_json_requires_explicit_confirmation_without_reading_context(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "CookieExportConfirmProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/export",
        json={"confirm_export": False},
    )

    assert resp.status_code == 422
    assert resp.json() == {"detail": "Cookie export requires explicit confirmation"}
    running.context.cookies.assert_not_called()
    assert _audit_events_except("profile.created") == []
    main.browser_mgr.running.pop(pid, None)


def test_export_cookie_json_rejects_coerced_confirmation_without_reading_context(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "CookieExportCoercedConfirmProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)

    for confirm_export in ("true", "yes", 1):
        resp = app_client.post(
            f"/api/profiles/{pid}/cookies/export",
            json={"confirm_export": confirm_export},
        )

        assert resp.status_code == 422

    running.context.cookies.assert_not_called()
    assert _audit_events_except("profile.created") == []
    main.browser_mgr.running.pop(pid, None)


def test_export_cookie_json_returns_document_and_writes_redacted_audit(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "CookieExportProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)
    cookie_value = "super-secret-cookie-value"
    cookie_domain = "sensitive.example.com"
    cookie_url = "https://example.org/account?token=hidden"
    running.context.cookies.return_value = [
        {
            "name": "sid",
            "value": cookie_value,
            "domain": cookie_domain,
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "Lax",
        },
        {
            "name": "analytics_id",
            "value": "another-secret-cookie-value",
            "url": cookie_url,
            "expires": 1_893_456_000,
        },
    ]

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/export",
        json={"confirm_export": True},
    )

    assert resp.status_code == 200
    running.context.cookies.assert_awaited_once()
    data = resp.json()
    assert data["profile_id"] == pid
    assert data["exported"] == 2
    assert data["summary"]["cookie_count"] == 2
    assert data["summary"]["domain_scoped_count"] == 1
    assert data["summary"]["url_scoped_count"] == 1
    assert data["document"]["format"] == "cloakbrowser.cookie-json.v1"
    assert data["document"]["schema_version"] == 1
    assert data["document"]["profile_id"] == pid
    assert data["document"]["cookies"][0]["value"] == cookie_value
    assert data["document"]["cookies"][1]["url"] == cookie_url

    events = _audit_events_of_type("cookie.exported")
    assert [event["event_type"] for event in events] == ["cookie.exported"]
    assert events[0]["actor_type"] == "local_admin"
    assert events[0]["profile_id"] == pid
    assert events[0]["runtime_session_id"] is None
    assert events[0]["external_session_id"] is None
    assert events[0]["metadata"] == {
        "format": "cloakbrowser.cookie-json.v1",
        "schema_version": 1,
        "total_count": 2,
        "domain_scoped_count": 1,
        "url_scoped_count": 1,
        "secure_count": 1,
        "http_only_count": 1,
        "session_count": 1,
        "persistent_count": 1,
        "same_site_counts": {"Strict": 0, "Lax": 1, "None": 0, "unset": 1},
    }
    audit_text = json.dumps(events, sort_keys=True)
    assert cookie_value not in audit_text
    assert "another-secret-cookie-value" not in audit_text
    assert "sid" not in audit_text
    assert "analytics_id" not in audit_text
    assert cookie_domain not in audit_text
    assert "token=hidden" not in audit_text
    main.browser_mgr.running.pop(pid, None)


def test_export_cookie_json_requires_running_profile(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "StoppedCookieExportProfile"})
    pid = create.json()["id"]

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/export",
        json={"confirm_export": True},
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Profile not running"}
    assert _audit_events_except("profile.created") == []


def test_export_cookie_json_context_failure_uses_fixed_error_without_audit_or_leak(
    app_client: TestClient,
    caplog: pytest.LogCaptureFixture,
):
    create = app_client.post("/api/profiles", json={"name": "FailingCookieExportProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)
    running.context.cookies.side_effect = RuntimeError("super-secret-cookie-value sensitive.example.com")
    caplog.set_level("WARNING", logger="invisible_browser.manager")

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/export",
        json={"confirm_export": True},
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "Cookie export failed"}
    assert _audit_events_except("profile.created") == []
    assert "super-secret-cookie-value" not in resp.text
    assert "sensitive.example.com" not in resp.text
    assert "super-secret-cookie-value" not in caplog.text
    assert "sensitive.example.com" not in caplog.text
    main.browser_mgr.running.pop(pid, None)


def test_export_cookie_netscape_requires_explicit_confirmation_without_reading_context(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "NetscapeCookieExportConfirmProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/export/netscape",
        json={"confirm_export": False},
    )

    assert resp.status_code == 422
    assert resp.json() == {"detail": "Cookie export requires explicit confirmation"}
    running.context.cookies.assert_not_called()
    assert _audit_events_except("profile.created") == []
    main.browser_mgr.running.pop(pid, None)


def test_export_cookie_netscape_rejects_coerced_confirmation_without_reading_context(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "NetscapeCookieExportCoercedConfirmProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)

    for confirm_export in ("true", "yes", 1):
        resp = app_client.post(
            f"/api/profiles/{pid}/cookies/export/netscape",
            json={"confirm_export": confirm_export},
        )

        assert resp.status_code == 422

    running.context.cookies.assert_not_called()
    assert _audit_events_except("profile.created") == []
    main.browser_mgr.running.pop(pid, None)


def test_export_cookie_netscape_returns_text_and_writes_redacted_audit(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "NetscapeCookieExportProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)
    running.context.cookies.return_value = [
        {
            "name": "sid",
            "value": "super-secret-cookie-value",
            "domain": ".sensitive.example.com",
            "path": "/",
            "expires": 1_893_456_000,
            "secure": True,
        },
        {
            "name": "acctid",
            "value": "session-secret",
            "url": "https://app.example.org/dashboard?token=hidden#frag",
            "path": "/dashboard",
            "httpOnly": True,
        },
    ]

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/export/netscape",
        json={"confirm_export": True},
    )

    assert resp.status_code == 200
    running.context.cookies.assert_awaited_once()
    data = resp.json()
    assert data["profile_id"] == pid
    assert data["exported"] == 2
    assert data["summary"] == {
        "format": "netscape-cookie-file",
        "cookie_count": 2,
        "secure_count": 1,
        "session_cookie_count": 1,
        "persistent_cookie_count": 1,
        "http_only_count": 1,
    }
    assert data["text"].splitlines() == [
        "# Netscape HTTP Cookie File",
        ".sensitive.example.com\tTRUE\t/\tTRUE\t1893456000\tsid\tsuper-secret-cookie-value",
        "#HttpOnly_app.example.org\tFALSE\t/dashboard\tFALSE\t0\tacctid\tsession-secret",
    ]
    assert "token=hidden" not in data["text"]
    assert "#frag" not in data["text"]

    events = _audit_events_of_type("cookie.exported")
    assert [event["event_type"] for event in events] == ["cookie.exported"]
    assert events[0]["actor_type"] == "local_admin"
    assert events[0]["profile_id"] == pid
    assert events[0]["metadata"] == {
        "format": "netscape-cookie-file",
        "total_count": 2,
        "secure_count": 1,
        "session_count": 1,
        "persistent_count": 1,
        "http_only_count": 1,
    }
    audit_text = json.dumps(events, sort_keys=True)
    assert "super-secret-cookie-value" not in audit_text
    assert "session-secret" not in audit_text
    assert "sid" not in audit_text
    assert "acctid" not in audit_text
    assert "sensitive.example.com" not in audit_text
    assert "token=hidden" not in audit_text
    main.browser_mgr.running.pop(pid, None)


def test_export_cookie_netscape_requires_running_profile(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "StoppedNetscapeCookieExportProfile"})
    pid = create.json()["id"]

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/export/netscape",
        json={"confirm_export": True},
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Profile not running"}
    assert _audit_events_except("profile.created") == []


def test_export_cookie_netscape_context_failure_uses_fixed_error_without_audit_or_leak(
    app_client: TestClient,
    caplog: pytest.LogCaptureFixture,
):
    create = app_client.post("/api/profiles", json={"name": "FailingNetscapeCookieExportProfile"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)
    running.context.cookies.side_effect = RuntimeError("super-secret-cookie-value sensitive.example.com")
    caplog.set_level("WARNING", logger="invisible_browser.manager")

    resp = app_client.post(
        f"/api/profiles/{pid}/cookies/export/netscape",
        json={"confirm_export": True},
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "Cookie export failed"}
    assert _audit_events_except("profile.created") == []
    assert "super-secret-cookie-value" not in resp.text
    assert "sensitive.example.com" not in resp.text
    assert "super-secret-cookie-value" not in caplog.text
    assert "sensitive.example.com" not in caplog.text
    main.browser_mgr.running.pop(pid, None)


def test_export_profile_bundle_returns_config_only_manifest_without_sensitive_fields(app_client: TestClient):
    create = app_client.post(
        "/api/profiles",
        json={
            "name": "Bundle API Profile",
            "proxy": "http://user:super-secret-proxy-password@bundle.example:8080",
            "platform": "macos",
            "screen_width": 1440,
            "screen_height": 900,
            "tags": [{"tag": "bundle", "color": "#2563eb"}],
        },
    )
    pid = create.json()["id"]

    resp = app_client.post(f"/api/profiles/{pid}/bundle/export", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["profile_id"] == pid
    bundle = data["bundle"]
    assert bundle["format"] == "cloakbrowser.profile-bundle.v1"
    assert bundle["schema_version"] == 1
    assert bundle["profile"]["config"]["name"] == "Bundle API Profile"
    assert bundle["profile"]["config"]["proxy"] == "http://bundle.example:8080"
    assert bundle["profile"]["config"]["tags"] == [{"tag": "bundle", "color": "#2563eb"}]
    assert bundle["cookies"] == {
        "included": False,
        "format": "cloakbrowser.cookie-json.v1",
        "schema_version": 1,
        "summary": {"cookie_count": 0},
    }
    assert bundle["local_storage"] == {"included": False, "origin_count": 0}
    assert bundle["profile_dir"]["included"] is False
    assert bundle["profile_dir"]["archive"] is None
    assert bundle["metadata"]["source_profile_id"] == pid
    assert bundle["metadata"]["sensitive_proxy_included"] is False
    assert bundle["metadata"]["cookies_included"] is False
    assert bundle["metadata"]["local_storage_included"] is False
    assert bundle["metadata"]["profile_dir_archive_included"] is False

    response_text = resp.text
    assert "super-secret-proxy-password" not in response_text
    assert "user_data_dir" not in response_text
    assert "automation_url" not in response_text
    assert "vnc_ws_port" not in response_text
    assert "viewer_token" not in response_text
    assert "runtime_session" not in response_text
    assert "wallet" not in response_text
    assert "order" not in response_text
    assert "payment" not in response_text
    assert _audit_events_except("profile.created") == []


def test_export_profile_bundle_can_include_sensitive_proxy_only_when_explicit(app_client: TestClient):
    create = app_client.post(
        "/api/profiles",
        json={
            "name": "Bundle Sensitive Proxy",
            "proxy": "http://user:super-secret-proxy-password@bundle.example:8080",
        },
    )
    pid = create.json()["id"]

    resp = app_client.post(
        f"/api/profiles/{pid}/bundle/export",
        json={"include_sensitive_proxy": True},
    )

    assert resp.status_code == 200
    bundle = resp.json()["bundle"]
    assert bundle["profile"]["config"]["proxy"] == (
        "http://user:super-secret-proxy-password@bundle.example:8080"
    )
    assert bundle["metadata"]["sensitive_proxy_included"] is True


def test_export_profile_bundle_rejects_coerced_sensitive_flag_without_echoing_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Bundle Coerced Flag"})
    pid = create.json()["id"]

    resp = app_client.post(
        f"/api/profiles/{pid}/bundle/export",
        json={
            "include_sensitive_proxy": "true",
            "cookies": [{"value": "super-secret-cookie-value"}],
            "user_data_dir": "/data/profiles/secret-path",
        },
    )

    assert resp.status_code == 422
    assert resp.json() == {"detail": "Invalid profile bundle export request"}
    assert "super-secret-cookie-value" not in resp.text
    assert "/data/profiles/secret-path" not in resp.text


def test_export_profile_bundle_requires_existing_profile(app_client: TestClient):
    resp = app_client.post("/api/profiles/missing/bundle/export", json={})

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Profile not found"}


def test_export_profile_bundle_cookie_bundle_requires_explicit_confirmation_without_reading_context(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "Bundle Cookie Confirm"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)

    resp = app_client.post(
        f"/api/profiles/{pid}/bundle/export",
        json={"include_cookies": True, "confirm_cookie_export": False},
    )

    assert resp.status_code == 422
    assert resp.json() == {"detail": "Profile bundle cookie export requires explicit confirmation"}
    running.context.cookies.assert_not_called()
    assert _audit_events_except("profile.created") == []
    main.browser_mgr.running.pop(pid, None)


def test_export_profile_bundle_cookie_bundle_rejects_coerced_flags_without_reading_context(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "Bundle Cookie Coerced"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)

    for payload in (
        {"include_cookies": "true", "confirm_cookie_export": True},
        {"include_cookies": True, "confirm_cookie_export": "true"},
    ):
        resp = app_client.post(f"/api/profiles/{pid}/bundle/export", json=payload)
        assert resp.status_code == 422
        assert resp.json() == {"detail": "Invalid profile bundle export request"}

    running.context.cookies.assert_not_called()
    assert _audit_events_except("profile.created") == []
    main.browser_mgr.running.pop(pid, None)


def test_export_profile_bundle_cookie_bundle_requires_running_profile(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Stopped Bundle Cookie"})
    pid = create.json()["id"]

    resp = app_client.post(
        f"/api/profiles/{pid}/bundle/export",
        json={"include_cookies": True, "confirm_cookie_export": True},
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Profile not running"}
    assert _audit_events_except("profile.created") == []


def test_export_profile_bundle_cookie_bundle_embeds_cookie_json_and_writes_redacted_audit(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "Bundle Cookie Export"})
    pid = create.json()["id"]
    running = _automation_running_profile(pid)
    running.context.cookies.return_value = [
        {
            "name": "sid",
            "value": "super-secret-cookie-value",
            "domain": "sensitive.example.com",
            "path": "/",
            "secure": True,
            "httpOnly": True,
        }
    ]

    resp = app_client.post(
        f"/api/profiles/{pid}/bundle/export",
        json={"include_cookies": True, "confirm_cookie_export": True},
    )

    assert resp.status_code == 200
    running.context.cookies.assert_awaited_once()
    data = resp.json()
    bundle = data["bundle"]
    assert bundle["cookies"]["included"] is True
    assert bundle["cookies"]["format"] == "cloakbrowser.cookie-json.v1"
    assert bundle["cookies"]["schema_version"] == 1
    assert bundle["cookies"]["summary"]["cookie_count"] == 1
    assert bundle["cookies"]["document"]["cookies"][0]["value"] == "super-secret-cookie-value"
    assert bundle["metadata"]["cookies_included"] is True

    events = _audit_events_of_type("profile_bundle.cookie_exported")
    assert [event["event_type"] for event in events] == ["profile_bundle.cookie_exported"]
    assert events[0]["actor_type"] == "local_admin"
    assert events[0]["profile_id"] == pid
    audit_text = json.dumps(events, sort_keys=True)
    assert "super-secret-cookie-value" not in audit_text
    assert "sid" not in audit_text
    assert "sensitive.example.com" not in audit_text
    main.browser_mgr.running.pop(pid, None)


def test_export_profile_bundle_local_storage_requires_explicit_confirmation_without_reading_page(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "Bundle LocalStorage Confirm"})
    pid = create.json()["id"]
    page = _automation_page(url="https://app.example.com/dashboard?token=hidden#frag")
    _automation_running_profile(pid, pages=[page])

    resp = app_client.post(
        f"/api/profiles/{pid}/bundle/export",
        json={"include_local_storage": True, "confirm_local_storage_export": False},
    )

    assert resp.status_code == 422
    assert resp.json() == {"detail": "Profile bundle local storage export requires explicit confirmation"}
    page.evaluate.assert_not_called()
    assert _audit_events_except("profile.created") == []
    main.browser_mgr.running.pop(pid, None)


def test_export_profile_bundle_local_storage_rejects_coerced_flags_without_reading_page(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "Bundle LocalStorage Coerced"})
    pid = create.json()["id"]
    page = _automation_page(url="https://app.example.com/dashboard")
    _automation_running_profile(pid, pages=[page])

    for payload in (
        {"include_local_storage": "true", "confirm_local_storage_export": True},
        {"include_local_storage": True, "confirm_local_storage_export": "true"},
    ):
        resp = app_client.post(f"/api/profiles/{pid}/bundle/export", json=payload)
        assert resp.status_code == 422
        assert resp.json() == {"detail": "Invalid profile bundle export request"}

    page.evaluate.assert_not_called()
    assert _audit_events_except("profile.created") == []
    main.browser_mgr.running.pop(pid, None)


def test_export_profile_bundle_local_storage_requires_running_profile(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "Stopped Bundle LocalStorage"})
    pid = create.json()["id"]

    resp = app_client.post(
        f"/api/profiles/{pid}/bundle/export",
        json={"include_local_storage": True, "confirm_local_storage_export": True},
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Profile not running"}
    assert _audit_events_except("profile.created") == []


def test_export_profile_bundle_local_storage_rejects_pages_without_safe_origin(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "Blank Bundle LocalStorage"})
    pid = create.json()["id"]
    page = _automation_page(url="about:blank")
    _automation_running_profile(pid, pages=[page])

    resp = app_client.post(
        f"/api/profiles/{pid}/bundle/export",
        json={"include_local_storage": True, "confirm_local_storage_export": True},
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "Local storage origin unavailable"}
    page.evaluate.assert_not_called()
    assert "about:blank" not in resp.text
    assert _audit_events_except("profile.created") == []
    main.browser_mgr.running.pop(pid, None)


def test_export_profile_bundle_local_storage_embeds_current_origin_entries_and_redacted_audit(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "Bundle LocalStorage Export"})
    pid = create.json()["id"]
    page = _automation_page(url="https://app.example.com/dashboard?token=hidden#frag")
    page.evaluate.return_value = [
        {"key": "authToken", "value": "super-secret-local-storage-value"},
        {"key": "theme", "value": "dark"},
    ]
    _automation_running_profile(pid, pages=[page])

    resp = app_client.post(
        f"/api/profiles/{pid}/bundle/export",
        json={"include_local_storage": True, "confirm_local_storage_export": True},
    )

    assert resp.status_code == 200
    page.evaluate.assert_awaited_once()
    expression = page.evaluate.await_args.args[0]
    assert "localStorage" in expression
    assert "token=hidden" not in expression
    data = resp.json()
    bundle = data["bundle"]
    assert bundle["local_storage"] == {
        "included": True,
        "format": "cloakbrowser.local-storage.v1",
        "schema_version": 1,
        "origin": "https://app.example.com",
        "origin_count": 1,
        "entry_count": 2,
        "entries": [
            {"key": "authToken", "value": "super-secret-local-storage-value"},
            {"key": "theme", "value": "dark"},
        ],
    }
    assert bundle["metadata"]["local_storage_included"] is True

    events = _audit_events_of_type("profile_bundle.local_storage_exported")
    assert [event["event_type"] for event in events] == ["profile_bundle.local_storage_exported"]
    assert events[0]["actor_type"] == "local_admin"
    assert events[0]["profile_id"] == pid
    metadata = events[0]["metadata"]
    assert metadata["format"] == "cloakbrowser.local-storage.v1"
    assert metadata["schema_version"] == 1
    assert metadata["entry_count"] == 2
    assert metadata["total_value_bytes"] == len("super-secret-local-storage-value") + len("dark")
    assert "origin_hash" in metadata
    audit_text = json.dumps(events, sort_keys=True)
    assert "super-secret-local-storage-value" not in audit_text
    assert "authToken" not in audit_text
    assert "app.example.com" not in audit_text
    assert "token=hidden" not in audit_text
    main.browser_mgr.running.pop(pid, None)


def test_import_profile_bundle_creates_new_profile_from_config_only_manifest(app_client: TestClient):
    source = app_client.post(
        "/api/profiles",
        json={
            "name": "Bundle Import Source",
            "proxy": "http://user:super-secret-proxy-password@bundle.example:8080",
            "platform": "macos",
            "screen_width": 1440,
            "screen_height": 900,
            "tags": [{"tag": "bundle", "color": "#2563eb"}],
        },
    ).json()
    exported = app_client.post(
        f"/api/profiles/{source['id']}/bundle/export",
        json={"include_sensitive_proxy": True},
    ).json()

    bundle = exported["bundle"]
    bundle["profile"]["config"]["user_data_dir"] = "/data/profiles/should-not-import"
    bundle["profile"]["config"]["status"] = "running"
    bundle["profile"]["config"]["automation_url"] = "http://127.0.0.1:9222"
    bundle["cookies"] = {
        "included": True,
        "cookies": [{"name": "sid", "value": "super-secret-cookie-value"}],
    }
    bundle["local_storage"] = {
        "included": True,
        "entries": [{"key": "token", "value": "local-storage-secret"}],
    }
    bundle["profile_dir"] = {
        "included": True,
        "archive": "profile-dir-secret",
    }
    bundle["metadata"]["wallet"] = {"balance": 100}
    bundle["metadata"]["order_id"] = "order-secret"
    bundle["metadata"]["viewer_token"] = "viewer-token-secret"

    resp = app_client.post("/api/profiles/bundle/import", json={"bundle": bundle})

    assert resp.status_code == 200
    data = resp.json()
    assert data["schema_version"] == 1
    assert data["imported"] == 1
    assert data["failed"] == 0
    result = data["results"][0]
    assert result["ok"] is True
    assert result["errors"] == []
    imported = result["profile"]
    assert imported["id"] != source["id"]
    assert imported["name"] == "Bundle Import Source"
    assert imported["proxy"] == "http://user:super-secret-proxy-password@bundle.example:8080"
    assert imported["platform"] == "macos"
    assert imported["screen_width"] == 1440
    assert imported["screen_height"] == 900
    assert imported["tags"] == [{"tag": "bundle", "color": "#2563eb"}]
    assert imported["status"] == "stopped"
    assert imported["automation_url"] is None
    assert imported["user_data_dir"] != "/data/profiles/should-not-import"

    response_text = resp.text
    assert "super-secret-cookie-value" not in response_text
    assert "local-storage-secret" not in response_text
    assert "profile-dir-secret" not in response_text
    assert "order-secret" not in response_text
    assert "viewer-token-secret" not in response_text


def test_import_profile_bundle_rejects_invalid_bundle_without_echoing_payload(app_client: TestClient):
    resp = app_client.post(
        "/api/profiles/bundle/import",
        json={
            "bundle": {
                "format": "wrong-format",
                "schema_version": 1,
                "profile": {
                    "config": {
                        "name": "",
                        "cookies": [{"value": "super-secret-cookie-value"}],
                    }
                },
                "profile_dir": {"archive": "profile-dir-secret"},
            }
        },
    )

    assert resp.status_code == 422
    assert resp.json() == {"detail": "Invalid profile bundle document"}
    assert "super-secret-cookie-value" not in resp.text
    assert "profile-dir-secret" not in resp.text


def test_automation_info_running(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationInfo"})
    pid = create.json()["id"]
    _automation_running_profile(pid)

    resp = app_client.get(f"/api/profiles/{pid}/automation")

    assert resp.status_code == 200
    assert resp.json() == {
        "profile_id": pid,
        "engine": "invisible_playwright",
        "status": "running",
        "pages_url": f"/api/profiles/{pid}/automation/pages",
    }
    main.browser_mgr.running.pop(pid, None)


def test_automation_info_not_running(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationStopped"})
    pid = create.json()["id"]

    resp = app_client.get(f"/api/profiles/{pid}/automation")

    assert resp.status_code == 404


def test_automation_pages_lists_existing_pages(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationPages"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [
        _automation_page("about:blank", "Blank"),
        _automation_page("https://example.com/", "Example"),
    ])

    resp = app_client.get(f"/api/profiles/{pid}/automation/pages")

    assert resp.status_code == 200
    data = resp.json()
    assert data["pages"][0]["index"] == 0
    assert data["pages"][0]["url"] == "about:blank"
    assert data["pages"][0]["title"] == "Blank"
    assert isinstance(data["pages"][0]["page_id"], str)
    assert data["pages"][1]["index"] == 1
    assert data["pages"][1]["url"] == "https://example.com/"
    assert data["pages"][1]["title"] == "Example"
    assert isinstance(data["pages"][1]["page_id"], str)
    assert data["pages"][0]["page_id"] != data["pages"][1]["page_id"]
    main.browser_mgr.running.pop(pid, None)


def test_automation_pages_create_new_page(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationNewPage"})
    pid = create.json()["id"]
    page = _automation_page("about:blank", "New")
    running = _automation_running_profile(pid, [])
    running.context.new_page.return_value = page
    running.context.pages = [page]

    resp = app_client.post(f"/api/profiles/{pid}/automation/pages")

    assert resp.status_code == 201
    running.context.new_page.assert_awaited_once()
    data = resp.json()
    assert data["index"] == 0
    assert data["url"] == "about:blank"
    assert data["title"] == "New"
    assert isinstance(data["page_id"], str)
    main.browser_mgr.running.pop(pid, None)


def test_automation_goto_navigates_page(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationGoto"})
    pid = create.json()["id"]
    page = _automation_page("about:blank", "Before")
    page.url = "https://example.com/"
    page.title.return_value = "Example"
    _automation_running_profile(pid, [page])

    resp = app_client.post(
        f"/api/profiles/{pid}/automation/pages/0/goto",
        json={"url": "https://example.com/", "wait_until": "domcontentloaded", "timeout_ms": 5000},
    )

    assert resp.status_code == 200
    page.set_extra_http_headers.assert_awaited_once_with({
        "Accept-Language": "en-US,en;q=0.9",
    })
    page.goto.assert_awaited_once_with(
        "https://example.com/",
        wait_until="domcontentloaded",
        timeout=5000,
    )
    data = resp.json()
    assert data["index"] == 0
    assert data["url"] == "https://example.com/"
    assert data["title"] == "Example"
    assert isinstance(data["page_id"], str)
    main.browser_mgr.running.pop(pid, None)


def test_automation_evaluate_returns_json_result(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationEval"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    page.evaluate.return_value = {"title": "Example", "ok": True}
    _automation_running_profile(pid, [page])

    resp = app_client.post(
        f"/api/profiles/{pid}/automation/pages/0/evaluate",
        json={"expression": "({ title: document.title, ok: true })"},
    )

    assert resp.status_code == 200
    page.evaluate.assert_awaited_once_with("({ title: document.title, ok: true })")
    assert resp.json() == {"result": {"title": "Example", "ok": True}}
    main.browser_mgr.running.pop(pid, None)


def test_automation_wait_for_selector_waits_and_returns_page(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationWaitSelector"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])

    resp = app_client.post(
        f"/api/profiles/{pid}/automation/pages/0/wait-for-selector",
        json={"selector": "#ready", "state": "visible", "timeout_ms": 2500},
    )

    assert resp.status_code == 200
    page.wait_for_selector.assert_awaited_once_with(
        "#ready",
        state="visible",
        timeout=2500,
    )
    data = resp.json()
    assert data["index"] == 0
    assert data["url"] == "https://example.com/"
    assert data["title"] == "Example"
    assert isinstance(data["page_id"], str)
    main.browser_mgr.running.pop(pid, None)


def test_automation_click_clicks_selector_and_returns_page(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationClick"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])

    resp = app_client.post(
        f"/api/profiles/{pid}/automation/pages/0/click",
        json={"selector": "#submit", "timeout_ms": 2500},
    )

    assert resp.status_code == 200
    page.click.assert_awaited_once_with("#submit", timeout=2500)
    data = resp.json()
    assert data["index"] == 0
    assert data["url"] == "https://example.com/"
    assert data["title"] == "Example"
    assert isinstance(data["page_id"], str)
    main.browser_mgr.running.pop(pid, None)


def test_automation_fill_fills_selector_and_returns_page(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationFill"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])

    resp = app_client.post(
        f"/api/profiles/{pid}/automation/pages/0/fill",
        json={"selector": "#email", "value": "user@example.com", "timeout_ms": 2500},
    )

    assert resp.status_code == 200
    page.fill.assert_awaited_once_with("#email", "user@example.com", timeout=2500)
    data = resp.json()
    assert data["index"] == 0
    assert data["url"] == "https://example.com/"
    assert data["title"] == "Example"
    assert isinstance(data["page_id"], str)
    main.browser_mgr.running.pop(pid, None)


def test_automation_keyboard_type_types_text_and_returns_page(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationKeyboardType"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])

    resp = app_client.post(
        f"/api/profiles/{pid}/automation/pages/0/keyboard/type",
        json={"text": "hello world", "delay_ms": 25},
    )

    assert resp.status_code == 200
    page.keyboard.type.assert_awaited_once_with("hello world", delay=25)
    data = resp.json()
    assert data["index"] == 0
    assert data["url"] == "https://example.com/"
    assert data["title"] == "Example"
    assert isinstance(data["page_id"], str)
    main.browser_mgr.running.pop(pid, None)


def test_automation_scroll_scrolls_page_and_returns_page(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationScroll"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])

    resp = app_client.post(
        f"/api/profiles/{pid}/automation/pages/0/scroll",
        json={"delta_x": 10, "delta_y": 600},
    )

    assert resp.status_code == 200
    page.evaluate.assert_awaited_once_with(
        "([deltaX, deltaY]) => window.scrollBy(deltaX, deltaY)",
        [10, 600],
    )
    data = resp.json()
    assert data["index"] == 0
    assert data["url"] == "https://example.com/"
    assert data["title"] == "Example"
    assert isinstance(data["page_id"], str)
    main.browser_mgr.running.pop(pid, None)


def test_automation_console_logs_returns_in_memory_page_logs(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationConsoleLogs"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    page.automation_console_logs = [
        {"type": "log", "text": "ready", "location": {"url": "https://example.com/app.js", "line": 4, "column": 2}},
        {"type": "error", "text": "failed", "location": {}},
    ]
    _automation_running_profile(pid, [page])

    resp = app_client.get(f"/api/profiles/{pid}/automation/pages/0/console-logs")

    assert resp.status_code == 200
    assert resp.json() == {
        "logs": [
            {
                "type": "log",
                "text": "ready",
                "location": {"url": "https://example.com/app.js", "line": 4, "column": 2},
            },
            {"type": "error", "text": "failed", "location": {}},
        ],
    }
    main.browser_mgr.running.pop(pid, None)


def test_automation_console_logs_captures_recent_console_messages(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationConsoleCapture"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])

    resp = app_client.get(f"/api/profiles/{pid}/automation/pages/0/console-logs")

    assert resp.status_code == 200
    page.on.assert_called_once()
    event_name, callback = page.on.call_args.args
    assert event_name == "console"
    for index in range(205):
        message = MagicMock()
        message.type = "log"
        message.text = f"message-{index}"
        message.location = {"url": "https://example.com/app.js", "lineNumber": index, "columnNumber": 1}
        callback(message)

    resp = app_client.get(f"/api/profiles/{pid}/automation/pages/0/console-logs")

    assert resp.status_code == 200
    logs = resp.json()["logs"]
    assert len(logs) == 200
    assert logs[0]["text"] == "message-5"
    assert logs[-1]["text"] == "message-204"
    assert logs[-1]["location"] == {
        "url": "https://example.com/app.js",
        "lineNumber": 204,
        "columnNumber": 1,
    }
    main.browser_mgr.running.pop(pid, None)


def test_automation_network_summary_redacts_urls_and_returns_recent_events(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationNetworkSummary"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])

    resp = app_client.get(f"/api/profiles/{pid}/automation/pages/0/network-summary")

    assert resp.status_code == 200
    assert page.on.call_count == 3
    event_callbacks = {call.args[0]: call.args[1] for call in page.on.call_args_list}

    request = MagicMock()
    request.method = "POST"
    request.url = "https://user:pass@example.com/api/orders?token=secret#frag"
    request.resource_type = "xhr"
    event_callbacks["request"](request)

    response = MagicMock()
    response.status = 201
    response.request = request
    event_callbacks["response"](response)

    failed_request = MagicMock()
    failed_request.method = "GET"
    failed_request.url = "https://example.com/private?authorization=secret"
    failed_request.resource_type = "document"
    failed_request.failure = "net::ERR_FAILED"
    event_callbacks["requestfailed"](failed_request)

    resp = app_client.get(f"/api/profiles/{pid}/automation/pages/0/network-summary")

    assert resp.status_code == 200
    assert resp.json() == {
        "events": [
            {
                "event": "request",
                "method": "POST",
                "url": "https://example.com/api/orders",
                "resource_type": "xhr",
                "status": None,
                "failure": None,
            },
            {
                "event": "response",
                "method": "POST",
                "url": "https://example.com/api/orders",
                "resource_type": "xhr",
                "status": 201,
                "failure": None,
            },
            {
                "event": "requestfailed",
                "method": "GET",
                "url": "https://example.com/private",
                "resource_type": "document",
                "status": None,
                "failure": "request_failed",
            },
        ],
    }
    main.browser_mgr.running.pop(pid, None)


def test_automation_network_summary_keeps_recent_redacted_events(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationNetworkRing"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])

    resp = app_client.get(f"/api/profiles/{pid}/automation/pages/0/network-summary")

    assert resp.status_code == 200
    event_callbacks = {call.args[0]: call.args[1] for call in page.on.call_args_list}
    for index in range(205):
        request = MagicMock()
        request.method = "GET"
        request.url = f"https://user:pass@example.com/items/{index}?token=secret#frag"
        request.resource_type = "fetch"
        event_callbacks["request"](request)

    resp = app_client.get(f"/api/profiles/{pid}/automation/pages/0/network-summary")

    assert resp.status_code == 200
    events = resp.json()["events"]
    assert len(events) == 200
    assert events[0]["url"] == "https://example.com/items/5"
    assert events[-1]["url"] == "https://example.com/items/204"
    assert all("token" not in event["url"] for event in events)
    assert all("user:pass" not in event["url"] for event in events)
    main.browser_mgr.running.pop(pid, None)


def test_automation_page_id_remains_stable_when_page_order_changes(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationPageId"})
    pid = create.json()["id"]
    first_page = _automation_page("https://first.example/", "First")
    second_page = _automation_page("https://second.example/", "Second")
    second_page.evaluate.return_value = "Second"
    running = _automation_running_profile(pid, [first_page, second_page])

    page_id = app_client.get(
        f"/api/profiles/{pid}/automation/pages",
    ).json()["pages"][1]["page_id"]
    running.context.pages = [second_page, first_page]

    resp = app_client.post(
        f"/api/profiles/{pid}/automation/pages/{page_id}/evaluate",
        json={"expression": "document.title"},
    )

    assert resp.status_code == 200
    second_page.evaluate.assert_awaited_once_with("document.title")
    first_page.evaluate.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_automation_screenshot_returns_png(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationScreenshot"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    page.screenshot.return_value = b"\x89PNG\r\n"
    _automation_running_profile(pid, [page])

    resp = app_client.post(
        f"/api/profiles/{pid}/automation/pages/0/screenshot",
        json={"full_page": True},
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == b"\x89PNG\r\n"
    page.screenshot.assert_awaited_once_with(type="png", full_page=True)
    main.browser_mgr.running.pop(pid, None)


def test_automation_close_page(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationClose"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])

    resp = app_client.delete(f"/api/profiles/{pid}/automation/pages/0")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    page.close.assert_awaited_once()
    main.browser_mgr.running.pop(pid, None)


def test_automation_page_not_found(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationMissingPage"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [])

    resp = app_client.post(
        f"/api/profiles/{pid}/automation/pages/0/evaluate",
        json={"expression": "document.title"},
    )

    assert resp.status_code == 404
    main.browser_mgr.running.pop(pid, None)


def test_automation_unknown_page_id_returns_404_before_listing(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "AutomationUnknownPageId"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])

    resp = app_client.post(
        f"/api/profiles/{pid}/automation/pages/not-a-page-id/evaluate",
        json={"expression": "document.title"},
    )

    assert resp.status_code == 404
    main.browser_mgr.running.pop(pid, None)


def test_create_automation_task_queues_steps_without_running_script(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskProfile"})
    pid = create.json()["id"]
    steps = [
        {"type": "open_url", "url": "https://example.com"},
        {"type": "wait", "ms": 1000},
    ]

    resp = app_client.post("/api/tasks", json={"profile_id": pid, "steps": steps})

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"]
    assert data["profile_id"] == pid
    assert data["status"] == "queued"
    assert data["steps"] == [
        {"type": "open_url"},
        {"type": "wait", "ms": 1000},
    ]
    assert data["result"] is None
    assert data["error"] is None
    assert data["created_at"] is not None
    assert data["started_at"] is None
    assert data["finished_at"] is None


def test_automation_task_create_cancel_retry_and_run_write_redacted_audit_events(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "TaskAuditProfile"})
    pid = create.json()["id"]
    page = _automation_page("about:blank", "Before")
    _automation_running_profile(pid, [page])
    secret_url = "https://sensitive.example.com/app?token=super-secret#frag"
    secret_selector = "input[name='account-token']"
    secret_value = "fill-super-secret-value"
    steps = [
        {
            "type": "open_url",
            "url": secret_url,
            "page_ref": "0",
            "wait_until": "domcontentloaded",
            "timeout_ms": 5000,
        },
        {
            "type": "fill",
            "selector": secret_selector,
            "value": secret_value,
            "page_ref": "0",
            "timeout_ms": 5000,
        },
    ]

    created = app_client.post("/api/tasks", json={"profile_id": pid, "steps": steps}).json()
    cancel_resp = app_client.post(f"/api/tasks/{created['id']}/cancel")
    retry_resp = app_client.post(f"/api/tasks/{created['id']}/retry")
    run_resp = app_client.post(f"/api/tasks/{retry_resp.json()['id']}/run")

    failing_task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "unknown", "value": "payload-super-secret"}]},
    ).json()
    fail_resp = app_client.post(f"/api/tasks/{failing_task['id']}/run")

    running_task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    main.db.update_automation_task(running_task["id"], status="running")
    cancel_requested_resp = app_client.post(f"/api/tasks/{running_task['id']}/cancel")

    assert cancel_resp.status_code == 200
    assert retry_resp.status_code == 201
    assert run_resp.status_code == 200
    assert fail_resp.status_code == 400
    assert cancel_requested_resp.status_code == 200

    events = _automation_task_audit_events()
    assert [event["event_type"] for event in events] == [
        "automation.task.created",
        "automation.task.cancelled",
        "automation.task.retried",
        "automation.task.succeeded",
        "automation.task.created",
        "automation.task.failed",
        "automation.task.created",
        "automation.task.cancel_requested",
    ]
    assert all(event["actor_type"] == "local_admin" for event in events)
    assert all(event["profile_id"] == pid for event in events)
    assert all(event["runtime_session_id"] is None for event in events)

    assert events[0]["metadata"] == {
        "task_id": created["id"],
        "status": "queued",
        "step_count": 2,
        "step_types": ["open_url", "fill"],
    }
    assert events[1]["metadata"] == {
        "task_id": created["id"],
        "previous_status": "queued",
        "status": "cancelled",
        "step_count": 2,
        "step_types": ["open_url", "fill"],
    }
    assert events[2]["metadata"] == {
        "task_id": retry_resp.json()["id"],
        "source_task_id": created["id"],
        "new_task_id": retry_resp.json()["id"],
        "status": "queued",
        "step_count": 2,
        "step_types": ["open_url", "fill"],
    }
    assert events[3]["metadata"] == {
        "task_id": retry_resp.json()["id"],
        "status": "succeeded",
        "step_count": 2,
        "step_types": ["open_url", "fill"],
        "runner_type": "api",
        "succeeded_step_count": 2,
        "failed_step_count": 0,
        "cancelled_step_count": 0,
    }
    assert events[5]["metadata"] == {
        "task_id": failing_task["id"],
        "status": "failed",
        "step_count": 1,
        "step_types": ["unknown"],
        "runner_type": "api",
        "succeeded_step_count": 0,
        "failed_step_count": 1,
        "cancelled_step_count": 0,
        "reason_code": "unsupported_step_type",
    }
    assert events[7]["metadata"] == {
        "task_id": running_task["id"],
        "previous_status": "running",
        "status": "cancel_requested",
        "step_count": 1,
        "step_types": ["wait"],
    }

    serialized_events = json.dumps(events, sort_keys=True)
    assert secret_url not in serialized_events
    assert "sensitive.example.com" not in serialized_events
    assert "super-secret" not in serialized_events
    assert "#frag" not in serialized_events
    assert secret_selector not in serialized_events
    assert secret_value not in serialized_events
    assert "payload-super-secret" not in serialized_events
    assert "steps" not in serialized_events
    assert "result" not in serialized_events
    assert "error" not in serialized_events
    assert "lease_owner" not in serialized_events
    assert "lease_expires_at" not in serialized_events
    main.browser_mgr.running.pop(pid, None)


def test_automation_task_responses_do_not_expose_worker_lease_metadata(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskLeaseRedactProfile"})
    pid = create.json()["id"]
    task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    claimed = main.db.claim_next_automation_task(lease_owner="worker-secret", lease_seconds=60)

    get_resp = app_client.get(f"/api/tasks/{task['id']}")
    list_resp = app_client.get("/api/tasks")

    assert claimed is not None
    assert claimed["lease_owner"] == "worker-secret"
    assert get_resp.status_code == 200
    assert "lease_owner" not in get_resp.json()
    assert "lease_expires_at" not in get_resp.json()
    assert "worker-secret" not in str(get_resp.json())
    assert list_resp.status_code == 200
    listed_task = next(item for item in list_resp.json()["tasks"] if item["id"] == task["id"])
    assert "lease_owner" not in listed_task
    assert "lease_expires_at" not in listed_task
    assert "worker-secret" not in str(list_resp.json())


def test_automation_task_responses_do_not_expose_renewed_or_finished_lease_metadata(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskLeaseFinishRedactProfile"})
    pid = create.json()["id"]
    task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    claimed = main.db.claim_next_automation_task(lease_owner="worker-secret", lease_seconds=60)
    renewed = main.db.renew_automation_task_lease(task["id"], lease_owner="worker-secret", lease_seconds=120)
    finished = main.db.finish_claimed_automation_task(
        task["id"],
        lease_owner="worker-secret",
        status="succeeded",
        result={"steps": [{"index": 0, "type": "wait", "status": "succeeded"}]},
        error=None,
    )

    get_resp = app_client.get(f"/api/tasks/{task['id']}")
    list_resp = app_client.get("/api/tasks")

    assert claimed is not None
    assert renewed is not None
    assert finished is not None
    assert get_resp.status_code == 200
    assert "lease_owner" not in get_resp.json()
    assert "lease_expires_at" not in get_resp.json()
    assert "worker-secret" not in str(get_resp.json())
    assert list_resp.status_code == 200
    listed_task = next(item for item in list_resp.json()["tasks"] if item["id"] == task["id"])
    assert "lease_owner" not in listed_task
    assert "lease_expires_at" not in listed_task
    assert "worker-secret" not in str(list_resp.json())


def test_automation_task_responses_redact_open_url_steps(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRedactProfile"})
    pid = create.json()["id"]
    secret_url = "https://example.com/app?token=super-secret#frag"
    steps = [
        {
            "type": "open_url",
            "url": secret_url,
            "page_ref": "0",
            "wait_until": "domcontentloaded",
            "timeout_ms": 5000,
        },
        {"type": "wait", "ms": 1},
    ]
    expected_steps = [
        {
            "type": "open_url",
            "page_ref": "0",
            "wait_until": "domcontentloaded",
            "timeout_ms": 5000,
        },
        {"type": "wait", "ms": 1},
    ]

    create_resp = app_client.post("/api/tasks", json={"profile_id": pid, "steps": steps})
    task_id = create_resp.json()["id"]
    get_resp = app_client.get(f"/api/tasks/{task_id}")
    list_resp = app_client.get("/api/tasks")
    cancel_resp = app_client.post(f"/api/tasks/{task_id}/cancel")

    assert create_resp.status_code == 201
    assert create_resp.json()["steps"] == expected_steps
    assert secret_url not in str(create_resp.json())
    assert "super-secret" not in str(create_resp.json())

    assert get_resp.status_code == 200
    assert get_resp.json()["steps"] == expected_steps
    assert secret_url not in str(get_resp.json())
    assert "super-secret" not in str(get_resp.json())

    assert list_resp.status_code == 200
    listed_task = next(task for task in list_resp.json()["tasks"] if task["id"] == task_id)
    assert listed_task["steps"] == expected_steps
    assert secret_url not in str(list_resp.json())
    assert "super-secret" not in str(list_resp.json())

    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["steps"] == expected_steps
    assert secret_url not in str(cancel_resp.json())
    assert "super-secret" not in str(cancel_resp.json())


def test_automation_task_responses_redact_wait_for_selector_steps(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskWaitForSelectorRedactProfile"})
    pid = create.json()["id"]
    selector = "#ready-token-super-secret"
    steps = [
        {
            "type": "wait_for_selector",
            "selector": selector,
            "page_ref": "0",
            "state": "attached",
            "timeout_ms": 5000,
            "note": "do-not-echo",
        },
    ]
    expected_steps = [
        {
            "type": "wait_for_selector",
            "page_ref": "0",
            "state": "attached",
            "timeout_ms": 5000,
        },
    ]

    create_resp = app_client.post("/api/tasks", json={"profile_id": pid, "steps": steps})
    task_id = create_resp.json()["id"]
    get_resp = app_client.get(f"/api/tasks/{task_id}")
    list_resp = app_client.get("/api/tasks")
    cancel_resp = app_client.post(f"/api/tasks/{task_id}/cancel")

    assert create_resp.status_code == 201
    assert create_resp.json()["steps"] == expected_steps
    assert selector not in str(create_resp.json())
    assert "super-secret" not in str(create_resp.json())
    assert "do-not-echo" not in str(create_resp.json())

    assert get_resp.status_code == 200
    assert get_resp.json()["steps"] == expected_steps
    assert selector not in str(get_resp.json())
    assert "super-secret" not in str(get_resp.json())
    assert "do-not-echo" not in str(get_resp.json())

    assert list_resp.status_code == 200
    listed_task = next(task for task in list_resp.json()["tasks"] if task["id"] == task_id)
    assert listed_task["steps"] == expected_steps
    assert selector not in str(list_resp.json())
    assert "super-secret" not in str(list_resp.json())
    assert "do-not-echo" not in str(list_resp.json())

    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["steps"] == expected_steps
    assert selector not in str(cancel_resp.json())
    assert "super-secret" not in str(cancel_resp.json())
    assert "do-not-echo" not in str(cancel_resp.json())


def test_automation_task_responses_redact_evaluate_steps(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskEvaluateRedactProfile"})
    pid = create.json()["id"]
    expression = "window.localStorage.getItem('account-token-super-secret')"
    steps = [
        {
            "type": "evaluate",
            "expression": expression,
            "page_ref": "0",
            "note": "do-not-echo",
        },
    ]
    expected_steps = [{"type": "evaluate", "page_ref": "0"}]

    create_resp = app_client.post("/api/tasks", json={"profile_id": pid, "steps": steps})
    task_id = create_resp.json()["id"]
    get_resp = app_client.get(f"/api/tasks/{task_id}")
    list_resp = app_client.get("/api/tasks")
    cancel_resp = app_client.post(f"/api/tasks/{task_id}/cancel")

    assert create_resp.status_code == 201
    assert create_resp.json()["steps"] == expected_steps
    assert expression not in str(create_resp.json())
    assert "super-secret" not in str(create_resp.json())
    assert "do-not-echo" not in str(create_resp.json())

    assert get_resp.status_code == 200
    assert get_resp.json()["steps"] == expected_steps
    assert expression not in str(get_resp.json())
    assert "super-secret" not in str(get_resp.json())
    assert "do-not-echo" not in str(get_resp.json())

    assert list_resp.status_code == 200
    listed_task = next(task for task in list_resp.json()["tasks"] if task["id"] == task_id)
    assert listed_task["steps"] == expected_steps
    assert expression not in str(list_resp.json())
    assert "super-secret" not in str(list_resp.json())
    assert "do-not-echo" not in str(list_resp.json())

    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["steps"] == expected_steps
    assert expression not in str(cancel_resp.json())
    assert "super-secret" not in str(cancel_resp.json())
    assert "do-not-echo" not in str(cancel_resp.json())


def test_automation_task_responses_redact_screenshot_steps(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskScreenshotRedactProfile"})
    pid = create.json()["id"]
    steps = [
        {
            "type": "screenshot",
            "page_ref": "0",
            "full_page": True,
            "path": "/tmp/screenshot-token-super-secret.png",
            "filename": "screenshot-token-super-secret.png",
            "base64": "png-token-super-secret",
            "note": "do-not-echo",
        },
    ]
    expected_steps = [{"type": "screenshot", "page_ref": "0", "full_page": True}]

    create_resp = app_client.post("/api/tasks", json={"profile_id": pid, "steps": steps})
    task_id = create_resp.json()["id"]
    get_resp = app_client.get(f"/api/tasks/{task_id}")
    list_resp = app_client.get("/api/tasks")
    cancel_resp = app_client.post(f"/api/tasks/{task_id}/cancel")

    assert create_resp.status_code == 201
    assert create_resp.json()["steps"] == expected_steps
    assert "super-secret" not in str(create_resp.json())
    assert "do-not-echo" not in str(create_resp.json())

    assert get_resp.status_code == 200
    assert get_resp.json()["steps"] == expected_steps
    assert "super-secret" not in str(get_resp.json())
    assert "do-not-echo" not in str(get_resp.json())

    assert list_resp.status_code == 200
    listed_task = next(task for task in list_resp.json()["tasks"] if task["id"] == task_id)
    assert listed_task["steps"] == expected_steps
    assert "super-secret" not in str(list_resp.json())
    assert "do-not-echo" not in str(list_resp.json())

    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["steps"] == expected_steps
    assert "super-secret" not in str(cancel_resp.json())
    assert "do-not-echo" not in str(cancel_resp.json())


def test_create_automation_task_persists_sanitized_screenshot_step(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskScreenshotPersistProfile"})
    pid = create.json()["id"]
    resp = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "screenshot",
                    "page_ref": "0",
                    "full_page": True,
                    "path": "/tmp/screenshot-token-super-secret.png",
                    "filename": "screenshot-token-super-secret.png",
                    "base64": "png-token-super-secret",
                    "note": "do-not-echo",
                }
            ],
        },
    )

    persisted = main.db.get_automation_task(resp.json()["id"])

    assert resp.status_code == 201
    assert persisted is not None
    assert persisted["steps"] == [{"type": "screenshot", "page_ref": "0", "full_page": True}]
    assert "super-secret" not in str(persisted["steps"])
    assert "do-not-echo" not in str(persisted["steps"])


def test_automation_task_responses_redact_persisted_result_steps(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskResultRedactProfile"})
    pid = create.json()["id"]
    secret_url = "https://example.com/app?token=super-secret#frag"
    create_resp = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "open_url", "url": secret_url}]},
    )
    task_id = create_resp.json()["id"]
    main.db.update_automation_task(
        task_id,
        status="succeeded",
        result={
            "steps": [
                {
                    "index": 0,
                    "type": "open_url",
                    "status": "succeeded",
                    "url": secret_url,
                    "payload": {"token": "super-secret"},
                }
            ],
            "raw_url": secret_url,
        },
    )
    evaluate_resp = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [{"type": "evaluate", "expression": "window.secret"}],
        },
    )
    evaluate_task_id = evaluate_resp.json()["id"]
    main.db.update_automation_task(
        evaluate_task_id,
        status="succeeded",
        result={
            "steps": [
                {
                    "index": 0,
                    "type": "evaluate",
                    "status": "succeeded",
                    "expression": "window.localStorage.getItem('super-secret')",
                    "result": {"token": "super-secret"},
                    "payload": {"token": "super-secret"},
                }
            ],
            "raw_result": {"token": "super-secret"},
        },
    )
    screenshot_resp = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [{"type": "screenshot", "full_page": True, "path": "/tmp/super-secret.png"}],
        },
    )
    screenshot_task_id = screenshot_resp.json()["id"]
    main.db.update_automation_task(
        screenshot_task_id,
        status="succeeded",
        result={
            "steps": [
                {
                    "index": 0,
                    "type": "screenshot",
                    "status": "succeeded",
                    "png": b"\x89PNG\r\nsuper-secret".hex(),
                    "base64": "c3VwZXItc2VjcmV0",
                    "path": "/tmp/super-secret.png",
                    "payload": {"token": "super-secret"},
                }
            ],
            "png": "super-secret",
            "base64": "c3VwZXItc2VjcmV0",
            "path": "/tmp/super-secret.png",
        },
    )

    get_resp = app_client.get(f"/api/tasks/{task_id}")
    evaluate_get_resp = app_client.get(f"/api/tasks/{evaluate_task_id}")
    screenshot_get_resp = app_client.get(f"/api/tasks/{screenshot_task_id}")
    list_resp = app_client.get("/api/tasks")

    assert get_resp.status_code == 200
    assert get_resp.json()["result"] == {"steps": [{"index": 0, "type": "open_url", "status": "succeeded"}]}
    assert secret_url not in str(get_resp.json())
    assert "super-secret" not in str(get_resp.json())

    assert evaluate_get_resp.status_code == 200
    assert evaluate_get_resp.json()["result"] == {
        "steps": [{"index": 0, "type": "evaluate", "status": "succeeded"}],
    }
    assert "window.localStorage" not in str(evaluate_get_resp.json())
    assert "super-secret" not in str(evaluate_get_resp.json())

    assert screenshot_get_resp.status_code == 200
    assert screenshot_get_resp.json()["result"] == {
        "steps": [{"index": 0, "type": "screenshot", "status": "succeeded"}],
    }
    assert "c3VwZXItc2VjcmV0" not in str(screenshot_get_resp.json())
    assert "super-secret" not in str(screenshot_get_resp.json())

    assert list_resp.status_code == 200
    listed_task = next(task for task in list_resp.json()["tasks"] if task["id"] == task_id)
    assert listed_task["result"] == {"steps": [{"index": 0, "type": "open_url", "status": "succeeded"}]}
    listed_evaluate_task = next(task for task in list_resp.json()["tasks"] if task["id"] == evaluate_task_id)
    assert listed_evaluate_task["result"] == {
        "steps": [{"index": 0, "type": "evaluate", "status": "succeeded"}],
    }
    listed_screenshot_task = next(task for task in list_resp.json()["tasks"] if task["id"] == screenshot_task_id)
    assert listed_screenshot_task["result"] == {
        "steps": [{"index": 0, "type": "screenshot", "status": "succeeded"}],
    }
    assert secret_url not in str(list_resp.json())
    assert "window.localStorage" not in str(list_resp.json())
    assert "c3VwZXItc2VjcmV0" not in str(list_resp.json())
    assert "super-secret" not in str(list_resp.json())


def test_get_automation_task_returns_persisted_task(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskGetProfile"})
    pid = create.json()["id"]
    create_task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]})
    task_id = create_task.json()["id"]

    resp = app_client.get(f"/api/tasks/{task_id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == task_id
    assert resp.json()["status"] == "queued"


def test_create_automation_task_rejects_missing_profile(app_client: TestClient):
    resp = app_client.post("/api/tasks", json={"profile_id": "missing", "steps": [{"type": "wait", "ms": 1}]})

    assert resp.status_code == 404


def test_list_automation_tasks_returns_newest_tasks(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskListProfile"})
    pid = create.json()["id"]
    first = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    second = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 2}]}).json()

    resp = app_client.get("/api/tasks")

    assert resp.status_code == 200
    task_ids = [task["id"] for task in resp.json()["tasks"]]
    assert task_ids[:2] == [second["id"], first["id"]]


def test_list_automation_tasks_filters_by_profile(app_client: TestClient):
    first_profile = app_client.post("/api/profiles", json={"name": "TaskListFilterFirst"}).json()["id"]
    second_profile = app_client.post("/api/profiles", json={"name": "TaskListFilterSecond"}).json()["id"]
    first_task = app_client.post(
        "/api/tasks",
        json={"profile_id": first_profile, "steps": [{"type": "wait", "ms": 1}]},
    ).json()
    app_client.post(
        "/api/tasks",
        json={"profile_id": second_profile, "steps": [{"type": "wait", "ms": 2}]},
    )

    resp = app_client.get(f"/api/tasks?profile_id={first_profile}")

    assert resp.status_code == 200
    assert [task["id"] for task in resp.json()["tasks"]] == [first_task["id"]]


def test_list_automation_tasks_paginates_newest_tasks(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskListPaginationProfile"})
    pid = create.json()["id"]
    first = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    second = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 2}]}).json()
    third = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 3}]}).json()

    resp = app_client.get("/api/tasks?limit=2&offset=1")

    assert resp.status_code == 200
    assert [task["id"] for task in resp.json()["tasks"]] == [second["id"], first["id"]]
    assert third["id"] not in [task["id"] for task in resp.json()["tasks"]]


def test_list_automation_tasks_rejects_invalid_pagination(app_client: TestClient):
    negative_offset = app_client.get("/api/tasks?offset=-1")
    excessive_limit = app_client.get("/api/tasks?limit=501")

    assert negative_offset.status_code == 422
    assert excessive_limit.status_code == 422


def test_list_automation_tasks_filter_rejects_missing_profile(app_client: TestClient):
    resp = app_client.get("/api/tasks?profile_id=missing")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Profile not found"


def test_list_automation_tasks_filter_keeps_steps_redacted(app_client: TestClient):
    pid = app_client.post("/api/profiles", json={"name": "TaskListFilterRedact"}).json()["id"]
    secret_url = "https://example.com/account?token=super-secret#frag"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "open_url",
                    "url": secret_url,
                    "page_ref": "0",
                    "wait_until": "domcontentloaded",
                    "timeout_ms": 5000,
                }
            ],
        },
    ).json()

    resp = app_client.get(f"/api/tasks?profile_id={pid}")

    assert resp.status_code == 200
    assert resp.json()["tasks"] == [
        {
            **task,
            "steps": [
                {
                    "type": "open_url",
                    "page_ref": "0",
                    "wait_until": "domcontentloaded",
                    "timeout_ms": 5000,
                }
            ],
        }
    ]
    assert secret_url not in str(resp.json())
    assert "super-secret" not in str(resp.json())


def test_cancel_queued_automation_task_marks_cancelled(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskCancelProfile"})
    pid = create.json()["id"]
    task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/cancel")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == task["id"]
    assert data["status"] == "cancelled"
    assert data["finished_at"] is not None


def test_cancel_running_automation_task_requests_cooperative_cancel_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskCancelRunningProfile"})
    pid = create.json()["id"]
    secret_url = "https://example.com/app?token=super-secret#frag"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {"type": "wait", "ms": 1},
                {"type": "open_url", "url": secret_url, "note": "do-not-echo"},
            ],
        },
    ).json()
    main.db.update_automation_task(task["id"], status="running")

    resp = app_client.post(f"/api/tasks/{task['id']}/cancel")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == task["id"]
    assert data["status"] == "cancel_requested"
    assert data["finished_at"] is None
    assert data["result"] is None
    assert data["error"] is None
    assert secret_url not in str(data)
    assert "super-secret" not in str(data)
    assert "do-not-echo" not in str(data)


def test_cancel_requested_automation_task_blocks_same_profile_run_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskCancelRequestedConcurrentProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    cancel_requested_task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]},
    ).json()
    main.db.update_automation_task(cancel_requested_task["id"], status="cancel_requested")
    secret_url = "https://example.com/app?token=super-secret#frag"
    queued_task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "open_url", "url": secret_url, "note": "do-not-echo"}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{queued_task['id']}/run")
    persisted = main.db.get_automation_task(queued_task["id"])

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Automation profile already has a running task"
    assert secret_url not in resp.text
    assert "super-secret" not in resp.text
    assert "do-not-echo" not in resp.text
    assert persisted is not None
    assert persisted["status"] == "queued"
    assert persisted["started_at"] is None
    assert persisted["finished_at"] is None
    page.goto.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_retry_failed_automation_task_creates_new_queued_task_without_running_script(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRetryFailedProfile"})
    pid = create.json()["id"]
    original = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    main.db.update_automation_task(
        original["id"],
        status="failed",
        result={"steps": [{"index": 0, "type": "wait", "status": "failed"}]},
        error="Invalid wait step",
        started_at="2026-05-27T00:00:00+00:00",
        finished_at="2026-05-27T00:00:01+00:00",
    )

    resp = app_client.post(f"/api/tasks/{original['id']}/retry")

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] != original["id"]
    assert data["profile_id"] == pid
    assert data["status"] == "queued"
    assert data["steps"] == [{"type": "wait", "ms": 1}]
    assert data["result"] is None
    assert data["error"] is None
    assert data["started_at"] is None
    assert data["finished_at"] is None
    persisted_original = main.db.get_automation_task(original["id"])
    assert persisted_original["status"] == "failed"
    assert persisted_original["error"] == "Invalid wait step"


def test_retry_automation_task_rejects_active_status(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRetryActiveProfile"})
    pid = create.json()["id"]
    queued = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    running = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    main.db.update_automation_task(running["id"], status="running")

    queued_resp = app_client.post(f"/api/tasks/{queued['id']}/retry")
    running_resp = app_client.post(f"/api/tasks/{running['id']}/retry")

    assert queued_resp.status_code == 409
    assert queued_resp.json()["detail"] == "Only finished automation tasks can be retried"
    assert running_resp.status_code == 409
    assert running_resp.json()["detail"] == "Only finished automation tasks can be retried"


def test_retry_automation_task_rejects_missing_profile(app_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    create = app_client.post("/api/profiles", json={"name": "TaskRetryMissingProfile"})
    pid = create.json()["id"]
    task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    main.db.update_automation_task(task["id"], status="failed")
    original_get_profile = main.db.get_profile

    def get_profile_or_missing(profile_id: str):
        if profile_id == pid:
            return None
        return original_get_profile(profile_id)

    monkeypatch.setattr(main.db, "get_profile", get_profile_or_missing)

    resp = app_client.post(f"/api/tasks/{task['id']}/retry")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Profile not found"


def test_retry_automation_task_keeps_steps_redacted(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRetryRedactProfile"})
    pid = create.json()["id"]
    secret_url = "https://example.com/account?token=super-secret#frag"
    original = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "open_url",
                    "url": secret_url,
                    "page_ref": "0",
                    "wait_until": "domcontentloaded",
                    "timeout_ms": 5000,
                }
            ],
        },
    ).json()
    main.db.update_automation_task(
        original["id"],
        status="failed",
        result={
            "steps": [
                {
                    "index": 0,
                    "type": "open_url",
                    "status": "failed",
                    "url": secret_url,
                    "payload": {"token": "super-secret"},
                }
            ],
            "raw_url": secret_url,
        },
        error="Open URL step failed",
    )

    resp = app_client.post(f"/api/tasks/{original['id']}/retry")

    assert resp.status_code == 201
    assert resp.json()["steps"] == [
        {
            "type": "open_url",
            "page_ref": "0",
            "wait_until": "domcontentloaded",
            "timeout_ms": 5000,
        }
    ]
    assert resp.json()["result"] is None
    assert secret_url not in str(resp.json())
    assert "super-secret" not in str(resp.json())


def test_run_wait_automation_task_marks_succeeded(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunWaitProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == task["id"]
    assert data["status"] == "succeeded"
    assert data["result"] == {"steps": [{"index": 0, "type": "wait", "status": "succeeded"}]}
    assert data["error"] is None
    assert data["started_at"] is not None
    assert data["finished_at"] is not None
    main.browser_mgr.running.pop(pid, None)


def test_run_automation_task_rejects_non_queued_status(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunNonQueuedProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    main.db.update_automation_task(task["id"], status="cancelled")

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 409
    main.browser_mgr.running.pop(pid, None)


def test_run_automation_task_rejects_concurrent_task_for_same_profile_without_leaking_payload(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "TaskRunConcurrentProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    running_task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]},
    ).json()
    main.db.update_automation_task(running_task["id"], status="running")
    secret_url = "https://example.com/app?token=super-secret#frag"
    queued_task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [{"type": "open_url", "url": secret_url, "note": "do-not-echo"}],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{queued_task['id']}/run")
    persisted = main.db.get_automation_task(queued_task["id"])

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Automation profile already has a running task"
    assert secret_url not in resp.text
    assert "super-secret" not in resp.text
    assert "do-not-echo" not in resp.text
    assert persisted is not None
    assert persisted["status"] == "queued"
    assert persisted["started_at"] is None
    assert persisted["finished_at"] is None
    page.goto.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_automation_task_allows_running_task_on_different_profile(app_client: TestClient):
    first_create = app_client.post("/api/profiles", json={"name": "TaskRunConcurrentFirstProfile"})
    second_create = app_client.post("/api/profiles", json={"name": "TaskRunConcurrentSecondProfile"})
    first_pid = first_create.json()["id"]
    second_pid = second_create.json()["id"]
    _automation_running_profile(second_pid, [_automation_page()])
    first_task = app_client.post(
        "/api/tasks",
        json={"profile_id": first_pid, "steps": [{"type": "wait", "ms": 1}]},
    ).json()
    main.db.update_automation_task(first_task["id"], status="running")
    second_task = app_client.post(
        "/api/tasks",
        json={"profile_id": second_pid, "steps": [{"type": "wait", "ms": 1}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{second_task['id']}/run")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == second_task["id"]
    assert data["status"] == "succeeded"
    assert data["result"] == {"steps": [{"index": 0, "type": "wait", "status": "succeeded"}]}
    assert main.db.get_automation_task(first_task["id"])["status"] == "running"
    main.browser_mgr.running.pop(second_pid, None)


def test_run_automation_task_honors_cancel_request_at_step_boundary_without_running_next_step(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    create = app_client.post("/api/profiles", json={"name": "TaskRunCancelBoundaryProfile"})
    pid = create.json()["id"]
    page = _automation_page("about:blank", "Before")
    _automation_running_profile(pid, [page])
    secret_url = "https://example.com/app?token=super-secret#frag"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {"type": "wait", "ms": 1},
                {"type": "open_url", "url": secret_url, "note": "do-not-echo"},
            ],
        },
    ).json()

    async def request_cancel(_seconds: float):
        main.db.update_automation_task(task["id"], status="cancel_requested")

    monkeypatch.setattr(main.asyncio, "sleep", request_cancel)

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == task["id"]
    assert data["status"] == "cancelled"
    assert data["result"] == {
        "steps": [
            {"index": 0, "type": "wait", "status": "succeeded"},
            {"index": 1, "type": "open_url", "status": "cancelled"},
        ]
    }
    assert data["error"] is None
    assert data["finished_at"] is not None
    assert secret_url not in str(data)
    assert "super-secret" not in str(data)
    assert "do-not-echo" not in str(data)
    page.goto.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_automation_task_requires_running_profile(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunStoppedProfile"})
    pid = create.json()["id"]
    task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Profile not running"


def test_run_automation_task_fails_unknown_step_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunUnknownProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    secret_value = "token=super-secret"
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "unknown", "value": secret_value}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["id"] == task["id"]
    assert data["status"] == "failed"
    assert data["result"] == {"steps": [{"index": 0, "type": "unknown", "status": "failed"}]}
    assert data["error"] == "Unsupported automation step type"
    assert secret_value not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_automation_task_marks_failed_for_invalid_wait_ms(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunInvalidWaitProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 0}]}).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["id"] == task["id"]
    assert data["status"] == "failed"
    assert data["result"] == {"steps": [{"index": 0, "type": "wait", "status": "failed"}]}
    assert data["error"] == "Invalid wait step"
    assert data["started_at"] is not None
    assert data["finished_at"] is not None
    main.browser_mgr.running.pop(pid, None)


@pytest.mark.asyncio
async def test_automation_worker_run_once_returns_none_without_queued_task(app_client: TestClient):
    result = await main.run_automation_worker_once(lease_owner="worker-a")

    assert result is None


@pytest.mark.asyncio
async def test_automation_worker_run_once_fails_claimed_task_when_profile_not_running_without_leaking_payload(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "TaskWorkerStoppedProfile"})
    pid = create.json()["id"]
    secret_url = "https://example.com/app?token=super-secret#frag"
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "open_url", "url": secret_url, "note": "do-not-echo"}]},
    ).json()

    result = await main.run_automation_worker_once(lease_owner="worker-a")

    assert result is not None
    data = main._automation_task_response(result).model_dump()
    assert data["id"] == task["id"]
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "open_url"}]
    assert data["result"] == {"steps": []}
    assert data["error"] == "Profile not running"
    assert data["started_at"] is not None
    assert data["finished_at"] is not None
    assert "lease_owner" not in data
    assert "lease_expires_at" not in data
    assert secret_url not in str(data)
    assert "super-secret" not in str(data)
    assert "do-not-echo" not in str(data)

    persisted = main.db.get_automation_task(task["id"])
    assert persisted is not None
    assert persisted["status"] == "failed"
    assert persisted["lease_owner"] is None
    assert persisted["lease_expires_at"] is None


@pytest.mark.asyncio
async def test_automation_worker_run_once_executes_claimed_task_and_clears_lease(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskWorkerRunProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()

    result = await main.run_automation_worker_once(lease_owner="worker-a")

    assert result is not None
    data = main._automation_task_response(result).model_dump()
    assert data["id"] == task["id"]
    assert data["status"] == "succeeded"
    assert data["result"] == {"steps": [{"index": 0, "type": "wait", "status": "succeeded"}]}
    assert data["started_at"] is not None
    assert data["finished_at"] is not None
    assert "lease_owner" not in data
    assert "lease_expires_at" not in data

    persisted = main.db.get_automation_task(task["id"])
    assert persisted is not None
    assert persisted["lease_owner"] is None
    assert persisted["lease_expires_at"] is None
    main.browser_mgr.running.pop(pid, None)


@pytest.mark.asyncio
async def test_automation_worker_run_once_writes_redacted_terminal_audit_event(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskWorkerAuditProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()

    result = await main.run_automation_worker_once(lease_owner="worker-secret-owner")

    assert result is not None
    assert result["status"] == "succeeded"
    events = _automation_task_audit_events()
    assert [event["event_type"] for event in events] == [
        "automation.task.created",
        "automation.task.succeeded",
    ]
    assert events[1]["actor_type"] == "local_admin"
    assert events[1]["profile_id"] == pid
    assert events[1]["metadata"] == {
        "task_id": task["id"],
        "status": "succeeded",
        "step_count": 1,
        "step_types": ["wait"],
        "runner_type": "worker",
        "succeeded_step_count": 1,
        "failed_step_count": 0,
        "cancelled_step_count": 0,
    }
    serialized_events = json.dumps(events, sort_keys=True)
    assert "worker-secret-owner" not in serialized_events
    assert "lease_owner" not in serialized_events
    assert "lease_expires_at" not in serialized_events
    main.browser_mgr.running.pop(pid, None)


@pytest.mark.asyncio
async def test_automation_worker_run_once_renews_lease_during_wait_without_exposing_metadata(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    create = app_client.post("/api/profiles", json={"name": "TaskWorkerRenewProfile"})
    pid = create.json()["id"]
    page = _automation_page()
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {"type": "wait", "ms": 1},
                {"type": "click", "selector": "#safe-button"},
            ],
        },
    ).json()
    renew_calls: list[tuple[str, str, int]] = []
    renew_seen = main.asyncio.Event()
    renew_seen_during_wait = False
    original_renew = main.db.renew_automation_task_lease

    def record_renew(task_id: str, *, lease_owner: str, lease_seconds: int, **kwargs):
        renew_calls.append((task_id, lease_owner, lease_seconds))
        renew_seen.set()
        return original_renew(task_id, lease_owner=lease_owner, lease_seconds=lease_seconds, **kwargs)

    async def controlled_sleep(seconds: float):
        nonlocal renew_seen_during_wait
        try:
            await main.asyncio.wait_for(renew_seen.wait(), timeout=0.2)
            renew_seen_during_wait = True
        except main.asyncio.TimeoutError:
            pass

    monkeypatch.setattr(main.db, "renew_automation_task_lease", record_renew)
    monkeypatch.setattr(main, "_automation_worker_lease_heartbeat_interval", lambda lease_seconds: 0.01)
    monkeypatch.setattr(main.asyncio, "sleep", controlled_sleep)

    result = await main.run_automation_worker_once(lease_owner="worker-a", lease_seconds=1)

    assert result is not None
    data = main._automation_task_response(result).model_dump()
    assert data["id"] == task["id"]
    assert data["status"] == "succeeded"
    assert data["result"] == {
        "steps": [
            {"index": 0, "type": "wait", "status": "succeeded"},
            {"index": 1, "type": "click", "status": "succeeded"},
        ],
    }
    assert renew_seen_during_wait is True
    assert renew_calls
    assert all(call == (task["id"], "worker-a", 1) for call in renew_calls)
    assert "lease_owner" not in data
    assert "lease_expires_at" not in data
    assert "#safe-button" not in str(data)

    persisted = main.db.get_automation_task(task["id"])
    assert persisted is not None
    assert persisted["lease_owner"] is None
    assert persisted["lease_expires_at"] is None
    main.browser_mgr.running.pop(pid, None)


@pytest.mark.asyncio
async def test_automation_worker_run_once_fails_http_step_errors_without_leaking_payload(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "TaskWorkerStepHttpErrorProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    secret_selector = "#token-super-secret"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [{"type": "click", "selector": secret_selector, "page_ref": "99"}],
        },
    ).json()

    result = await main.run_automation_worker_once(lease_owner="worker-a")

    assert result is not None
    data = main._automation_task_response(result).model_dump()
    assert data["id"] == task["id"]
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "click", "page_ref": "99"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "click", "status": "failed"}]}
    assert data["error"] == "Automation step failed"
    assert data["finished_at"] is not None
    assert secret_selector not in str(data)
    assert "super-secret" not in str(data)

    persisted = main.db.get_automation_task(task["id"])
    assert persisted is not None
    assert persisted["lease_owner"] is None
    assert persisted["lease_expires_at"] is None
    main.browser_mgr.running.pop(pid, None)


@pytest.mark.asyncio
async def test_automation_worker_loop_runs_multiple_claimed_tasks(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskWorkerLoopProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    first = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    second = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()

    summary = await main.run_automation_worker_loop(
        lease_owner="worker-a",
        max_runs=2,
        idle_sleep_seconds=0,
    )

    assert summary == {"claimed": 2, "succeeded": 2, "failed": 0, "cancelled": 0, "idle_cycles": 0}
    assert main.db.get_automation_task(first["id"])["status"] == "succeeded"
    assert main.db.get_automation_task(second["id"])["status"] == "succeeded"
    main.browser_mgr.running.pop(pid, None)


@pytest.mark.asyncio
async def test_automation_worker_loop_stops_after_idle_cycles(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    sleeps: list[float] = []

    async def record_sleep(seconds: float):
        sleeps.append(seconds)

    monkeypatch.setattr(main.asyncio, "sleep", record_sleep)

    summary = await main.run_automation_worker_loop(
        lease_owner="worker-a",
        max_runs=5,
        max_idle_cycles=2,
        idle_sleep_seconds=0.25,
    )

    assert summary == {"claimed": 0, "succeeded": 0, "failed": 0, "cancelled": 0, "idle_cycles": 2}
    assert sleeps == [0.25]


@pytest.mark.asyncio
async def test_automation_worker_loop_honors_stop_event_before_claiming(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskWorkerLoopStopProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    task = app_client.post("/api/tasks", json={"profile_id": pid, "steps": [{"type": "wait", "ms": 1}]}).json()
    stop_event = main.asyncio.Event()
    stop_event.set()

    summary = await main.run_automation_worker_loop(
        lease_owner="worker-a",
        max_runs=1,
        idle_sleep_seconds=0,
        stop_event=stop_event,
    )

    assert summary == {"claimed": 0, "succeeded": 0, "failed": 0, "cancelled": 0, "idle_cycles": 0}
    assert main.db.get_automation_task(task["id"])["status"] == "queued"
    main.browser_mgr.running.pop(pid, None)


@pytest.mark.asyncio
async def test_automation_worker_loop_counts_lost_lease_as_failed_without_leaking_payload(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    create = app_client.post("/api/profiles", json={"name": "TaskWorkerLoopLostLeaseProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    secret_url = "https://example.com/app?token=super-secret#frag"
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "open_url", "url": secret_url}]},
    ).json()
    original_run_once = main.run_automation_worker_once

    async def run_once_then_lose_lease(**kwargs):
        claimed = main.db.claim_next_automation_task(
            lease_owner=kwargs["lease_owner"],
            lease_seconds=kwargs["lease_seconds"],
        )
        assert claimed is not None
        raise main.HTTPException(status_code=409, detail="Automation task lease no longer owned by worker")

    monkeypatch.setattr(main, "run_automation_worker_once", run_once_then_lose_lease)

    summary = await main.run_automation_worker_loop(
        lease_owner="worker-a",
        lease_seconds=1,
        max_runs=1,
        idle_sleep_seconds=0,
    )

    assert summary == {"claimed": 1, "succeeded": 0, "failed": 1, "cancelled": 0, "idle_cycles": 0}
    data = main._automation_task_response(main.db.get_automation_task(task["id"])).model_dump()
    assert data["status"] == "running"
    assert "lease_owner" not in data
    assert "lease_expires_at" not in data
    assert secret_url not in str(data)
    assert "super-secret" not in str(data)
    monkeypatch.setattr(main, "run_automation_worker_once", original_run_once)
    main.browser_mgr.running.pop(pid, None)


def test_automation_worker_lifespan_keeps_worker_disabled_by_default(
    tmp_db,
    monkeypatch: pytest.MonkeyPatch,
):
    worker_loop = AsyncMock(return_value={"claimed": 0, "succeeded": 0, "failed": 0, "cancelled": 0, "idle_cycles": 0})
    monkeypatch.delenv("AUTOMATION_WORKER_ENABLED", raising=False)
    monkeypatch.setattr(main, "run_automation_worker_loop", worker_loop)
    monkeypatch.setattr(main.browser_mgr, "cleanup_stale", AsyncMock())
    monkeypatch.setattr(main.browser_mgr, "cleanup_all", AsyncMock())
    monkeypatch.setattr(main.browser_mgr, "auto_launch_all", AsyncMock())

    with TestClient(main.app):
        pass

    worker_loop.assert_not_called()


def test_automation_worker_lifespan_starts_enabled_worker_and_stops_it(
    tmp_db,
    monkeypatch: pytest.MonkeyPatch,
):
    started = threading.Event()
    stopped = threading.Event()
    captured: dict = {}

    async def fake_worker_loop(**kwargs):
        captured.update(kwargs)
        started.set()
        await kwargs["stop_event"].wait()
        stopped.set()
        return {"claimed": 0, "succeeded": 0, "failed": 0, "cancelled": 0, "idle_cycles": 0}

    monkeypatch.setenv("AUTOMATION_WORKER_ENABLED", "true")
    monkeypatch.setenv("AUTOMATION_WORKER_LEASE_SECONDS", "42")
    monkeypatch.setenv("AUTOMATION_WORKER_IDLE_SLEEP_SECONDS", "0.25")
    monkeypatch.setenv("AUTOMATION_WORKER_SHUTDOWN_TIMEOUT_SECONDS", "1")
    monkeypatch.setattr(main, "run_automation_worker_loop", fake_worker_loop)
    monkeypatch.setattr(main.browser_mgr, "cleanup_stale", AsyncMock())
    monkeypatch.setattr(main.browser_mgr, "cleanup_all", AsyncMock())
    monkeypatch.setattr(main.browser_mgr, "auto_launch_all", AsyncMock())

    with TestClient(main.app):
        assert started.wait(timeout=1)
        assert captured["lease_owner"].startswith("automation-worker-")
        assert captured["lease_seconds"] == 42
        assert captured["idle_sleep_seconds"] == 0.25
        assert captured["max_runs"] is None
        assert captured["max_idle_cycles"] is None
        assert not captured["stop_event"].is_set()

    assert stopped.wait(timeout=1)
    assert captured["stop_event"].is_set()


def test_automation_worker_lifespan_uses_defaults_for_invalid_worker_config_without_leaking_values(
    tmp_db,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    started = threading.Event()
    stopped = threading.Event()
    captured: dict = {}

    async def fake_worker_loop(**kwargs):
        captured.update(kwargs)
        started.set()
        await kwargs["stop_event"].wait()
        stopped.set()
        return {"claimed": 0, "succeeded": 0, "failed": 0, "cancelled": 0, "idle_cycles": 0}

    monkeypatch.setenv("AUTOMATION_WORKER_ENABLED", "true")
    monkeypatch.setenv("AUTOMATION_WORKER_LEASE_SECONDS", "0")
    monkeypatch.setenv("AUTOMATION_WORKER_IDLE_SLEEP_SECONDS", "nan")
    monkeypatch.setenv("AUTOMATION_WORKER_SHUTDOWN_TIMEOUT_SECONDS", "secret-timeout-value")
    monkeypatch.setattr(main, "run_automation_worker_loop", fake_worker_loop)
    monkeypatch.setattr(main.browser_mgr, "cleanup_stale", AsyncMock())
    monkeypatch.setattr(main.browser_mgr, "cleanup_all", AsyncMock())
    monkeypatch.setattr(main.browser_mgr, "auto_launch_all", AsyncMock())
    caplog.set_level("WARNING", logger="invisible_browser.manager")

    with TestClient(main.app):
        assert started.wait(timeout=1)
        assert captured["lease_seconds"] == 60
        assert captured["idle_sleep_seconds"] == 1.0

    assert stopped.wait(timeout=1)
    assert "AUTOMATION_WORKER_LEASE_SECONDS" in caplog.text
    assert "AUTOMATION_WORKER_IDLE_SLEEP_SECONDS" in caplog.text
    assert "AUTOMATION_WORKER_SHUTDOWN_TIMEOUT_SECONDS" in caplog.text
    assert "secret-timeout-value" not in caplog.text
    assert "nan" not in caplog.text


def test_run_open_url_step_navigates_existing_page_without_leaking_query(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunOpenUrlProfile"})
    pid = create.json()["id"]
    page = _automation_page("about:blank", "Before")
    _automation_running_profile(pid, [page])
    target_url = "https://example.com/app?token=super-secret#frag"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "open_url",
                    "url": target_url,
                    "page_ref": "0",
                    "wait_until": "domcontentloaded",
                    "timeout_ms": 5000,
                },
            ],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.goto.assert_awaited_once_with(
        target_url,
        wait_until="domcontentloaded",
        timeout=5000,
    )
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["steps"] == [
        {
            "type": "open_url",
            "page_ref": "0",
            "wait_until": "domcontentloaded",
            "timeout_ms": 5000,
        },
    ]
    assert data["result"] == {"steps": [{"index": 0, "type": "open_url", "status": "succeeded"}]}
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_open_url_step_marks_failed_for_invalid_url_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunOpenUrlInvalidProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    invalid_url = "not-a-url?token=super-secret"
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "open_url", "url": invalid_url}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "open_url"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "open_url", "status": "failed"}]}
    assert data["error"] == "Invalid open_url step"
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_wait_for_selector_step_waits_existing_page_without_leaking_selector(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunWaitForSelectorProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    selector = "#ready-token-super-secret"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "wait_for_selector",
                    "selector": selector,
                    "page_ref": "0",
                    "state": "hidden",
                    "timeout_ms": 2500,
                },
            ],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.wait_for_selector.assert_awaited_once_with(selector, state="hidden", timeout=2500)
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["steps"] == [{"type": "wait_for_selector", "page_ref": "0", "state": "hidden", "timeout_ms": 2500}]
    assert data["result"] == {"steps": [{"index": 0, "type": "wait_for_selector", "status": "succeeded"}]}
    assert selector not in str(data)
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_wait_for_selector_step_marks_failed_for_invalid_selector_without_leaking_payload(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "TaskRunWaitForSelectorInvalidProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    secret_note = "#ready-token-super-secret"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [{"type": "wait_for_selector", "selector": "", "note": secret_note}],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "wait_for_selector"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "wait_for_selector", "status": "failed"}]}
    assert data["error"] == "Invalid wait_for_selector step"
    assert secret_note not in str(data)
    assert "super-secret" not in str(data)
    page.wait_for_selector.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_wait_for_selector_step_marks_failed_for_invalid_state(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunWaitForSelectorInvalidStateProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    secret_note = "#ready-token-super-secret"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [{"type": "wait_for_selector", "selector": "#ready", "state": "shown", "note": secret_note}],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "wait_for_selector"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "wait_for_selector", "status": "failed"}]}
    assert data["error"] == "Invalid wait_for_selector step"
    assert secret_note not in str(data)
    assert "super-secret" not in str(data)
    page.wait_for_selector.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_wait_for_selector_step_marks_failed_for_bool_timeout(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunWaitForSelectorBoolTimeoutProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "wait_for_selector", "selector": "#ready", "timeout_ms": True}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "wait_for_selector"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "wait_for_selector", "status": "failed"}]}
    assert data["error"] == "Invalid wait_for_selector step"
    page.wait_for_selector.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_wait_for_selector_step_uses_defaults(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunWaitForSelectorDefaultsProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "wait_for_selector", "selector": "#ready"}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.wait_for_selector.assert_awaited_once_with("#ready", state="visible", timeout=30_000)
    data = resp.json()
    assert data["steps"] == [{"type": "wait_for_selector"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "wait_for_selector", "status": "succeeded"}]}
    main.browser_mgr.running.pop(pid, None)


def test_run_wait_for_selector_step_failure_uses_redacted_error(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunWaitForSelectorFailureProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    selector = "#ready-token-super-secret"
    page.wait_for_selector.side_effect = RuntimeError(f"selector failed: {selector}")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "wait_for_selector", "selector": selector}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "wait_for_selector"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "wait_for_selector", "status": "failed"}]}
    assert data["error"] == "Wait for selector step failed"
    assert selector not in str(data)
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_evaluate_step_evaluates_existing_page_without_leaking_expression_or_result(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunEvaluateProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    page.evaluate.return_value = {"token": "result-token-super-secret"}
    _automation_running_profile(pid, [page])
    expression = "window.localStorage.getItem('account-token-super-secret')"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "evaluate",
                    "expression": expression,
                    "page_ref": "0",
                    "note": "do-not-echo",
                },
            ],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.evaluate.assert_awaited_once_with(expression)
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["steps"] == [{"type": "evaluate", "page_ref": "0"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "evaluate", "status": "succeeded"}]}
    assert data["error"] is None
    assert expression not in str(data)
    assert "result-token-super-secret" not in str(data)
    assert "super-secret" not in str(data)
    assert "do-not-echo" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_evaluate_step_marks_failed_for_invalid_expression_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunEvaluateInvalidProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    secret_note = "account-token-super-secret"
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "evaluate", "expression": "", "note": secret_note}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "evaluate"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "evaluate", "status": "failed"}]}
    assert data["error"] == "Invalid evaluate step"
    assert secret_note not in str(data)
    assert "super-secret" not in str(data)
    page.evaluate.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_evaluate_step_marks_failed_for_non_string_expression_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunEvaluateNonStringProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    secret_note = "account-token-super-secret"
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "evaluate", "expression": 123, "note": secret_note}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "evaluate"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "evaluate", "status": "failed"}]}
    assert data["error"] == "Invalid evaluate step"
    assert secret_note not in str(data)
    assert "super-secret" not in str(data)
    page.evaluate.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_evaluate_step_failure_uses_redacted_error(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunEvaluateFailureProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    expression = "window.localStorage.getItem('account-token-super-secret')"
    page.evaluate.side_effect = RuntimeError(f"evaluate failed: {expression}")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "evaluate", "expression": expression}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "evaluate"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "evaluate", "status": "failed"}]}
    assert data["error"] == "Evaluate step failed"
    assert expression not in str(data)
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_click_step_clicks_existing_page_without_leaking_selector(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunClickProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    selector = "#submit-token-super-secret"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "click",
                    "selector": selector,
                    "page_ref": "0",
                    "timeout_ms": 2500,
                },
            ],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.click.assert_awaited_once_with(selector, timeout=2500)
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["steps"] == [{"type": "click", "page_ref": "0", "timeout_ms": 2500}]
    assert data["result"] == {"steps": [{"index": 0, "type": "click", "status": "succeeded"}]}
    assert selector not in str(data)
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_click_step_marks_failed_for_invalid_selector_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunClickInvalidProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    secret_selector = "#submit-token-super-secret"
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "click", "selector": "", "value": secret_selector}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "click"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "click", "status": "failed"}]}
    assert data["error"] == "Invalid click step"
    assert secret_selector not in str(data)
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_click_step_marks_failed_for_bool_timeout(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunClickBoolTimeoutProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "click", "selector": "#submit", "timeout_ms": True}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "click"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "click", "status": "failed"}]}
    assert data["error"] == "Invalid click step"
    page.click.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_click_step_failure_uses_redacted_error(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunClickFailureProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    selector = "#submit-token-super-secret"
    page.click.side_effect = RuntimeError(f"selector failed: {selector}")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "click", "selector": selector}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "click"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "click", "status": "failed"}]}
    assert data["error"] == "Click step failed"
    assert selector not in str(data)
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_fill_step_fills_existing_page_without_leaking_selector_or_value(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunFillProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    selector = "#email-token-super-secret"
    value = "account-token-super-secret@example.com"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "fill",
                    "selector": selector,
                    "value": value,
                    "page_ref": "0",
                    "timeout_ms": 2500,
                },
            ],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.fill.assert_awaited_once_with(selector, value, timeout=2500)
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["steps"] == [{"type": "fill", "page_ref": "0", "timeout_ms": 2500}]
    assert data["result"] == {"steps": [{"index": 0, "type": "fill", "status": "succeeded"}]}
    assert selector not in str(data)
    assert value not in str(data)
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_fill_step_marks_failed_for_invalid_value_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunFillInvalidProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    secret_value = "account-token-super-secret@example.com"
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "fill", "selector": "#email", "value": 123, "note": secret_value}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "fill"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "fill", "status": "failed"}]}
    assert data["error"] == "Invalid fill step"
    assert secret_value not in str(data)
    assert "super-secret" not in str(data)
    page.fill.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_fill_step_allows_empty_value(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunFillEmptyValueProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "fill", "selector": "#email", "value": ""}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.fill.assert_awaited_once_with("#email", "", timeout=30_000)
    data = resp.json()
    assert data["steps"] == [{"type": "fill"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "fill", "status": "succeeded"}]}
    main.browser_mgr.running.pop(pid, None)


def test_run_fill_step_marks_failed_for_bool_timeout(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunFillBoolTimeoutProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "fill", "selector": "#email", "value": "x", "timeout_ms": True}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "fill"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "fill", "status": "failed"}]}
    assert data["error"] == "Invalid fill step"
    page.fill.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_fill_step_failure_uses_redacted_error(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunFillFailureProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    selector = "#email-token-super-secret"
    value = "account-token-super-secret@example.com"
    page.fill.side_effect = RuntimeError(f"fill failed: {selector} {value}")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "fill", "selector": selector, "value": value}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "fill"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "fill", "status": "failed"}]}
    assert data["error"] == "Fill step failed"
    assert selector not in str(data)
    assert value not in str(data)
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_keyboard_type_step_types_existing_page_without_leaking_text(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunKeyboardTypeProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    text = "account-token-super-secret@example.com"
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "keyboard_type",
                    "text": text,
                    "page_ref": "0",
                    "delay_ms": 25,
                },
            ],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.keyboard.type.assert_awaited_once_with(text, delay=25)
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["steps"] == [{"type": "keyboard_type", "page_ref": "0", "delay_ms": 25}]
    assert data["result"] == {"steps": [{"index": 0, "type": "keyboard_type", "status": "succeeded"}]}
    assert text not in str(data)
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_keyboard_type_step_marks_failed_for_bool_delay(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunKeyboardTypeBoolDelayProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    text = "account-token-super-secret@example.com"
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "keyboard_type", "text": text, "delay_ms": True}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "keyboard_type"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "keyboard_type", "status": "failed"}]}
    assert data["error"] == "Invalid keyboard_type step"
    assert text not in str(data)
    assert "super-secret" not in str(data)
    page.keyboard.type.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_keyboard_type_step_uses_default_delay(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunKeyboardTypeDefaultDelayProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    text = "hello"
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "keyboard_type", "text": text}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.keyboard.type.assert_awaited_once_with(text, delay=0)
    data = resp.json()
    assert data["steps"] == [{"type": "keyboard_type"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "keyboard_type", "status": "succeeded"}]}
    main.browser_mgr.running.pop(pid, None)


def test_run_keyboard_type_step_marks_failed_for_empty_text(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunKeyboardTypeEmptyTextProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    secret_note = "account-token-super-secret@example.com"
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "keyboard_type", "text": "", "note": secret_note}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "keyboard_type"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "keyboard_type", "status": "failed"}]}
    assert data["error"] == "Invalid keyboard_type step"
    assert secret_note not in str(data)
    assert "super-secret" not in str(data)
    page.keyboard.type.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_keyboard_type_step_failure_uses_redacted_error(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunKeyboardTypeFailureProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    text = "account-token-super-secret@example.com"
    page.keyboard.type.side_effect = RuntimeError(f"keyboard failed: {text}")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "keyboard_type", "text": text}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "keyboard_type"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "keyboard_type", "status": "failed"}]}
    assert data["error"] == "Keyboard type step failed"
    assert text not in str(data)
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_scroll_step_scrolls_existing_page(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunScrollProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "scroll",
                    "page_ref": "0",
                    "delta_x": 10,
                    "delta_y": 600,
                    "note": "do-not-echo",
                },
            ],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.evaluate.assert_awaited_once_with(
        "([deltaX, deltaY]) => window.scrollBy(deltaX, deltaY)",
        [10, 600],
    )
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["steps"] == [{"type": "scroll", "page_ref": "0", "delta_x": 10, "delta_y": 600}]
    assert data["result"] == {"steps": [{"index": 0, "type": "scroll", "status": "succeeded"}]}
    assert "do-not-echo" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_scroll_step_marks_failed_for_invalid_delta_without_leaking_payload(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunScrollInvalidProfile"})
    pid = create.json()["id"]
    _automation_running_profile(pid, [_automation_page()])
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [{"type": "scroll", "delta_x": 0, "delta_y": 100001, "note": "do-not-echo"}],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "scroll", "delta_x": 0}]
    assert data["result"] == {"steps": [{"index": 0, "type": "scroll", "status": "failed"}]}
    assert data["error"] == "Invalid scroll step"
    assert "do-not-echo" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_screenshot_step_captures_existing_page_without_returning_png(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunScreenshotProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    page.screenshot.return_value = b"\x89PNG\r\nsuper-secret"
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "screenshot",
                    "page_ref": "0",
                    "full_page": True,
                    "note": "do-not-echo",
                    "base64": "png-token-super-secret",
                },
            ],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.screenshot.assert_awaited_once_with(type="png", full_page=True)
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["steps"] == [{"type": "screenshot", "page_ref": "0", "full_page": True}]
    assert data["result"] == {"steps": [{"index": 0, "type": "screenshot", "status": "succeeded"}]}
    assert data["error"] is None
    assert "PNG" not in str(data)
    assert "png-token" not in str(data)
    assert "super-secret" not in str(data)
    assert "do-not-echo" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def test_run_screenshot_step_uses_default_full_page(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunScreenshotDefaultProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "screenshot"}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 200
    page.screenshot.assert_awaited_once_with(type="png", full_page=False)
    data = resp.json()
    assert data["steps"] == [{"type": "screenshot"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "screenshot", "status": "succeeded"}]}
    main.browser_mgr.running.pop(pid, None)


def test_run_screenshot_step_marks_failed_for_non_bool_full_page_without_leaking_payload(
    app_client: TestClient,
):
    create = app_client.post("/api/profiles", json={"name": "TaskRunScreenshotInvalidFullPageProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={
            "profile_id": pid,
            "steps": [
                {
                    "type": "screenshot",
                    "full_page": "true",
                    "path": "/tmp/screenshot-token-super-secret.png",
                    "note": "do-not-echo",
                },
            ],
        },
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "screenshot"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "screenshot", "status": "failed"}]}
    assert data["error"] == "Invalid screenshot step"
    assert "super-secret" not in str(data)
    assert "do-not-echo" not in str(data)
    page.screenshot.assert_not_awaited()
    main.browser_mgr.running.pop(pid, None)


def test_run_screenshot_step_failure_uses_redacted_error(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "TaskRunScreenshotFailureProfile"})
    pid = create.json()["id"]
    page = _automation_page("https://example.com/", "Example")
    page.screenshot.side_effect = RuntimeError("failed /tmp/screenshot-token-super-secret.png")
    _automation_running_profile(pid, [page])
    task = app_client.post(
        "/api/tasks",
        json={"profile_id": pid, "steps": [{"type": "screenshot"}]},
    ).json()

    resp = app_client.post(f"/api/tasks/{task['id']}/run")

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "failed"
    assert data["steps"] == [{"type": "screenshot"}]
    assert data["result"] == {"steps": [{"index": 0, "type": "screenshot", "status": "failed"}]}
    assert data["error"] == "Screenshot step failed"
    assert "screenshot-token" not in str(data)
    assert "super-secret" not in str(data)
    main.browser_mgr.running.pop(pid, None)


def _mock_running_profile(pid: str) -> MagicMock:
    """Create a mock RunningProfile and register it in browser_mgr."""
    mock = MagicMock(spec=RunningProfile)
    mock.display = 100
    mock.ws_port = 6100
    mock.engine = "invisible_playwright"
    mock.profile_id = pid
    main.browser_mgr.running[pid] = mock
    return mock


@pytest.mark.parametrize("path", [
    "/cdp",
    "/cdp/json/version",
    "/cdp/json/list",
    "/cdp/json",
])
def test_cdp_http_routes_are_not_product_api(app_client: TestClient, path: str):
    create = app_client.post("/api/profiles", json={"name": "NoCdpApi"})
    pid = create.json()["id"]
    _mock_running_profile(pid)

    resp = app_client.get(f"/api/profiles/{pid}{path}")

    assert resp.status_code == 404
    main.browser_mgr.running.pop(pid, None)


# ── WebSocket Origin Validation ──────────────────────────────────────────────


def test_vnc_ws_rejects_cross_origin(app_client: TestClient):
    """VNC WebSocket should reject cross-origin browser connections."""
    create = app_client.post("/api/profiles", json={"name": "OriginVnc"})
    pid = create.json()["id"]
    _mock_running_profile(pid)

    with pytest.raises(Exception):
        with app_client.websocket_connect(
            f"/api/profiles/{pid}/vnc",
            headers={"origin": "http://evil.com"},
        ):
            pass
    main.browser_mgr.running.pop(pid, None)


def test_ws_allows_same_origin(app_client: TestClient):
    """WebSocket from same origin should pass Origin check (not get 4403)."""
    create = app_client.post("/api/profiles", json={"name": "OriginOk"})
    pid = create.json()["id"]
    _mock_running_profile(pid)

    # Same-origin passes Origin check. VNC proxy then fails to connect to
    # real KasmVNC (not running), but that's fine — we're testing Origin only.
    # The connection is accepted (no 4403), then closes due to VNC connect error.
    try:
        with app_client.websocket_connect(
            f"/api/profiles/{pid}/vnc",
            headers={"origin": "http://testserver"},
        ) as ws:
            pass  # connection accepted = Origin check passed
    except Exception as exc:
        # Any error other than 4403 means Origin check passed
        assert "4403" not in str(exc)
    main.browser_mgr.running.pop(pid, None)


def test_ws_allows_no_origin(app_client: TestClient):
    """WebSocket without Origin header (Playwright/Puppeteer) should be accepted."""
    create = app_client.post("/api/profiles", json={"name": "NoOrigin"})
    pid = create.json()["id"]
    _mock_running_profile(pid)

    try:
        with app_client.websocket_connect(f"/api/profiles/{pid}/vnc") as ws:
            pass
    except Exception as exc:
        assert "4403" not in str(exc)
    main.browser_mgr.running.pop(pid, None)


def test_vnc_proxy_connects_websockify_path(app_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    create = app_client.post("/api/profiles", json={"name": "VncPath"})
    pid = create.json()["id"]
    _mock_running_profile(pid)
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
        f"/api/profiles/{pid}/vnc",
        headers={"origin": "http://testserver"},
        subprotocols=["binary"],
    ):
        pass

    assert captured["url"] == "ws://127.0.0.1:6100/websockify"
    kwargs = captured["kwargs"]
    assert kwargs["subprotocols"] == ["binary"]
    assert kwargs["compression"] is None
    assert kwargs["ping_interval"] is None
    main.browser_mgr.running.pop(pid, None)
