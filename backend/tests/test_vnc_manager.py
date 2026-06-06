"""Tests for VNCManager — allocation logic and get_ws_port."""

from __future__ import annotations

import builtins
from types import SimpleNamespace

import pytest

from backend import vnc_manager as vm
from backend.vnc_manager import VNCInstance, VNCManager


@pytest.fixture()
def vnc() -> VNCManager:
    return VNCManager()


# ── allocate ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_allocate_first(vnc: VNCManager):
    display, ws_port = await vnc.allocate()
    assert display == 100
    assert ws_port == 6100


@pytest.mark.asyncio
async def test_allocate_sequential(vnc: VNCManager):
    d1, p1 = await vnc.allocate()
    d2, p2 = await vnc.allocate()
    d3, p3 = await vnc.allocate()
    assert (d1, d2, d3) == (100, 101, 102)
    assert (p1, p2, p3) == (6100, 6101, 6102)


@pytest.mark.asyncio
async def test_allocate_fills_gap(vnc: VNCManager):
    """After freeing display 100, next allocate should reuse it."""
    await vnc.allocate()  # 100
    await vnc.allocate()  # 101
    # Simulate freeing display 100 (like stop_vnc would)
    vnc._allocated.pop(100)
    d, p = await vnc.allocate()
    assert d == 100  # gap filled
    assert p == 6100


@pytest.mark.asyncio
async def test_allocate_skips_unavailable_display_or_ws_port(
    vnc: VNCManager,
    monkeypatch: pytest.MonkeyPatch,
):
    unavailable = {(100, 6100)}
    monkeypatch.setattr(
        vnc,
        "_is_resource_available",
        lambda display, ws_port: (display, ws_port) not in unavailable,
    )

    display, ws_port = await vnc.allocate()

    assert (display, ws_port) == (101, 6101)
    assert 100 not in vnc._allocated
    assert 101 in vnc._allocated


@pytest.mark.asyncio
async def test_allocate_tracks_instances(vnc: VNCManager):
    await vnc.allocate()
    await vnc.allocate()
    assert len(vnc._allocated) == 2
    assert 100 in vnc._allocated
    assert 101 in vnc._allocated


@pytest.mark.asyncio
async def test_allocate_instance_fields(vnc: VNCManager):
    await vnc.allocate()
    instance = vnc._allocated[100]
    assert isinstance(instance, VNCInstance)
    assert instance.display == 100
    assert instance.ws_port == 6100
    assert instance.process is None  # not started yet


# ── get_ws_port ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_ws_port_allocated(vnc: VNCManager):
    await vnc.allocate()
    assert vnc.get_ws_port(100) == 6100


def test_get_ws_port_not_allocated(vnc: VNCManager):
    assert vnc.get_ws_port(999) is None


# ── active_displays ──────────────────────────────────────────────────────────


def test_active_displays_empty(vnc: VNCManager):
    assert vnc.active_displays == []


@pytest.mark.asyncio
async def test_active_displays_after_allocate(vnc: VNCManager):
    await vnc.allocate()
    await vnc.allocate()
    assert sorted(vnc.active_displays) == [100, 101]


# ── start_vnc ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_vnc_logs_action_without_internal_log_path(
    vnc: VNCManager,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    class FakeLogFile:
        def close(self) -> None:
            pass

    proc = SimpleNamespace(poll=lambda: None)
    async def fake_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(vm.shutil, "which", lambda _name: "/usr/bin/Xvnc")
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: FakeLogFile())
    monkeypatch.setattr(vm.subprocess, "Popen", lambda *args, **kwargs: proc)
    monkeypatch.setattr(vm.asyncio, "sleep", fake_sleep)
    caplog.set_level("INFO", logger="invisible_browser.manager.vnc")

    started = await vnc.start_vnc(100, 6100)

    assert started is proc
    assert "action=vnc.start_requested display=:100 ws_port=6100" in caplog.text
    assert "/tmp/xvnc-100.log" not in caplog.text


