"""Tests for VNCManager — allocation logic and get_ws_port."""

from __future__ import annotations

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
