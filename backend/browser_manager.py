"""Launch/stop/track invisible_playwright browser instances per profile."""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from invisible_playwright.async_api import InvisiblePlaywright

from .geoip import resolve_profile_network_fingerprint
from .vnc_manager import VNCManager

logger = logging.getLogger("invisible_browser.manager.browser")

INVISIBLE_FIREFOX_PROCESS_PATTERN = r"\.cache/invisible-playwright/.*/firefox"
EXISTING_PAGE_INIT_TIMEOUT_SECONDS = 2.0
INTERNAL_FIREFOX_PAGE_URLS = {"about:home", "about:newtab", "about:welcome"}
DEFAULT_TASKBAR_HEIGHT_PX = 40
WINDOWS_1080P_TASKBAR_HEIGHT_PX = 48
DEFAULT_WEBGL_RENDERER = "ANGLE (NVIDIA, NVIDIA GeForce GTX 980 Direct3D11 vs_5_0 ps_5_0, D3D11)"
DEFAULT_DISPLAY_WIDTH_PX = 1920
DEFAULT_DISPLAY_HEIGHT_PX = 1080
MIN_SCREEN_DIMENSION_PX = 320
MAX_SCREEN_DIMENSION_PX = 8192
PUBLIC_HARDWARE_CONCURRENCY_VALUES = frozenset({1, 2, 4, 6, 8, 10, 12, 16, 24, 32})
MAX_RUNNING_PROFILES_ENV = "MAX_RUNNING_PROFILES"
WEBRTC_PUBLIC_IP_ENV = "STEALTHFOX_WEBRTC_PUBLIC_IP"
MANAGED_FIREFOX_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) "
    "Gecko/20100101 Firefox/149.0"
)
DEFAULT_BROWSER_LOCALE = "en-US"
MANAGED_FIREFOX_IDENTITY_PREFS = {
    "general.useragent.override": MANAGED_FIREFOX_USER_AGENT,
    "general.appversion.override": "5.0 (Windows)",
    "general.platform.override": "Win32",
    "general.oscpu.override": "Windows NT 10.0; Win64; x64",
}
WEBRTC_LOCAL_IP_SUPPRESSION_PREFS = {
    "media.peerconnection.ice.no_host": True,
    "media.peerconnection.ice.default_address_only": True,
    "media.peerconnection.ice.obfuscate_host_addresses": False,
    "media.peerconnection.ice.disableIPv6": True,
}
PUBLIC_VERSION_RE = re.compile(r"^\d+(?:\.\d+){0,5}$")
PUBLIC_FIREFOX_BUILD_ID_RE = re.compile(r"^\d{8,20}$")
PUBLIC_LOCALE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-(?:[A-Za-z]{2,8}|\d{3})){0,2}$")
PUBLIC_TIMEZONE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._+-]*(?:/[A-Za-z0-9._+-]+){0,3}$")
PUBLIC_GPU_TEXT_RE = re.compile(r"^[A-Za-z0-9 .,_()+:/\\-]{1,160}$")
SENSITIVE_TEXT_RE = re.compile(
    r"(?:https?://|[?&#]|authorization:|bearer\s+|token=|password=|secret=|cookie=)",
    re.IGNORECASE,
)
PUBLIC_PROFILE_LOG_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
STEALTH_PREF_CATEGORY_ALIASES = {
    "fpp": "fingerprint",
    "hw_concurrency": "hardware",
    "seed": "fingerprint",
    "webgl2": "webgl",
}
PUBLIC_STEALTH_PREF_CATEGORIES = frozenset({
    "audio",
    "canvas",
    "debugger",
    "fingerprint",
    "font",
    "hardware",
    "screen",
    "storage",
    "timezone",
    "voices",
    "webgl",
    "webrtc",
    "unknown",
})
LAUNCH_FAILURE_STAGES = frozenset({
    "validate_proxy",
    "claim_launch_slot",
    "resource_limit",
    "allocate_vnc",
    "cleanup_startup_state",
    "start_vnc",
    "resolve_network_fingerprint",
    "build_launch_kwargs",
    "enter_browser",
    "configure_context",
    "bootstrap_page",
    "fit_window",
    "publish_running",
    "unknown",
})


