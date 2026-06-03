"""Invisible Browser Manager — FastAPI application.

Serves the React dashboard (static files) and provides a REST API
for browser profile management with live VNC viewing.
"""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import hmac
import logging
import math
import os
import random
import re
import secrets
import struct
import shutil
import uuid
from contextlib import asynccontextmanager
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
import starlette.requests
from starlette.types import ASGIApp, Receive, Scope, Send

from . import database as db
from .browser_manager import (
    BrowserManager,
    BrowserResourceLimitError,
    get_max_running_profiles_limit,
    managed_firefox_identity_summary,
)
from .cookie_formats import (
    CookieJsonDocument,
    build_cookie_json_export,
    build_netscape_cookie_export,
    cookie_json_audit_summary,
    cookies_for_playwright,
    netscape_cookie_audit_summary,
    parse_netscape_cookies,
)
from .geoip import (
    public_geoip_country_code,
    public_geoip_ip,
    public_geoip_locale,
    public_geoip_source,
    public_geoip_timezone,
    resolve_network_geo,
)
from .health import (
    ProfileHealthResponse,
    compute_profile_health,
    validate_profile_proxy,
)
from .models import (
    AutomationClickRequest,
    AutomationConsoleLogsResponse,
    AutomationEvaluateRequest,
    AutomationEvaluateResponse,
    AutomationFillRequest,
    AutomationGotoRequest,
    AutomationInfoResponse,
    AutomationKeyboardTypeRequest,
    AutomationNetworkSummaryResponse,
    AutomationPageCloseRequest,
    AutomationPageResponse,
    AutomationPagesResponse,
    AutomationScreenshotRequest,
    AutomationScrollRequest,
    AutomationTaskCancelRequest,
    AutomationTaskCreate,
    AutomationTaskResponse,
    AutomationTasksResponse,
    AutomationWaitForSelectorRequest,
    ClipboardRequest,
    CookieExportRequest,
    CookieExportResponse,
    CookieImportConfirmRequest,
    CookieImportResponse,
    DiagnosticsAutomationWorkerResponse,
    DiagnosticsCountsResponse,
    DiagnosticsResponse,
    DiagnosticsRuntimeResponse,
    DiagnosticsRuntimeSessionsResponse,
    DiagnosticsStorageResponse,
    NetscapeCookieExportResponse,
    NetscapeCookieImportRequest,
    LaunchResponse,
    LoginRequest,
    ProxyAssignRequest,
    ProxyAssignResponse,
    ProxyAssignResult,
    ProxyBulkCheckRequest,
    ProxyBulkCheckResponse,
    ProxyBulkCheckResult,
    ProxyCreate,
    ProxyDeleteRequest,
    ProxyFromProfileCreate,
    ProxyProviderPresetCreate,
    ProxyProviderPresetDeleteRequest,
    ProxyProviderPresetResponse,
    ProxyProviderPresetUpdate,
    ProxyRandomAssignRequest,
    ProxyRandomAssignResponse,
    ProxyRandomAssignResult,
    ProxyResponse,
    ProxyUpdate,
    ProfileCreate,
    ProfileConfigImportRequest,
    ProfileConfigImportResponse,
    ProfileConfigImportResult,
    ProfileConfigExport,
    ProfileDeleteRequest,
    ProfileLaunchRequest,
    ProfileBundleExportRequest,
    ProfileBundleExportResponse,
    ProfileExportRequest,
    ProfileExportResponse,
    ProfileExportResult,
    ProfileImportResponse,
    ProfileImportRequest,
    ProfileImportPreviewRequest,
    ProfileImportPreviewResponse,
    ProfileImportResult,
    ProfileResponse,
    ProfileStatusResponse,
    ProfileStopRequest,
    ProfileTemplateCreate,
    ProfileTemplateDeleteRequest,
    ProfileTemplateResponse,
    ProfileTemplateUpdate,
    ProfileUpdate,
    RuntimeSessionCreate,
    RuntimeSessionRenew,
    RuntimeSessionResponse,
    RuntimeSessionTerminate,
    RuntimeViewerTokenCreate,
    RuntimeViewerTokenResponse,
    StatusResponse,
    TagResponse,
)
from .profile_import import (
    ProfileImportHeaderError,
    ProfileTemplateNotFoundError,
    apply_profile_template_fields,
    parse_profile_csv_import,
    profile_create_data_for_import,
    preview_profile_csv_import,
    sanitize_profile_config_export_data,
    sanitize_profile_response_data,
    sanitize_profile_template_response_data,
)
from .profile_bundle import (
    ProfileBundleImportRequest,
    add_cookie_document_to_bundle,
    add_local_storage_entries_to_bundle,
    build_profile_config_bundle,
    local_storage_audit_metadata,
)
from .proxies import redact_proxy_asset_url

logger = logging.getLogger("invisible_browser.manager")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# Optional authentication via AUTH_TOKEN env var.
# If not set, all routes are open (local dev). If set, all /api/* routes
# (except /api/auth/* and /api/status) require Bearer token or cookie.
AUTH_TOKEN: str | None = os.environ.get("AUTH_TOKEN") or None
RUNTIME_SERVICE_TOKEN: str | None = os.environ.get("RUNTIME_SERVICE_TOKEN") or None
_AUTOMATION_CONSOLE_LOG_LIMIT = 200
_AUTOMATION_NETWORK_EVENT_LIMIT = 200
_AUTOMATION_WORKER_LOST_LEASE_DETAIL = "Automation task lease no longer owned by worker"
_AUTOMATION_TEXT_URL_RE = re.compile(r"https?://[^\s\"'<>]+")
_AUTOMATION_AUTHORIZATION_HEADER_RE = re.compile(
    r"\bAuthorization\s*[:=]\s*(?:(?:Bearer|Basic|Digest)\s+)?[A-Za-z0-9._~+/\-=]+",
    re.IGNORECASE,
)
_AUTOMATION_COOKIE_HEADER_RE = re.compile(
    r"\b(Cookie|Set-Cookie)\s*[:=]\s*[^\s;,]+",
    re.IGNORECASE,
)
_AUTOMATION_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"\b(authorization|auth_token|cookie|password|runtime_service_token|secret|service_token|token|viewer_token)"
    r"\s*=\s*([^\s&#]+)",
    re.IGNORECASE,
)
_AUTOMATION_BEARER_TOKEN_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/\-=]+", re.IGNORECASE)
_AUTOMATION_INVALID_PAGE_REF = "invalid"

# Paths that bypass authentication even when AUTH_TOKEN is set
_AUTH_EXEMPT = frozenset({"/api/auth/status", "/api/auth/login", "/api/status"})
_AUTOMATION_WORKER_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _auth_cookie_value() -> str | None:
    if not AUTH_TOKEN:
        return None
    digest = hmac.new(
        AUTH_TOKEN.encode("utf-8"),
        b"cloakbrowser-auth-cookie-v1",
        hashlib.sha256,
    ).hexdigest()
    return f"v1.{digest}"


