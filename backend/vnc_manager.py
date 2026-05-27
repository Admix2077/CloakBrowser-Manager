"""KasmVNC display allocation and lifecycle management."""

from __future__ import annotations

import asyncio
import logging
import socket
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("invisible_browser.manager.vnc")


@dataclass
class VNCInstance:
    display: int
    ws_port: int
    process: subprocess.Popen | None = None


class VNCManager:
    BASE_DISPLAY = 100
    BASE_WS_PORT = 6100

    def __init__(self):
        self._allocated: dict[int, VNCInstance] = {}
        self._lock = asyncio.Lock()

    async def allocate(self) -> tuple[int, int]:
        """Returns (display_number, ws_port) for a new profile."""
        async with self._lock:
            display = self.BASE_DISPLAY
            while True:
                ws_port = self.BASE_WS_PORT + (display - self.BASE_DISPLAY)
                if display not in self._allocated and self._is_resource_available(display, ws_port):
                    break
                display += 1
            self._allocated[display] = VNCInstance(display=display, ws_port=ws_port)
            return display, ws_port

    def _is_resource_available(self, display: int, ws_port: int) -> bool:
        if Path(f"/tmp/.X{display}-lock").exists():
            logger.warning("Skipping unavailable X display :%d", display)
            return False
        if Path(f"/tmp/.X11-unix/X{display}").exists():
            logger.warning("Skipping unavailable X display :%d", display)
            return False

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", ws_port))
            except OSError:
                logger.warning("Skipping unavailable VNC websocket port %d", ws_port)
                return False
        return True

    async def start_vnc(
        self,
        display: int,
        ws_port: int,
        width: int = 1920,
        height: int = 1080,
    ) -> subprocess.Popen:
        """Start Xvnc (KasmVNC) on the given display."""
        xvnc_bin = shutil.which("Xvnc") or "Xvnc"

        # KasmVNC requires -httpd to enable the WebSocket handler on the websocket port.
        # Without it, the port accepts TCP but won't do WebSocket upgrade.
        httpd_dir = "/usr/share/kasmvnc/www"

        cmd = [
            xvnc_bin,
            f":{display}",
            "-websocketPort", str(ws_port),
            "-rfbport", "-1",  # disable raw VNC TCP port — WebSocket only
            "-geometry", f"{width}x{height}",
            "-depth", "24",
            "-SecurityTypes", "None",
            "-DisableBasicAuth",
            "-interface", "127.0.0.1",  # internal only, proxied by FastAPI
            "-AlwaysShared",
            "-httpd", httpd_dir,
        ]

        log_path = f"/tmp/xvnc-{display}.log"
        logger.info("Starting Xvnc on :%d (ws_port=%d) log=%s", display, ws_port, log_path)

        log_file = open(log_path, "w")
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
        )
        log_file.close()  # Popen inherited the fd, parent doesn't need it

        # Wait a moment for Xvnc to initialize
        await asyncio.sleep(0.5)

        if proc.poll() is not None:
            try:
                with open(log_path) as f:
                    err = f.read()
            except Exception as exc:
                logger.debug("Failed to read Xvnc log %s: %s", log_path, exc)
                err = ""
            raise RuntimeError(f"Xvnc failed to start on :{display}: {err}")

        async with self._lock:
            if display in self._allocated:
                self._allocated[display].process = proc

        return proc

    async def stop_vnc(self, display: int):
        """Kill Xvnc for given display and release allocation."""
        async with self._lock:
            instance = self._allocated.pop(display, None)

        if instance and instance.process:
            logger.info("Stopping Xvnc on :%d", display)
            instance.process.terminate()
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, instance.process.wait, 5,
                )
            except subprocess.TimeoutExpired:
                instance.process.kill()

    async def cleanup_all(self):
        """Kill all managed Xvnc processes. Called on shutdown."""
        async with self._lock:
            displays = list(self._allocated.keys())

        for display in displays:
            await self.stop_vnc(display)

    async def cleanup_stale(self):
        """Kill orphan Xvnc processes from previous runs."""
        try:
            result = subprocess.run(
                ["pkill", "-f", r"Xvnc :[0-9]"],
                capture_output=True,
            )
            if result.returncode == 0:
                logger.info("Cleaned up stale Xvnc processes")
        except FileNotFoundError:
            logger.debug("pkill not found, skipping stale Xvnc cleanup")

    def get_ws_port(self, display: int) -> int | None:
        """Get WebSocket port for a display."""
        instance = self._allocated.get(display)
        return instance.ws_port if instance else None

    @property
    def active_displays(self) -> list[int]:
        return list(self._allocated.keys())
