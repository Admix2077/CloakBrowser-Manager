"""Profile health calculation for fingerprint and runtime diagnostics."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, Literal

from pydantic import BaseModel

from .browser_manager import _normalize_proxy, _validate_proxy
from .geoip import (
    GeoIPResult,
    public_geoip_country_code,
    public_geoip_ip,
    public_geoip_locale,
    public_geoip_source,
    public_geoip_timezone,
)

HealthStatus = Literal["good", "warning", "error", "unknown"]
WarningSeverity = Literal["info", "warning", "error"]
HealthWarningCode = Literal[
    "geoip_missing",
    "geoip_stale",
    "proxy_invalid",
    "geoip_lookup_failed",
    "manual_timezone_mismatch",
    "manual_locale_mismatch",
    "runtime_vnc_missing",
    "runtime_automation_missing",
    "launch_failed",
]

HEALTH_WARNING_CODES: set[str] = {
    "geoip_missing",
    "geoip_stale",
    "proxy_invalid",
    "geoip_lookup_failed",
    "manual_timezone_mismatch",
    "manual_locale_mismatch",
    "runtime_vnc_missing",
    "runtime_automation_missing",
    "launch_failed",
}

GEOIP_STALE_AFTER_SECONDS = 24 * 60 * 60
_SAFE_PROXY_ERROR_DETAILS = (
    ("Invalid proxy scheme", "Invalid proxy scheme"),
    ("Invalid proxy URL", "Invalid proxy URL"),
    ("Proxy URL missing hostname", "Proxy URL missing hostname"),
    ("Proxy URL invalid port", "Proxy URL invalid port"),
    ("Proxy URL missing port", "Proxy URL missing port"),
)
_PUBLIC_RUNTIME_STATUSES = {"running", "stopped"}
_PUBLIC_PROFILE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PUBLIC_AUTOMATION_URL_RE = re.compile(r"^/api/profiles/[A-Za-z0-9][A-Za-z0-9._-]{0,127}/automation$")
_SENSITIVE_RUNTIME_TEXT_RE = re.compile(
    r"https?://|socks[45]://|@|\b(authorization|bearer)\b|"
    r"\b(access[_-]?token|api[_-]?key|auth[_-]?token|client[_-]?secret|cookie|password|"
    r"private[_-]?key|refresh[_-]?token|secret|session[_-]?id|token|viewer[_-]?token|"
    r"x[_-]?api[_-]?key)\b",
    re.IGNORECASE,
)


class HealthWarning(BaseModel):
    code: HealthWarningCode
    message: str
    severity: WarningSeverity
    action: str | None = None


class HealthGeoIP(BaseModel):
    ip: str | None = None
    country_code: str | None = None
    timezone: str | None = None
    locale: str | None = None
    source: str | None = None
    resolved_at: str | None = None


class ProfileHealthResponse(BaseModel):
    profile_id: str
    status: HealthStatus
    geoip: HealthGeoIP | None = None
    manual_overrides: dict[str, bool]
    runtime: dict[str, Any]
    warnings: list[HealthWarning]
    checked_at: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _nonempty(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _profile_geoip(profile: dict[str, Any]) -> HealthGeoIP | None:
    ip = public_geoip_ip(profile.get("last_geoip_ip"))
    country_code = public_geoip_country_code(profile.get("last_geoip_country_code"))
    timezone = public_geoip_timezone(profile.get("last_geoip_timezone"))
    locale = public_geoip_locale(profile.get("last_geoip_locale"))
    source = public_geoip_source(profile.get("last_geoip_source"))
    if not any((ip, country_code, timezone, locale, source)):
        return None
    return HealthGeoIP(
        ip=ip,
        country_code=country_code,
        timezone=timezone,
        locale=locale,
        source=source,
        resolved_at=_nonempty(profile.get("last_geoip_resolved_at")),
    )


def _parse_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _is_geoip_stale(resolved_at: str | None, checked_at: str) -> bool:
    resolved = _parse_datetime(resolved_at)
    checked = _parse_datetime(checked_at)
    if resolved is None or checked is None:
        return False
    return (checked - resolved).total_seconds() > GEOIP_STALE_AFTER_SECONDS


def _geoip_from_result(result: GeoIPResult) -> HealthGeoIP | None:
    ip = public_geoip_ip(result.ip)
    country_code = public_geoip_country_code(result.country_code)
    timezone = public_geoip_timezone(result.timezone)
    locale = public_geoip_locale(result.locale)
    if not any((ip, country_code, timezone, locale)):
        return None
    return HealthGeoIP(
        ip=ip,
        country_code=country_code,
        timezone=timezone,
        locale=locale,
        source=public_geoip_source(result.source),
        resolved_at=now_iso(),
    )


def _status_from_warnings(warnings: list[HealthWarning], geoip: HealthGeoIP | None) -> HealthStatus:
    if any(w.severity == "error" for w in warnings):
        return "error"
    if warnings:
        if geoip is None and all(w.code == "geoip_missing" for w in warnings):
            return "unknown"
        return "warning"
    return "good"


def validate_profile_proxy(profile: dict[str, Any]) -> str | None:
    proxy = _nonempty(profile.get("proxy"))
    if not proxy:
        return None
    normalized = _normalize_proxy(proxy)
    _validate_proxy(normalized)
    return normalized


def _safe_proxy_error_detail(message: str) -> str:
    for prefix, detail in _SAFE_PROXY_ERROR_DETAILS:
        if message.startswith(prefix):
            return detail
    return "Invalid proxy URL"


def _public_runtime_status(value: object) -> str:
    if isinstance(value, str) and value in _PUBLIC_RUNTIME_STATUSES:
        return value
    return "unknown"


def _public_profile_id(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    text = value.strip()
    if not text:
        return "unknown"
    if not _PUBLIC_PROFILE_ID_RE.fullmatch(text):
        return "unknown"
    if _SENSITIVE_RUNTIME_TEXT_RE.search(text):
        return "unknown"
    return text


def _public_runtime_vnc_ws_port(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and 1 <= value <= 65535:
        return value
    return None


def _public_runtime_automation_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if not _PUBLIC_AUTOMATION_URL_RE.fullmatch(text):
        return None
    if _SENSITIVE_RUNTIME_TEXT_RE.search(text):
        return None
    return text


def compute_profile_health(
    profile: dict[str, Any],
    runtime_status: dict[str, Any],
    *,
    checked_at: str | None = None,
    geoip_result: GeoIPResult | None = None,
    geoip_lookup_failed: bool = False,
    proxy_error: str | None = None,
) -> ProfileHealthResponse:
    checked_at = checked_at or now_iso()
    warnings: list[HealthWarning] = []
    geoip = _geoip_from_result(geoip_result) if geoip_result else _profile_geoip(profile)

    if proxy_error is None:
        try:
            validate_profile_proxy(profile)
        except ValueError as exc:
            proxy_error = str(exc)
    if proxy_error:
        proxy_error = _safe_proxy_error_detail(proxy_error)
        warnings.append(
            HealthWarning(
                code="proxy_invalid",
                message=proxy_error,
                severity="error",
                action="修正 proxy 格式后重新检测。",
            )
        )

    if geoip_lookup_failed:
        warnings.append(
            HealthWarning(
                code="geoip_lookup_failed",
                message="GeoIP 查询失败，无法确认当前出口 IP 指纹。",
                severity="warning" if geoip else "error",
                action="检查网络、代理连通性或稍后重试。",
            )
        )

    if geoip is None:
        warnings.append(
            HealthWarning(
                code="geoip_missing",
                message="还没有可用的 GeoIP 检测结果。",
                severity="info",
                action="运行健康检测以解析当前出口 IP、国家、时区和语言。",
            )
        )
    elif _is_geoip_stale(geoip.resolved_at, checked_at):
        warnings.append(
            HealthWarning(
                code="geoip_stale",
                message="最近一次 GeoIP 检测结果已过期。",
                severity="warning",
                action="重新运行健康检测刷新出口 IP 指纹。",
            )
        )

    manual_timezone = _nonempty(profile.get("timezone"))
    manual_locale = _nonempty(profile.get("locale"))
    if geoip and manual_timezone and geoip.timezone and manual_timezone != geoip.timezone:
        warnings.append(
            HealthWarning(
                code="manual_timezone_mismatch",
                message="手动 timezone 与当前出口建议不一致。",
                severity="warning",
                action="确认是否需要保留手动覆盖，或清空 timezone 交给 GeoIP 自动匹配。",
            )
        )
    if geoip and manual_locale and geoip.locale and manual_locale != geoip.locale:
        warnings.append(
            HealthWarning(
                code="manual_locale_mismatch",
                message="手动 locale 与当前出口建议不一致。",
                severity="warning",
                action="确认是否需要保留手动覆盖，或清空 locale 交给 GeoIP 自动匹配。",
            )
        )

    public_runtime_status = _public_runtime_status(runtime_status.get("status"))
    public_vnc_ws_port = _public_runtime_vnc_ws_port(runtime_status.get("vnc_ws_port"))
    public_automation_url = _public_runtime_automation_url(runtime_status.get("automation_url"))
    if public_runtime_status == "running":
        if public_vnc_ws_port is None:
            warnings.append(
                HealthWarning(
                    code="runtime_vnc_missing",
                    message="Profile 正在运行，但缺少 VNC WebSocket 端口。",
                    severity="warning",
                    action="重启 profile 或检查 VNC runtime。",
                )
            )
        if public_automation_url is None:
            warnings.append(
                HealthWarning(
                    code="runtime_automation_missing",
                    message="Profile 正在运行，但缺少 Automation API 地址。",
                    severity="warning",
                    action="重启 profile 或检查 Automation runtime。",
                )
            )

    return ProfileHealthResponse(
        profile_id=_public_profile_id(profile.get("id")),
        status=_status_from_warnings(warnings, geoip),
        geoip=geoip,
        manual_overrides={
            "timezone": manual_timezone is not None,
            "locale": manual_locale is not None,
        },
        runtime={
            "status": public_runtime_status,
            "vnc_ws_port": public_vnc_ws_port,
            "automation_url": public_automation_url,
        },
        warnings=warnings,
        checked_at=checked_at,
    )
