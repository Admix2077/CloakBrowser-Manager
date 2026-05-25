"""Launch/stop/track invisible_playwright browser instances per profile."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from invisible_playwright.async_api import InvisiblePlaywright

from .vnc_manager import VNCManager

logger = logging.getLogger("cloakbrowser.manager.browser")

INVISIBLE_FIREFOX_PROCESS_PATTERN = r"\.cache/invisible-playwright/.*/firefox"


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
        raise ValueError(f"Proxy URL missing hostname: {url}")
    if not parsed.port:
        raise ValueError(f"Proxy URL missing port: {url}")


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

    width = profile.get("screen_width")
    height = profile.get("screen_height")
    if width:
        pin["screen.width"] = int(width)
        pin["screen.avail_width"] = int(width)
    if height:
        height_int = int(height)
        pin["screen.height"] = height_int
        pin["screen.avail_height"] = max(1, height_int - 40)

    gpu_vendor = profile.get("gpu_vendor")
    if gpu_vendor:
        pin["gpu.vendor"] = gpu_vendor
    gpu_renderer = profile.get("gpu_renderer")
    if gpu_renderer:
        pin["gpu.renderer"] = gpu_renderer

    hardware_concurrency = profile.get("hardware_concurrency")
    if hardware_concurrency is not None:
        pin["hardware.concurrency"] = int(hardware_concurrency)

    color_scheme = profile.get("color_scheme")
    if color_scheme == "dark":
        pin["dark_theme"] = True
    elif color_scheme == "light":
        pin["dark_theme"] = False

    return pin


_CHROMIUM_ONLY_ARG_PREFIXES = (
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
)

_CHROMIUM_ONLY_ARG_EXACT = (
    "--disable-infobars",
    "--test-type",
    "--headless",
)

_CHROMIUM_ONLY_ARGS_WITH_VALUE = (
    "--remote-debugging-port",
    "--remote-debugging-address",
    "--remote-allow-origins",
    "--load-extension",
    "--disable-extensions-except",
    "--user-agent",
    "--profile",
    "-profile",
    "-P",
)


def _filter_firefox_launch_args(raw_args: list[str] | None) -> list[str]:
    """Drop Chromium/CDP/profile flags that break invisible_playwright Firefox."""
    if not raw_args:
        return []

    filtered: list[str] = []
    skip_next = False
    for arg in raw_args:
        if skip_next:
            skip_next = False
            continue

        if arg in _CHROMIUM_ONLY_ARG_EXACT:
            continue

        blocked_prefix = next(
            (
                prefix
                for prefix in _CHROMIUM_ONLY_ARG_PREFIXES
                if arg == prefix or arg.startswith(f"{prefix}=")
                or (prefix == "--fingerprint" and arg.startswith("--fingerprint-"))
            ),
            None,
        )
        if blocked_prefix:
            if arg == blocked_prefix and blocked_prefix in _CHROMIUM_ONLY_ARGS_WITH_VALUE:
                skip_next = True
            continue

        filtered.append(arg)

    return filtered


def _build_invisible_kwargs(profile: dict[str, Any]) -> dict[str, Any]:
    """Build kwargs for InvisiblePlaywright from a Manager profile."""
    return {
        "seed": profile.get("fingerprint_seed"),
        "pin": _build_invisible_pin(profile),
        "headless": False,
        "proxy": _proxy_to_invisible(profile.get("proxy") or None),
        "extra_args": _filter_firefox_launch_args(profile.get("launch_args") or []),
        "humanize": bool(profile.get("humanize", False)),
        "locale": profile.get("locale") or "en-US",
        "timezone": profile.get("timezone") or "",
        "profile_dir": str(profile["user_data_dir"]),
    }


@dataclass
class RunningProfile:
    profile_id: str
    context: Any  # Playwright BrowserContext
    display: int
    ws_port: int
    engine: str
    runner: Any | None = None
    automation_page_ids: dict[int, str] = field(default_factory=dict)


class BrowserManager:
    def __init__(self):
        self.running: dict[str, RunningProfile] = {}
        self._launching: set[str] = set()  # profile IDs currently being launched
        self.vnc = VNCManager()
        self._lock = asyncio.Lock()
        self._launch_env_lock = asyncio.Lock()
        self._auto_launch_task: asyncio.Task | None = None

    async def launch(self, profile: dict[str, Any]) -> RunningProfile:
        """Launch a browser instance for the given profile."""
        profile_id = profile["id"]

        async with self._lock:
            if profile_id in self.running or profile_id in self._launching:
                raise RuntimeError(f"Profile {profile_id} is already running")
            self._launching.add(profile_id)

        display, ws_port = await self.vnc.allocate()

        # Clean stale browser lock files from existing profile directories.
        user_data_dir = Path(profile["user_data_dir"])
        for lock_file in (
            "SingletonLock",
            "SingletonCookie",
            "SingletonSocket",
            ".parentlock",
            "lock",
        ):
            lock_path = user_data_dir / lock_file
            lock_path.unlink(missing_ok=True)

        runner: InvisiblePlaywright | None = None
        try:
            # Start KasmVNC on the allocated display
            await self.vnc.start_vnc(
                display,
                ws_port,
                width=profile.get("screen_width", 1920),
                height=profile.get("screen_height", 1080),
            )

            kwargs = _build_invisible_kwargs(profile)
            runner = InvisiblePlaywright(**kwargs)

            # invisible_playwright builds its env from os.environ in __aenter__.
            # Keep this mutation serialized and restore it immediately after
            # Firefox has inherited the display.
            async with self._launch_env_lock:
                old_display = os.environ.get("DISPLAY")
                os.environ["DISPLAY"] = f":{display}"
                try:
                    context = await runner.__aenter__()
                finally:
                    if old_display is None:
                        os.environ.pop("DISPLAY", None)
                    else:
                        os.environ["DISPLAY"] = old_display

            # Inject clipboard listener: captures copied text on every page
            # so the GET /clipboard endpoint can read it via page.evaluate()
            _clipboard_init_js = """
                window.__clipboardText = '';
                document.addEventListener('copy', () => {
                    const sel = window.getSelection();
                    if (sel) window.__clipboardText = sel.toString();
                });
                document.addEventListener('keydown', (e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'c' && !e.altKey && !e.shiftKey) {
                        const sel = window.getSelection();
                        if (sel && sel.toString()) window.__clipboardText = sel.toString();
                    }
                });
            """
            await context.add_init_script(_clipboard_init_js)
            # Also inject into already-open pages (about:blank created before init_script)
            for p in context.pages:
                try:
                    await p.evaluate(_clipboard_init_js)
                except Exception as exc:
                    logger.debug("Clipboard init failed on existing page: %s", exc)

            running = RunningProfile(
                profile_id=profile_id,
                context=context,
                display=display,
                ws_port=ws_port,
                engine="invisible_playwright",
                runner=runner,
            )

            # Auto-cleanup if browser crashes or user closes Firefox via VNC
            context.on("close", lambda: asyncio.ensure_future(
                self._on_browser_closed(profile_id)
            ))

            async with self._lock:
                self.running[profile_id] = running
                self._launching.discard(profile_id)

            logger.info(
                "Launched profile %s on display :%d (ws_port=%d, engine=%s)",
                profile_id, display, ws_port, running.engine,
            )

            return running

        except BaseException:
            async with self._lock:
                self._launching.discard(profile_id)
            if runner is not None:
                try:
                    await runner.__aexit__(None, None, None)
                except Exception as exc:
                    logger.debug("InvisiblePlaywright teardown failed after launch error: %s", exc)
            await self.vnc.stop_vnc(display)
            raise

    async def _on_browser_closed(self, profile_id: str):
        """Called when browser exits (crash, user closed via VNC, or stop())."""
        async with self._lock:
            running = self.running.pop(profile_id, None)

        if running:
            logger.info("Browser closed for profile %s, cleaning up", profile_id)
            if running.runner is not None:
                try:
                    await running.runner.__aexit__(None, None, None)
                except Exception as exc:
                    logger.debug("InvisiblePlaywright teardown failed for %s: %s", profile_id, exc)
            await self.vnc.stop_vnc(running.display)

    async def stop(self, profile_id: str):
        """Stop a running browser instance."""
        # Pop before close so _on_browser_closed() finds nothing to clean up
        async with self._lock:
            running = self.running.pop(profile_id, None)

        if not running:
            return

        logger.info("Stopping profile %s", profile_id)

        if running.runner is not None:
            try:
                await running.runner.__aexit__(None, None, None)
            except Exception as exc:
                logger.warning("Error closing invisible_playwright runner for %s: %s", profile_id, exc)
        else:
            try:
                await running.context.close()
            except Exception as exc:
                logger.warning("Error closing context for %s: %s", profile_id, exc)

        await self.vnc.stop_vnc(running.display)

    def get_status(self, profile_id: str) -> dict[str, Any]:
        """Get running status for a profile."""
        running = self.running.get(profile_id)
        if running:
            return {
                "status": "running",
                "vnc_ws_port": running.ws_port,
                "display": f":{running.display}",
                "cdp_url": None,
                "automation_url": f"/api/profiles/{profile_id}/automation",
            }
        return {
            "status": "stopped",
            "vnc_ws_port": None,
            "display": None,
            "cdp_url": None,
            "automation_url": None,
        }

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
                logger.info("Auto-launched profile %s (%s)", profile["name"], profile["id"])
            except Exception as exc:
                logger.error(
                    "Auto-launch failed for profile %s (%s): %s",
                    profile["name"], profile["id"], exc,
                )
        logger.info("Auto-launch complete: %d running", len(self.running))