class BrowserResourceLimitError(RuntimeError):
    """Raised before launch when a configured browser resource limit is reached."""


def _normalize_proxy(raw: str) -> str:
    """Convert common proxy formats to http://user:pass@host:port.

    Accepts:
      - http://user:pass@host:port  (already valid)
      - host:port:user:pass
      - host:port
    """
    if raw.startswith(("http://", "https://", "socks5://")):
        return raw
    parts = raw.split(":")
    if len(parts) == 4:
        host, port, user, passwd = parts
        return f"http://{user}:{passwd}@{host}:{port}"
    if len(parts) == 2:
        return f"http://{raw}"
    return raw


def _validate_proxy(url: str) -> None:
    """Validate that a normalized proxy URL has scheme, host, and port."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", "socks5"):
        raise ValueError(
            f"Invalid proxy scheme '{parsed.scheme}'. Must be http, https, or socks5."
        )
    if not parsed.hostname:
        raise ValueError(f"Proxy URL missing hostname: {_redact_proxy_url(url)}")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"Proxy URL invalid port: {_redact_proxy_url(url)}") from exc
    if not port:
        raise ValueError(f"Proxy URL missing port: {_redact_proxy_url(url)}")


def _redact_proxy_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url

    host = parsed.hostname or ""
    try:
        port = parsed.port
    except ValueError:
        port = None
    port_part = f":{port}" if port else ""
    return f"{parsed.scheme}://{host}{port_part}"


def _public_profile_log_id(profile_id: Any) -> str:
    if not isinstance(profile_id, str):
        return "unknown"
    text = profile_id.strip()
    if not text:
        return "unknown"
    if not PUBLIC_PROFILE_LOG_ID_RE.fullmatch(text):
        return "unknown"
    if SENSITIVE_TEXT_RE.search(text):
        return "unknown"
    return text


def get_max_running_profiles_limit() -> int | None:
    raw = os.environ.get(MAX_RUNNING_PROFILES_ENV)
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid integer config for %s", MAX_RUNNING_PROFILES_ENV)
        return None
    if value < 1:
        logger.warning("Ignoring out-of-range integer config for %s", MAX_RUNNING_PROFILES_ENV)
        return None
    return value


def _proxy_to_invisible(raw: str | None) -> dict[str, str] | None:
    """Convert Manager proxy text into invisible_playwright's proxy dict."""
    if not raw:
        return None

    normalized = _normalize_proxy(raw)
    _validate_proxy(normalized)
    parsed = urlparse(normalized)
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    result = {"server": f"{parsed.scheme}://{host}:{parsed.port}"}
    if parsed.username is not None:
        result["username"] = unquote(parsed.username)
    if parsed.password is not None:
        result["password"] = unquote(parsed.password)
    return result


def _build_invisible_pin(profile: dict[str, Any]) -> dict[str, Any]:
    """Map Manager profile fields to invisible_playwright pin keys."""
    pin: dict[str, Any] = {}

    width = _public_screen_dimension(profile.get("screen_width"))
    height = _public_screen_dimension(profile.get("screen_height"))
    if width is not None:
        pin["screen.width"] = width
        pin["screen.avail_width"] = width
    if height is not None:
        pin["screen.height"] = height
        taskbar_height = (
            WINDOWS_1080P_TASKBAR_HEIGHT_PX
            if height == 1080
            else DEFAULT_TASKBAR_HEIGHT_PX
        )
        pin["screen.avail_height"] = max(1, height - taskbar_height)

    gpu_vendor = _public_gpu_text(profile.get("gpu_vendor"))
    if gpu_vendor:
        pin["gpu.vendor"] = gpu_vendor
    gpu_renderer = _public_gpu_text(profile.get("gpu_renderer"))
    if gpu_renderer:
        pin["gpu.renderer"] = gpu_renderer

    hardware_concurrency = _public_hardware_concurrency(profile.get("hardware_concurrency"))
    if hardware_concurrency is not None:
        pin["hardware.concurrency"] = hardware_concurrency

    color_scheme = profile.get("color_scheme")
    if color_scheme == "dark":
        pin["dark_theme"] = True
    elif color_scheme == "light":
        pin["dark_theme"] = False

    return pin


