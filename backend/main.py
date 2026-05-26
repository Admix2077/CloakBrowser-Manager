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
import os
import random
import secrets
import struct
import shutil
import uuid
from contextlib import asynccontextmanager
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import starlette.requests
from starlette.types import ASGIApp, Receive, Scope, Send

from . import database as db
from .browser_manager import BrowserManager
from .geoip import resolve_network_geo
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
    AutomationPageResponse,
    AutomationPagesResponse,
    AutomationScreenshotRequest,
    AutomationScrollRequest,
    AutomationWaitForSelectorRequest,
    ClipboardRequest,
    LaunchResponse,
    LoginRequest,
    ProxyAssignRequest,
    ProxyAssignResponse,
    ProxyAssignResult,
    ProxyBulkCheckRequest,
    ProxyBulkCheckResponse,
    ProxyBulkCheckResult,
    ProxyCreate,
    ProxyFromProfileCreate,
    ProxyProviderPresetCreate,
    ProxyProviderPresetResponse,
    ProxyProviderPresetUpdate,
    ProxyRandomAssignRequest,
    ProxyRandomAssignResponse,
    ProxyRandomAssignResult,
    ProxyResponse,
    ProxyUpdate,
    ProfileCreate,
    ProfileConfigExport,
    ProfileExportRequest,
    ProfileExportResponse,
    ProfileExportResult,
    ProfileImportResponse,
    ProfileImportPreviewRequest,
    ProfileImportPreviewResponse,
    ProfileImportResult,
    ProfileResponse,
    ProfileStatusResponse,
    ProfileTemplateCreate,
    ProfileTemplateResponse,
    ProfileTemplateUpdate,
    ProfileUpdate,
    RuntimeSessionCreate,
    RuntimeSessionRenew,
    RuntimeSessionResponse,
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

# Paths that bypass authentication even when AUTH_TOKEN is set
_AUTH_EXEMPT = frozenset({"/api/auth/status", "/api/auth/login", "/api/status"})


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
                if cookie_val and hmac.compare_digest(cookie_val, AUTH_TOKEN):
                    return True
            break

    return False


