"""Tests for BrowserManager invisible_playwright launch mapping."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
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


def test_build_invisible_pin_drops_non_public_screen_and_hardware_values():
    pin = bm._build_invisible_pin({
        "screen_width": 99999,
        "screen_height": -20,
        "hardware_concurrency": 999,
    })

    assert "screen.width" not in pin
    assert "screen.height" not in pin
    assert "screen.avail_width" not in pin
    assert "screen.avail_height" not in pin
    assert "hardware.concurrency" not in pin


def test_build_invisible_pin_drops_corrupted_screen_and_hardware_text():
    pin = bm._build_invisible_pin({
        "screen_width": "1920\nAuthorization: Bearer screen-super-secret",
        "screen_height": "1080?token=screen-super-secret",
        "hardware_concurrency": "8 cookie=screen-super-secret",
    })

    assert "screen.width" not in pin
    assert "screen.height" not in pin
    assert "hardware.concurrency" not in pin
    assert "screen-super-secret" not in repr(pin)


def test_build_invisible_pin_drops_non_public_gpu_text():
    pin = bm._build_invisible_pin({
        "gpu_vendor": "Google Inc. (NVIDIA)\nAuthorization: Bearer gpu-super-secret",
        "gpu_renderer": "ANGLE (NVIDIA)\nhttps://example.test/?token=gpu-super-secret",
    })

    assert "gpu.vendor" not in pin
    assert "gpu.renderer" not in pin
    assert "gpu-super-secret" not in repr(pin)


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


def test_build_invisible_kwargs_drops_non_public_fingerprint_seed_values(tmp_path: Path):
    kwargs = bm._build_invisible_kwargs({
        "fingerprint_seed": "https://seed.example/profile?token=seed-super-secret",
        "user_data_dir": str(tmp_path / "profile"),
        "proxy": None,
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "launch_args": None,
    })

    assert kwargs["seed"] is None
    assert "seed-super-secret" not in repr(kwargs)

    bool_kwargs = bm._build_invisible_kwargs({
        "fingerprint_seed": True,
        "user_data_dir": str(tmp_path / "profile-bool"),
        "proxy": None,
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "launch_args": None,
    })
    assert bool_kwargs["seed"] is None


def test_build_invisible_kwargs_drops_non_public_locale_text(tmp_path: Path):
    kwargs = bm._build_invisible_kwargs({
        "fingerprint_seed": 7,
        "user_data_dir": str(tmp_path / "profile"),
        "proxy": None,
        "timezone": "America/Los_Angeles",
        "locale": "en-US,fr;q=1 locale-super-secret",
        "launch_args": None,
    })

    assert kwargs["locale"] == "en-US"


def test_build_invisible_kwargs_drops_non_public_timezone_text(tmp_path: Path):
    kwargs = bm._build_invisible_kwargs({
        "fingerprint_seed": 7,
        "user_data_dir": str(tmp_path / "profile"),
        "proxy": None,
        "timezone": "America/Los_Angeles\r\nAuthorization: Bearer timezone-super-secret",
        "locale": "en-US",
        "launch_args": None,
    })

    assert kwargs["timezone"] == ""


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


def test_build_invisible_kwargs_pins_managed_firefox_identity(tmp_path: Path):
    kwargs = bm._build_invisible_kwargs({
        "fingerprint_seed": 7,
        "user_data_dir": str(tmp_path / "profile"),
        "user_agent": "Mozilla/5.0 custom",
        "proxy": None,
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "launch_args": None,
    })

    prefs = kwargs["extra_prefs"]
    assert prefs["general.useragent.override"] == bm.MANAGED_FIREFOX_USER_AGENT
    assert "Firefox/149.0" in prefs["general.useragent.override"]
    assert prefs["general.appversion.override"] == "5.0 (Windows)"
    assert prefs["general.platform.override"] == "Win32"
    assert prefs["general.oscpu.override"] == "Windows NT 10.0; Win64; x64"


def test_stealth_pref_category_normalizes_sensitive_pref_keys():
    assert bm._stealth_pref_category("zoom.stealth.fpp.hw_seed") == "fingerprint"
    assert bm._stealth_pref_category("zoom.stealth.seed") == "fingerprint"
    assert bm._stealth_pref_category("zoom.stealth.hw_concurrency") == "hardware"
    assert bm._stealth_pref_category("zoom.stealth.webgl2.extensions") == "webgl"
    assert bm._stealth_pref_category("zoom.stealth.canvas.noise_skip_mask") == "canvas"
    assert bm._stealth_pref_category("zoom.stealth.api-token-super-secret.value") == "unknown"
    assert bm._stealth_pref_category("general.useragent.override") is None


def test_invisible_stealth_pref_summary_degrades_without_full_package():
    bm._invisible_stealth_pref_summary.cache_clear()

    summary = bm._invisible_stealth_pref_summary()

    assert summary == {
        "stealth_pref_count": None,
        "stealth_pref_categories": [],
    }


def test_identity_metadata_debug_logs_error_type_without_raw_exception(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    bm._firefox_application_ini_metadata.cache_clear()
    caplog.set_level("DEBUG", logger="invisible_browser.manager.browser")

    download_module = ModuleType("invisible_playwright.download")

    def fail_ensure_binary():
        raise RuntimeError(
            "metadata-token-super-secret via /tmp/profile-secret/application.ini",
        )

    download_module.ensure_binary = fail_ensure_binary  # type: ignore[attr-defined]
    monkeypatch.setattr(sys.modules["invisible_playwright"], "__path__", [], raising=False)
    monkeypatch.setitem(sys.modules, "invisible_playwright.download", download_module)

    assert bm._firefox_application_ini_metadata() == {}
    assert (
        "action=browser.firefox_metadata_detection_skipped error_type=RuntimeError"
    ) in caplog.text
    assert "metadata-token-super-secret" not in caplog.text
    assert "/tmp/profile-secret" not in caplog.text


def test_stealth_pref_summary_debug_logs_error_type_without_raw_exception(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    bm._invisible_stealth_pref_summary.cache_clear()
    caplog.set_level("DEBUG", logger="invisible_browser.manager.browser")

    fpforge_module = ModuleType("invisible_playwright._fpforge")
    profile_module = ModuleType("invisible_playwright._fpforge.profile")
    prefs_module = ModuleType("invisible_playwright.prefs")

    def fail_generate_profile(_seed: int):
        raise RuntimeError("stealth-token-super-secret from https://secret.example")

    profile_module.generate_profile = fail_generate_profile  # type: ignore[attr-defined]
    prefs_module.translate_profile_to_prefs = lambda *args, **kwargs: {}  # type: ignore[attr-defined]
    monkeypatch.setattr(sys.modules["invisible_playwright"], "__path__", [], raising=False)
    monkeypatch.setattr(fpforge_module, "__path__", [], raising=False)
    monkeypatch.setitem(sys.modules, "invisible_playwright._fpforge", fpforge_module)
    monkeypatch.setitem(sys.modules, "invisible_playwright._fpforge.profile", profile_module)
    monkeypatch.setitem(sys.modules, "invisible_playwright.prefs", prefs_module)

    assert bm._invisible_stealth_pref_summary() == {
        "stealth_pref_count": None,
        "stealth_pref_categories": [],
    }
    assert (
        "action=browser.stealth_pref_summary_skipped error_type=RuntimeError"
    ) in caplog.text
    assert "stealth-token-super-secret" not in caplog.text
    assert "https://secret.example" not in caplog.text


def test_managed_firefox_identity_summary_discards_non_public_version_metadata(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        bm,
        "MANAGED_FIREFOX_USER_AGENT",
        "Mozilla/5.0 Firefox/149.0-token-super-secret",
    )
    monkeypatch.setattr(
        bm,
        "_invisible_playwright_package_version",
        lambda: "0.1.8-token-super-secret",
    )
    monkeypatch.setattr(
        bm,
        "_firefox_application_ini_metadata",
        lambda: {
            "Version": "150.0.1-token-super-secret",
            "BuildID": "20260521160037-token-super-secret",
        },
    )
    monkeypatch.setattr(
        bm,
        "_invisible_stealth_pref_summary",
        lambda: {"stealth_pref_count": 1, "stealth_pref_categories": ["canvas"]},
    )

    summary = bm.managed_firefox_identity_summary()

    assert summary["managed_user_agent_version"] is None
    assert summary["invisible_playwright_version"] is None
    assert summary["firefox_binary_version"] is None
    assert summary["firefox_binary_build_id"] is None
    assert "token-super-secret" not in str(summary)


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


def test_accept_language_header_drops_non_public_locale_text():
    header = bm._accept_language_header("en-US\r\nAuthorization: Bearer locale-super-secret")

    assert header == "en-US,en;q=0.9"
    assert "locale-super-secret" not in header
    assert "Authorization" not in header


def test_browser_init_script_aligns_navigator_languages():
    script = bm._browser_init_script("en-US")

    assert '"en-US"' in script
    assert "Navigator.prototype" in script
    assert "languages" in script
    assert "__clipboardText" in script


def test_browser_init_script_aligns_navigator_languages_with_accept_language_fallback():
    script = bm._browser_init_script("en-US")

    assert '["en-US", "en"]' in script


def test_browser_init_script_drops_non_public_locale_text():
    script = bm._browser_init_script("en-US\r\nAuthorization: Bearer locale-super-secret")

    assert "locale-super-secret" not in script
    assert "Authorization" not in script
    assert '["en-US", "en"]' in script


def test_browser_init_script_overrides_stale_navigator_build_id(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bm, "_firefox_build_id_override", lambda: "20260521160037")

    script = bm._browser_init_script("en-US")

    assert '"20260521160037"' in script
    assert "'buildID'" in script
    assert "Navigator.prototype" in script


def test_browser_init_script_drops_non_public_firefox_build_id(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        bm,
        "_firefox_application_ini_metadata",
        lambda: {"BuildID": "20260521160037-token-super-secret"},
    )

    script = bm._browser_init_script("en-US")

    assert "token-super-secret" not in script
    assert "20260521160037-token-super-secret" not in script
    assert "const __managerBuildID = null" in script


def test_coherent_webgl_renderer_collapses_modern_nvidia_to_firefox_sanitize_bucket():
    renderer = bm._coherent_webgl_renderer_override({
        "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"
    })

    assert renderer == (
        "ANGLE (NVIDIA, NVIDIA GeForce GTX 980 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    )


def test_with_coherent_webgl_identity_rewrites_profile_renderer():
    profile = {
        "gpu_vendor": "Google Inc. (NVIDIA)",
        "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
    }

    rewritten = bm._with_coherent_webgl_identity(profile)

    assert rewritten is not profile
    assert rewritten["gpu_renderer"] == (
        "ANGLE (NVIDIA, NVIDIA GeForce GTX 980 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    )
    assert profile["gpu_renderer"].endswith("RTX 3060 Direct3D11 vs_5_0 ps_5_0)")


def test_with_coherent_webgl_identity_drops_non_public_renderer_text():
    rewritten = bm._with_coherent_webgl_identity({
        "gpu_vendor": "Google Inc. (NVIDIA)",
        "gpu_renderer": "ANGLE (NVIDIA)\nAuthorization: Bearer gpu-super-secret",
    })

    assert rewritten["gpu_renderer"] == (
        "ANGLE (NVIDIA, NVIDIA GeForce GTX 980 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    )
    assert "gpu-super-secret" not in repr(rewritten)


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


@pytest.mark.asyncio
async def test_launch_drops_non_public_geoip_exit_ip_for_webrtc_env(
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
            "ip": "https://geoip.example/ip?token=webrtc-super-secret",
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
    monkeypatch.delenv("STEALTHFOX_WEBRTC_PUBLIC_IP", raising=False)

    mgr = BrowserManager()
    mgr.vnc.allocate = AsyncMock(return_value=(100, 6100))  # type: ignore[attr-defined]
    mgr.vnc.start_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]

    user_data_dir = tmp_path / "profile"
    user_data_dir.mkdir()

    await mgr.launch({
        "id": "profile-geoip-webrtc-redaction",
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

    assert seen_env == [None]
    assert "webrtc-super-secret" not in repr(mock_invisible_playwright.instances[0].kwargs)
    assert os.environ.get("STEALTHFOX_WEBRTC_PUBLIC_IP") is None

    await mgr.stop("profile-geoip-webrtc-redaction")


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


@pytest.mark.asyncio
async def test_stop_logs_fixed_error_type_without_runner_exception_text(
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level("WARNING", logger="invisible_browser.manager.browser")

    mgr = BrowserManager()
    runner = SimpleNamespace(
        __aexit__=AsyncMock(
            side_effect=RuntimeError("runner-token-super-secret /tmp/profile-secret")
        )
    )
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.running["profile-runner-log"] = bm.RunningProfile(
        profile_id="profile-runner-log",
        context=SimpleNamespace(close=AsyncMock()),
        display=111,
        ws_port=6111,
        engine="invisible_playwright",
        runner=runner,
    )

    await mgr.stop("profile-runner-log")

    mgr.vnc.stop_vnc.assert_awaited_once_with(111)
    assert (
        "action=profile.stop_runner_close_failed profile_id=profile-runner-log "
        "error_type=RuntimeError"
    ) in caplog.text
    assert "runner-token-super-secret" not in caplog.text
    assert "/tmp/profile-secret" not in caplog.text


@pytest.mark.asyncio
async def test_stop_logs_fixed_error_type_without_context_exception_text(
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level("WARNING", logger="invisible_browser.manager.browser")

    mgr = BrowserManager()
    context = SimpleNamespace(
        close=AsyncMock(
            side_effect=RuntimeError("context-token-super-secret /tmp/profile-secret")
        )
    )
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.running["profile-context-log"] = bm.RunningProfile(
        profile_id="profile-context-log",
        context=context,
        display=111,
        ws_port=6111,
        engine="invisible_playwright",
        runner=None,
    )

    await mgr.stop("profile-context-log")

    mgr.vnc.stop_vnc.assert_awaited_once_with(111)
    assert (
        "action=profile.stop_context_close_failed profile_id=profile-context-log "
        "error_type=RuntimeError"
    ) in caplog.text
    assert "context-token-super-secret" not in caplog.text
    assert "/tmp/profile-secret" not in caplog.text


# ── launch lifecycle ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_launch_clears_launching_state_when_vnc_allocation_fails(tmp_path: Path):
    mgr = BrowserManager()
    mgr.vnc.allocate = AsyncMock(side_effect=RuntimeError("no display available"))  # type: ignore[attr-defined]

    user_data_dir = tmp_path / "profile"
    user_data_dir.mkdir()

    with pytest.raises(RuntimeError, match="no display available"):
        await mgr.launch({
            "id": "profile-alloc-fail",
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

    assert "profile-alloc-fail" not in mgr._launching
    assert mgr.launch_failure_summary() == {
        "launch_failure_count": 1,
        "launch_failure_stage_counts": {"allocate_vnc": 1},
    }


@pytest.mark.asyncio
async def test_launch_releases_vnc_when_startup_state_cleanup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    mgr = BrowserManager()
    mgr.vnc.allocate = AsyncMock(return_value=(100, 6100))  # type: ignore[attr-defined]
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]

    user_data_dir = tmp_path / "profile"
    user_data_dir.mkdir()

    def fail_cleanup(_path: Path) -> None:
        raise PermissionError("startup state locked")

    monkeypatch.setattr(bm, "_clean_firefox_startup_state", fail_cleanup)

    with pytest.raises(PermissionError, match="startup state locked"):
        await mgr.launch({
            "id": "profile-cleanup-fail",
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

    assert "profile-cleanup-fail" not in mgr._launching
    mgr.vnc.stop_vnc.assert_awaited_once_with(100)
    assert mgr.launch_failure_summary() == {
        "launch_failure_count": 1,
        "launch_failure_stage_counts": {"cleanup_startup_state": 1},
    }


def test_launch_failure_summary_sanitizes_existing_stage_counts():
    mgr = BrowserManager()
    leak_marker = "launch-stage-secret"
    mgr._launch_failure_stage_counts = {
        "allocate_vnc": 2,
        f"https://stage.example/fail?token={leak_marker} Authorization=Bearer {leak_marker}": 3,
        "bootstrap_page": 0,
        "start_vnc": -1,
        "fit_window": True,
        "configure_context": "not-a-count",  # type: ignore[dict-item]
    }

    summary = mgr.launch_failure_summary()

    assert summary == {
        "launch_failure_count": 5,
        "launch_failure_stage_counts": {
            "allocate_vnc": 2,
            "unknown": 3,
        },
    }
    serialized = json.dumps(summary, sort_keys=True)
    assert leak_marker not in serialized
    assert "Authorization" not in serialized
    assert "Bearer" not in serialized
    assert "stage.example" not in serialized


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
async def test_lifecycle_logs_sanitize_sensitive_profile_ids(
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level("INFO", logger="invisible_browser.manager.browser")
    mgr = BrowserManager()
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]
    leak_marker = "profile-log-secret"
    polluted_profile_id = (
        f"https://profile.example/{leak_marker}"
        f"?token={leak_marker} Authorization=Bearer {leak_marker}"
    )

    mgr._record_launch_failure(polluted_profile_id, "allocate_vnc")
    mgr.running[polluted_profile_id] = bm.RunningProfile(
        profile_id=polluted_profile_id,
        context=SimpleNamespace(close=AsyncMock()),
        display=111,
        ws_port=6111,
        engine="invisible_playwright",
        runner=None,
    )
    await mgr.stop(polluted_profile_id)
    mgr.running[polluted_profile_id] = bm.RunningProfile(
        profile_id=polluted_profile_id,
        context=SimpleNamespace(close=AsyncMock()),
        display=112,
        ws_port=6112,
        engine="invisible_playwright",
        runner=None,
    )
    await mgr._on_browser_closed(polluted_profile_id)

    assert "action=profile.launch_failed profile_id=unknown stage=allocate_vnc" in caplog.text
    assert "action=profile.stop_requested profile_id=unknown" in caplog.text
    assert "action=profile.stop_finished profile_id=unknown" in caplog.text
    assert "action=profile.browser_closed profile_id=unknown" in caplog.text
    assert leak_marker not in caplog.text
    assert "Authorization" not in caplog.text
    assert "Bearer" not in caplog.text
    assert "profile.example" not in caplog.text


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
async def test_launch_uses_safe_display_dimensions_for_non_public_screen_values(
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

    running = await mgr.launch({
        "id": "profile-safe-display",
        "fingerprint_seed": 123,
        "user_data_dir": str(user_data_dir),
        "screen_width": "1920\nAuthorization: Bearer vnc-super-secret",
        "screen_height": "1080?token=vnc-super-secret",
        "proxy": None,
        "timezone": "Asia/Shanghai",
        "locale": "zh-CN",
        "humanize": False,
        "headless": False,
        "launch_args": [],
    })

    assert running.profile_id == "profile-safe-display"
    mgr.vnc.start_vnc.assert_awaited_once_with(100, 6100, width=1920, height=1080)
    assert calls == [(100, 1920, 1080)]
    assert "vnc-super-secret" not in repr(mgr.vnc.start_vnc.await_args)

    await mgr.stop("profile-safe-display")


@pytest.mark.asyncio
async def test_fit_firefox_window_debug_log_uses_error_type_without_raw_exception(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level("DEBUG", logger="invisible_browser.manager.browser")

    async def fail_subprocess(*args, **kwargs):
        raise RuntimeError("xdotool-token-super-secret via /tmp/profile-secret")

    monkeypatch.setattr(bm.shutil, "which", lambda _name: "/usr/bin/xdotool")
    monkeypatch.setattr(bm.asyncio, "create_subprocess_exec", fail_subprocess)

    await bm._fit_firefox_window_to_vnc(100, 1920, 1080)

    assert (
        "action=profile.fit_window_skipped display=:100 error_type=RuntimeError"
    ) in caplog.text
    assert "xdotool-token-super-secret" not in caplog.text
    assert "/tmp/profile-secret" not in caplog.text


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
async def test_launch_debug_logs_init_and_bootstrap_error_types_without_raw_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    mock_invisible_playwright,
):
    caplog.set_level("DEBUG", logger="invisible_browser.manager.browser")

    class InternalPage:
        url = "about:home"

        async def evaluate(self, script: str):
            raise RuntimeError("init-token-super-secret via https://secret.example/app")

    async def fake_enter(self):
        self.context.pages = [InternalPage()]
        self.context.new_page = AsyncMock(
            side_effect=RuntimeError("bootstrap-token-super-secret /tmp/profile-secret"),
        )
        return self.context

    async def fake_fit(display: int, width: int, height: int) -> None:
        return None

    monkeypatch.setattr(mock_invisible_playwright, "__aenter__", fake_enter)
    monkeypatch.setattr(bm, "_fit_firefox_window_to_vnc", fake_fit)

    mgr = BrowserManager()
    mgr.vnc.allocate = AsyncMock(return_value=(100, 6100))  # type: ignore[attr-defined]
    mgr.vnc.start_vnc = AsyncMock()  # type: ignore[attr-defined]
    mgr.vnc.stop_vnc = AsyncMock()  # type: ignore[attr-defined]

    user_data_dir = tmp_path / "profile"
    user_data_dir.mkdir()

    running = await mgr.launch({
        "id": "profile-debug-redaction",
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

    assert running.profile_id == "profile-debug-redaction"
    assert (
        "action=profile.existing_page_init_failed profile_id=profile-debug-redaction "
        "error_type=RuntimeError"
    ) in caplog.text
    assert (
        "action=profile.bootstrap_page_failed profile_id=profile-debug-redaction "
        "error_type=RuntimeError"
    ) in caplog.text
    assert "init-token-super-secret" not in caplog.text
    assert "bootstrap-token-super-secret" not in caplog.text
    assert "https://secret.example" not in caplog.text
    assert "/tmp/profile-secret" not in caplog.text

    await mgr.stop("profile-debug-redaction")


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


@pytest.mark.asyncio
async def test_auto_launch_all_logs_profile_ids_and_error_types_without_sensitive_text(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    from backend import database as db

    caplog.set_level("INFO", logger="invisible_browser.manager.browser")
    mgr = BrowserManager()

    profiles = [
        {"id": "auto-ok", "name": "ok-token-super-secret", "auto_launch": True},
        {"id": "auto-fail", "name": "fail-token-super-secret", "auto_launch": True},
    ]

    async def fake_launch(profile: dict):
        if profile["id"] == "auto-fail":
            raise RuntimeError("launch-token-super-secret /tmp/profile-secret")

    monkeypatch.setattr(db, "list_profiles", lambda: profiles)
    monkeypatch.setattr(mgr, "launch", fake_launch)

    await mgr.auto_launch_all()

    assert "action=profile.auto_launch_succeeded profile_id=auto-ok" in caplog.text
    assert (
        "action=profile.auto_launch_failed profile_id=auto-fail "
        "error_type=RuntimeError"
    ) in caplog.text
    assert "ok-token-super-secret" not in caplog.text
    assert "fail-token-super-secret" not in caplog.text
    assert "launch-token-super-secret" not in caplog.text
    assert "/tmp/profile-secret" not in caplog.text