def _public_int(value: object) -> int | None:
    try:
        if isinstance(value, bool):
            return None
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _public_screen_dimension(value: object) -> int | None:
    dimension = _public_int(value)
    if dimension is None:
        return None
    if MIN_SCREEN_DIMENSION_PX <= dimension <= MAX_SCREEN_DIMENSION_PX:
        return dimension
    return None


def _public_display_dimensions(profile: dict[str, Any]) -> tuple[int, int]:
    width = _public_screen_dimension(profile.get("screen_width"))
    height = _public_screen_dimension(profile.get("screen_height"))
    return (
        width if width is not None else DEFAULT_DISPLAY_WIDTH_PX,
        height if height is not None else DEFAULT_DISPLAY_HEIGHT_PX,
    )


def _public_hardware_concurrency(value: object) -> int | None:
    concurrency = _public_int(value)
    if concurrency in PUBLIC_HARDWARE_CONCURRENCY_VALUES:
        return concurrency
    return None


def _public_gpu_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not PUBLIC_GPU_TEXT_RE.fullmatch(text):
        return ""
    if SENSITIVE_TEXT_RE.search(text):
        return ""
    return text


def _coherent_webgl_renderer_override(profile: dict[str, Any]) -> str:
    renderer = _public_gpu_text(profile.get("gpu_renderer"))
    if "NVIDIA" in renderer and "GeForce" in renderer:
        return DEFAULT_WEBGL_RENDERER
    if renderer:
        return renderer
    return DEFAULT_WEBGL_RENDERER


def _with_coherent_webgl_identity(profile: dict[str, Any]) -> dict[str, Any]:
    renderer = _coherent_webgl_renderer_override(profile)
    if profile.get("gpu_renderer") == renderer:
        return profile
    return {**profile, "gpu_renderer": renderer}


_BLOCKED_FIREFOX_ARG_PREFIXES = (
    "--remote-debugging-port",
    "--remote-debugging-address",
    "--remote-allow-origins",
    "--fingerprint",
    "--disable-features",
    "--enable-features",
    "--disable-blink-features",
    "--enable-blink-features",
    "--use-angle",
    "--load-extension",
    "--disable-extensions-except",
    "--user-agent",
    "--profile",
    "-profile",
    "-P",
    "--width",
    "--height",
    "--window-size",
)

_BLOCKED_FIREFOX_ARG_EXACT = (
    "--disable-infobars",
    "--test-type",
    "--headless",
)

_BLOCKED_FIREFOX_ARGS_WITH_VALUE = (
    "--remote-debugging-port",
    "--remote-debugging-address",
    "--remote-allow-origins",
    "--load-extension",
    "--disable-extensions-except",
    "--user-agent",
    "--profile",
    "-profile",
    "-P",
    "--width",
    "--height",
    "--window-size",
)


def _filter_firefox_launch_args(raw_args: list[str] | None) -> list[str]:
    """Drop launch flags that conflict with managed invisible_playwright Firefox."""
    if not raw_args:
        return []

    filtered: list[str] = []
    skip_next = False
    for arg in raw_args:
        if skip_next:
            skip_next = False
            continue

        if arg in _BLOCKED_FIREFOX_ARG_EXACT:
            continue

        blocked_prefix = next(
            (
                prefix
                for prefix in _BLOCKED_FIREFOX_ARG_PREFIXES
                if arg == prefix or arg.startswith(f"{prefix}=")
                or (prefix == "--fingerprint" and arg.startswith("--fingerprint-"))
            ),
            None,
        )
        if blocked_prefix:
            if arg == blocked_prefix and blocked_prefix in _BLOCKED_FIREFOX_ARGS_WITH_VALUE:
                skip_next = True
            continue

        filtered.append(arg)

    return filtered


def _public_locale(value: str | None) -> str:
    if not isinstance(value, str):
        return DEFAULT_BROWSER_LOCALE
    locale = value.strip().replace("_", "-")
    if not PUBLIC_LOCALE_RE.fullmatch(locale):
        return DEFAULT_BROWSER_LOCALE

    parts = locale.split("-")
    canonical = [parts[0].lower()]
    for part in parts[1:]:
        if part.isalpha() and len(part) == 2:
            canonical.append(part.upper())
        elif part.isalpha() and len(part) == 4:
            canonical.append(part.title())
        elif part.isalpha():
            canonical.append(part.lower())
        else:
            canonical.append(part)
    return "-".join(canonical)