def _is_https(request: Request) -> bool:
    """Check if the original client connection was HTTPS (via reverse proxy header)."""
    proto = request.headers.get("x-forwarded-proto", "")
    return "https" in proto


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
        logger.warning("WebSocket origin malformed: %s", origin)
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

    logger.warning("WebSocket origin mismatch: origin=%s host=%s", origin, host)
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
    logger.info("Invisible Browser Manager started")
    yield
    logger.info("Shutting down — stopping all browsers...")
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
    response.set_cookie(
        key="auth_token",
        value=AUTH_TOKEN,
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


def _proxy_response(proxy: dict) -> ProxyResponse:
    safe = dict(proxy)
    safe["url"] = redact_proxy_asset_url(str(safe["url"]))
    safe["tags"] = [TagResponse(**tag) for tag in safe.get("tags", [])]
    return ProxyResponse(**safe)


def _proxy_provider_preset_response(preset: dict) -> ProxyProviderPresetResponse:
    safe = dict(preset)
    safe["tags"] = [TagResponse(**tag) for tag in safe.get("tags", [])]
    return ProxyProviderPresetResponse(**safe)


def _tag_payloads(tags: list[dict] | None) -> list[dict]:
    return [tag.model_dump() if hasattr(tag, "model_dump") else tag for tag in (tags or [])]


def _normalize_filter_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_country_code(value: str | None) -> str | None:
    normalized = _normalize_filter_value(value)
    return normalized.upper() if normalized else None


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
    if provider and _normalize_filter_value(proxy.get("provider")) != provider:
        return False
    if country_code and _normalize_country_code(proxy.get("country_code")) != country_code:
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
    return ProfileTemplateResponse(**template)


def _runtime_session_response(session: dict) -> RuntimeSessionResponse:
    return RuntimeSessionResponse(**session)


def _audit_runtime_event(event_type: str, session: dict, metadata: dict | None = None) -> None:
    db.create_audit_event(
        event_type=event_type,
        actor_type="runtime_service",
        runtime_session_id=str(session["id"]),
        profile_id=str(session["profile_id"]),
        external_session_id=str(session["external_session_id"]),
        metadata=metadata,
    )


def _audit_runtime_viewer_event(event_type: str, session: dict, metadata: dict | None = None) -> None:
    db.create_audit_event(
        event_type=event_type,
        actor_type="runtime_viewer",
        runtime_session_id=str(session["id"]),
        profile_id=str(session["profile_id"]),
        external_session_id=str(session["external_session_id"]),
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
            runtime_session_id=str(session["id"]) if session else session_id,
            profile_id=str(session["profile_id"]) if session else None,
            external_session_id=str(session["external_session_id"]) if session else None,
            metadata={"reason_code": reason_code},
        )
    except Exception as exc:
        logger.warning("Runtime viewer failure audit skipped: %s", type(exc).__name__)


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


def _safe_proxy_check_error(exc: Exception, raw_url: str) -> str:
    redacted_url = redact_proxy_asset_url(raw_url)
    message = str(exc).replace(raw_url, redacted_url)
    parsed = urlparse(raw_url)
    if parsed.password:
        message = message.replace(parsed.password, "[redacted]")
    return message


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
            last_check_ip=geo.ip,
            last_check_country_code=geo.country_code,
            last_check_timezone=geo.timezone,
            last_check_locale=geo.locale,
            last_check_source=geo.source,
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    if "tags" in data and data["tags"] is not None:
        data["tags"] = _tag_payloads(data["tags"])
    try:
        proxy = db.update_proxy(proxy_id, **data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return _proxy_response(proxy)


@app.delete("/api/proxies/{proxy_id}")
async def delete_proxy(proxy_id: str):
    deleted = db.delete_proxy(proxy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Proxy not found")
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
    if "tags" in data and data["tags"] is not None:
        data["tags"] = _tag_payloads(data["tags"])
    preset = db.update_proxy_provider_preset(preset_id, **data)
    if not preset:
        raise HTTPException(status_code=404, detail="Proxy provider preset not found")
    return _proxy_provider_preset_response(preset)


@app.delete("/api/proxy-provider-presets/{preset_id}")
async def delete_proxy_provider_preset(preset_id: str):
    deleted = db.delete_proxy_provider_preset(preset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Proxy provider preset not found")
    return {"ok": True}


@app.post("/api/proxies/{proxy_id}/assign", response_model=ProxyAssignResponse)
async def assign_proxy_to_profiles(proxy_id: str, req: ProxyAssignRequest):
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
    return ProxyAssignResponse(
        proxy_id=proxy_id,
        proxy=_proxy_response(proxy),
        total=len(req.profile_ids),
        succeeded=succeeded,
        failed=len(req.profile_ids) - succeeded,
        results=results,
    )


@app.post("/api/proxies/assign/random", response_model=ProxyRandomAssignResponse)
async def assign_random_proxy_to_profiles(req: ProxyRandomAssignRequest):
    preset = None
    if req.provider_preset_id:
        preset = db.get_proxy_provider_preset(req.provider_preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail="Proxy provider preset not found")

    provider = _normalize_filter_value(req.provider) or _normalize_filter_value(
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
    return ProxyRandomAssignResponse(
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


@app.post("/api/proxies/bulk/check", response_model=ProxyBulkCheckResponse)
async def bulk_check_proxies(req: ProxyBulkCheckRequest):
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
                error=None if ok else updated.get("last_check_error") or "Proxy check failed",
                proxy=_proxy_response(updated),
            )
        )

    succeeded = sum(1 for result in results if result.ok)
    return ProxyBulkCheckResponse(
        total=len(req.proxy_ids),
        succeeded=succeeded,
        failed=len(req.proxy_ids) - succeeded,
        results=results,
    )


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
async def delete_profile_template(template_id: str):
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
        profile = db.create_profile(
            name=f"Runtime {req.external_session_id}",
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
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.error("Failed to launch runtime session profile %s: %s", profile_id, exc)
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

    viewer_url = f"/api/runtime/sessions/{session_id}/vnc?viewer_token={viewer_token}"
    return RuntimeViewerTokenResponse(
        viewer_url=viewer_url,
        viewer_token=viewer_token,
        expires_at=expires_at,
    )


@app.post("/api/runtime/sessions/{session_id}/terminate", response_model=RuntimeSessionResponse)
async def terminate_runtime_session(session_id: str, request: Request):
    _require_runtime_service_token(request)
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
        p["tags"] = [TagResponse(**t) for t in p.get("tags", [])]
        result.append(ProfileResponse(**p))
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
    profile["tags"] = [TagResponse(**t) for t in profile.get("tags", [])]
    return ProfileResponse(**profile)


@app.post("/api/profiles/import/preview", response_model=ProfileImportPreviewResponse)
async def preview_profile_import(req: ProfileImportPreviewRequest):
    try:
        return preview_profile_csv_import(req.csv_text)
    except ProfileImportHeaderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/profiles/import", response_model=ProfileImportResponse)
async def import_profiles(req: ProfileImportPreviewRequest):
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
        profile["tags"] = [TagResponse(**t) for t in profile.get("tags", [])]
        results.append(
            ProfileImportResult(
                line_number=row.line_number,
                ok=True,
                errors=[],
                source=row.source,
                profile=ProfileResponse(**profile),
            )
        )

    succeeded = sum(1 for result in results if result.ok)
    return ProfileImportResponse(
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=results,
    )


@app.post("/api/profiles/export", response_model=ProfileExportResponse)
async def export_profiles(req: ProfileExportRequest):
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

        profile["tags"] = [TagResponse(**t) for t in profile.get("tags", [])]
        results.append(
            ProfileExportResult(
                profile_id=profile_id,
                ok=True,
                error=None,
                config=ProfileConfigExport(**profile),
            )
        )

    exported = sum(1 for result in results if result.ok)
    return ProfileExportResponse(
        total=len(results),
        exported=exported,
        failed=len(results) - exported,
        results=results,
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    profile["tags"] = [TagResponse(**t) for t in profile.get("tags", [])]
    return ProfileResponse(**profile)


@app.put("/api/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: str, req: ProfileUpdate):
    # Only pass fields that were explicitly set
    data = req.model_dump(exclude_unset=True)
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
    profile["tags"] = [TagResponse(**t) for t in profile.get("tags", [])]
    return ProfileResponse(**profile)


@app.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: str):
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

    return {"ok": True}


# ── Launch / Stop ─────────────────────────────────────────────────────────────


@app.post("/api/profiles/{profile_id}/launch", response_model=LaunchResponse)
async def launch_profile(profile_id: str):
    profile = db.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile_id in browser_mgr.running:
        raise HTTPException(status_code=409, detail="Profile is already running")

    try:
        running = await browser_mgr.launch(profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to launch profile %s: %s", profile_id, exc)
        raise HTTPException(status_code=500, detail="Failed to launch browser")

    db.update_profile_geoip_result(profile_id, getattr(running, "resolved_geoip", None))

    return LaunchResponse(
        profile_id=profile_id,
        status="running",
        vnc_ws_port=running.ws_port,
        display=f":{running.display}",
        automation_url=f"/api/profiles/{profile_id}/automation",
    )


@app.post("/api/profiles/{profile_id}/stop")
async def stop_profile(profile_id: str):
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
        return compute_profile_health(
            profile,
            runtime_status,
            proxy_error=str(exc),
        )

    try:
        geo = await resolve_network_geo(proxy_url)
    except Exception as exc:
        logger.warning("Health GeoIP lookup failed for %s: %s", profile_id, exc)
        return compute_profile_health(
            profile,
            runtime_status,
            geoip_lookup_failed=True,
        )

    if any((geo.timezone, geo.locale, geo.ip, geo.country_code)):
        profile = db.update_profile_geoip_result(profile_id, geo.as_dict()) or profile
        return compute_profile_health(profile, runtime_status)

    return compute_profile_health(
        profile,
        runtime_status,
        geoip_lookup_failed=True,
    )


# ── System Status ─────────────────────────────────────────────────────────────


@app.get("/api/status", response_model=StatusResponse)
async def get_system_status():
    profiles = db.list_profiles()
    return StatusResponse(
        running_count=len(browser_mgr.running),
        binary_version="invisible-playwright",
        profiles_total=len(profiles),
    )


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
                logger.debug("Clipboard read failed on page: %s", exc)
                continue
    except Exception as exc:
        logger.debug("Playwright clipboard read failed: %s", exc)

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
                    logger.warning("VNC proxy [c->v]: %s: %s (after %d msgs)", type(exc).__name__, exc, count)

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
                    logger.warning("VNC proxy [v->c]: %s: %s (after %d msgs)", type(exc).__name__, exc, count)

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

            # Dump Xvnc log on disconnect
            import os
            xvnc_log = f"/tmp/xvnc-{running.display}.log"
            if os.path.exists(xvnc_log):
                with open(xvnc_log) as f:
                    log_content = f.read()
                if log_content.strip():
                    for line in log_content.strip().split("\n")[-20:]:
                        logger.info("Xvnc[:%d] %s", running.display, line)

            for task in pending:
                task.cancel()

    except Exception as exc:
        logger.error("VNC proxy connect error for %s: %s: %s", profile_id, type(exc).__name__, exc)
        if on_connect_failed and not audit_connected:
            on_connect_failed()
    finally:
        if on_disconnected and audit_connected:
            on_disconnected(disconnect_metadata)
        try:
            await websocket.close()
        except Exception as exc:
            logger.debug("VNC proxy: websocket.close() failed: %s", exc)


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


def _automation_console_log_entry(message) -> dict:
    try:
        location = message.location
    except Exception:
        location = {}
    if not isinstance(location, dict):
        location = {}
    return {
        "type": str(getattr(message, "type", "")),
        "text": str(getattr(message, "text", "")),
        "location": {
            key: value
            for key, value in location.items()
            if key in {"url", "lineNumber", "columnNumber", "line", "column"}
        },
    }


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


async def _automation_page_summary(running, index: int, page) -> AutomationPageResponse:
    _automation_ensure_console_capture(page)
    try:
        title = await page.title()
    except Exception as exc:
        logger.debug("Automation page title failed for index %d: %s", index, exc)
        title = ""
    return AutomationPageResponse(
        page_id=_automation_page_id(running, page),
        index=index,
        url=page.url,
        title=title,
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
    pages = list(getattr(running.context, "pages", []) or [])

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
    pages = list(getattr(running.context, "pages", []) or [])
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
    return AutomationConsoleLogsResponse(logs=list(getattr(page, "automation_console_logs", []) or []))


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
        logger.warning("Automation new_page failed for %s: %s", profile_id, exc)
        raise HTTPException(status_code=400, detail=str(exc))

    pages = list(getattr(running.context, "pages", []) or [])
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
        logger.warning("Automation goto failed for %s page %d: %s", profile_id, page_index, exc)
        raise HTTPException(status_code=400, detail=str(exc))
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
        logger.warning("Automation evaluate failed for %s page %d: %s", profile_id, page_index, exc)
        raise HTTPException(status_code=400, detail=str(exc))
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
        logger.warning(
            "Automation wait_for_selector failed for %s page %d: %s",
            profile_id,
            page_index,
            exc,
        )
        raise HTTPException(status_code=400, detail=str(exc))
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
        logger.warning("Automation click failed for %s page %d: %s", profile_id, page_index, exc)
        raise HTTPException(status_code=400, detail=str(exc))
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
        logger.warning("Automation fill failed for %s page %d: %s", profile_id, page_index, exc)
        raise HTTPException(status_code=400, detail=str(exc))
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
        logger.warning(
            "Automation keyboard type failed for %s page %d: %s",
            profile_id,
            page_index,
            exc,
        )
        raise HTTPException(status_code=400, detail=str(exc))
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
        logger.warning("Automation scroll failed for %s page %d: %s", profile_id, page_index, exc)
        raise HTTPException(status_code=400, detail=str(exc))
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
        logger.warning("Automation screenshot failed for %s page %d: %s", profile_id, page_index, exc)
        raise HTTPException(status_code=400, detail=str(exc))
    return Response(content=png, media_type="image/png")


@app.delete("/api/profiles/{profile_id}/automation/pages/{page_ref}")
async def automation_close_page(profile_id: str, page_ref: str):
    _, page, page_index = _automation_get_page(profile_id, page_ref)
    try:
        await page.close()
    except Exception as exc:
        logger.warning("Automation page close failed for %s page %d: %s", profile_id, page_index, exc)
        raise HTTPException(status_code=400, detail=str(exc))
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
