"""Tests for BrowserManager invisible_playwright launch mapping."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from backend import browser_manager as bm

BrowserManager = bm.BrowserManager


# ── _normalize_proxy ─────────────────────────────────────────────────────────


def test_normalize_already_http():
    assert bm._normalize_proxy("http://user:pass@host:8080") == "http://user:pass@host:8080"


def test_normalize_already_https():
    assert bm._normalize_proxy("https://host:443") == "https://host:443"


def test_normalize_already_socks5():
    assert bm._normalize_proxy("socks5://host:1080") == "socks5://host:1080"


def test_normalize_host_port_user_pass():
    assert bm._normalize_proxy("proxy.com:8080:myuser:mypass") == "http://myuser:mypass@proxy.com:8080"


def test_normalize_host_port_only():
    assert bm._normalize_proxy("proxy.com:8080") == "http://proxy.com:8080"


def test_normalize_three_parts():
    # 3 parts doesn't match any pattern — returned as-is
    assert bm._normalize_proxy("a:b:c") == "a:b:c"


def test_normalize_five_parts():
    # 5 parts doesn't match — returned as-is
    assert bm._normalize_proxy("a:b:c:d:e") == "a:b:c:d:e"


def test_normalize_empty_parts():
    # host:port:user:pass with empty parts
    result = bm._normalize_proxy(":8080:user:pass")
    assert result == "http://user:pass@:8080"


# ── _validate_proxy ──────────────────────────────────────────────────────────


def test_validate_valid_http():
    bm._validate_proxy("http://proxy.com:8080")  # should not raise


def test_validate_valid_socks5():
    bm._validate_proxy("socks5://proxy.com:1080")  # should not raise


def test_validate_valid_with_auth():
    bm._validate_proxy("http://user:pass@proxy.com:8080")  # should not raise


def test_validate_bad_scheme():
    with pytest.raises(ValueError, match="Invalid proxy scheme 'ftp'"):
        bm._validate_proxy("ftp://host:80")


def test_validate_no_hostname():
    with pytest.raises(ValueError, match="missing hostname"):
        bm._validate_proxy("http://:8080")


def test_validate_no_port():
    with pytest.raises(ValueError, match="missing port"):
        bm._validate_proxy("http://host")


# ── _proxy_to_invisible ──────────────────────────────────────────────────────


def test_proxy_to_invisible_none():
    assert bm._proxy_to_invisible(None) is None


def test_proxy_to_invisible_http_with_auth():
    assert bm._proxy_to_invisible("http://user:pass@proxy.com:8080") == {
        "server": "http://proxy.com:8080",
        "username": "user",
        "password": "pass",
    }


def test_proxy_to_invisible_https_no_auth():
    assert bm._proxy_to_invisible("https://proxy.com:443") == {
        "server": "https://proxy.com:443",
    }


def test_proxy_to_invisible_socks5_no_auth():
    assert bm._proxy_to_invisible("socks5://proxy.com:1080") == {
        "server": "socks5://proxy.com:1080",
    }


def test_proxy_to_invisible_normalizes_host_port_user_pass():
    assert bm._proxy_to_invisible("proxy.com:8080:myuser:mypass") == {
        "server": "http://proxy.com:8080",
        "username": "myuser",
        "password": "mypass",
    }


# ── _build_invisible_pin ─────────────────────────────────────────────────────


def test_build_invisible_pin_screen_gpu_hardware_dark_theme():
    pin = bm._build_invisible_pin({
        "screen_width": 2560,
        "screen_height": 1440,
        "gpu_vendor": "Google Inc. (NVIDIA)",
        "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11)",
        "hardware_concurrency": 12,
        "color_scheme": "dark",
    })
    assert pin == {
        "screen.width": 2560,
        "screen.height": 1440,
        "screen.avail_width": 2560,
        "screen.avail_height": 1400,
        "gpu.vendor": "Google Inc. (NVIDIA)",
        "gpu.renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11)",
        "hardware.concurrency": 12,
        "dark_theme": True,
    }


def test_build_invisible_pin_light_theme():
    assert bm._build_invisible_pin({"color_scheme": "light"})["dark_theme"] is False


def test_build_invisible_pin_no_preference_does_not_pin_theme():
    assert "dark_theme" not in bm._build_invisible_pin({"color_scheme": "no-preference"})


# ── _build_invisible_kwargs ──────────────────────────────────────────────────


def test_build_invisible_kwargs_maps_manager_profile(tmp_path: Path):
    user_data_dir = tmp_path / "profile"
    profile = {
        "fingerprint_seed": 42,
        "user_data_dir": str(user_data_dir),
        "proxy": "http://user:pass@proxy.com:8080",
        "timezone": "America/New_York",
        "locale": "en-US",
        "screen_width": 1366,
        "screen_height": 768,
        "gpu_vendor": "Google Inc. (Intel)",
        "gpu_renderer": "ANGLE (Intel, Intel UHD Graphics Direct3D11)",
        "hardware_concurrency": 8,
        "color_scheme": "dark",
        "launch_args": ["--safe-mode"],
        "humanize": True,
        "headless": True,
    }
    kwargs = bm._build_invisible_kwargs(profile)

    assert kwargs["seed"] == 42
    assert kwargs["profile_dir"] == str(user_data_dir)
    assert kwargs["proxy"] == {
        "server": "http://proxy.com:8080",
        "username": "user",
        "password": "pass",
    }
    assert kwargs["timezone"] == "America/New_York"
    assert kwargs["locale"] == "en-US"
    assert kwargs["headless"] is False
    assert kwargs["humanize"] is True
    assert kwargs["extra_args"] == ["--safe-mode"]
    assert kwargs["pin"]["screen.width"] == 1366
    assert kwargs["pin"]["screen.height"] == 768
    assert kwargs["pin"]["dark_theme"] is True


def test_build_invisible_kwargs_omits_empty_optional_values(tmp_path: Path):
    kwargs = bm._build_invisible_kwargs({
        "fingerprint_seed": 7,
        "user_data_dir": str(tmp_path / "profile"),
        "proxy": None,
        "timezone": "",
        "locale": "",
        "launch_args": None,
    })
    assert kwargs["seed"] == 7
    assert kwargs["proxy"] is None
    assert kwargs["timezone"] == ""
    assert kwargs["locale"] == "en-US"
    assert kwargs["extra_args"] == []


# ── launch lifecycle ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_launch_uses_invisible_playwright_on_vnc_display(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_invisible_playwright,
):
    mgr = BrowserManager()
    mgr.vnc.allocate = AsyncMock(return_value=(100, 6100))  # type: ignore[attr-defined]
    mgr.vnc.start_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]

    user_data_dir = tmp_path / "profile"
    user_data_dir.mkdir()
    for lock_file in ("SingletonLock", "SingletonCookie", "SingletonSocket", ".parentlock", "lock"):
        (user_data_dir / lock_file).write_text("stale")
    monkeypatch.setenv("DISPLAY", ":77")

    running = await mgr.launch({
        "id": "profile-1",
        "fingerprint_seed": 123,
        "user_data_dir": str(user_data_dir),
        "screen_width": 1366,
        "screen_height": 768,
        "proxy": "socks5://proxy.com:1080",
        "timezone": "Asia/Shanghai",
        "locale": "zh-CN",
        "humanize": True,
        "headless": False,
        "launch_args": ["--private-window"],
    })

    assert running.profile_id == "profile-1"
    assert running.engine == "invisible_playwright"
    assert running.display == 100
    assert running.ws_port == 6100
    assert os.environ["DISPLAY"] == ":77"

    assert len(mock_invisible_playwright.instances) == 1
    launch = mock_invisible_playwright.instances[0]
    assert launch.kwargs["seed"] == 123
    assert launch.kwargs["profile_dir"] == str(user_data_dir)
    assert launch.kwargs["proxy"] == {"server": "socks5://proxy.com:1080"}
    assert launch.kwargs["timezone"] == "Asia/Shanghai"
    assert launch.kwargs["locale"] == "zh-CN"
    assert launch.kwargs["headless"] is False
    assert launch.kwargs["extra_args"] == ["--private-window"]
    assert not any(arg.startswith("--remote-debugging-port=") for arg in launch.kwargs["extra_args"])
    assert not (user_data_dir / "Default" / "Bookmarks").exists()
    assert not (user_data_dir / "Default" / "Preferences").exists()
    assert not (user_data_dir / "SingletonLock").exists()
    assert not (user_data_dir / ".parentlock").exists()
    assert not (user_data_dir / "lock").exists()

    mgr.vnc.start_vnc.assert_awaited_once_with(100, 6100, width=1366, height=768)
    launch.context.add_init_script.assert_awaited_once()
    launch.context.on.assert_called_once()

    await mgr.stop("profile-1")
    assert launch.closed is True
    mgr.vnc.stop_vnc.assert_awaited_once_with(100)