def _public_timezone(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    timezone = value.strip()
    if not timezone or not PUBLIC_TIMEZONE_RE.fullmatch(timezone):
        return ""
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        return ""
    return timezone


def _build_invisible_kwargs(profile: dict[str, Any]) -> dict[str, Any]:
    """Build kwargs for InvisiblePlaywright from a Manager profile."""
    extra_prefs = {
        **MANAGED_FIREFOX_IDENTITY_PREFS,
        **WEBRTC_LOCAL_IP_SUPPRESSION_PREFS,
    }
    return {
        "seed": profile.get("fingerprint_seed"),
        "pin": _build_invisible_pin(profile),
        "headless": False,
        "proxy": _proxy_to_invisible(profile.get("proxy") or None),
        "extra_args": _filter_firefox_launch_args(profile.get("launch_args") or []),
        "humanize": bool(profile.get("humanize", False)),
        "locale": _public_locale(profile.get("locale")),
        "timezone": _public_timezone(profile.get("timezone")),
        "extra_prefs": extra_prefs,
        "profile_dir": str(profile["user_data_dir"]),
    }


def _geoip_exit_ip(profile: dict[str, Any]) -> str | None:
    geoip_result = profile.get("_geoip_result")
    if not isinstance(geoip_result, dict):
        return None
    ip = geoip_result.get("ip")
    if isinstance(ip, str) and ip.strip():
        return ip.strip()
    return None


def _navigator_languages(locale: str | None) -> list[str]:
    lang = _public_locale(locale)
    base = lang.split("-")[0]
    if base == lang:
        return [lang]
    return [lang, base]


def _accept_language_header(locale: str | None) -> str:
    languages = _navigator_languages(locale)
    if len(languages) == 1:
        return languages[0]
    return f"{languages[0]},{languages[1]};q=0.9"


@lru_cache(maxsize=1)
def _firefox_application_ini_metadata() -> dict[str, str]:
    try:
        from invisible_playwright.download import ensure_binary

        application_ini = Path(ensure_binary()).parent / "application.ini"
        metadata: dict[str, str] = {}
        for line in application_ini.read_text(errors="ignore").splitlines():
            key, separator, value = line.partition("=")
            if separator and key in {"Version", "BuildID"}:
                metadata[key] = value.strip()
        return {key: value for key, value in metadata.items() if value}
    except Exception as exc:
        logger.debug(
            "action=browser.firefox_metadata_detection_skipped error_type=%s",
            type(exc).__name__,
        )
    return {}


def _managed_user_agent_version() -> str | None:
    marker = "Firefox/"
    if marker not in MANAGED_FIREFOX_USER_AGENT:
        return None
    version = MANAGED_FIREFOX_USER_AGENT.rsplit(marker, 1)[1].split()[0].strip()
    return _public_version_string(version)


def _invisible_playwright_package_version() -> str | None:
    try:
        version = importlib.metadata.version("invisible_playwright")
    except importlib.metadata.PackageNotFoundError:
        return None
    return _public_version_string(version)


def _public_version_string(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    version = value.strip()
    return version if PUBLIC_VERSION_RE.fullmatch(version) else None


def _public_firefox_build_id(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    build_id = value.strip()
    return build_id if PUBLIC_FIREFOX_BUILD_ID_RE.fullmatch(build_id) else None


def _stealth_pref_category(pref_key: str) -> str | None:
    prefix = "zoom.stealth."
    if not pref_key.startswith(prefix):
        return None
    raw_category = pref_key.removeprefix(prefix).split(".", 1)[0]
    category = STEALTH_PREF_CATEGORY_ALIASES.get(raw_category, raw_category)
    return category if category in PUBLIC_STEALTH_PREF_CATEGORIES else "unknown"


@lru_cache(maxsize=1)
def _invisible_stealth_pref_summary() -> dict[str, Any]:
    try:
        from invisible_playwright._fpforge.profile import generate_profile
        from invisible_playwright.prefs import translate_profile_to_prefs

        profile = generate_profile(1)
        prefs = translate_profile_to_prefs(
            profile,
            locale="en-US",
            timezone="UTC",
            extra_prefs={
                **MANAGED_FIREFOX_IDENTITY_PREFS,
                **WEBRTC_LOCAL_IP_SUPPRESSION_PREFS,
            },
        )
        stealth_keys = [key for key in prefs if key.startswith("zoom.stealth.")]
        categories = sorted(
            {
                category
                for key in stealth_keys
                if (category := _stealth_pref_category(key))
            }
        )
        return {
            "stealth_pref_count": len(stealth_keys),
            "stealth_pref_categories": categories,
        }
    except Exception as exc:
        logger.debug(
            "action=browser.stealth_pref_summary_skipped error_type=%s",
            type(exc).__name__,
        )
    return {"stealth_pref_count": None, "stealth_pref_categories": []}


def managed_firefox_identity_summary() -> dict[str, Any]:
    metadata = _firefox_application_ini_metadata()
    stealth_summary = _invisible_stealth_pref_summary()
    return {
        "managed_user_agent_version": _managed_user_agent_version(),
        "invisible_playwright_version": _public_version_string(
            _invisible_playwright_package_version(),
        ),
        "firefox_binary_version": _public_version_string(metadata.get("Version")),
        "firefox_binary_build_id": _public_firefox_build_id(metadata.get("BuildID")),
        "stealth_pref_count": stealth_summary["stealth_pref_count"],
        "stealth_pref_categories": stealth_summary["stealth_pref_categories"],
    }


def _firefox_build_id_override() -> str | None:
    return _public_firefox_build_id(_firefox_application_ini_metadata().get("BuildID"))


def _browser_init_script(locale: str | None) -> str:
    lang = _public_locale(locale)
    language_json = json.dumps(lang)
    languages_json = json.dumps(_navigator_languages(locale))
    build_id_json = json.dumps(_firefox_build_id_override())
    return f"""
        (() => {{
            const __managerLanguage = {language_json};
            const __managerLanguages = {languages_json};
            const __managerBuildID = {build_id_json};
            try {{
                Object.defineProperty(Navigator.prototype, 'language', {{
                    get: () => __managerLanguage,
                    configurable: true
                }});
                Object.defineProperty(Navigator.prototype, 'languages', {{
                    get: () => __managerLanguages.slice(),
                    configurable: true
                }});
                if (__managerBuildID) {{
                    Object.defineProperty(Navigator.prototype, 'buildID', {{
                        get: () => __managerBuildID,
                        enumerable: true,
                        configurable: true
                    }});
                }}
            }} catch (e) {{}}

            window.__clipboardText = '';
            document.addEventListener('copy', () => {{
                const sel = window.getSelection();
                if (sel) window.__clipboardText = sel.toString();
            }});
            document.addEventListener('keydown', (e) => {{
                if ((e.ctrlKey || e.metaKey) && e.key === 'c' && !e.altKey && !e.shiftKey) {{
                    const sel = window.getSelection();
                    if (sel && sel.toString()) window.__clipboardText = sel.toString();
                }}
            }});
        }})();
    """


_FIREFOX_LOCK_FILES = (
    "SingletonLock",
    "SingletonCookie",
    "SingletonSocket",
    ".parentlock",
    "lock",
)

_FIREFOX_SESSION_RESTORE_FILES = (
    "sessionstore.jsonlz4",
    "sessionCheckpoints.json",
    "sessionstore-backups/recovery.jsonlz4",
    "sessionstore-backups/recovery.baklz4",
    "sessionstore-backups/previous.jsonlz4",
)


def _clean_firefox_startup_state(user_data_dir: Path) -> None:
    """Clean locks and tab session restore without touching site data."""
    for lock_file in _FIREFOX_LOCK_FILES:
        lock_path = user_data_dir / lock_file
        lock_path.unlink(missing_ok=True)

    for restore_file in _FIREFOX_SESSION_RESTORE_FILES:
        (user_data_dir / restore_file).unlink(missing_ok=True)


async def _fit_firefox_window_to_vnc(display: int, width: int, height: int) -> None:
    """Best-effort X11 window sizing for the visible VNC workspace."""
    xdotool_bin = shutil.which("xdotool")
    if not xdotool_bin:
        logger.debug("xdotool not found; skipping Firefox window fit")
        return

    env = {**os.environ, "DISPLAY": f":{display}"}
    try:
        search = await asyncio.create_subprocess_exec(
            xdotool_bin,
            "search",
            "--onlyvisible",
            "--class",
            "firefox",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=env,
        )
        stdout, _ = await asyncio.wait_for(search.communicate(), timeout=1.0)
        if search.returncode != 0:
            return
        window_ids = [line.strip() for line in stdout.decode().splitlines() if line.strip()]
        if not window_ids:
            return

        window_id = window_ids[-1]
        proc = await asyncio.create_subprocess_exec(
            xdotool_bin,
            "windowsize",
            window_id,
            str(width),
            str(height),
            "windowmove",
            window_id,
            "0",
            "0",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            env=env,
        )
        await asyncio.wait_for(proc.wait(), timeout=1.0)
    except Exception as exc:
        logger.debug(
            "action=profile.fit_window_skipped display=:%d error_type=%s",
            display,
            type(exc).__name__,
        )


def _page_url(page: Any) -> str:
    return str(getattr(page, "url", "") or "")


def _is_internal_firefox_page(page: Any) -> bool:
    return _page_url(page) in INTERNAL_FIREFOX_PAGE_URLS


@dataclass
class RunningProfile:
    profile_id: str
    context: Any  # Playwright BrowserContext
    display: int
    ws_port: int
    engine: str
    runner: Any | None = None
    accept_language: str | None = None
    resolved_geoip: dict[str, Any] | None = None
    automation_page_ids: dict[int, str] = field(default_factory=dict)


class BrowserManager:
    def __init__(self):
        self.running: dict[str, RunningProfile] = {}
        self._launching: set[str] = set()  # profile IDs currently being launched
        self._launch_failure_stage_counts: dict[str, int] = {}
        self.vnc = VNCManager()
        self._lock = asyncio.Lock()
        self._launch_env_lock = asyncio.Lock()
        self._auto_launch_task: asyncio.Task | None = None

    async def launch(self, profile: dict[str, Any]) -> RunningProfile:
        """Launch a browser instance for the given profile."""
        profile_id = profile["id"]
        runner: InvisiblePlaywright | None = None
        display: int | None = None
        launch_registered = False
        failure_stage = "validate_proxy"
        try:
            raw_proxy = profile.get("proxy")
            if raw_proxy:
                _validate_proxy(_normalize_proxy(raw_proxy))

            failure_stage = "claim_launch_slot"
            async with self._lock:
                if profile_id in self.running or profile_id in self._launching:
                    failure_stage = "already_running"
                    raise RuntimeError(f"Profile {profile_id} is already running")
                max_running = get_max_running_profiles_limit()
                if max_running is not None and len(self.running) + len(self._launching) >= max_running:
                    failure_stage = "resource_limit"
                    raise BrowserResourceLimitError("Maximum running profiles reached")
                self._launching.add(profile_id)
                launch_registered = True

            failure_stage = "allocate_vnc"
            display, ws_port = await self.vnc.allocate()

            user_data_dir = Path(profile["user_data_dir"])
            failure_stage = "cleanup_startup_state"
            _clean_firefox_startup_state(user_data_dir)
            display_width, display_height = _public_display_dimensions(profile)

            # Start KasmVNC on the allocated display
            failure_stage = "start_vnc"
            await self.vnc.start_vnc(
                display,
                ws_port,
                width=display_width,
                height=display_height,
            )

            failure_stage = "resolve_network_fingerprint"
            resolved_profile = await resolve_profile_network_fingerprint(profile)
            resolved_profile = _with_coherent_webgl_identity(resolved_profile)
            failure_stage = "build_launch_kwargs"
            kwargs = _build_invisible_kwargs(resolved_profile)
            runner = InvisiblePlaywright(**kwargs)

            # invisible_playwright builds its env from os.environ in __aenter__.
            # Keep this mutation serialized and restore it immediately after
            # Firefox has inherited the display.
            failure_stage = "enter_browser"
            async with self._launch_env_lock:
                old_display = os.environ.get("DISPLAY")
                old_webrtc_public_ip = os.environ.get(WEBRTC_PUBLIC_IP_ENV)
                os.environ["DISPLAY"] = f":{display}"
                geoip_exit_ip = _geoip_exit_ip(resolved_profile)
                if geoip_exit_ip:
                    os.environ[WEBRTC_PUBLIC_IP_ENV] = geoip_exit_ip
                try:
                    context = await runner.__aenter__()
                finally:
                    if old_display is None:
                        os.environ.pop("DISPLAY", None)
                    else:
                        os.environ["DISPLAY"] = old_display
                    if old_webrtc_public_ip is None:
                        os.environ.pop(WEBRTC_PUBLIC_IP_ENV, None)
                    else:
                        os.environ[WEBRTC_PUBLIC_IP_ENV] = old_webrtc_public_ip

            accept_language = _accept_language_header(kwargs.get("locale"))
            failure_stage = "configure_context"
            await context.set_extra_http_headers({"Accept-Language": accept_language})

            init_js = _browser_init_script(kwargs.get("locale"))
            await context.add_init_script(init_js)
            # Also inject into already-open pages (about:blank created before init_script)
            for p in context.pages:
                try:
                    await asyncio.wait_for(
                        p.evaluate(init_js),
                        timeout=EXISTING_PAGE_INIT_TIMEOUT_SECONDS,
                    )
                except Exception as exc:
                    logger.debug(
                        "action=profile.existing_page_init_failed profile_id=%s error_type=%s",
                        _public_profile_log_id(profile_id),
                        type(exc).__name__,
                    )

            if not any(not _is_internal_firefox_page(p) for p in context.pages):
                try:
                    failure_stage = "bootstrap_page"
                    await context.new_page()
                except Exception as exc:
                    logger.debug(
                        "action=profile.bootstrap_page_failed profile_id=%s error_type=%s",
                        _public_profile_log_id(profile_id),
                        type(exc).__name__,
                    )

            failure_stage = "fit_window"
            await _fit_firefox_window_to_vnc(
                display,
                display_width,
                display_height,
            )

            running = RunningProfile(
                profile_id=profile_id,
                context=context,
                display=display,
                ws_port=ws_port,
                engine="invisible_playwright",
                runner=runner,
                accept_language=accept_language,
                resolved_geoip=resolved_profile.get("_geoip_result"),
            )

            # Auto-cleanup if browser crashes or user closes Firefox via VNC
            context.on("close", lambda: asyncio.ensure_future(
                self._on_browser_closed(profile_id)
            ))

            failure_stage = "publish_running"
            async with self._lock:
                self.running[profile_id] = running
                self._launching.discard(profile_id)

            logger.info(
                "action=profile.launch_succeeded profile_id=%s display=:%d ws_port=%d engine=%s",
                _public_profile_log_id(profile_id), display, ws_port, running.engine,
            )

            return running

        except BaseException:
            if failure_stage != "already_running":
                self._record_launch_failure(profile_id, failure_stage)
            if launch_registered:
                async with self._lock:
                    self._launching.discard(profile_id)
            if runner is not None:
                try:
                    await runner.__aexit__(None, None, None)
                except Exception as exc:
                    logger.debug(
                        "action=profile.launch_teardown_failed profile_id=%s error_type=%s",
                        _public_profile_log_id(profile_id),
                        type(exc).__name__,
                    )
            if display is not None:
                await self.vnc.stop_vnc(display)
            raise

    def _record_launch_failure(self, profile_id: str, stage: str) -> None:
        public_stage = stage if stage in LAUNCH_FAILURE_STAGES else "unknown"
        self._launch_failure_stage_counts[public_stage] = (
            self._launch_failure_stage_counts.get(public_stage, 0) + 1
        )
        logger.warning(
            "action=profile.launch_failed profile_id=%s stage=%s",
            _public_profile_log_id(profile_id),
            public_stage,
        )

    def launch_failure_summary(self) -> dict[str, Any]:
        stage_counts: dict[str, int] = {}
        for stage, count in self._launch_failure_stage_counts.items():
            if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
                continue
            public_stage = stage if stage in LAUNCH_FAILURE_STAGES else "unknown"
            stage_counts[public_stage] = stage_counts.get(public_stage, 0) + count
        stage_counts = {stage: stage_counts[stage] for stage in sorted(stage_counts)}
        return {
            "launch_failure_count": sum(stage_counts.values()),
            "launch_failure_stage_counts": stage_counts,
        }

    def reset_launch_failure_summary(self) -> None:
        self._launch_failure_stage_counts.clear()

    async def _on_browser_closed(self, profile_id: str):
        """Called when browser exits (crash, user closed via VNC, or stop())."""
        async with self._lock:
            running = self.running.pop(profile_id, None)

        if running:
            logger.info(
                "action=profile.browser_closed profile_id=%s",
                _public_profile_log_id(profile_id),
            )
            if running.runner is not None:
                try:
                    await running.runner.__aexit__(None, None, None)
                except Exception as exc:
                    logger.debug(
                        "action=profile.browser_closed_teardown_failed profile_id=%s error_type=%s",
                        _public_profile_log_id(profile_id),
                        type(exc).__name__,
                    )
            await self.vnc.stop_vnc(running.display)

    async def stop(self, profile_id: str):
        """Stop a running browser instance."""
        # Pop before close so _on_browser_closed() finds nothing to clean up
        async with self._lock:
            running = self.running.pop(profile_id, None)

        if not running:
            return

        logger.info(
            "action=profile.stop_requested profile_id=%s",
            _public_profile_log_id(profile_id),
        )

        if running.runner is not None:
            try:
                await running.runner.__aexit__(None, None, None)
            except Exception as exc:
                logger.warning(
                    "action=profile.stop_runner_close_failed profile_id=%s error_type=%s",
                    _public_profile_log_id(profile_id),
                    type(exc).__name__,
                )
        else:
            try:
                await running.context.close()
            except Exception as exc:
                logger.warning(
                    "action=profile.stop_context_close_failed profile_id=%s error_type=%s",
                    _public_profile_log_id(profile_id),
                    type(exc).__name__,
                )

        await self.vnc.stop_vnc(running.display)
        logger.info(
            "action=profile.stop_finished profile_id=%s",
            _public_profile_log_id(profile_id),
        )

    def get_status(self, profile_id: str) -> dict[str, Any]:
        """Get running status for a profile."""
        running = self.running.get(profile_id)
        if running:
            return {
                "status": "running",
                "vnc_ws_port": running.ws_port,
                "display": f":{running.display}",
                "automation_url": f"/api/profiles/{profile_id}/automation",
            }
        return {
            "status": "stopped",
            "vnc_ws_port": None,
            "display": None,
            "automation_url": None,
        }

    @property
    def launching_count(self) -> int:
        """Number of profiles currently in the launch critical section."""
        return len(self._launching)

    async def cleanup_all(self):
        """Stop all running profiles. Called on shutdown."""
        async with self._lock:
            profile_ids = list(self.running.keys())

        for pid in profile_ids:
            await self.stop(pid)

        await self.vnc.cleanup_all()

    async def cleanup_stale(self):
        """Kill orphan processes from previous container runs."""
        await self.vnc.cleanup_stale()
        try:
            result = subprocess.run(
                ["pkill", "-f", INVISIBLE_FIREFOX_PROCESS_PATTERN],
                capture_output=True,
            )
            if result.returncode == 0:
                logger.info("Cleaned up stale invisible_playwright Firefox processes")
        except FileNotFoundError:
            logger.debug("pkill not found, skipping stale Firefox cleanup")

    async def auto_launch_all(self):
        """Launch all profiles with auto_launch=True. Called on startup."""
        from . import database as db

        profiles = db.list_profiles()
        auto_profiles = [p for p in profiles if p.get("auto_launch")]
        if not auto_profiles:
            logger.info("No profiles configured for auto-launch")
            return

        logger.info("Auto-launching %d profile(s)...", len(auto_profiles))
        for profile in auto_profiles:
            try:
                await asyncio.wait_for(self.launch(profile), timeout=60)
                logger.info(
                    "action=profile.auto_launch_succeeded profile_id=%s",
                    _public_profile_log_id(profile.get("id")),
                )
            except Exception as exc:
                logger.error(
                    "action=profile.auto_launch_failed profile_id=%s error_type=%s",
                    _public_profile_log_id(profile.get("id")),
                    type(exc).__name__,
                )
        logger.info("Auto-launch complete: %d running", len(self.running))
