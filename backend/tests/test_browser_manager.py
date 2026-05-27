"""Tests for BrowserManager invisible_playwright launch mapping."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
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


def test_build_invisible_pin_uses_realistic_1080p_available_height():
    pin = bm._build_invisible_pin({
        "screen_width": 1920,
        "screen_height": 1080,
    })

    assert pin["screen.width"] == 1920
    assert pin["screen.height"] == 1080
    assert pin["screen.avail_width"] == 1920
    assert pin["screen.avail_height"] == 1032


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


def test_build_invisible_kwargs_suppresses_webrtc_host_candidates(tmp_path: Path):
    kwargs = bm._build_invisible_kwargs({
        "fingerprint_seed": 7,
        "user_data_dir": str(tmp_path / "profile"),
        "proxy": None,
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "launch_args": None,
    })

    assert kwargs["extra_prefs"]["media.peerconnection.ice.no_host"] is True
    assert kwargs["extra_prefs"]["media.peerconnection.ice.default_address_only"] is True
    assert kwargs["extra_prefs"]["media.peerconnection.ice.obfuscate_host_addresses"] is False
    assert kwargs["extra_prefs"]["media.peerconnection.ice.disableIPv6"] is True


def test_build_invisible_kwargs_drops_user_window_size_overrides(tmp_path: Path):
    kwargs = bm._build_invisible_kwargs({
        "fingerprint_seed": 7,
        "user_data_dir": str(tmp_path / "profile"),
        "screen_width": 1920,
        "screen_height": 1080,
        "launch_args": ["--width=800", "--height", "600", "--private-window"],
    })

    assert kwargs["extra_args"] == ["--private-window"]


def test_accept_language_header_includes_base_language():
    assert bm._accept_language_header("en-US") == "en-US,en;q=0.9"
    assert bm._accept_language_header("zh_CN") == "zh-CN,zh;q=0.9"
    assert bm._accept_language_header("ja") == "ja"


def test_browser_init_script_aligns_navigator_languages():
    script = bm._browser_init_script("en-US")

    assert '"en-US"' in script
    assert "Navigator.prototype" in script
    assert "languages" in script
    assert "__clipboardText" in script


def test_clean_firefox_startup_state_removes_session_restore_without_lock(tmp_path: Path):
    profile_dir = tmp_path / "profile"
    session_dir = profile_dir / "sessionstore-backups"
    session_dir.mkdir(parents=True)
    (session_dir / "previous.jsonlz4").write_text("stale session")
    (session_dir / "recovery.jsonlz4").write_text("stale session")
    (profile_dir / "cookies.sqlite").write_text("site data")

    bm._clean_firefox_startup_state(profile_dir)

    assert not (session_dir / "previous.jsonlz4").exists()
    assert not (session_dir / "recovery.jsonlz4").exists()
    assert (profile_dir / "cookies.sqlite").read_text() == "site data"


@pytest.mark.asyncio
async def test_launch_resolves_missing_timezone_and_locale_before_invisible_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_invisible_playwright,
):
    async def fake_resolve(profile: dict):
        resolved = dict(profile)
        resolved["timezone"] = "America/Los_Angeles"
        resolved["locale"] = "en-US"
        return resolved

    monkeypatch.setattr(bm, "resolve_profile_network_fingerprint", fake_resolve)

    mgr = BrowserManager()
    mgr.vnc.allocate = AsyncMock(return_value=(100, 6100))  # type: ignore[attr-defined]
    mgr.vnc.start_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]

    user_data_dir = tmp_path / "profile"
    user_data_dir.mkdir()

    await mgr.launch({
        "id": "profile-geoip",
        "fingerprint_seed": 123,
        "user_data_dir": str(user_data_dir),
        "screen_width": 1366,
        "screen_height": 768,
        "proxy": None,
        "timezone": None,
        "locale": None,
        "humanize": False,
        "headless": False,
        "launch_args": [],
    })

    launch = mock_invisible_playwright.instances[0]
    assert launch.kwargs["timezone"] == "America/Los_Angeles"
    assert launch.kwargs["locale"] == "en-US"
    launch.context.set_extra_http_headers.assert_awaited_once_with({
        "Accept-Language": "en-US,en;q=0.9",
    })

    await mgr.stop("profile-geoip")


@pytest.mark.asyncio
async def test_launch_passes_geoip_exit_ip_to_invisible_webrtc_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_invisible_playwright,
):
    async def fake_resolve(profile: dict):
        resolved = dict(profile)
        resolved["timezone"] = "America/Los_Angeles"
        resolved["locale"] = "en-US"
        resolved["_geoip_result"] = {
            "timezone": "America/Los_Angeles",
            "locale": "en-US",
            "ip": "23.144.4.92",
            "country_code": "US",
            "source": "test-direct",
        }
        return resolved

    seen_env: list[str | None] = []

    async def fake_enter(self):
        seen_env.append(os.environ.get("STEALTHFOX_WEBRTC_PUBLIC_IP"))
        return self.context

    monkeypatch.setattr(bm, "resolve_profile_network_fingerprint", fake_resolve)
    monkeypatch.setattr(mock_invisible_playwright, "__aenter__", fake_enter)
    monkeypatch.setenv("STEALTHFOX_WEBRTC_PUBLIC_IP", "198.51.100.10")

    mgr = BrowserManager()
    mgr.vnc.allocate = AsyncMock(return_value=(100, 6100))  # type: ignore[attr-defined]
    mgr.vnc.start_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]

    user_data_dir = tmp_path / "profile"
    user_data_dir.mkdir()

    await mgr.launch({
        "id": "profile-geoip-webrtc",
        "fingerprint_seed": 123,
        "user_data_dir": str(user_data_dir),
        "screen_width": 1366,
        "screen_height": 768,
        "proxy": None,
        "timezone": None,
        "locale": None,
        "geoip": True,
        "humanize": False,
        "headless": False,
        "launch_args": [],
    })

    assert seen_env == ["23.144.4.92"]
    assert os.environ["STEALTHFOX_WEBRTC_PUBLIC_IP"] == "198.51.100.10"

    await mgr.stop("profile-geoip-webrtc")


def test_build_invisible_kwargs_filters_chromium_only_launch_args(tmp_path: Path):
    kwargs = bm._build_invisible_kwargs({
        "fingerprint_seed": 7,
        "user_data_dir": str(tmp_path / "profile"),
        "launch_args": [
            "--private-window",
            "--remote-debugging-port=9222",
            "--remote-debugging-address",
            "0.0.0.0",
            "--fingerprint=123",
            "--fingerprint-platform=windows",
            "--disable-features=AutomationControlled",
            "--use-angle=swiftshader",
            "--load-extension",
            "/data/chrome-extension",
            "--profile",
            "/tmp/other-profile",
            "--headless",
        ],
    })

    assert kwargs["extra_args"] == ["--private-window"]


@pytest.mark.asyncio
async def test_stop_without_runner_closes_context_and_releases_vnc():
    mgr = BrowserManager()
    context = SimpleNamespace(close=AsyncMock())
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.running["profile-context"] = bm.RunningProfile(
        profile_id="profile-context",
        context=context,
        display=111,
        ws_port=6111,
        engine="invisible_playwright",
        runner=None,
    )

    await mgr.stop("profile-context")

    context.close.assert_awaited_once()
    mgr.vnc.stop_vnc.assert_awaited_once_with(111)
    assert "profile-context" not in mgr.running


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
    session_dir = user_data_dir / "sessionstore-backups"
    session_dir.mkdir()
    (user_data_dir / "sessionCheckpoints.json").write_text("{}")
    (session_dir / "recovery.jsonlz4").write_text("stale session")
    (session_dir / "previous.jsonlz4").write_text("stale session")
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
    assert not (user_data_dir / "sessionCheckpoints.json").exists()
    assert not (session_dir / "recovery.jsonlz4").exists()
    assert not (session_dir / "previous.jsonlz4").exists()

    mgr.vnc.start_vnc.assert_awaited_once_with(100, 6100, width=1366, height=768)
    launch.context.add_init_script.assert_awaited_once()
    launch.context.set_extra_http_headers.assert_awaited_once_with({
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    launch.context.on.assert_called_once()

    await mgr.stop("profile-1")
    assert launch.closed is True
    mgr.vnc.stop_vnc.assert_awaited_once_with(100)


@pytest.mark.asyncio
async def test_launch_and_stop_logs_include_action_and_profile_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_invisible_playwright,
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level("INFO", logger="invisible_browser.manager.browser")
    mgr = BrowserManager()
    mgr.vnc.allocate = AsyncMock(return_value=(100, 6100))  # type: ignore[attr-defined]
    mgr.vnc.start_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]

    user_data_dir = tmp_path / "profile"
    user_data_dir.mkdir()
    await mgr.launch({
        "id": "profile-log",
        "fingerprint_seed": 123,
        "user_data_dir": str(user_data_dir),
        "screen_width": 1366,
        "screen_height": 768,
        "proxy": None,
        "timezone": None,
        "locale": None,
        "humanize": False,
        "headless": False,
        "launch_args": [],
    })
    await mgr.stop("profile-log")

    assert "action=profile.launch_succeeded profile_id=profile-log" in caplog.text
    assert "action=profile.stop_requested profile_id=profile-log" in caplog.text
    assert "action=profile.stop_finished profile_id=profile-log" in caplog.text
    assert str(user_data_dir) not in caplog.text


@pytest.mark.asyncio
async def test_launch_fits_firefox_window_to_vnc_after_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_invisible_playwright,
):
    calls: list[tuple[int, int, int]] = []

    async def fake_fit(display: int, width: int, height: int) -> None:
        calls.append((display, width, height))

    monkeypatch.setattr(bm, "_fit_firefox_window_to_vnc", fake_fit)

    mgr = BrowserManager()
    mgr.vnc.allocate = AsyncMock(return_value=(100, 6100))  # type: ignore[attr-defined]
    mgr.vnc.start_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]

    user_data_dir = tmp_path / "profile"
    user_data_dir.mkdir()

    await mgr.launch({
        "id": "profile-window-fit",
        "fingerprint_seed": 123,
        "user_data_dir": str(user_data_dir),
        "screen_width": 1920,
        "screen_height": 1080,
        "proxy": None,
        "timezone": "Asia/Shanghai",
        "locale": "zh-CN",
        "humanize": False,
        "headless": False,
        "launch_args": [],
    })

    assert calls == [(100, 1920, 1080)]

    await mgr.stop("profile-window-fit")


@pytest.mark.asyncio
async def test_launch_does_not_block_on_existing_page_init_script_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_invisible_playwright,
):
    class HangingPage:
        async def evaluate(self, script: str):
            await asyncio.Event().wait()

    async def fake_enter(self):
        self.context.pages = [HangingPage()]
        return self.context

    monkeypatch.setattr(mock_invisible_playwright, "__aenter__", fake_enter)
    monkeypatch.setattr(bm, "EXISTING_PAGE_INIT_TIMEOUT_SECONDS", 0.01, raising=False)

    mgr = BrowserManager()
    mgr.vnc.allocate = AsyncMock(return_value=(100, 6100))  # type: ignore[attr-defined]
    mgr.vnc.start_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]

    user_data_dir = tmp_path / "profile"
    user_data_dir.mkdir()

    running = await asyncio.wait_for(
        mgr.launch({
            "id": "profile-slow-existing-page",
            "fingerprint_seed": 123,
            "user_data_dir": str(user_data_dir),
            "screen_width": 1366,
            "screen_height": 768,
            "proxy": None,
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "humanize": False,
            "headless": False,
            "launch_args": [],
        }),
        timeout=0.5,
    )

    assert running.profile_id == "profile-slow-existing-page"
    assert mgr.get_status("profile-slow-existing-page")["status"] == "running"

    await mgr.stop("profile-slow-existing-page")


@pytest.mark.asyncio
async def test_launch_creates_automation_blank_page_when_only_internal_pages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_invisible_playwright,
):
    class InternalPage:
        url = "about:home"

        async def evaluate(self, script: str):
            return None

    async def fake_enter(self):
        self.context.pages = [InternalPage()]
        self.context.new_page = AsyncMock()
        return self.context

    monkeypatch.setattr(mock_invisible_playwright, "__aenter__", fake_enter)

    mgr = BrowserManager()
    mgr.vnc.allocate = AsyncMock(return_value=(100, 6100))  # type: ignore[attr-defined]
    mgr.vnc.start_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]

    user_data_dir = tmp_path / "profile"
    user_data_dir.mkdir()

    await mgr.launch({
        "id": "profile-internal-only",
        "fingerprint_seed": 123,
        "user_data_dir": str(user_data_dir),
        "screen_width": 1366,
        "screen_height": 768,
        "proxy": None,
        "timezone": "Asia/Shanghai",
        "locale": "zh-CN",
        "humanize": False,
        "headless": False,
        "launch_args": [],
    })

    launch = mock_invisible_playwright.instances[0]
    launch.context.new_page.assert_awaited_once()

    await mgr.stop("profile-internal-only")


@pytest.mark.asyncio
async def test_cleanup_stale_kills_scoped_invisible_playwright_firefox(
    monkeypatch: pytest.MonkeyPatch,
):
    mgr = BrowserManager()
    mgr.vnc.cleanup_stale = AsyncMock()  # type: ignore[attr-defined]
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], capture_output: bool):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(bm.subprocess, "run", fake_run)

    await mgr.cleanup_stale()

    mgr.vnc.cleanup_stale.assert_awaited_once()
    assert ["pkill", "-f", bm.INVISIBLE_FIREFOX_PROCESS_PATTERN] in calls
    assert "invisible-playwright" in bm.INVISIBLE_FIREFOX_PROCESS_PATTERN
    assert "firefox" in bm.INVISIBLE_FIREFOX_PROCESS_PATTERN


@pytest.mark.asyncio
async def test_auto_launch_all_launches_only_enabled_profiles(
    monkeypatch: pytest.MonkeyPatch,
):
    from backend import database as db

    mgr = BrowserManager()
    launched: list[str] = []

    profiles = [
        {"id": "manual", "name": "Manual", "auto_launch": False},
        {"id": "auto-1", "name": "Auto 1", "auto_launch": True},
        {"id": "auto-2", "name": "Auto 2", "auto_launch": True},
    ]

    async def fake_launch(profile: dict):
        launched.append(profile["id"])
        if profile["id"] == "auto-1":
            raise RuntimeError("launch failed")

    monkeypatch.setattr(db, "list_profiles", lambda: profiles)
    monkeypatch.setattr(mgr, "launch", fake_launch)

    await mgr.auto_launch_all()

    assert launched == ["auto-1", "auto-2"]
