"""Tests for FastAPI routes via TestClient."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend import main
from backend.browser_manager import RunningProfile


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


def test_launch_success_response_invisible_playwright_no_cdp(app_client: TestClient):
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
        "cdp_url": None,
    }


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


def test_profile_response_has_cdp_url_field(app_client: TestClient):
    """Stopped profiles should have cdp_url=null."""
    app_client.post("/api/profiles", json={"name": "CdpShape"})
    resp = app_client.get("/api/profiles")
    for profile in resp.json():
        assert "cdp_url" in profile
        if profile["status"] == "stopped":
            assert profile["cdp_url"] is None


def test_status_stopped_has_cdp_url_null(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "CdpStatus"})
    pid = create.json()["id"]
    resp = app_client.get(f"/api/profiles/{pid}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cdp_url"] is None


def test_running_profile_has_no_cdp_url(app_client: TestClient):
    """Running invisible_playwright profiles keep noVNC, but do not expose CDP."""
    create = app_client.post("/api/profiles", json={"name": "CdpRunning"})
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
    assert data["cdp_url"] is None

    # Cleanup
    main.browser_mgr.running.pop(pid, None)


# ── CDP Proxy ───────────────────────────────────────────────────────────────


def test_cdp_json_version_not_running(app_client: TestClient):
    resp = app_client.get("/api/profiles/nonexistent/cdp/json/version")
    assert resp.status_code == 404


def test_cdp_json_list_not_running(app_client: TestClient):
    resp = app_client.get("/api/profiles/nonexistent/cdp/json/list")
    assert resp.status_code == 404


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
def test_cdp_http_running_returns_501(app_client: TestClient, path: str):
    """Firefox invisible_playwright profiles do not provide Chromium CDP."""
    create = app_client.post("/api/profiles", json={"name": "CdpUnavailable"})
    pid = create.json()["id"]
    _mock_running_profile(pid)

    resp = app_client.get(f"/api/profiles/{pid}{path}")

    assert resp.status_code == 501
    assert "CDP is not available" in resp.json()["detail"]
    main.browser_mgr.running.pop(pid, None)


def test_cdp_ws_running_closes_as_unavailable(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "CdpWsUnavailable"})
    pid = create.json()["id"]
    _mock_running_profile(pid)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with app_client.websocket_connect(
            f"/api/profiles/{pid}/cdp",
            headers={"origin": "http://testserver"},
        ) as ws:
            ws.receive_text()

    assert exc_info.value.code == 4006
    main.browser_mgr.running.pop(pid, None)


def test_cdp_page_ws_running_closes_as_unavailable(app_client: TestClient):
    create = app_client.post("/api/profiles", json={"name": "CdpPageUnavailable"})
    pid = create.json()["id"]
    _mock_running_profile(pid)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with app_client.websocket_connect(
            f"/api/profiles/{pid}/cdp/devtools/page/abc",
            headers={"origin": "http://testserver"},
        ) as ws:
            ws.receive_text()

    assert exc_info.value.code == 4006
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


def test_cdp_ws_rejects_cross_origin(app_client: TestClient):
    """CDP WebSocket should reject cross-origin browser connections."""
    create = app_client.post("/api/profiles", json={"name": "OriginCdp"})
    pid = create.json()["id"]
    _mock_running_profile(pid)

    with pytest.raises(Exception):
        with app_client.websocket_connect(
            f"/api/profiles/{pid}/cdp",
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