def _env_bool(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _AUTOMATION_WORKER_TRUE_VALUES


def _env_int(name: str, *, default: int, minimum: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid integer config for %s", name)
        return default
    if value < minimum:
        logger.warning("Ignoring out-of-range integer config for %s", name)
        return default
    return value


def _env_float(name: str, *, default: float, minimum: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid float config for %s", name)
        return default
    if not math.isfinite(value) or value < minimum:
        logger.warning("Ignoring out-of-range float config for %s", name)
        return default
    return value


def _automation_worker_diagnostics() -> DiagnosticsAutomationWorkerResponse:
    return DiagnosticsAutomationWorkerResponse(
        enabled=_env_bool("AUTOMATION_WORKER_ENABLED", default=False),
        lease_seconds=_env_int("AUTOMATION_WORKER_LEASE_SECONDS", default=60, minimum=1),
        idle_sleep_seconds=_env_float("AUTOMATION_WORKER_IDLE_SLEEP_SECONDS", default=1.0, minimum=0.0),
        shutdown_timeout_seconds=_env_float("AUTOMATION_WORKER_SHUTDOWN_TIMEOUT_SECONDS", default=5.0, minimum=0.0),
    )


def _check_auth(scope: Scope) -> bool:
    """Check if the request has a valid auth token (header or cookie)."""
    # Check Authorization: Bearer <token> header
    for key, val in scope.get("headers", []):
        if key == b"authorization":
            auth_value = val.decode()
            if auth_value.startswith("Bearer "):
                token = auth_value[7:]
                if token and hmac.compare_digest(token, AUTH_TOKEN):
                    return True
            break

    # Check auth_token cookie
    for key, val in scope.get("headers", []):
        if key == b"cookie":
            cookies = SimpleCookie()
            cookies.load(val.decode())
            if "auth_token" in cookies:
                cookie_val = cookies["auth_token"].value
                auth_cookie_value = _auth_cookie_value()
                if (
                    cookie_val
                    and auth_cookie_value
                    and hmac.compare_digest(cookie_val, auth_cookie_value)
                ):
                    return True
                if cookie_val and hmac.compare_digest(cookie_val, AUTH_TOKEN):
                    return True
            break

    return False


def _is_https(request: Request) -> bool:
    """Check if the original client connection was HTTPS (via reverse proxy header)."""
    proto = request.headers.get("x-forwarded-proto", "")
    return "https" in proto


def _websocket_public_host_label(value: str | None) -> str:
    if not value:
        return "missing"
    raw_value = str(value).strip()
    if not raw_value:
        return "missing"
    try:
        parsed = urlparse(raw_value if "://" in raw_value else f"//{raw_value}")
        host = parsed.hostname or ""
        port = parsed.port
    except ValueError:
        return "malformed"
    if not host:
        return "missing"
    if port and port not in (80, 443):
        return f"{host}:{port}"
    return host


async def _check_websocket_origin(websocket: WebSocket, on_rejected=None) -> bool:
    """Reject cross-origin WebSocket connections (CSWSH protection).

    Browsers always send an Origin header on WebSocket upgrades.
    Non-browser clients (Playwright, curl) typically don't — those are allowed.
    If Origin is present, its host must match the request Host header.
    """
    origin = None
    host = None
    for key, val in websocket.scope.get("headers", []):
        if key == b"origin":
            origin = val.decode("latin-1")
        elif key == b"host":
            host = val.decode("latin-1")

    # No Origin header → non-browser client (Playwright, Puppeteer) → allow
    if not origin:
        return True

    # Parse origin to extract host:port
    try:
        parsed = urlparse(origin)
        origin_host = parsed.hostname or ""
        origin_port = parsed.port
    except ValueError:
        logger.warning("WebSocket origin malformed: origin=%s", _websocket_public_host_label(origin))
        if on_rejected:
            on_rejected()
        await websocket.close(code=4403, reason="Origin not allowed")
        return False
    # Build origin netloc (host:port or just host if default port)
    if origin_port and origin_port not in (80, 443):
        origin_netloc = f"{origin_host}:{origin_port}"
    else:
        origin_netloc = origin_host

    if not host:
        return True  # no Host header to compare against

    # Strip default port from Host too (some proxies send "example.com:443")
    host_normalized = host
    if host.endswith(":80") or host.endswith(":443"):
        host_normalized = host.rsplit(":", 1)[0]

    if origin_netloc == host_normalized:
        return True

    logger.warning(
        "WebSocket origin mismatch: origin=%s host=%s",
        _websocket_public_host_label(origin),
        _websocket_public_host_label(host),
    )
    if on_rejected:
        on_rejected()
    await websocket.close(code=4403, reason="Origin not allowed")
    return False


class AuthMiddleware:
    """Raw ASGI middleware for optional token auth.

    Uses raw ASGI instead of BaseHTTPMiddleware because the latter
    breaks WebSocket routes (wraps request body, preventing WS upgrade).
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Pass through if auth disabled, or non-HTTP/WS scope (e.g. lifespan)
        if not AUTH_TOKEN or scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope["path"]

        # Skip auth for exempt endpoints, runtime service endpoints, and non-API paths.
        if path in _AUTH_EXEMPT or path.startswith("/api/runtime/") or not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return

        if _check_auth(scope):
            await self.app(scope, receive, send)
            return

        # Reject — unauthenticated
        if scope["type"] == "websocket":
            # ASGI requires receiving websocket.connect before sending close
            await receive()
            await send({"type": "websocket.close", "code": 4401, "reason": "Unauthorized"})
        else:
            response = JSONResponse({"detail": "Unauthorized"}, status_code=401)
            await response(scope, receive, send)


# Singleton browser manager
browser_mgr = BrowserManager()

# Frontend build directory (React production build)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"


# ---------------------------------------------------------------------------
# RFB server message translator — KasmVNC BinaryClipboard → standard RFB
# ---------------------------------------------------------------------------


def _parse_kasmvnc_clipboard(data: bytes) -> str | None:
    """Extract text/plain from KasmVNC BinaryClipboard (type 180).

    Format: type(1) + action(1) + flags(4) + entries...
    Each entry: mime_len(u8) + mime(N) + data_len(u32 BE) + data(M)
    """
    if len(data) < 7:
        return None
    offset = 6  # skip type(1) + action(1) + flags(4)
    while offset < len(data):
        if offset + 1 > len(data):
            break
        mime_len = data[offset]
        offset += 1
        if offset + mime_len > len(data):
            break
        mime_type = data[offset:offset + mime_len]
        offset += mime_len
        if offset + 4 > len(data):
            break
        data_len = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        if mime_type == b"text/plain":
            end = min(offset + data_len, len(data))
            return data[offset:end].decode("utf-8", errors="replace")
        offset += data_len
    return None


def _build_server_cut_text(text: str) -> bytes:
    """Build standard RFB ServerCutText (type 3) message.

    RFB spec mandates Latin-1 encoding for ServerCutText.
    Characters outside Latin-1 (CJK, emoji, etc.) are replaced with '?'.
    """
    text_bytes = text.encode("latin-1", errors="replace")
    return struct.pack(">BxxxI", 3, len(text_bytes)) + text_bytes


# ---------------------------------------------------------------------------
# RFB client message filter — strip extension types KasmVNC doesn't support
# ---------------------------------------------------------------------------
# noVNC v1.4 batches multiple RFB messages into one WebSocket frame.
# KasmVNC 1.3.3 crashes on unsupported types (150, 248, etc.).
# We parse message boundaries using known sizes and keep only standard types.

# Client→server message sizes (fixed, except 2 and 6 which encode length)
_RFB_MSG_SIZE: dict[int, int | None] = {
    0: 20,    # SetPixelFormat
    2: None,  # SetEncodings — 4 + numEncodings*4 (rewritten to strip bad pseudo-encodings)
    3: 10,    # FramebufferUpdateRequest
    4: 8,     # KeyEvent
    5: 6,     # PointerEvent
    6: None,  # ClientCutText — 8 + length
}

# Extension types that noVNC sends — known sizes so we can skip past them
# instead of breaking and dropping all trailing data in the frame.
_RFB_EXTENSION_SIZE: dict[int, int] = {
    150: 10,  # EnableContinuousUpdates (1+1+2+2+2+2)
    248: 10,  # QEMU-like key event (observed from noVNC 1.4.0)
    252: 4,   # xvp (1+1+1+1)
    255: 4,   # QEMU audio control (1+1+2) — noVNC QEMUExtendedKeyEvent is actually 12
}

# Whitelist of encodings safe to send to KasmVNC.
# Instead of trying to blocklist problematic pseudo-encodings (error-prone —
# we had wrong numbers), we ONLY keep known-good encodings.
# Anything not on this list is stripped from SetEncodings.
_ALLOWED_ENCODINGS: set[int] = {
    # Framebuffer encodings (standard RFB)
    0,    # Raw
    1,    # CopyRect
    2,    # RRE
    5,    # Hextile
    7,    # Tight
    16,   # ZRLE
    # Safe pseudo-encodings
    -239,  # Cursor (0xFFFFFF11) — cursor shape
    -224,  # LastRect (0xFFFFFF20) — performance optimization
    # Tight quality/compress levels (these are just hints)
    *range(-32, -22),   # quality levels 0-9
    *range(-256, -246),  # compress levels 0-9
}


def _rfb_msg_length(data: bytes, offset: int) -> int | None:
    """Return total length of the RFB message at offset, or None if unrecognized."""
    if offset >= len(data):
        return None
    msg_type = data[offset]
    fixed = _RFB_MSG_SIZE.get(msg_type)
    if fixed is not None:
        return fixed
    remaining = len(data) - offset
    if msg_type == 2 and remaining >= 4:  # SetEncodings
        num_enc = struct.unpack_from(">H", data, offset + 2)[0]
        return 4 + num_enc * 4
    if msg_type == 6 and remaining >= 8:  # ClientCutText
        length = struct.unpack_from(">I", data, offset + 4)[0]
        return 8 + length
    # Known extension types — skip past them instead of giving up
    ext_size = _RFB_EXTENSION_SIZE.get(msg_type)
    if ext_size is not None:
        return ext_size
    return None  # truly unknown type


def _rewrite_set_encodings(data: bytes, offset: int, msg_len: int) -> bytes:
    """Keep only whitelisted encodings in a SetEncodings message."""
    _log = logging.getLogger("invisible_browser.manager")
    num_enc = struct.unpack_from(">H", data, offset + 2)[0]
    kept = []
    stripped = []
    for i in range(num_enc):
        enc = struct.unpack_from(">i", data, offset + 4 + i * 4)[0]  # signed
        if enc in _ALLOWED_ENCODINGS:
            kept.append(enc)
        else:
            stripped.append(enc)
    if not stripped:
        return data[offset:offset + msg_len]
    _log.info("RFB filter: SetEncodings keeping %d: %s, stripped %d: %s", len(kept), kept, len(stripped), stripped)
    result = struct.pack(">BxH", 2, len(kept))
    for enc in kept:
        result += struct.pack(">i", enc)
    return result


def _rewrite_pointer_event(data: bytes, offset: int) -> bytes:
    """Convert standard 6-byte PointerEvent to KasmVNC's 11-byte format.

    Standard RFB:  [5:u8][mask:u8][x:u16][y:u16]          = 6 bytes
    KasmVNC:       [5:u8][mask:u16][x:u16][y:u16][sx:s16][sy:s16] = 11 bytes
    """
    mask = data[offset + 1]
    x = struct.unpack_from(">H", data, offset + 2)[0]
    y = struct.unpack_from(">H", data, offset + 4)[0]
    # Expand mask from u8 to u16.  Scroll deltas (sx, sy) are zero because
    # noVNC encodes scroll as button-mask bits (3=up, 4=down, 5=left, 6=right)
    # which pass through in the mask.  KasmVNC accepts mask-bit scroll on its
    # extended 11-byte format, so explicit deltas are unnecessary.
    return struct.pack(">BHHHhh", 5, mask, x, y, 0, 0)


def _filter_rfb_client_messages(data: bytes) -> bytes:
    """Parse concatenated RFB messages, keep only standard types (0-6).

    Rewrites PointerEvents from 6-byte standard to 11-byte KasmVNC format
    and strips unsupported pseudo-encodings from SetEncodings.
    """
    _log = logging.getLogger("invisible_browser.manager")
    result = bytearray()
    offset = 0
    msg_idx = 0
    while offset < len(data):
        msg_type = data[offset]
        msg_len = _rfb_msg_length(data, offset)
        if msg_len is None:
            _log.info("RFB filter: DROPPING unknown type=%d at offset=%d/%d, skipping %d trailing bytes, hex=%s",
                       msg_type, offset, len(data), len(data) - offset, data[offset:offset+20].hex())
            break
        if offset + msg_len > len(data):
            # Incomplete message — DO NOT forward partial data, it desynchronizes
            # the RFB stream (KasmVNC buffers partial reads across frames).
            _log.warning("RFB filter: DROPPING incomplete type=%d need=%d have=%d — would desync stream",
                         msg_type, msg_len, len(data) - offset)
            break
        msg_idx += 1
        if msg_type in _RFB_MSG_SIZE:
            # Standard RFB type — keep (with rewrites for KasmVNC compatibility)
            _log.debug("RFB filter: KEEP type=%d len=%d at offset=%d (msg #%d in frame)", msg_type, msg_len, offset, msg_idx)
            if msg_type == 2:  # SetEncodings — whitelist safe encodings
                result.extend(_rewrite_set_encodings(data, offset, msg_len))
            elif msg_type == 5:  # PointerEvent — expand to KasmVNC's 11-byte format
                result.extend(_rewrite_pointer_event(data, offset))
            else:
                result.extend(data[offset:offset + msg_len])
        else:
            # Extension type (150, 248, etc.) — skip but continue parsing
            _log.debug("RFB filter: SKIP extension type=%d len=%d at offset=%d (msg #%d in frame)", msg_type, msg_len, offset, msg_idx)
        offset += msg_len
    if len(result) != len(data):
        _log.info("RFB filter: input=%d output=%d (delta %+d bytes)", len(data), len(result), len(result) - len(data))
    return bytes(result)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    await browser_mgr.cleanup_stale()
    browser_mgr._auto_launch_task = asyncio.create_task(browser_mgr.auto_launch_all())
    automation_worker_task: asyncio.Task | None = None
    automation_worker_stop_event: asyncio.Event | None = None
    if _env_bool("AUTOMATION_WORKER_ENABLED", default=False):
        lease_seconds = _env_int("AUTOMATION_WORKER_LEASE_SECONDS", default=60, minimum=1)
        idle_sleep_seconds = _env_float("AUTOMATION_WORKER_IDLE_SLEEP_SECONDS", default=1.0, minimum=0.0)
        automation_worker_stop_event = asyncio.Event()
        automation_worker_task = asyncio.create_task(
            run_automation_worker_loop(
                lease_owner=f"automation-worker-{secrets.token_hex(8)}",
                lease_seconds=lease_seconds,
                max_runs=None,
                max_idle_cycles=None,
                idle_sleep_seconds=idle_sleep_seconds,
                stop_event=automation_worker_stop_event,
            ),
            name="automation-worker-loop",
        )
    logger.info("Invisible Browser Manager started")
    try:
        yield
    finally:
        logger.info("Shutting down — stopping all browsers...")
        if automation_worker_stop_event is not None:
            automation_worker_stop_event.set()
        if automation_worker_task is not None and not automation_worker_task.done():
            shutdown_timeout = _env_float("AUTOMATION_WORKER_SHUTDOWN_TIMEOUT_SECONDS", default=5.0, minimum=0.0)
            try:
                await asyncio.wait_for(automation_worker_task, timeout=shutdown_timeout)
            except asyncio.TimeoutError:
                automation_worker_task.cancel()
                await asyncio.gather(automation_worker_task, return_exceptions=True)
        if browser_mgr._auto_launch_task and not browser_mgr._auto_launch_task.done():
            browser_mgr._auto_launch_task.cancel()
            await asyncio.gather(browser_mgr._auto_launch_task, return_exceptions=True)
        await browser_mgr.cleanup_all()


app = FastAPI(title="Invisible Browser Manager", lifespan=lifespan)
app.add_middleware(AuthMiddleware)


# ── Authentication ────────────────────────────────────────────────────────────


@app.get("/api/auth/status")
async def auth_status(request: starlette.requests.Request):
    """Check if auth is enabled and if the current request is authenticated.

    Exempt from auth middleware so the frontend can always call it.
    """
    authenticated = False
    if AUTH_TOKEN:
        authenticated = _check_auth(request.scope)
    return {"auth_required": AUTH_TOKEN is not None, "authenticated": authenticated}


@app.post("/api/auth/login")
async def auth_login(body: LoginRequest, request: Request, response: Response):
    if not AUTH_TOKEN:
        return {"ok": True}
    if not body.token or not hmac.compare_digest(body.token, AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid token")
    is_https = _is_https(request)
    auth_cookie_value = _auth_cookie_value()
    if not auth_cookie_value:
        raise HTTPException(status_code=500, detail="Authentication unavailable")
    response.set_cookie(
        key="auth_token",
        value=auth_cookie_value,
        httponly=True,
        samesite="strict",
        secure=is_https,
        path="/",
    )
    return {"ok": True}


@app.post("/api/auth/logout")
async def auth_logout(request: Request, response: Response):
    is_https = _is_https(request)
    response.delete_cookie(
        key="auth_token", path="/", secure=is_https, samesite="strict",
    )
    return {"ok": True}


# ── Profile CRUD ──────────────────────────────────────────────────────────────

_PROXY_CHECK_ERROR_DETAIL = "Proxy check failed"
_PUBLIC_PROXY_CHECK_STATUSES = {"good", "error"}
_PUBLIC_PROXY_PROVIDER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}$")
_SENSITIVE_PROXY_PROVIDER_RE = re.compile(
    r"https?://|socks[45]://|@|[/?#=]|\b(authorization|bearer|token|secret|password|cookie|auth)\b",
    re.IGNORECASE,
)
_PUBLIC_AUDIT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()[\]-]{0,79}$")
_SENSITIVE_AUDIT_NAME_RE = re.compile(
    r"https?://|socks[45]://|@|[/?#=:]|\b(authorization|bearer|token|secret|password|cookie|auth)\b",
    re.IGNORECASE,
)


def _public_proxy_check_status(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value in _PUBLIC_PROXY_CHECK_STATUSES:
        return value
    return "unknown"


def _public_proxy_check_error(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value == _PROXY_CHECK_ERROR_DETAIL:
        return _PROXY_CHECK_ERROR_DETAIL
    return _PROXY_CHECK_ERROR_DETAIL


def _public_proxy_provider(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    provider = value.strip()
    if not provider:
        return None
    if not _PUBLIC_PROXY_PROVIDER_RE.fullmatch(provider):
        return None
    if _SENSITIVE_PROXY_PROVIDER_RE.search(provider):
        return None
    return provider


def _public_audit_name(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    name = value.strip()
    if not name:
        return None
    if not _PUBLIC_AUDIT_NAME_RE.fullmatch(name):
        return None
    if _SENSITIVE_AUDIT_NAME_RE.search(name):
        return None
    return name


def _tag_responses(tags: object) -> list[TagResponse]:
    if not isinstance(tags, list):
        return []
    responses: list[TagResponse] = []
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        name = tag.get("tag")
        if not isinstance(name, str):
            continue
        color = tag.get("color")
        responses.append(TagResponse(tag=name, color=color if isinstance(color, str) else None))
    return responses


def _proxy_response(proxy: dict) -> ProxyResponse:
    safe = dict(proxy)
    safe["url"] = redact_proxy_asset_url(str(safe["url"]))
    safe["provider"] = _public_proxy_provider(safe.get("provider"))
    safe["country_code"] = public_geoip_country_code(safe.get("country_code"))
    safe["last_check_status"] = _public_proxy_check_status(safe.get("last_check_status"))
    safe["last_check_ip"] = public_geoip_ip(safe.get("last_check_ip"))
    safe["last_check_country_code"] = public_geoip_country_code(safe.get("last_check_country_code"))
    safe["last_check_timezone"] = public_geoip_timezone(safe.get("last_check_timezone"))
    safe["last_check_locale"] = public_geoip_locale(safe.get("last_check_locale"))
    safe["last_check_source"] = public_geoip_source(safe.get("last_check_source"))
    safe["last_check_error"] = _public_proxy_check_error(safe.get("last_check_error"))
    safe["tags"] = _tag_responses(safe.get("tags"))
    return ProxyResponse(**safe)


def _profile_response(profile: dict) -> ProfileResponse:
    safe = sanitize_profile_response_data(profile)
    safe["last_geoip_ip"] = public_geoip_ip(safe.get("last_geoip_ip"))
    safe["last_geoip_country_code"] = public_geoip_country_code(safe.get("last_geoip_country_code"))
    safe["last_geoip_timezone"] = public_geoip_timezone(safe.get("last_geoip_timezone"))
    safe["last_geoip_locale"] = public_geoip_locale(safe.get("last_geoip_locale"))
    safe["last_geoip_source"] = public_geoip_source(safe.get("last_geoip_source"))
    safe["tags"] = _tag_responses(safe.get("tags"))
    return ProfileResponse(**safe)


def _proxy_audit_metadata(proxy: dict, *, updated_fields: list[str] | None = None) -> dict:
    metadata = {
        "proxy_id": str(proxy["id"]),
        "name": _public_audit_name(proxy.get("name")),
        "provider": _public_proxy_provider(proxy.get("provider")),
        "country_code": public_geoip_country_code(proxy.get("country_code")),
        "tag_count": len(proxy.get("tags") or []),
    }
    if updated_fields is not None:
        metadata = {
            "proxy_id": str(proxy["id"]),
            "updated_fields": sorted(updated_fields),
            "tag_count": len(proxy.get("tags") or []),
        }
    return {key: value for key, value in metadata.items() if value is not None}


def _audit_proxy_event(event_type: str, proxy: dict, *, updated_fields: list[str] | None = None) -> None:
    db.create_audit_event(
        event_type=event_type,
        actor_type="local_admin",
        metadata=_proxy_audit_metadata(proxy, updated_fields=updated_fields),
    )


def _profile_audit_metadata(profile: dict, *, updated_fields: list[str] | None = None) -> dict:
    if updated_fields is not None:
        return {
            "updated_fields": sorted(updated_fields),
            "tag_count": len(profile.get("tags") or []),
        }
    metadata = {
        "name": _public_audit_name(profile.get("name")),
        "platform": profile.get("platform"),
        "tag_count": len(profile.get("tags") or []),
    }
    return {key: value for key, value in metadata.items() if value is not None}


def _audit_profile_event(
    event_type: str,
    profile: dict,
    *,
    updated_fields: list[str] | None = None,
) -> None:
    db.create_audit_event(
        event_type=event_type,
        actor_type="local_admin",
        profile_id=str(profile["id"]),
        metadata=_profile_audit_metadata(profile, updated_fields=updated_fields),
    )


def _audit_bulk_event(
    event_type: str,
    metadata: dict,
    *,
    profile_id: str | None = None,
) -> None:
    db.create_audit_event(
        event_type=event_type,
        actor_type="local_admin",
        profile_id=profile_id,
        metadata=metadata,
    )


def _health_check_audit_metadata(
    health: ProfileHealthResponse,
    *,
    lookup_attempted: bool,
    lookup_result: str,
) -> dict:
    metadata = {
        "status": health.status,
        "warning_codes": [warning.code for warning in health.warnings],
        "warning_count": len(health.warnings),
        "lookup_attempted": lookup_attempted,
        "lookup_result": lookup_result,
        "manual_timezone_override": health.manual_overrides.get("timezone", False),
        "manual_locale_override": health.manual_overrides.get("locale", False),
        "runtime_status": health.runtime.get("status"),
    }
    if health.geoip and lookup_result == "success":
        if health.geoip.source:
            metadata["geoip_source"] = health.geoip.source
        if health.geoip.country_code:
            metadata["geoip_country_code"] = health.geoip.country_code
    return {key: value for key, value in metadata.items() if value is not None}


def _audit_health_check(
    profile_id: str,
    health: ProfileHealthResponse,
    *,
    lookup_attempted: bool,
    lookup_result: str,
) -> None:
    db.create_audit_event(
        event_type="profile.health_checked",
        actor_type="local_admin",
        profile_id=profile_id,
        metadata=_health_check_audit_metadata(
            health,
            lookup_attempted=lookup_attempted,
            lookup_result=lookup_result,
        ),
    )


def _proxy_provider_preset_response(preset: dict) -> ProxyProviderPresetResponse:
    safe = dict(preset)
    safe["provider"] = _public_proxy_provider(safe.get("provider"))
    safe["country_code"] = public_geoip_country_code(safe.get("country_code"))
    safe["tags"] = _tag_responses(safe.get("tags"))
    return ProxyProviderPresetResponse(**safe)


def _proxy_provider_preset_audit_metadata(
    preset: dict,
    *,
    updated_fields: list[str] | None = None,
) -> dict:
    metadata = {
        "preset_id": str(preset["id"]),
        "tag_count": len(preset.get("tags") or []),
    }
    if updated_fields is not None:
        metadata["updated_fields"] = sorted(updated_fields)
    return metadata


def _audit_proxy_provider_preset_event(
    event_type: str,
    preset: dict,
    *,
    updated_fields: list[str] | None = None,
) -> None:
    db.create_audit_event(
        event_type=event_type,
        actor_type="local_admin",
        metadata=_proxy_provider_preset_audit_metadata(
            preset,
            updated_fields=updated_fields,
        ),
    )


def _tag_payloads(tags: list[dict] | None) -> list[dict]:
    return [tag.model_dump() if hasattr(tag, "model_dump") else tag for tag in (tags or [])]


def _normalize_filter_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_country_code(value: str | None) -> str | None:
    return public_geoip_country_code(value)


def _normalize_tag(value: str | None) -> str | None:
    normalized = _normalize_filter_value(value)
    return normalized.lower() if normalized else None


def _merge_proxy_selection_tags(
    preset_tags: list[dict] | None,
    request_tags: list[str] | None,
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    tag_sources = [*(preset_tags or []), *({"tag": tag} for tag in (request_tags or []))]
    for tag in tag_sources:
        raw = tag.get("tag") if isinstance(tag, dict) else None
        normalized = _normalize_tag(raw)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return merged


def _proxy_matches_selection(
    proxy: dict,
    *,
    provider: str | None,
    country_code: str | None,
    tags: list[str],
) -> bool:
    if provider and _public_proxy_provider(proxy.get("provider")) != provider:
        return False
    if country_code and public_geoip_country_code(proxy.get("country_code")) != country_code:
        return False
    if tags:
        proxy_tags = {
            normalized
            for tag in proxy.get("tags", [])
            if (normalized := _normalize_tag(tag.get("tag") if isinstance(tag, dict) else None))
        }
        return all(tag in proxy_tags for tag in tags)
    return True


def _template_response(template: dict) -> ProfileTemplateResponse:
    return ProfileTemplateResponse(**sanitize_profile_template_response_data(template))


_PUBLIC_RUNTIME_SESSION_STATUSES = {"active", "terminated"}
_PUBLIC_RUNTIME_EXTERNAL_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SENSITIVE_RUNTIME_EXTERNAL_SESSION_ID_RE = re.compile(
    r"https?://|socks[45]://|@|[/?#=:]|\b(authorization|bearer)\b|"
    r"\b(auth_token|password|cookie|secret|token|viewer_token)\s*=",
    re.IGNORECASE,
)


def _public_runtime_session_status(value: object) -> str:
    if isinstance(value, str) and value in _PUBLIC_RUNTIME_SESSION_STATUSES:
        return value
    return "unknown"


def _public_runtime_external_session_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    external_session_id = value.strip()
    if not external_session_id:
        return None
    if not _PUBLIC_RUNTIME_EXTERNAL_SESSION_ID_RE.fullmatch(external_session_id):
        return None
    if _SENSITIVE_RUNTIME_EXTERNAL_SESSION_ID_RE.search(external_session_id):
        return None
    return external_session_id


def _public_uuid_identifier(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = uuid.UUID(text)
    except ValueError:
        return None
    return str(parsed)


def _runtime_session_response(session: dict) -> RuntimeSessionResponse:
    safe = dict(session)
    safe["id"] = _public_uuid_identifier(safe.get("id")) or "unknown"
    safe["profile_id"] = _public_uuid_identifier(safe.get("profile_id")) or "unknown"
    safe["status"] = _public_runtime_session_status(safe.get("status"))
    safe["external_session_id"] = _public_runtime_external_session_id(
        safe.get("external_session_id")
    ) or "unknown"
    return RuntimeSessionResponse(**safe)


def _audit_runtime_event(event_type: str, session: dict, metadata: dict | None = None) -> None:
    db.create_audit_event(
        event_type=event_type,
        actor_type="runtime_service",
        runtime_session_id=_public_uuid_identifier(session.get("id")),
        profile_id=_public_uuid_identifier(session.get("profile_id")),
        external_session_id=_public_runtime_external_session_id(session.get("external_session_id")),
        metadata=metadata,
    )


def _audit_runtime_viewer_event(event_type: str, session: dict, metadata: dict | None = None) -> None:
    db.create_audit_event(
        event_type=event_type,
        actor_type="runtime_viewer",
        runtime_session_id=_public_uuid_identifier(session.get("id")),
        profile_id=_public_uuid_identifier(session.get("profile_id")),
        external_session_id=_public_runtime_external_session_id(session.get("external_session_id")),
        metadata=metadata,
    )


def _audit_runtime_viewer_failure(
    reason_code: str,
    *,
    session: dict | None = None,
    session_id: str | None = None,
) -> None:
    try:
        db.create_audit_event(
            event_type="runtime.viewer.failed",
            actor_type="runtime_viewer",
            runtime_session_id=(
                _public_uuid_identifier(session.get("id"))
                if session
                else _public_uuid_identifier(session_id)
            ),
            profile_id=(
                _public_uuid_identifier(session.get("profile_id"))
                if session
                else None
            ),
            external_session_id=(
                _public_runtime_external_session_id(session.get("external_session_id"))
                if session
                else None
            ),
            metadata={"reason_code": reason_code},
        )
    except Exception as exc:
        logger.warning("Runtime viewer failure audit skipped: %s", type(exc).__name__)


def _cookie_export_audit_metadata(summary: dict) -> dict:
    return {
        "format": summary.get("format"),
        "schema_version": summary.get("schema_version"),
        "total_count": summary.get("cookie_count"),
        "domain_scoped_count": summary.get("domain_scoped_count"),
        "url_scoped_count": summary.get("url_scoped_count"),
        "secure_count": summary.get("secure_count"),
        "http_only_count": summary.get("http_only_count"),
        "session_count": summary.get("session_cookie_count"),
        "persistent_count": summary.get("persistent_cookie_count"),
        "same_site_counts": summary.get("same_site_counts"),
    }


def _netscape_cookie_export_audit_metadata(summary: dict) -> dict:
    return {
        "format": summary.get("format"),
        "total_count": summary.get("cookie_count"),
        "secure_count": summary.get("secure_count"),
        "session_count": summary.get("session_cookie_count"),
        "persistent_count": summary.get("persistent_cookie_count"),
        "http_only_count": summary.get("http_only_count"),
    }


def _origin_from_page_url(raw_url: str) -> str | None:
    parsed = urlparse(str(raw_url))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return f"{parsed.scheme}://{host}"


def _normalize_local_storage_entries(raw_entries: object) -> list[dict[str, str]]:
    if not isinstance(raw_entries, list):
        raise ValueError("Invalid local storage entries")
    entries: list[dict[str, str]] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            raise ValueError("Invalid local storage entries")
        key = raw_entry.get("key")
        value = raw_entry.get("value")
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("Invalid local storage entries")
        entries.append({"key": key, "value": value})
    return entries


_PROFILE_CONFIG_IMPORT_FIELDS = {
    "name",
    "fingerprint_seed",
    "proxy",
    "timezone",
    "locale",
    "platform",
    "user_agent",
    "screen_width",
    "screen_height",
    "gpu_vendor",
    "gpu_renderer",
    "hardware_concurrency",
    "humanize",
    "human_preset",
    "headless",
    "geoip",
    "clipboard_sync",
    "auto_launch",
    "color_scheme",
    "launch_args",
    "notes",
    "tags",
}


def _validation_error_messages(exc: ValidationError) -> list[str]:
    errors = []
    for error in exc.errors():
        loc = ".".join(str(item) for item in error.get("loc", ()))
        message = str(error.get("msg", "Invalid value"))
        errors.append(f"{loc}: {message}" if loc else message)
    return errors


def _validation_error_includes_field(exc: ValidationError, field_name: str) -> bool:
    return any(field_name in error.get("loc", ()) for error in exc.errors())


def _profile_config_import_data(config: dict) -> dict:
    return {
        field: config[field]
        for field in _PROFILE_CONFIG_IMPORT_FIELDS
        if field in config
    }


def _profile_config_import_errors(data: dict) -> list[str]:
    if not str(data.get("name", "")).strip():
        return ["name is required"]
    return []


async def _import_payload_with_confirmation(request: Request, detail: str) -> dict:
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail=detail) from None
    if not isinstance(payload, dict) or payload.get("confirm_import") is not True:
        raise HTTPException(status_code=422, detail=detail)
    return payload


async def _cookie_import_payload_with_confirmation(request: Request) -> dict:
    try:
        payload = await request.json()
        confirmation = CookieImportConfirmRequest.model_validate(payload)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Cookie import requires explicit confirmation",
        ) from None

    if confirmation.confirm_import is not True:
        raise HTTPException(
            status_code=422,
            detail="Cookie import requires explicit confirmation",
        )
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Invalid cookie JSON document")
    return {key: value for key, value in payload.items() if key != "confirm_import"}


def _runtime_service_token_from_request(request: Request) -> str | None:
    token = request.headers.get("X-Runtime-Service-Token")
    return token or None


def _require_runtime_service_token(request: Request) -> None:
    token = _runtime_service_token_from_request(request)
    if not RUNTIME_SERVICE_TOKEN or not token or not hmac.compare_digest(token, RUNTIME_SERVICE_TOKEN):
        raise HTTPException(status_code=401, detail="Runtime service token required")


def _runtime_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_datetime(value: str) -> datetime.datetime | None:
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)


def _runtime_session_is_live(session: dict) -> bool:
    if session.get("status") != "active":
        return False
    lease_expires_at = _parse_datetime(session.get("lease_expires_at", ""))
    return bool(lease_expires_at and lease_expires_at > _utc_now())


def _runtime_viewer_token_failure_reason(session: dict, viewer_token: str | None) -> str | None:
    if not viewer_token:
        return "viewer_credential_missing"
    token_hash = session.get("viewer_token_hash")
    if not token_hash or not hmac.compare_digest(token_hash, _runtime_token_hash(viewer_token)):
        return "viewer_credential_invalid"
    expires_at = _parse_datetime(session.get("viewer_token_expires_at", ""))
    if not expires_at or expires_at <= _utc_now():
        return "viewer_credential_expired"
    return None


def _runtime_viewer_token_is_valid(session: dict, viewer_token: str | None) -> bool:
    return _runtime_viewer_token_failure_reason(session, viewer_token) is None


def _safe_proxy_check_error(_exc: Exception, _raw_url: str) -> str:
    return _PROXY_CHECK_ERROR_DETAIL


_SAFE_PROXY_ASSET_ERROR_DETAILS = (
    ("Invalid proxy scheme", "Invalid proxy scheme"),
    ("Invalid proxy URL", "Invalid proxy URL"),
    ("Proxy URL missing hostname", "Proxy URL missing hostname"),
    ("Proxy URL invalid port", "Proxy URL invalid port"),
    ("Proxy URL missing port", "Proxy URL missing port"),
)
_RESOURCE_LIMIT_ERROR_DETAIL = "Maximum running profiles reached"


def _safe_proxy_asset_error_detail(exc: ValueError) -> str:
    message = str(exc)
    for prefix, detail in _SAFE_PROXY_ASSET_ERROR_DETAILS:
        if message.startswith(prefix):
            return detail
    return "Invalid proxy URL"


async def _run_proxy_check(proxy: dict) -> dict:
    raw_url = str(proxy["url"])
    check_at = db._now()

    try:
        geo = await resolve_network_geo(raw_url)
    except Exception as exc:
        safe_error = _safe_proxy_check_error(exc, raw_url)
        updated = db.update_proxy(
            str(proxy["id"]),
            last_check_status="error",
            last_check_error=safe_error,
            last_check_at=check_at,
        )
    else:
        updated = db.update_proxy(
            str(proxy["id"]),
            last_check_status="good",
            last_check_ip=public_geoip_ip(geo.ip),
            last_check_country_code=public_geoip_country_code(geo.country_code),
            last_check_timezone=public_geoip_timezone(geo.timezone),
            last_check_locale=public_geoip_locale(geo.locale),
            last_check_source=public_geoip_source(geo.source),
            last_check_error=None,
            last_check_at=check_at,
        )

    if not updated:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return updated


@app.get("/api/proxies", response_model=list[ProxyResponse])
async def list_proxies():
    return [_proxy_response(proxy) for proxy in db.list_proxies()]


@app.post("/api/proxies", response_model=ProxyResponse, status_code=201)
async def create_proxy(req: ProxyCreate):
    data = req.model_dump()
    data["tags"] = _tag_payloads(data.get("tags"))
    try:
        proxy = db.create_proxy(**data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_safe_proxy_asset_error_detail(exc)) from exc
    _audit_proxy_event("proxy.created", proxy)
    return _proxy_response(proxy)


@app.get("/api/proxies/{proxy_id}", response_model=ProxyResponse)
async def get_proxy(proxy_id: str):
    proxy = db.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return _proxy_response(proxy)


@app.put("/api/proxies/{proxy_id}", response_model=ProxyResponse)
async def update_proxy(proxy_id: str, req: ProxyUpdate):
    data = req.model_dump(exclude_unset=True)
    audit_fields = sorted(data.keys())
    if "tags" in data and data["tags"] is not None:
        data["tags"] = _tag_payloads(data["tags"])
    try:
        proxy = db.update_proxy(proxy_id, **data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_safe_proxy_asset_error_detail(exc)) from exc
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    _audit_proxy_event("proxy.updated", proxy, updated_fields=audit_fields)
    return _proxy_response(proxy)


@app.delete("/api/proxies/{proxy_id}")
async def delete_proxy(proxy_id: str, request: Request):
    try:
        req = ProxyDeleteRequest.model_validate(await request.json())
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Proxy delete requires explicit confirmation",
        ) from None

    if req.confirm_delete is not True:
        raise HTTPException(
            status_code=422,
            detail="Proxy delete requires explicit confirmation",
        )

    proxy = db.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    deleted = db.delete_proxy(proxy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Proxy not found")
    _audit_proxy_event("proxy.deleted", proxy)
    return {"ok": True}


@app.get("/api/proxy-provider-presets", response_model=list[ProxyProviderPresetResponse])
async def list_proxy_provider_presets():
    return [
        _proxy_provider_preset_response(preset)
        for preset in db.list_proxy_provider_presets()
    ]


@app.post(
    "/api/proxy-provider-presets",
    response_model=ProxyProviderPresetResponse,
    status_code=201,
)
async def create_proxy_provider_preset(req: ProxyProviderPresetCreate):
    data = req.model_dump()
    data["tags"] = _tag_payloads(data.get("tags"))
    preset = db.create_proxy_provider_preset(**data)
    _audit_proxy_provider_preset_event("proxy.provider_preset.created", preset)
    return _proxy_provider_preset_response(preset)


@app.get("/api/proxy-provider-presets/{preset_id}", response_model=ProxyProviderPresetResponse)
async def get_proxy_provider_preset(preset_id: str):
    preset = db.get_proxy_provider_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Proxy provider preset not found")
    return _proxy_provider_preset_response(preset)


@app.put("/api/proxy-provider-presets/{preset_id}", response_model=ProxyProviderPresetResponse)
async def update_proxy_provider_preset(preset_id: str, req: ProxyProviderPresetUpdate):
    data = req.model_dump(exclude_unset=True)
    audit_fields = sorted(data.keys())
    if "tags" in data and data["tags"] is not None:
        data["tags"] = _tag_payloads(data["tags"])
    preset = db.update_proxy_provider_preset(preset_id, **data)
    if not preset:
        raise HTTPException(status_code=404, detail="Proxy provider preset not found")
    _audit_proxy_provider_preset_event(
        "proxy.provider_preset.updated",
        preset,
        updated_fields=audit_fields,
    )
    return _proxy_provider_preset_response(preset)


@app.delete("/api/proxy-provider-presets/{preset_id}")
async def delete_proxy_provider_preset(preset_id: str, request: Request):
    try:
        req = ProxyProviderPresetDeleteRequest.model_validate(await request.json())
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Proxy provider preset delete requires explicit confirmation",
        ) from None

    if req.confirm_delete is not True:
        raise HTTPException(
            status_code=422,
            detail="Proxy provider preset delete requires explicit confirmation",
        )

    preset = db.get_proxy_provider_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Proxy provider preset not found")
    deleted = db.delete_proxy_provider_preset(preset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Proxy provider preset not found")
    _audit_proxy_provider_preset_event("proxy.provider_preset.deleted", preset)
    return {"ok": True}


@app.post("/api/proxies/{proxy_id}/assign", response_model=ProxyAssignResponse)
async def assign_proxy_to_profiles(proxy_id: str, request: Request):
    try:
        req = ProxyAssignRequest.model_validate(await request.json())
    except ValidationError as exc:
        if _validation_error_includes_field(exc, "confirm_assign"):
            raise HTTPException(
                status_code=422,
                detail="Proxy assignment requires explicit confirmation",
            ) from None
        raise HTTPException(status_code=422, detail=_validation_error_messages(exc)) from exc
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Proxy assignment requires explicit confirmation",
        ) from None

    if req.confirm_assign is not True:
        raise HTTPException(
            status_code=422,
            detail="Proxy assignment requires explicit confirmation",
        )

    proxy = db.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    results: list[ProxyAssignResult] = []
    raw_url = str(proxy["url"])
    for profile_id in req.profile_ids:
        profile = db.update_profile(profile_id, proxy=raw_url)
        if not profile:
            results.append(
                ProxyAssignResult(
                    profile_id=profile_id,
                    ok=False,
                    error="Profile not found",
                )
            )
            continue
        results.append(ProxyAssignResult(profile_id=profile_id, ok=True, error=None))

    succeeded = sum(1 for result in results if result.ok)
    response = ProxyAssignResponse(
        proxy_id=proxy_id,
        proxy=_proxy_response(proxy),
        total=len(req.profile_ids),
        succeeded=succeeded,
        failed=len(req.profile_ids) - succeeded,
        results=results,
    )
    if succeeded:
        _audit_bulk_event(
            "proxy.assigned",
            {
                "proxy_id": proxy_id,
                "profile_count": len(req.profile_ids),
                "assigned_count": succeeded,
                "missing_profile_count": len(req.profile_ids) - succeeded,
            },
        )
    return response


@app.post("/api/proxies/assign/random", response_model=ProxyRandomAssignResponse)
async def assign_random_proxy_to_profiles(request: Request):
    try:
        req = ProxyRandomAssignRequest.model_validate(await request.json())
    except ValidationError as exc:
        if _validation_error_includes_field(exc, "confirm_assign"):
            raise HTTPException(
                status_code=422,
                detail="Random proxy assignment requires explicit confirmation",
            ) from None
        raise HTTPException(status_code=422, detail=_validation_error_messages(exc)) from exc
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Random proxy assignment requires explicit confirmation",
        ) from None

    if req.confirm_assign is not True:
        raise HTTPException(
            status_code=422,
            detail="Random proxy assignment requires explicit confirmation",
        )

    preset = None
    if req.provider_preset_id:
        preset = db.get_proxy_provider_preset(req.provider_preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail="Proxy provider preset not found")

    provider = _public_proxy_provider(req.provider) or _public_proxy_provider(
        preset.get("provider") if preset else None
    )
    country_code = _normalize_country_code(req.country_code) or _normalize_country_code(
        preset.get("country_code") if preset else None
    )
    tags = _merge_proxy_selection_tags(
        preset.get("tags") if preset else None,
        req.tags,
    )
    candidates = [
        proxy
        for proxy in db.list_proxies()
        if _proxy_matches_selection(
            proxy,
            provider=provider,
            country_code=country_code,
            tags=tags,
        )
    ]

    if not candidates:
        raise HTTPException(status_code=400, detail="No proxy assets match selection")

    results: list[ProxyRandomAssignResult] = []
    for profile_id in req.profile_ids:
        chosen = random.choice(candidates)
        profile = db.update_profile(profile_id, proxy=str(chosen["url"]))
        if not profile:
            results.append(
                ProxyRandomAssignResult(
                    profile_id=profile_id,
                    ok=False,
                    error="Profile not found",
                    proxy_id=None,
                    proxy=None,
                )
            )
            continue
        results.append(
            ProxyRandomAssignResult(
                profile_id=profile_id,
                ok=True,
                error=None,
                proxy_id=str(chosen["id"]),
                proxy=_proxy_response(chosen),
            )
        )

    succeeded = sum(1 for result in results if result.ok)
    response = ProxyRandomAssignResponse(
        strategy="random",
        provider_preset_id=req.provider_preset_id,
        provider=provider,
        country_code=country_code,
        tags=tags,
        candidate_count=len(candidates),
        total=len(req.profile_ids),
        succeeded=succeeded,
        failed=len(req.profile_ids) - succeeded,
        results=results,
    )
    if succeeded:
        audit_metadata = {
            "provider_preset_id": req.provider_preset_id,
            "provider": provider,
            "country_code": country_code,
            "tag_count": len(tags),
            "candidate_count": len(candidates),
            "profile_count": len(req.profile_ids),
            "assigned_count": succeeded,
            "missing_profile_count": len(req.profile_ids) - succeeded,
        }
        _audit_bulk_event(
            "proxy.random_assigned",
            {key: value for key, value in audit_metadata.items() if value is not None},
        )
    return response


@app.post("/api/proxies/bulk/check", response_model=ProxyBulkCheckResponse)
async def bulk_check_proxies(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Proxy bulk check requires explicit confirmation",
        ) from None

    if not isinstance(payload, dict) or payload.get("confirm_bulk_check") is not True:
        raise HTTPException(
            status_code=422,
            detail="Proxy bulk check requires explicit confirmation",
        )

    try:
        req = ProxyBulkCheckRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_validation_error_messages(exc)) from exc

    results: list[ProxyBulkCheckResult] = []

    for proxy_id in req.proxy_ids:
        proxy = db.get_proxy(proxy_id)
        if not proxy:
            results.append(
                ProxyBulkCheckResult(
                    proxy_id=proxy_id,
                    ok=False,
                    error="Proxy not found",
                    proxy=None,
                )
            )
            continue

        updated = await _run_proxy_check(proxy)
        ok = updated.get("last_check_status") == "good"
        results.append(
            ProxyBulkCheckResult(
                proxy_id=proxy_id,
                ok=ok,
                error=None if ok else updated.get("last_check_error") or _PROXY_CHECK_ERROR_DETAIL,
                proxy=_proxy_response(updated),
            )
        )

    succeeded = sum(1 for result in results if result.ok)
    response = ProxyBulkCheckResponse(
        total=len(req.proxy_ids),
        succeeded=succeeded,
        failed=len(req.proxy_ids) - succeeded,
        results=results,
    )
    checked_count = sum(1 for result in results if result.proxy is not None)
    missing_count = len(req.proxy_ids) - checked_count
    error_count = checked_count - succeeded
    if checked_count:
        _audit_bulk_event(
            "proxy.bulk_checked",
            {
                "proxy_count": len(req.proxy_ids),
                "checked_count": checked_count,
                "good_count": succeeded,
                "error_count": error_count,
                "missing_count": missing_count,
            },
        )
    return response


@app.get("/api/profile-templates", response_model=list[ProfileTemplateResponse])
async def list_profile_templates():
    return [_template_response(template) for template in db.list_profile_templates()]


@app.post("/api/profile-templates", response_model=ProfileTemplateResponse, status_code=201)
async def create_profile_template(req: ProfileTemplateCreate):
    template = db.create_profile_template(**req.model_dump())
    return _template_response(template)


@app.get("/api/profile-templates/{template_id}", response_model=ProfileTemplateResponse)
async def get_profile_template(template_id: str):
    template = db.get_profile_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Profile template not found")
    return _template_response(template)


@app.put("/api/profile-templates/{template_id}", response_model=ProfileTemplateResponse)
async def update_profile_template(template_id: str, req: ProfileTemplateUpdate):
    template = db.update_profile_template(template_id, **req.model_dump(exclude_unset=True))
    if not template:
        raise HTTPException(status_code=404, detail="Profile template not found")
    return _template_response(template)


@app.delete("/api/profile-templates/{template_id}")
async def delete_profile_template(template_id: str, request: Request):
    try:
        req = ProfileTemplateDeleteRequest.model_validate(await request.json())
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Profile template delete requires explicit confirmation",
        ) from None

    if req.confirm_delete is not True:
        raise HTTPException(
            status_code=422,
            detail="Profile template delete requires explicit confirmation",
        )

    deleted = db.delete_profile_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile template not found")
    return {"ok": True}


@app.post("/api/runtime/sessions", response_model=RuntimeSessionResponse, status_code=201)
async def create_runtime_session(req: RuntimeSessionCreate, request: Request):
    _require_runtime_service_token(request)

    profile = None
    if req.profile_id:
        profile = db.get_profile(req.profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
    else:
        template = db.get_profile_template(req.template_id or "")
        if not template:
            raise HTTPException(status_code=404, detail="Profile template not found")
        public_external_session_id = _public_runtime_external_session_id(req.external_session_id)
        runtime_profile_name = (
            f"Runtime {public_external_session_id}"
            if public_external_session_id
            else "Runtime session"
        )
        profile = db.create_profile(
            name=runtime_profile_name,
            platform=template.get("platform", "windows"),
            screen_width=template.get("screen_width", 1920),
            screen_height=template.get("screen_height", 1080),
            gpu_vendor=template.get("gpu_vendor"),
            gpu_renderer=template.get("gpu_renderer"),
            hardware_concurrency=template.get("hardware_concurrency"),
            color_scheme=template.get("color_scheme"),
            humanize=template.get("humanize", False),
            human_preset=template.get("human_preset", "default"),
            launch_args=template.get("launch_args") or [],
            geoip=template.get("geoip", True),
        )

    profile_id = str(profile["id"])
    if profile_id not in browser_mgr.running:
        try:
            running = await browser_mgr.launch(profile)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=_safe_proxy_asset_error_detail(exc)) from exc
        except BrowserResourceLimitError as exc:
            raise HTTPException(status_code=409, detail=_RESOURCE_LIMIT_ERROR_DETAIL) from exc
        except Exception as exc:
            logger.error(
                "Failed to launch runtime session profile %s error_type=%s",
                profile_id,
                type(exc).__name__,
            )
            raise HTTPException(status_code=500, detail="Failed to launch browser") from exc
        db.update_profile_geoip_result(profile_id, getattr(running, "resolved_geoip", None))

    session = db.create_runtime_session(
        profile_id=profile_id,
        external_session_id=req.external_session_id,
        lease_seconds=req.lease_seconds,
        status="active",
    )
    _audit_runtime_event(
        "runtime.session.created",
        session,
        {
            "profile_source": "profile_id" if req.profile_id else "template_id",
            "lease_seconds": req.lease_seconds,
        },
    )
    return _runtime_session_response(session)


@app.get("/api/runtime/sessions/{session_id}", response_model=RuntimeSessionResponse)
async def get_runtime_session(session_id: str, request: Request):
    _require_runtime_service_token(request)
    session = db.get_runtime_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Runtime session not found")
    _audit_runtime_event("runtime.session.read", session)
    return _runtime_session_response(session)


@app.post(
    "/api/runtime/sessions/{session_id}/viewer-token",
    response_model=RuntimeViewerTokenResponse,
    status_code=201,
)
async def create_runtime_viewer_token(
    session_id: str,
    req: RuntimeViewerTokenCreate,
    request: Request,
):
    _require_runtime_service_token(request)
    session = db.get_runtime_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Runtime session not found")
    if not _runtime_session_is_live(session):
        raise HTTPException(status_code=409, detail="Runtime session is not active")

    viewer_token = secrets.token_urlsafe(32)
    expires_at = (_utc_now() + datetime.timedelta(seconds=req.ttl_seconds)).isoformat()
    updated = db.set_runtime_session_viewer_token(
        session_id,
        _runtime_token_hash(viewer_token),
        expires_at,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Runtime session not found")
    _audit_runtime_event(
        "runtime.viewer_token.created",
        updated,
        {
            "ttl_seconds": req.ttl_seconds,
            "viewer_token_expires_at": expires_at,
        },
    )

    public_session_id = _public_uuid_identifier(updated.get("id")) or "unknown"
    viewer_url = f"/api/runtime/sessions/{public_session_id}/vnc?viewer_token={viewer_token}"
    return RuntimeViewerTokenResponse(
        viewer_url=viewer_url,
        viewer_token=viewer_token,
        expires_at=expires_at,
    )


@app.post("/api/runtime/sessions/{session_id}/terminate", response_model=RuntimeSessionResponse)
async def terminate_runtime_session(session_id: str, request: Request):
    _require_runtime_service_token(request)
    try:
        req = RuntimeSessionTerminate.model_validate(await request.json())
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Runtime session terminate requires explicit confirmation",
        ) from None

    if req.confirm_terminate is not True:
        raise HTTPException(
            status_code=422,
            detail="Runtime session terminate requires explicit confirmation",
        )

    session = db.terminate_runtime_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Runtime session not found")
    _audit_runtime_event("runtime.session.terminated", session)
    return _runtime_session_response(session)


@app.post("/api/runtime/sessions/{session_id}/renew", response_model=RuntimeSessionResponse)
async def renew_runtime_session(session_id: str, req: RuntimeSessionRenew, request: Request):
    _require_runtime_service_token(request)
    session = db.get_runtime_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Runtime session not found")
    if not _runtime_session_is_live(session):
        raise HTTPException(status_code=409, detail="Runtime session is not active")
    renewed = db.renew_runtime_session(session_id, req.lease_seconds)
    if not renewed:
        raise HTTPException(status_code=404, detail="Runtime session not found")
    _audit_runtime_event(
        "runtime.session.renewed",
        renewed,
        {
            "lease_seconds": req.lease_seconds,
            "lease_expires_at": renewed["lease_expires_at"],
        },
    )
    return _runtime_session_response(renewed)


@app.post("/api/proxies/{proxy_id}/check", response_model=ProxyResponse)
async def check_proxy(proxy_id: str):
    proxy = db.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    updated = await _run_proxy_check(proxy)
    return _proxy_response(updated)


@app.get("/api/profiles", response_model=list[ProfileResponse])
async def list_profiles():
    profiles = db.list_profiles()
    result = []
    for p in profiles:
        status = browser_mgr.get_status(p["id"])
        p["status"] = status["status"]
        p["vnc_ws_port"] = status["vnc_ws_port"]
        p["automation_url"] = status["automation_url"]
        result.append(_profile_response(p))
    return result


@app.post("/api/profiles", response_model=ProfileResponse, status_code=201)
async def create_profile(req: ProfileCreate):
    data = req.model_dump()
    try:
        data = apply_profile_template_fields(data, set(req.model_fields_set))
    except ProfileTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    data.pop("template_id", None)
    tags = data.pop("tags", None)
    if tags:
        data["tags"] = [t.model_dump() if hasattr(t, "model_dump") else t for t in tags]
    else:
        data["tags"] = []
    profile = db.create_profile(**data)
    status = browser_mgr.get_status(profile["id"])
    profile["status"] = status["status"]
    profile["vnc_ws_port"] = status["vnc_ws_port"]
    profile["automation_url"] = status["automation_url"]
    _audit_profile_event("profile.created", profile)
    return _profile_response(profile)


@app.post("/api/profiles/import/preview", response_model=ProfileImportPreviewResponse)
async def preview_profile_import(req: ProfileImportPreviewRequest):
    try:
        return preview_profile_csv_import(req.csv_text)
    except ProfileImportHeaderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/profiles/import", response_model=ProfileImportResponse)
async def import_profiles(request: Request):
    payload = await _import_payload_with_confirmation(
        request,
        "Profile import requires explicit confirmation",
    )
    try:
        req = ProfileImportRequest.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid profile import request") from exc

    try:
        rows = parse_profile_csv_import(req.csv_text)
    except ProfileImportHeaderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    results: list[ProfileImportResult] = []
    for row in rows:
        if row.errors or row.create_data is None:
            results.append(
                ProfileImportResult(
                    line_number=row.line_number,
                    ok=False,
                    errors=row.errors,
                    source=row.source,
                    profile=None,
                )
            )
            continue

        try:
            profile = db.create_profile(**profile_create_data_for_import(row))
        except Exception:
            results.append(
                ProfileImportResult(
                    line_number=row.line_number,
                    ok=False,
                    errors=["Failed to create profile"],
                    source=row.source,
                    profile=None,
                )
            )
            continue

        status = browser_mgr.get_status(profile["id"])
        profile["status"] = status["status"]
        profile["vnc_ws_port"] = status["vnc_ws_port"]
        profile["automation_url"] = status["automation_url"]
        results.append(
            ProfileImportResult(
                line_number=row.line_number,
                ok=True,
                errors=[],
                source=row.source,
                profile=_profile_response(profile),
            )
        )

    succeeded = sum(1 for result in results if result.ok)
    response = ProfileImportResponse(
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=results,
    )
    if succeeded:
        _audit_bulk_event(
            "profile.imported",
            {
                "source_format": "csv",
                "total": len(results),
                "created_count": succeeded,
                "failed_count": len(results) - succeeded,
            },
        )
    return response


@app.post("/api/profiles/export", response_model=ProfileExportResponse)
async def export_profiles(req: ProfileExportRequest):
    if req.include_sensitive and req.confirm_sensitive_export is not True:
        raise HTTPException(
            status_code=422,
            detail="Profile export sensitive proxy requires explicit confirmation",
        )

    results: list[ProfileExportResult] = []
    for profile_id in req.profile_ids:
        profile = db.get_profile(profile_id)
        if not profile:
            results.append(
                ProfileExportResult(
                    profile_id=profile_id,
                    ok=False,
                    error="Profile not found",
                    config=None,
                )
            )
            continue

        profile = sanitize_profile_config_export_data(
            profile,
            include_sensitive_proxy=req.include_sensitive,
        )
        profile["tags"] = _tag_responses(profile.get("tags"))
        results.append(
            ProfileExportResult(
                profile_id=profile_id,
                ok=True,
                error=None,
                config=ProfileConfigExport(**profile),
            )
        )

    exported = sum(1 for result in results if result.ok)
    response = ProfileExportResponse(
        total=len(results),
        exported=exported,
        failed=len(results) - exported,
        results=results,
    )
    if exported:
        _audit_bulk_event(
            "profile.config_exported",
            {
                "source_format": "profile_config_json",
                "schema_version": 1,
                "include_sensitive": req.include_sensitive,
                "total": len(results),
                "exported_count": exported,
                "failed_count": len(results) - exported,
            },
        )
    return response


@app.post("/api/profiles/config/import", response_model=ProfileConfigImportResponse)
async def import_profile_configs(request: Request):
    payload = await _import_payload_with_confirmation(
        request,
        "Profile config import requires explicit confirmation",
    )
    try:
        req = ProfileConfigImportRequest.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid profile config import request") from exc

    results: list[ProfileConfigImportResult] = []
    for index, config in enumerate(req.configs):
        data = _profile_config_import_data(config)
        errors = _profile_config_import_errors(data)
        try:
            profile_create = ProfileCreate(**data)
        except ValidationError as exc:
            errors.extend(_validation_error_messages(exc))

        if errors:
            results.append(
                ProfileConfigImportResult(
                    index=index,
                    ok=False,
                    errors=errors,
                    profile=None,
                )
            )
            continue

        create_data = profile_create.model_dump()
        tags = create_data.pop("tags", None)
        if tags:
            create_data["tags"] = [tag.model_dump() if hasattr(tag, "model_dump") else tag for tag in tags]
        else:
            create_data["tags"] = []

        try:
            profile = db.create_profile(**create_data)
        except Exception:
            results.append(
                ProfileConfigImportResult(
                    index=index,
                    ok=False,
                    errors=["Failed to create profile"],
                    profile=None,
                )
            )
            continue

        status = browser_mgr.get_status(profile["id"])
        profile["status"] = status["status"]
        profile["vnc_ws_port"] = status["vnc_ws_port"]
        profile["automation_url"] = status["automation_url"]
        results.append(
            ProfileConfigImportResult(
                index=index,
                ok=True,
                errors=[],
                profile=_profile_response(profile),
            )
        )

    imported = sum(1 for result in results if result.ok)
    response = ProfileConfigImportResponse(
        total=len(results),
        imported=imported,
        failed=len(results) - imported,
        results=results,
    )
    if imported:
        _audit_bulk_event(
            "profile.config_imported",
            {
                "source_format": "profile_config_json",
                "schema_version": req.schema_version,
                "total": len(results),
                "created_count": imported,
                "failed_count": len(results) - imported,
            },
        )
    return response


@app.post("/api/profiles/{profile_id}/cookies/import", response_model=CookieImportResponse)
async def import_profile_cookies(profile_id: str, request: Request):
    running = _automation_running(profile_id)
    try:
        payload = await _cookie_import_payload_with_confirmation(request)
        document = CookieJsonDocument.model_validate(payload)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        logger.warning("Cookie JSON import validation failed for %s: %s", profile_id, type(exc).__name__)
        raise HTTPException(status_code=422, detail="Invalid cookie JSON document") from exc

    cookies = cookies_for_playwright(document)
    try:
        await running.context.add_cookies(cookies)
    except Exception as exc:
        logger.warning("Cookie import failed for %s: %s", profile_id, type(exc).__name__)
        raise HTTPException(status_code=400, detail="Cookie import failed") from exc

    return CookieImportResponse(
        profile_id=profile_id,
        imported=len(cookies),
        summary=cookie_json_audit_summary(document),
    )


@app.post("/api/profiles/{profile_id}/cookies/import/netscape", response_model=CookieImportResponse)
async def import_profile_cookies_netscape(profile_id: str, request: Request):
    running = _automation_running(profile_id)
    try:
        payload = await _cookie_import_payload_with_confirmation(request)
        req = NetscapeCookieImportRequest.model_validate({**payload, "confirm_import": True})
        document = parse_netscape_cookies(req.text)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        logger.warning("Netscape cookie import validation failed for %s: %s", profile_id, type(exc).__name__)
        raise HTTPException(status_code=422, detail="Invalid Netscape cookie document") from exc

    cookies = cookies_for_playwright(document)
    try:
        await running.context.add_cookies(cookies)
    except Exception as exc:
        logger.warning("Cookie import failed for %s: %s", profile_id, type(exc).__name__)
        raise HTTPException(status_code=400, detail="Cookie import failed") from exc

    return CookieImportResponse(
        profile_id=profile_id,
        imported=len(cookies),
        summary=netscape_cookie_audit_summary(document),
    )


@app.post("/api/profiles/{profile_id}/cookies/export", response_model=CookieExportResponse)
async def export_profile_cookies(profile_id: str, req: CookieExportRequest):
    if req.confirm_export is not True:
        raise HTTPException(status_code=422, detail="Cookie export requires explicit confirmation")

    running = _automation_running(profile_id)
    try:
        cookies = await running.context.cookies()
    except Exception:
        raise HTTPException(status_code=400, detail="Cookie export failed") from None

    exported_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        document = build_cookie_json_export(cookies, profile_id=profile_id, exported_at=exported_at)
    except Exception:
        raise HTTPException(status_code=400, detail="Cookie export failed") from None

    summary = cookie_json_audit_summary(document)
    db.create_audit_event(
        event_type="cookie.exported",
        actor_type="local_admin",
        profile_id=profile_id,
        metadata=_cookie_export_audit_metadata(summary),
    )
    return CookieExportResponse(
        profile_id=profile_id,
        exported=len(document.cookies),
        summary=summary,
        document=document.model_dump(mode="json", by_alias=True, exclude_none=True),
    )


@app.post("/api/profiles/{profile_id}/cookies/export/netscape", response_model=NetscapeCookieExportResponse)
async def export_profile_cookies_netscape(profile_id: str, req: CookieExportRequest):
    if req.confirm_export is not True:
        raise HTTPException(status_code=422, detail="Cookie export requires explicit confirmation")

    running = _automation_running(profile_id)
    try:
        cookies = await running.context.cookies()
    except Exception:
        raise HTTPException(status_code=400, detail="Cookie export failed") from None

    try:
        document = build_cookie_json_export(cookies, profile_id=profile_id)
        text = build_netscape_cookie_export(document)
    except Exception:
        raise HTTPException(status_code=400, detail="Cookie export failed") from None

    summary = netscape_cookie_audit_summary(document)
    db.create_audit_event(
        event_type="cookie.exported",
        actor_type="local_admin",
        profile_id=profile_id,
        metadata=_netscape_cookie_export_audit_metadata(summary),
    )
    return NetscapeCookieExportResponse(
        profile_id=profile_id,
        exported=len(document.cookies),
        summary=summary,
        text=text,
    )


@app.post("/api/profiles/{profile_id}/bundle/export", response_model=ProfileBundleExportResponse)
async def export_profile_bundle(profile_id: str, request: Request):
    try:
        req = ProfileBundleExportRequest.model_validate(await request.json())
    except Exception as exc:
        logger.warning("Profile bundle export validation failed for %s: %s", profile_id, type(exc).__name__)
        raise HTTPException(status_code=422, detail="Invalid profile bundle export request") from exc

    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if req.include_sensitive_proxy and req.confirm_sensitive_proxy_export is not True:
        raise HTTPException(
            status_code=422,
            detail="Profile bundle sensitive proxy export requires explicit confirmation",
        )

    cookie_document = None
    if req.include_cookies:
        if req.confirm_cookie_export is not True:
            raise HTTPException(
                status_code=422,
                detail="Profile bundle cookie export requires explicit confirmation",
            )
        running = _automation_running(profile_id)
        try:
            cookies = await running.context.cookies()
            cookie_document = build_cookie_json_export(
                cookies,
                profile_id=profile_id,
                exported_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Profile bundle cookie export failed",
            ) from None

    local_storage_origin = None
    local_storage_entries = None
    if req.include_local_storage:
        if req.confirm_local_storage_export is not True:
            raise HTTPException(
                status_code=422,
                detail="Profile bundle local storage export requires explicit confirmation",
            )
        _, page, _ = _automation_get_page(profile_id, req.local_storage_page_ref)
        local_storage_origin = _origin_from_page_url(getattr(page, "url", ""))
        if local_storage_origin is None:
            raise HTTPException(status_code=400, detail="Local storage origin unavailable")
        try:
            local_storage_entries = _normalize_local_storage_entries(
                await page.evaluate(
                    """() => Array.from({ length: window.localStorage.length }, (_, index) => {
                        const key = window.localStorage.key(index);
                        return { key, value: key === null ? "" : window.localStorage.getItem(key) ?? "" };
                    })"""
                )
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Profile bundle local storage export failed for %s: %s", profile_id, type(exc).__name__)
            raise HTTPException(status_code=400, detail="Profile bundle local storage export failed") from exc

    exported_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    bundle = build_profile_config_bundle(
        profile,
        exported_at=exported_at,
        include_sensitive_proxy=req.include_sensitive_proxy,
    )
    if cookie_document is not None:
        bundle = add_cookie_document_to_bundle(bundle, cookie_document)
        db.create_audit_event(
            event_type="profile_bundle.cookie_exported",
            actor_type="local_admin",
            profile_id=profile_id,
            metadata=_cookie_export_audit_metadata(cookie_json_audit_summary(cookie_document)),
        )
    if local_storage_origin is not None and local_storage_entries is not None:
        bundle = add_local_storage_entries_to_bundle(
            bundle,
            origin=local_storage_origin,
            entries=local_storage_entries,
        )
        db.create_audit_event(
            event_type="profile_bundle.local_storage_exported",
            actor_type="local_admin",
            profile_id=profile_id,
            metadata=local_storage_audit_metadata(local_storage_origin, local_storage_entries),
        )
    bundle_payload = bundle.model_dump(mode="json", by_alias=True)
    if bundle_payload.get("cookies", {}).get("document") is None:
        bundle_payload["cookies"].pop("document", None)
    if bundle_payload.get("local_storage", {}).get("entries") is None:
        bundle_payload["local_storage"].pop("entries", None)
    if bundle_payload.get("local_storage", {}).get("origin") is None:
        bundle_payload["local_storage"].pop("origin", None)
    if bundle_payload.get("local_storage", {}).get("format") is None:
        bundle_payload["local_storage"].pop("format", None)
    if bundle_payload.get("local_storage", {}).get("schema_version") is None:
        bundle_payload["local_storage"].pop("schema_version", None)
    if bundle_payload.get("local_storage", {}).get("entry_count") is None:
        bundle_payload["local_storage"].pop("entry_count", None)
    return ProfileBundleExportResponse(
        profile_id=profile_id,
        bundle=bundle_payload,
    )


@app.post("/api/profiles/bundle/import", response_model=ProfileConfigImportResponse)
async def import_profile_bundle(request: Request):
    payload = await _import_payload_with_confirmation(
        request,
        "Profile bundle import requires explicit confirmation",
    )
    try:
        req = ProfileBundleImportRequest.model_validate(payload)
    except Exception as exc:
        logger.warning("Profile bundle import validation failed: %s", type(exc).__name__)
        raise HTTPException(status_code=422, detail="Invalid profile bundle document") from exc

    config = req.bundle.profile.config.model_dump(mode="json", by_alias=True, exclude_none=True)
    data = _profile_config_import_data(config)
    errors = _profile_config_import_errors(data)
    try:
        profile_create = ProfileCreate(**data)
    except ValidationError as exc:
        errors.extend(_validation_error_messages(exc))

    if errors:
        return ProfileConfigImportResponse(
            total=1,
            imported=0,
            failed=1,
            results=[
                ProfileConfigImportResult(
                    index=0,
                    ok=False,
                    errors=errors,
                    profile=None,
                )
            ],
        )

    create_data = profile_create.model_dump()
    tags = create_data.pop("tags", None)
    create_data["tags"] = _tag_payloads(tags)

    try:
        profile = db.create_profile(**create_data)
    except Exception as exc:
        logger.warning("Profile bundle import create failed: %s", type(exc).__name__)
        return ProfileConfigImportResponse(
            total=1,
            imported=0,
            failed=1,
            results=[
                ProfileConfigImportResult(
                    index=0,
                    ok=False,
                    errors=["Failed to create profile"],
                    profile=None,
                )
            ],
        )

    status = browser_mgr.get_status(profile["id"])
    profile["status"] = status["status"]
    profile["vnc_ws_port"] = status["vnc_ws_port"]
    profile["automation_url"] = status["automation_url"]
    return ProfileConfigImportResponse(
        total=1,
        imported=1,
        failed=0,
        results=[
            ProfileConfigImportResult(
                index=0,
                ok=True,
                errors=[],
                profile=_profile_response(profile),
            )
        ],
    )


@app.post("/api/profiles/{profile_id}/proxy-asset", response_model=ProxyResponse, status_code=201)
async def save_profile_proxy_as_asset(profile_id: str, req: ProxyFromProfileCreate):
    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not profile.get("proxy"):
        raise HTTPException(status_code=400, detail="Profile has no proxy")

    data = req.model_dump()
    data["url"] = str(profile["proxy"])
    data["tags"] = _tag_payloads(data.get("tags"))
    try:
        proxy = db.create_proxy(**data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_safe_proxy_asset_error_detail(exc)) from exc
    return _proxy_response(proxy)


@app.get("/api/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str):
    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    status = browser_mgr.get_status(profile_id)
    profile["status"] = status["status"]
    profile["vnc_ws_port"] = status["vnc_ws_port"]
    profile["automation_url"] = status["automation_url"]
    return _profile_response(profile)


@app.put("/api/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: str, req: ProfileUpdate):
    # Only pass fields that were explicitly set
    data = req.model_dump(exclude_unset=True)
    audit_fields = sorted(data.keys())
    tags = data.pop("tags", None)
    if tags is not None:
        data["tags"] = [t.model_dump() if hasattr(t, "model_dump") else t for t in tags]
    profile = db.update_profile(profile_id, **data)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    status = browser_mgr.get_status(profile_id)
    profile["status"] = status["status"]
    profile["vnc_ws_port"] = status["vnc_ws_port"]
    profile["automation_url"] = status["automation_url"]
    _audit_profile_event("profile.updated", profile, updated_fields=audit_fields)
    return _profile_response(profile)


@app.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: str, request: Request):
    try:
        req = ProfileDeleteRequest.model_validate(await request.json())
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Profile delete requires explicit confirmation",
        ) from None

    if req.confirm_delete is not True:
        raise HTTPException(
            status_code=422,
            detail="Profile delete requires explicit confirmation",
        )

    # Stop browser if running
    if profile_id in browser_mgr.running:
        await browser_mgr.stop(profile_id)

    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    user_data_dir = Path(profile["user_data_dir"])

    # DB first — if this fails, filesystem is untouched
    db.delete_profile(profile_id)

    # Then clean up disk
    if user_data_dir.exists():
        shutil.rmtree(user_data_dir, ignore_errors=True)

    _audit_profile_event("profile.deleted", profile)
    return {"ok": True}


# ── Launch / Stop ─────────────────────────────────────────────────────────────


@app.post("/api/profiles/{profile_id}/launch", response_model=LaunchResponse)
async def launch_profile(profile_id: str, request: Request):
    try:
        req = ProfileLaunchRequest.model_validate(await request.json())
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Profile launch requires explicit confirmation",
        ) from None

    if req.confirm_launch is not True:
        raise HTTPException(
            status_code=422,
            detail="Profile launch requires explicit confirmation",
        )

    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile_id in browser_mgr.running:
        raise HTTPException(status_code=409, detail="Profile is already running")

    try:
        running = await browser_mgr.launch(profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_safe_proxy_asset_error_detail(exc)) from exc
    except BrowserResourceLimitError as exc:
        raise HTTPException(status_code=409, detail=_RESOURCE_LIMIT_ERROR_DETAIL) from exc
    except Exception as exc:
        logger.error(
            "Failed to launch profile %s error_type=%s",
            profile_id,
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="Failed to launch browser") from exc

    db.update_profile_geoip_result(profile_id, getattr(running, "resolved_geoip", None))

    return LaunchResponse(
        profile_id=profile_id,
        status="running",
        vnc_ws_port=running.ws_port,
        display=f":{running.display}",
        automation_url=f"/api/profiles/{profile_id}/automation",
    )


@app.post("/api/profiles/{profile_id}/stop")
async def stop_profile(profile_id: str, request: Request):
    try:
        req = ProfileStopRequest.model_validate(await request.json())
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Profile stop requires explicit confirmation",
        ) from None

    if req.confirm_stop is not True:
        raise HTTPException(
            status_code=422,
            detail="Profile stop requires explicit confirmation",
        )

    if profile_id not in browser_mgr.running:
        raise HTTPException(status_code=404, detail="Profile is not running")
    await browser_mgr.stop(profile_id)
    return {"ok": True}


@app.get("/api/profiles/{profile_id}/status", response_model=ProfileStatusResponse)
async def get_profile_status(profile_id: str):
    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    status = browser_mgr.get_status(profile_id)
    return ProfileStatusResponse(**status)


# ── Health ──────────────────────────────────────────────────────────────────


@app.get("/api/profiles/{profile_id}/health", response_model=ProfileHealthResponse)
async def get_profile_health(profile_id: str):
    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return compute_profile_health(profile, browser_mgr.get_status(profile_id))


@app.post("/api/profiles/{profile_id}/health/check", response_model=ProfileHealthResponse)
async def check_profile_health(profile_id: str):
    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    runtime_status = browser_mgr.get_status(profile_id)
    try:
        proxy_url = validate_profile_proxy(profile)
    except ValueError as exc:
        health = compute_profile_health(
            profile,
            runtime_status,
            proxy_error=str(exc),
        )
        _audit_health_check(
            profile_id,
            health,
            lookup_attempted=False,
            lookup_result="skipped_invalid_proxy",
        )
        return health

    try:
        geo = await resolve_network_geo(proxy_url)
    except Exception as exc:
        logger.warning(
            "action=profile.health_geoip_lookup_failed profile_id=%s error_type=%s",
            profile_id,
            type(exc).__name__,
        )
        health = compute_profile_health(
            profile,
            runtime_status,
            geoip_lookup_failed=True,
        )
        _audit_health_check(
            profile_id,
            health,
            lookup_attempted=True,
            lookup_result="failed",
        )
        return health

    if any((geo.timezone, geo.locale, geo.ip, geo.country_code)):
        profile = db.update_profile_geoip_result(profile_id, geo.as_dict()) or profile
        health = compute_profile_health(profile, runtime_status)
        _audit_health_check(
            profile_id,
            health,
            lookup_attempted=True,
            lookup_result="success",
        )
        return health

    health = compute_profile_health(
        profile,
        runtime_status,
        geoip_lookup_failed=True,
    )
    _audit_health_check(
        profile_id,
        health,
        lookup_attempted=True,
        lookup_result="empty",
    )
    return health


# ── System Status ─────────────────────────────────────────────────────────────


@app.get("/api/status", response_model=StatusResponse)
async def get_system_status():
    task_counts = db.count_automation_tasks_by_status()

    return StatusResponse(
        running_count=len(browser_mgr.running),
        launching_count=browser_mgr.launching_count,
        failed_count=task_counts.get("failed", 0),
        binary_version="invisible-playwright",
        profiles_total=db.count_profiles(),
        proxy_count=db.count_proxies(),
        task_queue_count=task_counts.get("queued", 0),
        automation_task_counts=task_counts,
    )


@app.get("/api/diagnostics", response_model=DiagnosticsResponse)
async def get_system_diagnostics():
    task_counts = db.count_automation_tasks_by_status()
    running_profiles = list(browser_mgr.running.values())
    firefox_identity = managed_firefox_identity_summary()
    launch_failure_summary = browser_mgr.launch_failure_summary()

    return DiagnosticsResponse(
        status="ok",
        binary_version="invisible-playwright",
        storage=DiagnosticsStorageResponse(
            data_dir_exists=db.DATA_DIR.exists(),
            db_exists=db.DB_PATH.exists(),
        ),
        counts=DiagnosticsCountsResponse(
            running=len(running_profiles),
            launching=browser_mgr.launching_count,
            profiles_total=db.count_profiles(),
            proxy_count=db.count_proxies(),
            queued_tasks=task_counts.get("queued", 0),
            failed_tasks=task_counts.get("failed", 0),
            automation_task_counts=task_counts,
        ),
        runtime=DiagnosticsRuntimeResponse(
            active_displays=sorted(running.display for running in running_profiles),
            active_vnc_ws_ports=sorted(running.ws_port for running in running_profiles),
            max_running_profiles=get_max_running_profiles_limit(),
            launch_failure_count=launch_failure_summary["launch_failure_count"],
            launch_failure_stage_counts=launch_failure_summary["launch_failure_stage_counts"],
            managed_user_agent_version=firefox_identity["managed_user_agent_version"],
            invisible_playwright_version=firefox_identity["invisible_playwright_version"],
            firefox_binary_version=firefox_identity["firefox_binary_version"],
            firefox_binary_build_id=firefox_identity["firefox_binary_build_id"],
            stealth_pref_count=firefox_identity["stealth_pref_count"],
            stealth_pref_categories=firefox_identity["stealth_pref_categories"],
        ),
        runtime_sessions=DiagnosticsRuntimeSessionsResponse(
            status_counts=db.count_runtime_sessions_by_status(),
            live_count=db.count_live_runtime_sessions(),
            active_viewer_token_count=db.count_active_runtime_viewer_tokens(),
        ),
        automation_worker=_automation_worker_diagnostics(),
    )


# ── Automation Tasks ─────────────────────────────────────────────────────────


def _automation_task_redacted_steps(steps: list[dict]) -> list[dict]:
    redacted_steps = []
    for step in steps:
        step_type = _automation_task_public_step_type(step.get("type"))
        redacted = {"type": step_type}
        if step_type == "wait" and isinstance(step.get("ms"), int) and not isinstance(step.get("ms"), bool):
            redacted["ms"] = step["ms"]
        if step_type == "open_url":
            page_ref = _automation_task_public_page_ref(step)
            if page_ref is not None:
                redacted["page_ref"] = page_ref
            if step.get("wait_until") in {"commit", "domcontentloaded", "load", "networkidle"}:
                redacted["wait_until"] = step["wait_until"]
            if (
                isinstance(step.get("timeout_ms"), int)
                and not isinstance(step.get("timeout_ms"), bool)
                and 1 <= step["timeout_ms"] <= 300_000
            ):
                redacted["timeout_ms"] = step["timeout_ms"]
        if step_type == "wait_for_selector":
            page_ref = _automation_task_public_page_ref(step)
            if page_ref is not None:
                redacted["page_ref"] = page_ref
            if step.get("state") in {"attached", "detached", "visible", "hidden"}:
                redacted["state"] = step["state"]
            if (
                isinstance(step.get("timeout_ms"), int)
                and not isinstance(step.get("timeout_ms"), bool)
                and 1 <= step["timeout_ms"] <= 300_000
            ):
                redacted["timeout_ms"] = step["timeout_ms"]
        if step_type == "evaluate":
            page_ref = _automation_task_public_page_ref(step)
            if page_ref is not None:
                redacted["page_ref"] = page_ref
        if step_type == "screenshot":
            page_ref = _automation_task_public_page_ref(step)
            if page_ref is not None:
                redacted["page_ref"] = page_ref
            if "full_page" in step and isinstance(step.get("full_page"), bool):
                redacted["full_page"] = step["full_page"]
        if step_type == "click":
            page_ref = _automation_task_public_page_ref(step)
            if page_ref is not None:
                redacted["page_ref"] = page_ref
            if (
                isinstance(step.get("timeout_ms"), int)
                and not isinstance(step.get("timeout_ms"), bool)
                and 1 <= step["timeout_ms"] <= 300_000
            ):
                redacted["timeout_ms"] = step["timeout_ms"]
        if step_type == "fill":
            page_ref = _automation_task_public_page_ref(step)
            if page_ref is not None:
                redacted["page_ref"] = page_ref
            if (
                isinstance(step.get("timeout_ms"), int)
                and not isinstance(step.get("timeout_ms"), bool)
                and 1 <= step["timeout_ms"] <= 300_000
            ):
                redacted["timeout_ms"] = step["timeout_ms"]
        if step_type == "keyboard_type":
            page_ref = _automation_task_public_page_ref(step)
            if page_ref is not None:
                redacted["page_ref"] = page_ref
            if (
                isinstance(step.get("delay_ms"), int)
                and not isinstance(step.get("delay_ms"), bool)
                and 0 <= step["delay_ms"] <= 10_000
            ):
                redacted["delay_ms"] = step["delay_ms"]
        if step_type == "scroll":
            page_ref = _automation_task_public_page_ref(step)
            if page_ref is not None:
                redacted["page_ref"] = page_ref
            if (
                isinstance(step.get("delta_x"), int)
                and not isinstance(step.get("delta_x"), bool)
                and -100_000 <= step["delta_x"] <= 100_000
            ):
                redacted["delta_x"] = step["delta_x"]
            if (
                isinstance(step.get("delta_y"), int)
                and not isinstance(step.get("delta_y"), bool)
                and -100_000 <= step["delta_y"] <= 100_000
            ):
                redacted["delta_y"] = step["delta_y"]
        redacted_steps.append(redacted)
    return redacted_steps


_AUTOMATION_STEP_TYPES = {
    "click",
    "evaluate",
    "fill",
    "keyboard_type",
    "open_url",
    "screenshot",
    "scroll",
    "wait",
    "wait_for_selector",
}
_AUTOMATION_RESULT_STATUSES = {"cancelled", "failed", "succeeded"}
_AUTOMATION_TASK_STATUSES = {
    "cancel_requested",
    "cancelled",
    "failed",
    "queued",
    "running",
    "succeeded",
}
_AUTOMATION_UNKNOWN_STEP_TYPE = "unknown"
_AUTOMATION_UNKNOWN_RESULT_STATUS = "unknown"
_AUTOMATION_UNKNOWN_TASK_STATUS = "unknown"
_AUTOMATION_UNKNOWN_TASK_ERROR = "Automation task failed"
_AUTOMATION_TASK_PUBLIC_ERRORS = {
    "Automation step failed",
    "Click step failed",
    "Evaluate step failed",
    "Fill step failed",
    "Invalid click step",
    "Invalid evaluate step",
    "Invalid fill step",
    "Invalid keyboard_type step",
    "Invalid open_url step",
    "Invalid screenshot step",
    "Invalid scroll step",
    "Invalid wait step",
    "Invalid wait_for_selector step",
    "Keyboard type step failed",
    "Open URL step failed",
    "Profile not found",
    "Profile not running",
    "Screenshot step failed",
    "Scroll step failed",
    "Unsupported automation step type",
    "Wait for selector step failed",
}


def _automation_task_public_step_type(value: object) -> str:
    if not isinstance(value, str):
        return _AUTOMATION_UNKNOWN_STEP_TYPE
    return value if value in _AUTOMATION_STEP_TYPES else _AUTOMATION_UNKNOWN_STEP_TYPE


def _automation_task_public_result_status(value: object) -> str:
    if not isinstance(value, str):
        return _AUTOMATION_UNKNOWN_RESULT_STATUS
    return value if value in _AUTOMATION_RESULT_STATUSES else _AUTOMATION_UNKNOWN_RESULT_STATUS


def _automation_task_public_status(value: object) -> str:
    if not isinstance(value, str):
        return _AUTOMATION_UNKNOWN_TASK_STATUS
    return value if value in _AUTOMATION_TASK_STATUSES else _AUTOMATION_UNKNOWN_TASK_STATUS


def _automation_task_public_error(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return _AUTOMATION_UNKNOWN_TASK_ERROR
    return value if value in _AUTOMATION_TASK_PUBLIC_ERRORS else _AUTOMATION_UNKNOWN_TASK_ERROR


def _automation_task_public_result_index(value: object) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if value < 0 or value > 1_000_000:
        return None
    return value


def _automation_task_safe_page_ref(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    page_ref = value.strip()
    if not page_ref:
        return None
    if page_ref.isascii() and page_ref.isdecimal():
        return page_ref
    try:
        parsed = uuid.UUID(page_ref)
    except ValueError:
        return None
    if str(parsed) == page_ref.lower():
        return str(parsed)
    return None


def _automation_task_public_page_ref(step: dict) -> str | None:
    if "page_ref" not in step:
        return None
    return _automation_task_safe_page_ref(step.get("page_ref")) or _AUTOMATION_INVALID_PAGE_REF


def _automation_task_persisted_steps(steps: list[dict]) -> list[dict]:
    persisted_steps = []
    allowed_keys_by_type = {
        "click": {"type", "selector", "page_ref", "timeout_ms"},
        "evaluate": {"type", "expression", "page_ref"},
        "fill": {"type", "selector", "value", "page_ref", "timeout_ms"},
        "keyboard_type": {"type", "text", "page_ref", "delay_ms"},
        "open_url": {"type", "url", "page_ref", "wait_until", "timeout_ms"},
        "screenshot": {"type", "page_ref", "full_page"},
        "scroll": {"type", "page_ref", "delta_x", "delta_y"},
        "wait": {"type", "ms"},
        "wait_for_selector": {"type", "selector", "page_ref", "state", "timeout_ms"},
    }
    for step in steps:
        step_type = _automation_task_public_step_type(step.get("type"))
        allowed_keys = allowed_keys_by_type.get(step_type, {"type"})
        persisted_step = {key: value for key, value in step.items() if key in allowed_keys}
        persisted_step["type"] = step_type
        page_ref = _automation_task_public_page_ref(step)
        if page_ref is not None and "page_ref" in allowed_keys:
            persisted_step["page_ref"] = page_ref
        persisted_steps.append(persisted_step)
    return persisted_steps


def _automation_task_redacted_result(result: dict | None) -> dict | None:
    if not isinstance(result, dict):
        return None
    steps = result.get("steps")
    if not isinstance(steps, list):
        return None
    redacted_steps = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        redacted_step = {
            "index": _automation_task_public_result_index(step.get("index")),
            "type": _automation_task_public_step_type(step.get("type")),
            "status": _automation_task_public_result_status(step.get("status")),
        }
        redacted_steps.append(redacted_step)
    return {"steps": redacted_steps}


def _automation_task_response(task: dict) -> AutomationTaskResponse:
    task = {
        **task,
        "status": _automation_task_public_status(task.get("status")),
        "error": _automation_task_public_error(task.get("error")),
        "steps": _automation_task_redacted_steps(task.get("steps") or []),
        "result": _automation_task_redacted_result(task.get("result")),
    }
    return AutomationTaskResponse(**task)


def _automation_task_finished_response(
    task: dict,
    status_code: int = 200,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(_automation_task_response(task)),
    )


def _automation_task_step_types(task: dict) -> list[str]:
    steps = task.get("steps") or []
    return [_automation_task_public_step_type(step.get("type")) for step in steps if isinstance(step, dict)]


def _automation_task_result_counts(task: dict) -> dict[str, int]:
    counts = {
        "succeeded_step_count": 0,
        "failed_step_count": 0,
        "cancelled_step_count": 0,
    }
    result = task.get("result")
    steps = result.get("steps") if isinstance(result, dict) else None
    if not isinstance(steps, list):
        return counts
    for step in steps:
        if not isinstance(step, dict):
            continue
        status = step.get("status")
        if status == "succeeded":
            counts["succeeded_step_count"] += 1
        elif status == "failed":
            counts["failed_step_count"] += 1
        elif status == "cancelled":
            counts["cancelled_step_count"] += 1
    return counts


def _automation_task_failure_reason_code(task: dict) -> str:
    error = task.get("error")
    reason_by_error = {
        "Unsupported automation step type": "unsupported_step_type",
        "Invalid click step": "invalid_step",
        "Invalid evaluate step": "invalid_step",
        "Invalid fill step": "invalid_step",
        "Invalid keyboard_type step": "invalid_step",
        "Invalid open_url step": "invalid_step",
        "Invalid screenshot step": "invalid_step",
        "Invalid scroll step": "invalid_step",
        "Invalid wait step": "invalid_step",
        "Invalid wait_for_selector step": "invalid_step",
        "Automation step failed": "automation_step_failed",
        "Click step failed": "automation_step_failed",
        "Evaluate step failed": "automation_step_failed",
        "Fill step failed": "automation_step_failed",
        "Keyboard type step failed": "automation_step_failed",
        "Open URL step failed": "automation_step_failed",
        "Screenshot step failed": "automation_step_failed",
        "Scroll step failed": "automation_step_failed",
        "Wait for selector step failed": "automation_step_failed",
    }
    return reason_by_error.get(str(error), "automation_step_failed")


def _automation_task_audit_metadata(
    task: dict,
    *,
    previous_status: str | None = None,
    runner_type: str | None = None,
    source_task_id: str | None = None,
    new_task_id: str | None = None,
    reason_code: str | None = None,
) -> dict:
    metadata = {
        "task_id": task.get("id"),
        "status": _automation_task_public_status(task.get("status")),
        "step_count": len(task.get("steps") or []),
        "step_types": _automation_task_step_types(task),
    }
    if previous_status is not None:
        metadata["previous_status"] = _automation_task_public_status(previous_status)
    if runner_type is not None:
        metadata["runner_type"] = runner_type
        metadata.update(_automation_task_result_counts(task))
    if source_task_id is not None:
        metadata["source_task_id"] = source_task_id
    if new_task_id is not None:
        metadata["new_task_id"] = new_task_id
    if reason_code is not None:
        metadata["reason_code"] = reason_code
    return {key: value for key, value in metadata.items() if value is not None}


def _audit_automation_task_event(
    event_type: str,
    task: dict,
    *,
    previous_status: str | None = None,
    runner_type: str | None = None,
    source_task_id: str | None = None,
    new_task_id: str | None = None,
    reason_code: str | None = None,
) -> None:
    db.create_audit_event(
        event_type=event_type,
        actor_type="local_admin",
        profile_id=str(task["profile_id"]),
        metadata=_automation_task_audit_metadata(
            task,
            previous_status=previous_status,
            runner_type=runner_type,
            source_task_id=source_task_id,
            new_task_id=new_task_id,
            reason_code=reason_code,
        ),
    )


def _audit_automation_task_terminal_event(task: dict, *, runner_type: str) -> None:
    status = task.get("status")
    if status == "succeeded":
        _audit_automation_task_event("automation.task.succeeded", task, runner_type=runner_type)
    elif status == "failed":
        _audit_automation_task_event(
            "automation.task.failed",
            task,
            runner_type=runner_type,
            reason_code=_automation_task_failure_reason_code(task),
        )
    elif status == "cancelled":
        _audit_automation_task_event("automation.task.cancelled_by_runner", task, runner_type=runner_type)


def _automation_task_step_result(index: int, step: dict, status: str) -> dict:
    return {
        "index": index,
        "type": _automation_task_public_step_type(step.get("type")),
        "status": _automation_task_public_result_status(status),
    }


def _fail_automation_worker_http_step(
    task_id: str,
    lease_owner: str,
    step_results: list[dict],
    index: int,
    step: dict,
) -> dict:
    step_results.append(_automation_task_step_result(index, step, "failed"))
    return _fail_automation_task(
        task_id,
        step_results,
        "Automation step failed",
        lease_owner=lease_owner,
    )


def _cancel_automation_task(task_id: str, step_results: list[dict]) -> dict:
    cancelled = db.update_automation_task(
        task_id,
        status="cancelled",
        result={"steps": step_results},
        finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
    if cancelled is None:
        raise HTTPException(status_code=404, detail="Automation task not found")
    return cancelled


def _finish_cancel_requested_automation_task(
    task_id: str,
    step_results: list[dict],
    index: int | None = None,
    step: dict | None = None,
    *,
    lease_owner: str | None = None,
) -> dict | None:
    latest = db.get_automation_task(task_id)
    if latest is None:
        raise HTTPException(status_code=404, detail="Automation task not found")
    if latest.get("status") != "cancel_requested":
        return None
    final_step_results = list(step_results)
    if index is not None and step is not None:
        final_step_results.append(_automation_task_step_result(index, step, "cancelled"))
    if lease_owner is not None:
        cancelled = db.finish_claimed_automation_task(
            task_id,
            lease_owner=lease_owner,
            status="cancelled",
            result={"steps": final_step_results},
            error=None,
            allowed_statuses={"running", "cancel_requested"},
        )
        if cancelled is None:
            raise HTTPException(status_code=409, detail=_AUTOMATION_WORKER_LOST_LEASE_DETAIL)
        return cancelled
    return _cancel_automation_task(task_id, final_step_results)


def _fail_automation_task(
    task_id: str,
    step_results: list[dict],
    error: str,
    *,
    lease_owner: str | None = None,
) -> dict:
    if lease_owner is not None:
        failed = db.finish_claimed_automation_task(
            task_id,
            lease_owner=lease_owner,
            status="failed",
            result={"steps": step_results},
            error=error,
        )
        if failed is None:
            raise HTTPException(status_code=409, detail=_AUTOMATION_WORKER_LOST_LEASE_DETAIL)
        return failed
    failed = db.update_automation_task(
        task_id,
        status="failed",
        result={"steps": step_results},
        error=error,
        finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
    if failed is None:
        raise HTTPException(status_code=404, detail="Automation task not found")
    return failed


def _succeed_automation_task(
    task_id: str,
    step_results: list[dict],
    *,
    lease_owner: str | None = None,
) -> dict:
    if lease_owner is not None:
        finished = db.finish_claimed_automation_task(
            task_id,
            lease_owner=lease_owner,
            status="succeeded",
            result={"steps": step_results},
            error=None,
        )
        if finished is None:
            raise HTTPException(status_code=409, detail=_AUTOMATION_WORKER_LOST_LEASE_DETAIL)
        return finished
    finished = db.update_automation_task(
        task_id,
        status="succeeded",
        result={"steps": step_results},
        finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
    if finished is None:
        raise HTTPException(status_code=404, detail="Automation task not found")
    return finished


def _renew_automation_worker_lease(
    task_id: str,
    *,
    lease_owner: str | None,
    lease_seconds: int | None,
) -> None:
    if lease_owner is None or lease_seconds is None:
        return
    renewed = db.renew_automation_task_lease(
        task_id,
        lease_owner=lease_owner,
        lease_seconds=lease_seconds,
        allowed_statuses={"running", "cancel_requested"},
    )
    if renewed is None:
        raise HTTPException(status_code=409, detail=_AUTOMATION_WORKER_LOST_LEASE_DETAIL)


def _automation_worker_lease_heartbeat_interval(lease_seconds: int) -> float:
    return max(0.1, min(float(lease_seconds) / 2, 30.0))


async def _run_automation_worker_lease_heartbeat(
    task_id: str,
    *,
    lease_owner: str,
    lease_seconds: int,
    stop_event: asyncio.Event,
) -> None:
    interval = _automation_worker_lease_heartbeat_interval(lease_seconds)
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            _renew_automation_worker_lease(task_id, lease_owner=lease_owner, lease_seconds=lease_seconds)


def _automation_step_str(step: dict, key: str, default: str | None = None) -> str | None:
    value = step.get(key, default)
    return value if isinstance(value, str) else default


def _automation_step_int(step: dict, key: str, default: int) -> int:
    value = step.get(key, default)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return default


def _is_supported_automation_url(raw_url: str) -> bool:
    parsed = urlparse(raw_url)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)


def _automation_profile_has_running_task(profile_id: str, task_id: str) -> bool:
    return any(
        existing_task.get("id") != task_id and existing_task.get("status") in {"running", "cancel_requested"}
        for existing_task in db.list_automation_tasks(profile_id=profile_id)
    )


@app.post("/api/tasks", response_model=AutomationTaskResponse, status_code=201)
async def create_automation_task(req: AutomationTaskCreate):
    if db.get_profile(req.profile_id) is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    task = db.create_automation_task(
        profile_id=req.profile_id,
        steps=_automation_task_persisted_steps(req.steps),
    )
    _audit_automation_task_event("automation.task.created", task)
    return _automation_task_response(task)


@app.get("/api/tasks", response_model=AutomationTasksResponse)
async def list_automation_tasks(
    profile_id: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    if profile_id is not None and db.get_profile(profile_id) is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    tasks = db.list_automation_tasks(profile_id=profile_id, limit=limit, offset=offset)
    return AutomationTasksResponse(tasks=[_automation_task_response(task) for task in tasks])


@app.get("/api/tasks/{task_id}", response_model=AutomationTaskResponse)
async def get_automation_task(task_id: str):
    task = db.get_automation_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Automation task not found")
    return _automation_task_response(task)


@app.post("/api/tasks/{task_id}/cancel", response_model=AutomationTaskResponse)
async def cancel_automation_task(task_id: str, request: Request):
    try:
        req = AutomationTaskCancelRequest.model_validate(await request.json())
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Automation task cancel requires explicit confirmation",
        ) from None

    task = db.get_automation_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Automation task not found")
    if req.confirm_cancel is not True:
        raise HTTPException(
            status_code=422,
            detail="Automation task cancel requires explicit confirmation",
        )
    if task["status"] == "cancel_requested":
        return _automation_task_response(task)
    if task["status"] not in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="Only queued or running automation tasks can be cancelled")
    next_status = "cancelled" if task["status"] == "queued" else "cancel_requested"
    cancelled = db.update_automation_task(
        task_id,
        status=next_status,
        finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat() if next_status == "cancelled" else None,
    )
    if cancelled is None:
        raise HTTPException(status_code=404, detail="Automation task not found")
    event_type = "automation.task.cancelled" if next_status == "cancelled" else "automation.task.cancel_requested"
    _audit_automation_task_event(event_type, cancelled, previous_status=task["status"])
    return _automation_task_response(cancelled)


@app.post("/api/tasks/{task_id}/retry", response_model=AutomationTaskResponse, status_code=201)
async def retry_automation_task(task_id: str):
    task = db.get_automation_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Automation task not found")
    if task["status"] not in {"cancelled", "failed", "succeeded"}:
        raise HTTPException(status_code=409, detail="Only finished automation tasks can be retried")
    if db.get_profile(task["profile_id"]) is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    retry_task = db.create_automation_task(
        profile_id=task["profile_id"],
        steps=_automation_task_persisted_steps(task.get("steps") or []),
    )
    _audit_automation_task_event(
        "automation.task.retried",
        retry_task,
        source_task_id=task["id"],
        new_task_id=retry_task["id"],
    )
    return _automation_task_response(retry_task)


async def _execute_running_automation_task(
    running_task: dict,
    *,
    lease_owner: str | None = None,
) -> tuple[dict, int]:
    task_id = running_task["id"]
    step_results: list[dict] = []
    for index, step in enumerate(running_task["steps"]):
        cancelled = _finish_cancel_requested_automation_task(
            task_id,
            step_results,
            index,
            step,
            lease_owner=lease_owner,
        )
        if cancelled is not None:
            return cancelled, 200

        step_type = step.get("type")
        if step_type != "wait":
            if step_type not in {
                "click",
                "evaluate",
                "fill",
                "keyboard_type",
                "open_url",
                "screenshot",
                "scroll",
                "wait_for_selector",
            }:
                step_results.append(_automation_task_step_result(index, step, "failed"))
                failed = _fail_automation_task(
                    task_id,
                    step_results,
                    "Unsupported automation step type",
                    lease_owner=lease_owner,
                )
                return failed, 400

            if step_type == "wait_for_selector":
                selector = _automation_step_str(step, "selector")
                state = _automation_step_str(step, "state", "visible")
                raw_timeout_ms = step.get("timeout_ms", 30_000)
                page_ref = _automation_step_str(step, "page_ref", "0") or "0"
                if (
                    selector is None
                    or not selector
                    or len(selector) > 10_000
                    or state not in {"attached", "detached", "visible", "hidden"}
                    or not isinstance(raw_timeout_ms, int)
                    or isinstance(raw_timeout_ms, bool)
                    or raw_timeout_ms < 1
                    or raw_timeout_ms > 300_000
                ):
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Invalid wait_for_selector step",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                try:
                    _, page, _ = _automation_get_page(running_task["profile_id"], page_ref)
                    await page.wait_for_selector(selector, state=state, timeout=raw_timeout_ms)
                except HTTPException:
                    if lease_owner is not None:
                        failed = _fail_automation_worker_http_step(task_id, lease_owner, step_results, index, step)
                        return failed, 400
                    raise
                except Exception:
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Wait for selector step failed",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                step_results.append(_automation_task_step_result(index, step, "succeeded"))
                continue

            if step_type == "evaluate":
                expression = _automation_step_str(step, "expression")
                page_ref = _automation_step_str(step, "page_ref", "0") or "0"
                if expression is None or not expression or len(expression) > 200_000:
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Invalid evaluate step",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                try:
                    _, page, _ = _automation_get_page(running_task["profile_id"], page_ref)
                    await page.evaluate(expression)
                except HTTPException:
                    if lease_owner is not None:
                        failed = _fail_automation_worker_http_step(task_id, lease_owner, step_results, index, step)
                        return failed, 400
                    raise
                except Exception:
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Evaluate step failed",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                step_results.append(_automation_task_step_result(index, step, "succeeded"))
                continue

            if step_type == "screenshot":
                raw_full_page = step.get("full_page", False)
                page_ref = _automation_step_str(step, "page_ref", "0") or "0"
                if not isinstance(raw_full_page, bool):
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Invalid screenshot step",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                try:
                    _, page, _ = _automation_get_page(running_task["profile_id"], page_ref)
                    await page.screenshot(type="png", full_page=raw_full_page)
                except HTTPException:
                    if lease_owner is not None:
                        failed = _fail_automation_worker_http_step(task_id, lease_owner, step_results, index, step)
                        return failed, 400
                    raise
                except Exception:
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Screenshot step failed",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                step_results.append(_automation_task_step_result(index, step, "succeeded"))
                continue

            if step_type == "click":
                selector = _automation_step_str(step, "selector")
                raw_timeout_ms = step.get("timeout_ms", 30_000)
                page_ref = _automation_step_str(step, "page_ref", "0") or "0"
                if (
                    selector is None
                    or not selector
                    or len(selector) > 10_000
                    or not isinstance(raw_timeout_ms, int)
                    or isinstance(raw_timeout_ms, bool)
                    or raw_timeout_ms < 1
                    or raw_timeout_ms > 300_000
                ):
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Invalid click step",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                try:
                    _, page, _ = _automation_get_page(running_task["profile_id"], page_ref)
                    await page.click(selector, timeout=raw_timeout_ms)
                except HTTPException:
                    if lease_owner is not None:
                        failed = _fail_automation_worker_http_step(task_id, lease_owner, step_results, index, step)
                        return failed, 400
                    raise
                except Exception:
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Click step failed",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                step_results.append(_automation_task_step_result(index, step, "succeeded"))
                continue

            if step_type == "fill":
                selector = _automation_step_str(step, "selector")
                value = _automation_step_str(step, "value")
                raw_timeout_ms = step.get("timeout_ms", 30_000)
                page_ref = _automation_step_str(step, "page_ref", "0") or "0"
                if (
                    selector is None
                    or not selector
                    or len(selector) > 10_000
                    or value is None
                    or len(value) > 1_048_576
                    or not isinstance(raw_timeout_ms, int)
                    or isinstance(raw_timeout_ms, bool)
                    or raw_timeout_ms < 1
                    or raw_timeout_ms > 300_000
                ):
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Invalid fill step",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                try:
                    _, page, _ = _automation_get_page(running_task["profile_id"], page_ref)
                    await page.fill(selector, value, timeout=raw_timeout_ms)
                except HTTPException:
                    if lease_owner is not None:
                        failed = _fail_automation_worker_http_step(task_id, lease_owner, step_results, index, step)
                        return failed, 400
                    raise
                except Exception:
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Fill step failed",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                step_results.append(_automation_task_step_result(index, step, "succeeded"))
                continue

            if step_type == "keyboard_type":
                text = _automation_step_str(step, "text")
                raw_delay_ms = step.get("delay_ms", 0)
                page_ref = _automation_step_str(step, "page_ref", "0") or "0"
                if (
                    text is None
                    or not text
                    or len(text) > 1_048_576
                    or not isinstance(raw_delay_ms, int)
                    or isinstance(raw_delay_ms, bool)
                    or raw_delay_ms < 0
                    or raw_delay_ms > 10_000
                ):
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Invalid keyboard_type step",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                try:
                    _, page, _ = _automation_get_page(running_task["profile_id"], page_ref)
                    await page.keyboard.type(text, delay=raw_delay_ms)
                except HTTPException:
                    if lease_owner is not None:
                        failed = _fail_automation_worker_http_step(task_id, lease_owner, step_results, index, step)
                        return failed, 400
                    raise
                except Exception:
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Keyboard type step failed",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                step_results.append(_automation_task_step_result(index, step, "succeeded"))
                continue

            if step_type == "scroll":
                delta_x = _automation_step_int(step, "delta_x", 0)
                delta_y = _automation_step_int(step, "delta_y", 0)
                page_ref = _automation_step_str(step, "page_ref", "0") or "0"
                if delta_x < -100_000 or delta_x > 100_000 or delta_y < -100_000 or delta_y > 100_000:
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Invalid scroll step",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                try:
                    _, page, _ = _automation_get_page(running_task["profile_id"], page_ref)
                    await page.evaluate(
                        "([deltaX, deltaY]) => window.scrollBy(deltaX, deltaY)",
                        [delta_x, delta_y],
                    )
                except HTTPException:
                    if lease_owner is not None:
                        failed = _fail_automation_worker_http_step(task_id, lease_owner, step_results, index, step)
                        return failed, 400
                    raise
                except Exception:
                    step_results.append(_automation_task_step_result(index, step, "failed"))
                    failed = _fail_automation_task(
                        task_id,
                        step_results,
                        "Scroll step failed",
                        lease_owner=lease_owner,
                    )
                    return failed, 400
                step_results.append(_automation_task_step_result(index, step, "succeeded"))
                continue

            url = _automation_step_str(step, "url")
            wait_until = _automation_step_str(step, "wait_until", "load")
            timeout_ms = _automation_step_int(step, "timeout_ms", 30_000)
            page_ref = _automation_step_str(step, "page_ref", "0") or "0"
            if (
                url is None
                or wait_until not in {"commit", "domcontentloaded", "load", "networkidle"}
                or timeout_ms < 1
                or timeout_ms > 300_000
                or not _is_supported_automation_url(url)
            ):
                step_results.append(_automation_task_step_result(index, step, "failed"))
                failed = _fail_automation_task(
                    task_id,
                    step_results,
                    "Invalid open_url step",
                    lease_owner=lease_owner,
                )
                return failed, 400

            try:
                running, page, _ = _automation_get_page(running_task["profile_id"], page_ref)
                await _automation_apply_page_headers(running, page)
                await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            except HTTPException:
                if lease_owner is not None:
                    failed = _fail_automation_worker_http_step(task_id, lease_owner, step_results, index, step)
                    return failed, 400
                raise
            except Exception:
                step_results.append(_automation_task_step_result(index, step, "failed"))
                failed = _fail_automation_task(
                    task_id,
                    step_results,
                    "Open URL step failed",
                    lease_owner=lease_owner,
                )
                return failed, 400

            step_results.append(_automation_task_step_result(index, step, "succeeded"))
            continue

        wait_ms = step.get("ms")
        if not isinstance(wait_ms, int) or isinstance(wait_ms, bool) or wait_ms < 1 or wait_ms > 300_000:
            step_results.append(_automation_task_step_result(index, step, "failed"))
            failed = _fail_automation_task(
                task_id,
                step_results,
                "Invalid wait step",
                lease_owner=lease_owner,
            )
            return failed, 400

        await asyncio.sleep(wait_ms / 1000)
        step_results.append(_automation_task_step_result(index, step, "succeeded"))
        next_index = index + 1
        if next_index < len(running_task["steps"]):
            cancelled = _finish_cancel_requested_automation_task(
                task_id,
                step_results,
                next_index,
                running_task["steps"][next_index],
                lease_owner=lease_owner,
            )
        else:
            cancelled = _finish_cancel_requested_automation_task(
                task_id,
                step_results,
                lease_owner=lease_owner,
            )
        if cancelled is not None:
            return cancelled, 200

    cancelled = _finish_cancel_requested_automation_task(
        task_id,
        step_results,
        lease_owner=lease_owner,
    )
    if cancelled is not None:
        return cancelled, 200

    finished = _succeed_automation_task(task_id, step_results, lease_owner=lease_owner)
    return finished, 200


async def run_automation_worker_once(
    *,
    lease_owner: str,
    lease_seconds: int = 60,
) -> dict | None:
    claimed = db.claim_next_automation_task(lease_owner=lease_owner, lease_seconds=lease_seconds)
    if claimed is None:
        return None
    if db.get_profile(claimed["profile_id"]) is None:
        return db.finish_claimed_automation_task(
            claimed["id"],
            lease_owner=lease_owner,
            status="failed",
            result={"steps": []},
            error="Profile not found",
        )
    try:
        _automation_running(claimed["profile_id"])
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "Profile not running"
        return db.finish_claimed_automation_task(
            claimed["id"],
            lease_owner=lease_owner,
            status="failed",
            result={"steps": []},
            error=detail,
        )
    try:
        stop_heartbeat = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            _run_automation_worker_lease_heartbeat(
                claimed["id"],
                lease_owner=lease_owner,
                lease_seconds=lease_seconds,
                stop_event=stop_heartbeat,
            )
        )
        try:
            finished, _ = await _execute_running_automation_task(claimed, lease_owner=lease_owner)
        finally:
            stop_heartbeat.set()
            await asyncio.gather(heartbeat_task, return_exceptions=True)
    except HTTPException:
        latest = db.get_automation_task(claimed["id"]) or claimed
        step_results = latest.get("result", {}).get("steps") if isinstance(latest.get("result"), dict) else None
        finished = db.finish_claimed_automation_task(
            claimed["id"],
            lease_owner=lease_owner,
            status="failed",
            result={"steps": step_results if isinstance(step_results, list) else []},
            error="Automation step failed",
        )
        if finished is None:
            raise HTTPException(status_code=409, detail=_AUTOMATION_WORKER_LOST_LEASE_DETAIL)
    _audit_automation_task_terminal_event(finished, runner_type="worker")
    return finished


async def run_automation_worker_loop(
    *,
    lease_owner: str,
    lease_seconds: int = 60,
    max_runs: int | None = None,
    max_idle_cycles: int | None = 1,
    idle_sleep_seconds: float = 1.0,
    stop_event: asyncio.Event | None = None,
) -> dict[str, int]:
    summary = {
        "claimed": 0,
        "succeeded": 0,
        "failed": 0,
        "cancelled": 0,
        "idle_cycles": 0,
    }
    while True:
        if stop_event is not None and stop_event.is_set():
            break
        if max_runs is not None and summary["claimed"] >= max_runs:
            break

        try:
            task = await run_automation_worker_once(lease_owner=lease_owner, lease_seconds=lease_seconds)
        except HTTPException as exc:
            if exc.status_code != 409 or exc.detail != _AUTOMATION_WORKER_LOST_LEASE_DETAIL:
                raise
            task = {"status": "failed"}
        if task is None:
            summary["idle_cycles"] += 1
            if max_idle_cycles is not None and summary["idle_cycles"] >= max_idle_cycles:
                break
            if idle_sleep_seconds > 0:
                await asyncio.sleep(idle_sleep_seconds)
            continue

        summary["claimed"] += 1
        if task["status"] in {"succeeded", "failed", "cancelled"}:
            summary[task["status"]] += 1
    return summary


@app.post("/api/tasks/{task_id}/run", response_model=AutomationTaskResponse)
async def run_automation_task(task_id: str):
    task = db.get_automation_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Automation task not found")
    if task["status"] != "queued":
        raise HTTPException(status_code=409, detail="Only queued automation tasks can be run")
    if db.get_profile(task["profile_id"]) is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    _automation_running(task["profile_id"])
    if _automation_profile_has_running_task(task["profile_id"], task_id):
        raise HTTPException(status_code=409, detail="Automation profile already has a running task")

    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    running_task = db.update_automation_task(task_id, status="running", started_at=started_at)
    if running_task is None:
        raise HTTPException(status_code=404, detail="Automation task not found")

    finished, status_code = await _execute_running_automation_task(running_task)
    _audit_automation_task_terminal_event(finished, runner_type="api")
    if status_code == 200:
        return _automation_task_response(finished)
    return _automation_task_finished_response(finished, status_code=status_code)


# ── Clipboard Relay ──────────────────────────────────────────────────────────

_CLIPBOARD_MAX_READ = 1_048_576  # 1MB cap on GET response

# Track xclip processes per display so we can kill the old one before spawning new
_xclip_procs: dict[int, asyncio.subprocess.Process] = {}


@app.post("/api/profiles/{profile_id}/clipboard")
async def set_clipboard(profile_id: str, body: ClipboardRequest):
    """Push text into the VNC session's X clipboard via xclip."""
    running = browser_mgr.running.get(profile_id)
    if not running:
        raise HTTPException(status_code=404, detail="Profile not running")

    import os

    # Kill previous xclip for this display (it stays alive to serve paste)
    old = _xclip_procs.pop(running.display, None)
    if old and old.returncode is None:
        old.kill()
        await old.wait()

    env = {**os.environ, "DISPLAY": f":{running.display}"}
    proc = await asyncio.create_subprocess_exec(
        "xclip", "-selection", "clipboard",
        stdin=asyncio.subprocess.PIPE,
        env=env,
    )
    # xclip reads stdin then stays alive to serve paste requests.
    proc.stdin.write(body.text.encode())  # type: ignore[union-attr]
    await proc.stdin.drain()  # type: ignore[union-attr]
    proc.stdin.close()  # type: ignore[union-attr]

    _xclip_procs[running.display] = proc

    return {"ok": True}


@app.get("/api/profiles/{profile_id}/clipboard")
async def get_clipboard(profile_id: str):
    """Read clipboard text captured from the VNC browser session."""
    running = browser_mgr.running.get(profile_id)
    if not running:
        raise HTTPException(status_code=404, detail="Profile not running")

    # The init script captures copy events when they fire. Some browser copy
    # paths under KasmVNC never reach X11 clipboard, so check all pages first.
    # Check all pages — user may have copied in any tab
    try:
        for page in running.context.pages:
            try:
                text = await page.evaluate("window.__clipboardText || ''")
                if text:
                    return {"text": text[:_CLIPBOARD_MAX_READ]}
            except Exception as exc:
                logger.debug(
                    "action=profile.clipboard_page_read_failed profile_id=%s error_type=%s",
                    profile_id,
                    type(exc).__name__,
                )
                continue
    except Exception as exc:
        logger.debug(
            "action=profile.clipboard_context_read_failed profile_id=%s error_type=%s",
            profile_id,
            type(exc).__name__,
        )

    # Fallback: xclip for non-browser clipboard owners.
    import os

    env = {**os.environ, "DISPLAY": f":{running.display}"}
    proc = await asyncio.create_subprocess_exec(
        "xclip", "-selection", "clipboard", "-o",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return {"text": ""}

    if proc.returncode != 0:
        return {"text": ""}

    text = stdout[:_CLIPBOARD_MAX_READ].decode("utf-8", errors="replace")
    return {"text": text}


# ── VNC WebSocket Proxy ──────────────────────────────────────────────────────


@app.websocket("/api/profiles/{profile_id}/vnc")
async def vnc_proxy(websocket: WebSocket, profile_id: str):
    """Proxy WebSocket frames between the frontend and a profile's KasmVNC."""
    if not await _check_websocket_origin(websocket):
        return

    running = browser_mgr.running.get(profile_id)
    if not running:
        await websocket.close(code=4004, reason="Profile not running")
        return

    await _proxy_running_vnc(websocket, profile_id, running)


@app.websocket("/api/runtime/sessions/{session_id}/vnc")
async def runtime_vnc_proxy(websocket: WebSocket, session_id: str):
    """Proxy a runtime session VNC stream after validating a short-lived viewer token."""
    if not await _check_websocket_origin(
        websocket,
        on_rejected=lambda: _audit_runtime_viewer_failure(
            "origin_not_allowed",
            session_id=session_id,
        ),
    ):
        return

    session = db.get_runtime_session(session_id)
    if not session:
        await websocket.close(code=4404, reason="Runtime session not found")
        return
    if not _runtime_session_is_live(session):
        _audit_runtime_viewer_failure("runtime_session_not_live", session=session)
        await websocket.close(code=4404, reason="Runtime session not found")
        return
    viewer_token_failure = _runtime_viewer_token_failure_reason(
        session,
        websocket.query_params.get("viewer_token"),
    )
    if viewer_token_failure:
        _audit_runtime_viewer_failure(viewer_token_failure, session=session)
        await websocket.close(code=4401, reason="Runtime viewer token invalid")
        return

    profile_id = str(session["profile_id"])
    running = browser_mgr.running.get(profile_id)
    if not running:
        _audit_runtime_viewer_failure("profile_not_running", session=session)
        await websocket.close(code=4004, reason="Profile not running")
        return

    await _proxy_running_vnc(
        websocket,
        profile_id,
        running,
        on_connected=lambda metadata: _audit_runtime_viewer_event(
            "runtime.viewer.connected",
            session,
            metadata,
        ),
        on_disconnected=lambda metadata: _audit_runtime_viewer_event(
            "runtime.viewer.disconnected",
            session,
            metadata,
        ),
        on_connect_failed=lambda: _audit_runtime_viewer_failure(
            "backend_vnc_unavailable",
            session=session,
        ),
    )


async def _proxy_running_vnc(
    websocket: WebSocket,
    profile_id: str,
    running,
    on_connected=None,
    on_disconnected=None,
    on_connect_failed=None,
):
    # Accept with client's requested subprotocol (if any) — RFC 6455 requires
    # the server must not respond with a subprotocol the client didn't request.
    requested = websocket.scope.get("subprotocols", [])
    subprotocol = "binary" if "binary" in requested else None
    await websocket.accept(subprotocol=subprotocol)

    import websockets

    vnc_url = f"ws://127.0.0.1:{running.ws_port}/websockify"
    audit_connected = False
    disconnect_metadata = {"close_code": None}

    try:
        async with websockets.connect(
            vnc_url,
            subprotocols=["binary"],
            origin=f"http://127.0.0.1:{running.ws_port}",
            max_size=None,  # VNC frames can be large (1920x1080 framebuffer)
            ping_interval=None,  # KasmVNC doesn't respond to WS pings
            ping_timeout=None,
            compression=None,  # KasmVNC can't handle permessage-deflate
        ) as vnc_ws:
            logger.info(
                "VNC proxy: connected to KasmVNC for %s (subprotocol=%s)",
                profile_id, vnc_ws.subprotocol,
            )
            if on_connected:
                on_connected({"subprotocol": subprotocol})
                audit_connected = True

            # noVNC v1.4 sends extension message types (150=ContinuousUpdates,
            # 248=QEMUKey, etc.) that KasmVNC 1.3.3 doesn't support, causing
            # "unknown message type" → disconnect.
            #
            # noVNC batches multiple RFB messages into a single WebSocket frame,
            # so we must parse the RFB stream to find message boundaries and strip
            # unsupported types before forwarding. Standard client→server types
            # have known fixed sizes (except SetEncodings and ClientCutText which
            # encode their length).

            async def client_to_vnc():
                count = 0
                handshake = 0  # first 3 messages are RFB handshake
                dropped = 0
                try:
                    while True:
                        msg = await websocket.receive()
                        msg_type = msg.get("type", "")
                        if msg_type == "websocket.disconnect":
                            disconnect_metadata["close_code"] = msg.get("code")
                            logger.info("VNC proxy [c->v]: client disconnect (code=%s) after %d msgs (%d dropped)", msg.get("code"), count, dropped)
                            break
                        if "bytes" in msg and msg["bytes"]:
                            count += 1
                            data = msg["bytes"]
                            handshake += 1

                            # First 3 messages are RFB handshake — forward as-is
                            if handshake <= 3:
                                logger.debug("VNC handshake #%d: %d bytes hex=%s", handshake, len(data), data[:20].hex())
                                await vnc_ws.send(data)
                                continue

                            # Parse RFB messages and strip unsupported types
                            filtered = _filter_rfb_client_messages(data)
                            if filtered:
                                # Safety: verify first byte is a valid RFB client type
                                if filtered[0] not in _RFB_MSG_SIZE:
                                    logger.error("RFB SAFETY: refusing to send data with invalid first byte=%d hex=%s",
                                                 filtered[0], filtered[:20].hex())
                                    dropped += 1
                                    continue
                                logger.debug("VNC send: %d bytes first_type=%d hex=%s", len(filtered), filtered[0], filtered[:100].hex())
                                await vnc_ws.send(filtered)
                            else:
                                dropped += 1

                        elif "text" in msg and msg["text"]:
                            # noVNC only sends binary frames — text frames are unexpected
                            # and would bypass the RFB filter, so drop them.
                            count += 1
                            logger.warning("VNC proxy [c->v]: DROPPING text frame len=%d (noVNC should only send binary)", len(msg["text"]))
                            dropped += 1
                        else:
                            logger.warning("VNC proxy [c->v]: unhandled msg keys=%s type=%s", list(msg.keys()), msg_type)
                except WebSocketDisconnect as exc:
                    disconnect_metadata["close_code"] = exc.code
                    logger.info("VNC proxy [c->v]: WebSocketDisconnect code=%s after %d msgs (%d dropped)", exc.code, count, dropped)
                except Exception as exc:
                    logger.warning(
                        "action=vnc.client_to_backend_failed profile_id=%s error_type=%s messages=%d",
                        profile_id,
                        type(exc).__name__,
                        count,
                    )

            async def vnc_to_client():
                count = 0
                try:
                    async for msg in vnc_ws:
                        count += 1
                        if isinstance(msg, bytes) and len(msg) > 0:
                            msg_type = msg[0]
                            if msg_type == 180:
                                # KasmVNC BinaryClipboard → convert to standard
                                # ServerCutText (type 3) so noVNC can handle it
                                text = _parse_kasmvnc_clipboard(msg)
                                if text:
                                    logger.info("VNC proxy [v->c]: clipboard %d chars", len(text))
                                    await websocket.send_bytes(_build_server_cut_text(text))
                                else:
                                    logger.info("VNC proxy [v->c]: dropped type 180 (no text/plain)")
                                continue
                            await websocket.send_bytes(msg)
                        elif isinstance(msg, bytes):
                            await websocket.send_bytes(msg)
                        else:
                            await websocket.send_text(msg)
                    disconnect_metadata["close_code"] = vnc_ws.close_code
                    logger.info("VNC proxy [v->c]: KasmVNC stream ended after %d msgs (close_code=%s)", count, vnc_ws.close_code)
                except WebSocketDisconnect as exc:
                    disconnect_metadata["close_code"] = exc.code
                    logger.info("VNC proxy [v->c]: client disconnect code=%s after %d msgs", exc.code, count)
                except Exception as exc:
                    logger.warning(
                        "action=vnc.backend_to_client_failed profile_id=%s error_type=%s messages=%d",
                        profile_id,
                        type(exc).__name__,
                        count,
                    )

            c2v = asyncio.create_task(client_to_vnc(), name="c2v")
            v2c = asyncio.create_task(vnc_to_client(), name="v2c")

            done, pending = await asyncio.wait(
                [c2v, v2c],
                return_when=asyncio.FIRST_COMPLETED,
            )
            finished = [t.get_name() for t in done]
            still_running = [t.get_name() for t in pending]

            # Check if Xvnc is still alive
            vnc_instance = browser_mgr.vnc._allocated.get(running.display)
            xvnc_alive = vnc_instance and vnc_instance.process and vnc_instance.process.poll() is None
            logger.info(
                "VNC proxy: finished=%s pending=%s xvnc_alive=%s display=:%d for %s",
                finished, still_running, xvnc_alive, running.display, profile_id,
            )

            # Xvnc logs can include backend URLs, profile paths, or token-like
            # text. Keep a low-sensitive signal without dumping raw log lines.
            import os
            xvnc_log = f"/tmp/xvnc-{running.display}.log"
            if os.path.exists(xvnc_log):
                logger.info(
                    "action=vnc.xvnc_log_available profile_id=%s display=:%d",
                    profile_id,
                    running.display,
                )

            for task in pending:
                task.cancel()

    except Exception as exc:
        logger.error(
            "action=vnc.proxy_connect_failed profile_id=%s error_type=%s",
            profile_id,
            type(exc).__name__,
        )
        if on_connect_failed and not audit_connected:
            on_connect_failed()
    finally:
        if on_disconnected and audit_connected:
            on_disconnected(disconnect_metadata)
        try:
            await websocket.close()
        except Exception as exc:
            logger.debug(
                "action=vnc.websocket_close_failed profile_id=%s error_type=%s",
                profile_id,
                type(exc).__name__,
            )


# ── Automation API ───────────────────────────────────────────────────────────
# These routes operate on the Playwright BrowserContext already owned by the
# running profile, so the noVNC viewer and external API control the same browser
# session.


def _automation_running(profile_id: str):
    running = browser_mgr.running.get(profile_id)
    if not running:
        raise HTTPException(status_code=404, detail="Profile not running")
    return running


def _automation_page_id(running, page) -> str:
    if not hasattr(running, "automation_page_ids"):
        running.automation_page_ids = {}
    key = id(page)
    page_id = running.automation_page_ids.get(key)
    if page_id is None:
        page_id = str(uuid.uuid4())
        running.automation_page_ids[key] = page_id
    return page_id


def _automation_page_url(page) -> str:
    return str(getattr(page, "url", "") or "")


def _automation_public_page_url(page) -> str:
    url = _automation_page_url(page)
    if url.startswith("about:"):
        return url
    return _automation_safe_url(url)


def _automation_is_internal_page(page) -> bool:
    return _automation_page_url(page) in {"about:home", "about:newtab", "about:welcome"}


def _automation_pages(running) -> list:
    pages = list(getattr(running.context, "pages", []) or [])
    return [page for page in pages if not _automation_is_internal_page(page)]


_AUTOMATION_CONSOLE_TYPES = {
    "assert",
    "clear",
    "count",
    "debug",
    "dir",
    "dirxml",
    "endgroup",
    "error",
    "info",
    "log",
    "profile",
    "profileend",
    "startgroup",
    "startgroupcollapsed",
    "table",
    "timeend",
    "trace",
    "warning",
}


def _automation_public_console_type(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    console_type = value.strip().lower()
    return console_type if console_type in _AUTOMATION_CONSOLE_TYPES else "unknown"


def _automation_public_location_int(value: object) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if value < 0 or value > 10_000_000:
        return None
    return value


def _automation_public_console_location(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    safe_location: dict[str, int | str] = {}
    raw_url = value.get("url")
    if raw_url is not None:
        safe_url = _automation_safe_url(str(raw_url))
        if safe_url:
            safe_location["url"] = safe_url
    for key in ("lineNumber", "columnNumber", "line", "column"):
        safe_value = _automation_public_location_int(value.get(key))
        if safe_value is not None:
            safe_location[key] = safe_value
    return safe_location


def _automation_console_log_response_entry(entry: object) -> dict:
    if not isinstance(entry, dict):
        return {"type": "unknown", "text": "", "location": {}}
    return {
        "type": _automation_public_console_type(entry.get("type")),
        "text": _automation_redact_text(str(entry.get("text", ""))),
        "location": _automation_public_console_location(entry.get("location")),
    }


def _automation_console_log_entry(message) -> dict:
    try:
        location = message.location
    except Exception:
        location = {}
    return _automation_console_log_response_entry(
        {
            "type": getattr(message, "type", ""),
            "text": getattr(message, "text", ""),
            "location": location,
        }
    )


def _automation_ensure_console_capture(page) -> None:
    if getattr(page, "automation_console_capture_ready", False) is True:
        return
    if not isinstance(getattr(page, "automation_console_logs", None), list):
        page.automation_console_logs = []

    def _record_console_message(message) -> None:
        logs = getattr(page, "automation_console_logs", [])
        logs.append(_automation_console_log_entry(message))
        if len(logs) > _AUTOMATION_CONSOLE_LOG_LIMIT:
            del logs[:-_AUTOMATION_CONSOLE_LOG_LIMIT]
        page.automation_console_logs = logs

    try:
        page.on("console", _record_console_message)
    except AttributeError:
        return
    page.automation_console_capture_ready = True


def _automation_safe_url(raw_url: str) -> str:
    parsed = urlparse(str(raw_url))
    if not parsed.scheme or not parsed.hostname:
        return ""
    host = parsed.hostname
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return parsed._replace(netloc=host, params="", query="", fragment="").geturl()


def _automation_redact_text(text: str) -> str:
    redacted = _AUTOMATION_TEXT_URL_RE.sub(
        lambda match: _automation_safe_url(match.group(0)) or "[redacted-url]",
        text,
    )
    redacted = _AUTOMATION_AUTHORIZATION_HEADER_RE.sub("Authorization=[redacted]", redacted)
    redacted = _AUTOMATION_COOKIE_HEADER_RE.sub(
        lambda match: f"{match.group(1)}=[redacted]",
        redacted,
    )
    redacted = _AUTOMATION_SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}=[redacted]",
        redacted,
    )
    return _AUTOMATION_BEARER_TOKEN_RE.sub("Bearer [redacted]", redacted)


_AUTOMATION_NETWORK_METHODS = {
    "CONNECT",
    "DELETE",
    "GET",
    "HEAD",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
    "TRACE",
}
_AUTOMATION_NETWORK_RESOURCE_TYPES = {
    "document",
    "eventsource",
    "fetch",
    "font",
    "image",
    "manifest",
    "media",
    "other",
    "script",
    "stylesheet",
    "texttrack",
    "websocket",
    "xhr",
}
_AUTOMATION_NETWORK_EVENTS = {"request", "requestfailed", "response"}
_AUTOMATION_NETWORK_FAILURES = {"request_failed"}


def _automation_public_network_event_type(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    event = value.strip().lower()
    return event if event in _AUTOMATION_NETWORK_EVENTS else "unknown"


def _automation_public_network_method(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return "UNKNOWN"
    method = value.strip().upper()
    return method if method in _AUTOMATION_NETWORK_METHODS else "UNKNOWN"


def _automation_public_resource_type(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return "unknown"
    resource_type = value.strip().lower()
    return resource_type if resource_type in _AUTOMATION_NETWORK_RESOURCE_TYPES else "unknown"


def _automation_public_network_status(value: object) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if value < 100 or value > 999:
        return None
    return value


def _automation_public_network_failure(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return "unknown"
    failure = value.strip().lower()
    return failure if failure in _AUTOMATION_NETWORK_FAILURES else "unknown"


def _automation_network_response_event(entry: object) -> dict:
    if not isinstance(entry, dict):
        return {
            "event": "unknown",
            "method": None,
            "url": "",
            "resource_type": None,
            "status": None,
            "failure": None,
        }
    return {
        "event": _automation_public_network_event_type(entry.get("event")),
        "method": _automation_public_network_method(entry.get("method")),
        "url": _automation_safe_url(str(entry.get("url", ""))),
        "resource_type": _automation_public_resource_type(entry.get("resource_type")),
        "status": _automation_public_network_status(entry.get("status")),
        "failure": _automation_public_network_failure(entry.get("failure")),
    }


def _automation_network_event(event: str, request=None, response=None, failure: str | None = None) -> dict:
    request_obj = request or getattr(response, "request", None)
    raw_url = getattr(request_obj, "url", "") if request_obj is not None else ""
    return _automation_network_response_event({
        "event": event,
        "method": getattr(request_obj, "method", None) if request_obj is not None else None,
        "url": raw_url,
        "resource_type": getattr(request_obj, "resource_type", None) if request_obj is not None else None,
        "status": getattr(response, "status", None) if response is not None else None,
        "failure": failure,
    })


def _automation_append_network_event(page, entry: dict) -> None:
    events = getattr(page, "automation_network_events", [])
    events.append(entry)
    if len(events) > _AUTOMATION_NETWORK_EVENT_LIMIT:
        del events[:-_AUTOMATION_NETWORK_EVENT_LIMIT]
    page.automation_network_events = events


def _automation_ensure_network_capture(page) -> None:
    if getattr(page, "automation_network_capture_ready", False) is True:
        return
    if not isinstance(getattr(page, "automation_network_events", None), list):
        page.automation_network_events = []

    try:
        page.on(
            "request",
            lambda request: _automation_append_network_event(
                page,
                _automation_network_event("request", request=request),
            ),
        )
        page.on(
            "response",
            lambda response: _automation_append_network_event(
                page,
                _automation_network_event("response", response=response),
            ),
        )
        page.on(
            "requestfailed",
            lambda request: _automation_append_network_event(
                page,
                _automation_network_event("requestfailed", request=request, failure="request_failed"),
            ),
        )
    except AttributeError:
        return
    page.automation_network_capture_ready = True


async def _automation_page_summary(running, index: int, page) -> AutomationPageResponse:
    _automation_ensure_console_capture(page)
    _automation_ensure_network_capture(page)
    try:
        title = await page.title()
    except Exception as exc:
        logger.debug(
            "action=automation.page_title_failed profile_id=%s page_index=%d error_type=%s",
            running.profile_id,
            index,
            type(exc).__name__,
        )
        title = ""
    return AutomationPageResponse(
        page_id=_automation_page_id(running, page),
        index=index,
        url=_automation_public_page_url(page),
        title=_automation_redact_text(title),
    )


async def _automation_apply_page_headers(running, page) -> None:
    accept_language = getattr(running, "accept_language", None)
    if not accept_language:
        return
    try:
        await page.set_extra_http_headers({"Accept-Language": accept_language})
    except AttributeError:
        return


def _automation_get_page(profile_id: str, page_ref: str):
    running = _automation_running(profile_id)
    if not hasattr(running, "automation_page_ids"):
        running.automation_page_ids = {}
    pages = _automation_pages(running)

    if page_ref.isdecimal():
        page_index = int(page_ref)
        if page_index < len(pages):
            return running, pages[page_index], page_index

    for index, page in enumerate(pages):
        if running.automation_page_ids.get(id(page)) == page_ref:
            return running, page, index

    for index, page in enumerate(pages):
        if _automation_page_id(running, page) == page_ref:
            return running, page, index

    if page_ref.isdecimal():
        raise HTTPException(status_code=404, detail="Automation page not found")
    raise HTTPException(status_code=404, detail="Automation page not found")


def _raise_automation_page_action_failed(
    action: str,
    profile_id: str,
    page_index: int,
    exc: Exception,
) -> None:
    logger.warning(
        "action=automation.%s_failed profile_id=%s page_index=%d error_type=%s",
        action,
        profile_id,
        page_index,
        type(exc).__name__,
    )
    raise HTTPException(status_code=400, detail="Automation page action failed") from exc


@app.get("/api/profiles/{profile_id}/automation", response_model=AutomationInfoResponse)
async def automation_info(profile_id: str):
    running = _automation_running(profile_id)
    return AutomationInfoResponse(
        profile_id=profile_id,
        engine=running.engine,
        status="running",
        pages_url=f"/api/profiles/{profile_id}/automation/pages",
    )


@app.get("/api/profiles/{profile_id}/automation/pages", response_model=AutomationPagesResponse)
async def automation_pages(profile_id: str):
    running = _automation_running(profile_id)
    pages = _automation_pages(running)
    return AutomationPagesResponse(
        pages=[
            await _automation_page_summary(running, index, page)
            for index, page in enumerate(pages)
        ],
    )


@app.get(
    "/api/profiles/{profile_id}/automation/pages/{page_ref}/console-logs",
    response_model=AutomationConsoleLogsResponse,
)
async def automation_console_logs(profile_id: str, page_ref: str):
    _, page, _ = _automation_get_page(profile_id, page_ref)
    _automation_ensure_console_capture(page)
    logs = [
        _automation_console_log_response_entry(entry)
        for entry in list(getattr(page, "automation_console_logs", []) or [])
    ]
    return AutomationConsoleLogsResponse(logs=logs)


@app.get(
    "/api/profiles/{profile_id}/automation/pages/{page_ref}/network-summary",
    response_model=AutomationNetworkSummaryResponse,
)
async def automation_network_summary(profile_id: str, page_ref: str):
    _, page, _ = _automation_get_page(profile_id, page_ref)
    _automation_ensure_network_capture(page)
    events = [
        _automation_network_response_event(entry)
        for entry in list(getattr(page, "automation_network_events", []) or [])
    ]
    return AutomationNetworkSummaryResponse(events=events)


@app.post(
    "/api/profiles/{profile_id}/automation/pages",
    response_model=AutomationPageResponse,
    status_code=201,
)
async def automation_create_page(profile_id: str):
    running = _automation_running(profile_id)
    try:
        page = await running.context.new_page()
        await _automation_apply_page_headers(running, page)
    except Exception as exc:
        _raise_automation_page_action_failed("new_page", profile_id, -1, exc)

    pages = _automation_pages(running)
    try:
        index = pages.index(page)
    except ValueError:
        index = max(0, len(pages) - 1)
    return await _automation_page_summary(running, index, page)


@app.post(
    "/api/profiles/{profile_id}/automation/pages/{page_ref}/goto",
    response_model=AutomationPageResponse,
)
async def automation_goto(profile_id: str, page_ref: str, body: AutomationGotoRequest):
    running, page, page_index = _automation_get_page(profile_id, page_ref)
    try:
        await _automation_apply_page_headers(running, page)
        await page.goto(body.url, wait_until=body.wait_until, timeout=body.timeout_ms)
    except Exception as exc:
        _raise_automation_page_action_failed("goto", profile_id, page_index, exc)
    return await _automation_page_summary(running, page_index, page)


@app.post(
    "/api/profiles/{profile_id}/automation/pages/{page_ref}/evaluate",
    response_model=AutomationEvaluateResponse,
)
async def automation_evaluate(
    profile_id: str,
    page_ref: str,
    body: AutomationEvaluateRequest,
):
    _, page, page_index = _automation_get_page(profile_id, page_ref)
    try:
        result = await page.evaluate(body.expression)
    except Exception as exc:
        _raise_automation_page_action_failed("evaluate", profile_id, page_index, exc)
    return AutomationEvaluateResponse(result=jsonable_encoder(result))


@app.post(
    "/api/profiles/{profile_id}/automation/pages/{page_ref}/wait-for-selector",
    response_model=AutomationPageResponse,
)
async def automation_wait_for_selector(
    profile_id: str,
    page_ref: str,
    body: AutomationWaitForSelectorRequest,
):
    running, page, page_index = _automation_get_page(profile_id, page_ref)
    try:
        await page.wait_for_selector(
            body.selector,
            state=body.state,
            timeout=body.timeout_ms,
        )
    except Exception as exc:
        _raise_automation_page_action_failed("wait_for_selector", profile_id, page_index, exc)
    return await _automation_page_summary(running, page_index, page)


@app.post(
    "/api/profiles/{profile_id}/automation/pages/{page_ref}/click",
    response_model=AutomationPageResponse,
)
async def automation_click(
    profile_id: str,
    page_ref: str,
    body: AutomationClickRequest,
):
    running, page, page_index = _automation_get_page(profile_id, page_ref)
    try:
        await page.click(body.selector, timeout=body.timeout_ms)
    except Exception as exc:
        _raise_automation_page_action_failed("click", profile_id, page_index, exc)
    return await _automation_page_summary(running, page_index, page)


@app.post(
    "/api/profiles/{profile_id}/automation/pages/{page_ref}/fill",
    response_model=AutomationPageResponse,
)
async def automation_fill(
    profile_id: str,
    page_ref: str,
    body: AutomationFillRequest,
):
    running, page, page_index = _automation_get_page(profile_id, page_ref)
    try:
        await page.fill(body.selector, body.value, timeout=body.timeout_ms)
    except Exception as exc:
        _raise_automation_page_action_failed("fill", profile_id, page_index, exc)
    return await _automation_page_summary(running, page_index, page)


@app.post(
    "/api/profiles/{profile_id}/automation/pages/{page_ref}/keyboard/type",
    response_model=AutomationPageResponse,
)
async def automation_keyboard_type(
    profile_id: str,
    page_ref: str,
    body: AutomationKeyboardTypeRequest,
):
    running, page, page_index = _automation_get_page(profile_id, page_ref)
    try:
        await page.keyboard.type(body.text, delay=body.delay_ms)
    except Exception as exc:
        _raise_automation_page_action_failed("keyboard_type", profile_id, page_index, exc)
    return await _automation_page_summary(running, page_index, page)


@app.post(
    "/api/profiles/{profile_id}/automation/pages/{page_ref}/scroll",
    response_model=AutomationPageResponse,
)
async def automation_scroll(
    profile_id: str,
    page_ref: str,
    body: AutomationScrollRequest,
):
    running, page, page_index = _automation_get_page(profile_id, page_ref)
    try:
        await page.evaluate(
            "([deltaX, deltaY]) => window.scrollBy(deltaX, deltaY)",
            [body.delta_x, body.delta_y],
        )
    except Exception as exc:
        _raise_automation_page_action_failed("scroll", profile_id, page_index, exc)
    return await _automation_page_summary(running, page_index, page)


@app.post("/api/profiles/{profile_id}/automation/pages/{page_ref}/screenshot")
async def automation_screenshot(
    profile_id: str,
    page_ref: str,
    body: AutomationScreenshotRequest,
):
    _, page, page_index = _automation_get_page(profile_id, page_ref)
    try:
        png = await page.screenshot(type="png", full_page=body.full_page)
    except Exception as exc:
        _raise_automation_page_action_failed("screenshot", profile_id, page_index, exc)
    return Response(content=png, media_type="image/png")


@app.delete("/api/profiles/{profile_id}/automation/pages/{page_ref}")
async def automation_close_page(profile_id: str, page_ref: str, request: Request):
    try:
        body = AutomationPageCloseRequest.model_validate(await request.json())
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Automation page close requires explicit confirmation",
        ) from None

    if body.confirm_close_page is not True:
        raise HTTPException(
            status_code=422,
            detail="Automation page close requires explicit confirmation",
        )

    _, page, page_index = _automation_get_page(profile_id, page_ref)
    try:
        await page.close()
    except Exception as exc:
        _raise_automation_page_action_failed("close_page", profile_id, page_index, exc)
    return {"ok": True}


# ── Static Frontend ───────────────────────────────────────────────────────────

# Serve React build. Must be AFTER API routes so /api/* isn't caught by the SPA.
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React SPA — all non-API routes return index.html."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = FRONTEND_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