@pytest.mark.asyncio
async def test_start_vnc_log_read_failure_logs_error_type_without_raw_exception(
    vnc: VNCManager,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    class FakeLogFile:
        def close(self) -> None:
            pass

    def fake_open(path: str, mode: str = "r", *args, **kwargs):
        if mode == "w":
            return FakeLogFile()
        raise OSError("xvnc-log-token-super-secret via /tmp/xvnc-100.log")

    proc = SimpleNamespace(poll=lambda: 1)
    async def fake_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(vm.shutil, "which", lambda _name: "/usr/bin/Xvnc")
    monkeypatch.setattr(builtins, "open", fake_open)
    monkeypatch.setattr(vm.subprocess, "Popen", lambda *args, **kwargs: proc)
    monkeypatch.setattr(vm.asyncio, "sleep", fake_sleep)
    caplog.set_level("DEBUG", logger="invisible_browser.manager.vnc")

    with pytest.raises(RuntimeError, match=r"Xvnc failed to start on :100"):
        await vnc.start_vnc(100, 6100)

    assert "action=vnc.start_log_read_failed display=:100 error_type=OSError" in caplog.text
    assert "xvnc-log-token-super-secret" not in caplog.text
    assert "/tmp/xvnc-100.log" not in caplog.text


@pytest.mark.asyncio
async def test_start_vnc_failure_exception_omits_raw_xvnc_log(
    vnc: VNCManager,
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeLogFile:
        def __init__(self, text: str = ""):
            self.text = text

        def read(self) -> str:
            return self.text

        def close(self) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    def fake_open(path: str, mode: str = "r", *args, **kwargs):
        if mode == "w":
            return FakeLogFile()
        return FakeLogFile(
            "viewer_token=xvnc-super-secret http://127.0.0.1:6100/websockify"
        )

    proc = SimpleNamespace(poll=lambda: 1)

    async def fake_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(vm.shutil, "which", lambda _name: "/usr/bin/Xvnc")
    monkeypatch.setattr(builtins, "open", fake_open)
    monkeypatch.setattr(vm.subprocess, "Popen", lambda *args, **kwargs: proc)
    monkeypatch.setattr(vm.asyncio, "sleep", fake_sleep)

    with pytest.raises(RuntimeError) as exc_info:
        await vnc.start_vnc(100, 6100)

    message = str(exc_info.value)
    assert message == "Xvnc failed to start on :100"
    assert "xvnc-super-secret" not in message
    assert "websockify" not in message


# ── stop_vnc ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stop_vnc_logs_public_display_when_display_is_polluted(
    vnc: VNCManager,
    caplog: pytest.LogCaptureFixture,
):
    leak_marker = "runtime_service_token_stop_display_marker"
    polluted_display = f"100 token={leak_marker}"
    terminated: list[bool] = []
    waited: list[int] = []

    class FakeProcess:
        def terminate(self) -> None:
            terminated.append(True)

        def wait(self, timeout: int) -> None:
            waited.append(timeout)

        def kill(self) -> None:
            raise AssertionError("kill should not be needed")

    vnc._allocated[polluted_display] = VNCInstance(  # type: ignore[index, arg-type]
        display=polluted_display,  # type: ignore[arg-type]
        ws_port=6100,
        process=FakeProcess(),  # type: ignore[arg-type]
    )
    caplog.set_level("INFO", logger="invisible_browser.manager.vnc")

    await vnc.stop_vnc(polluted_display)  # type: ignore[arg-type]

    assert terminated == [True]
    assert waited == [5]
    assert "action=vnc.stop_requested display=unknown" in caplog.text
    for leaked in (
        leak_marker,
        "runtime_service_token",
        "token=",
    ):
        assert leaked not in caplog.text


# ── cleanup_stale ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cleanup_stale_kills_scoped_xvnc_processes(
    vnc: VNCManager,
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], capture_output: bool):
        calls.append(cmd)
        assert capture_output is True
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(vm.subprocess, "run", fake_run)

    await vnc.cleanup_stale()

    assert calls == [["pkill", "-f", r"Xvnc :[0-9]"]]
    assert "firefox" not in calls[0]
    assert ".*" not in calls[0][-1]


# ── BrowserManager.get_status ────────────────────────────────────────────────


def test_get_status_stopped():
    from backend.browser_manager import BrowserManager
    mgr = BrowserManager()
    status = mgr.get_status("nonexistent")
    assert status == {
        "status": "stopped",
        "vnc_ws_port": None,
        "display": None,
        "automation_url": None,
    }


def test_get_status_running():
    from backend.browser_manager import BrowserManager, RunningProfile
    from unittest.mock import MagicMock
    mgr = BrowserManager()
    mgr.running["abc"] = RunningProfile(
        profile_id="abc",
        context=MagicMock(),
        display=100,
        ws_port=6100,
        engine="invisible_playwright",
    )
    status = mgr.get_status("abc")
    assert status == {
        "status": "running",
        "vnc_ws_port": 6100,
        "display": ":100",
        "automation_url": "/api/profiles/abc/automation",
    }
