"""GeoIP helpers for aligning timezone and locale with the active exit IP."""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import math
import os
import re
import time
from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

logger = logging.getLogger("invisible_browser.manager.geoip")

IP_API_URL = "http://ip-api.com/json/"
IP_API_FIELDS = "status,message,query,countryCode,timezone,offset,isp,org"
DEFAULT_GEOIP_TIMEOUT_SECONDS = 5.0
DEFAULT_GEOIP_CACHE_TTL_SECONDS = 30 * 60
GEOIP_TIMEOUT_ENV = "INVISIBLE_MANAGER_GEOIP_TIMEOUT_SECONDS"
LEGACY_GEOIP_TIMEOUT_ENV = "CLOAKBROWSER_GEOIP_TIMEOUT_SECONDS"
GEOIP_CACHE_TTL_ENV = "INVISIBLE_MANAGER_GEOIP_CACHE_TTL_SECONDS"

COUNTRY_LOCALE_MAP: dict[str, str] = {
    "US": "en-US", "GB": "en-GB", "AU": "en-AU", "CA": "en-CA", "NZ": "en-NZ",
    "IE": "en-IE", "ZA": "en-ZA", "SG": "en-SG", "PH": "en-PH",
    "DE": "de-DE", "AT": "de-AT", "CH": "de-CH",
    "FR": "fr-FR", "BE": "fr-BE",
    "ES": "es-ES", "MX": "es-MX", "AR": "es-AR", "CO": "es-CO", "CL": "es-CL",
    "BR": "pt-BR", "PT": "pt-PT",
    "IT": "it-IT", "NL": "nl-NL",
    "JP": "ja-JP", "KR": "ko-KR", "CN": "zh-CN", "TW": "zh-TW", "HK": "zh-HK",
    "RU": "ru-RU", "UA": "uk-UA", "PL": "pl-PL", "CZ": "cs-CZ", "RO": "ro-RO",
    "IL": "he-IL", "TR": "tr-TR", "SA": "ar-SA", "AE": "ar-AE", "EG": "ar-EG",
    "IN": "hi-IN", "ID": "id-ID",
    "TH": "th-TH", "VN": "vi-VN", "MY": "ms-MY",
    "SE": "sv-SE", "NO": "nb-NO", "DK": "da-DK", "FI": "fi-FI",
    "GR": "el-GR", "HU": "hu-HU", "BG": "bg-BG",
}

_transport_for_tests: httpx.AsyncBaseTransport | None = None
_cache: dict[str, tuple[float, "GeoIPResult"]] = {}
_PUBLIC_GEOIP_COUNTRY_CODE_RE = re.compile(r"^[A-Za-z]{2}$")
_PUBLIC_GEOIP_LOCALE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-(?:[A-Za-z]{2,8}|\d{3})){0,2}$")
_PUBLIC_GEOIP_TIMEZONE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._+-]*(?:/[A-Za-z0-9._+-]+){0,3}$")
_PUBLIC_GEOIP_SOURCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")
_SENSITIVE_GEOIP_SOURCE_RE = re.compile(
    r"https?://|socks5://|@|[/?#=]|"
    r"\b(authorization|bearer|token|secret|password|cookie|auth|"
    r"access[_-]?token|api[_-]?key|client[_-]?secret|private[_-]?key|"
    r"refresh[_-]?token|runtime[_-]?service[_-]?token|service[_-]?token|"
    r"session[_-]?id|viewer[_-]?token|x[_-]?api[_-]?key)(?=$|[^A-Za-z0-9])",
    re.IGNORECASE,
)


def public_geoip_country_code(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    country_code = value.strip()
    if not _PUBLIC_GEOIP_COUNTRY_CODE_RE.fullmatch(country_code):
        return None
    return country_code.upper()


def public_geoip_ip(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    ip = value.strip()
    if not ip:
        return None
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return None
    return ip


def public_geoip_locale(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    locale = value.strip().replace("_", "-")
    if not _PUBLIC_GEOIP_LOCALE_RE.fullmatch(locale):
        return None

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


def public_geoip_timezone(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    timezone = value.strip()
    if not timezone or not _PUBLIC_GEOIP_TIMEZONE_RE.fullmatch(timezone):
        return None
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        return None
    return timezone


def public_geoip_source(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    source = value.strip()
    if not source:
        return None
    if (
        len(source) > 32
        or _SENSITIVE_GEOIP_SOURCE_RE.search(source)
        or not _PUBLIC_GEOIP_SOURCE_RE.fullmatch(source)
    ):
        return "unknown"
    return source


@dataclass(frozen=True)
class GeoIPResult:
    timezone: str | None
    locale: str | None
    ip: str | None
    country_code: str | None
    source: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "timezone": public_geoip_timezone(self.timezone),
            "locale": public_geoip_locale(self.locale),
            "ip": public_geoip_ip(self.ip),
            "country_code": public_geoip_country_code(self.country_code),
            "source": public_geoip_source(self.source),
        }


def clear_geoip_cache() -> None:
    _cache.clear()


def _positive_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        value = float("nan")
    if not math.isfinite(value) or value < 0:
        logger.warning("Invalid %s; using %.1fs", name, default)
        return default
    return value


def _geoip_timeout_seconds() -> float:
    if os.getenv(GEOIP_TIMEOUT_ENV):
        return _positive_float_env(GEOIP_TIMEOUT_ENV, DEFAULT_GEOIP_TIMEOUT_SECONDS)
    return _positive_float_env(LEGACY_GEOIP_TIMEOUT_ENV, DEFAULT_GEOIP_TIMEOUT_SECONDS)


def _geoip_cache_ttl_seconds() -> float:
    return _positive_float_env(GEOIP_CACHE_TTL_ENV, DEFAULT_GEOIP_CACHE_TTL_SECONDS)


def _normalize_proxy_url(raw: str | None) -> str | None:
    if not raw:
        return None
    if raw.startswith(("http://", "https://", "socks5://")):
        return raw
    parts = raw.split(":")
    if len(parts) == 4:
        host, port, user, passwd = parts
        return f"http://{user}:{passwd}@{host}:{port}"
    if len(parts) == 2:
        return f"http://{raw}"
    return raw


def _cache_key(proxy_url: str | None) -> str:
    if not proxy_url:
        return "direct"
    digest = hashlib.sha256(proxy_url.encode("utf-8")).hexdigest()
    return f"proxy:{digest}"


def _cached_result(key: str) -> GeoIPResult | None:
    cached = _cache.get(key)
    if cached is None:
        return None
    resolved_at, result = cached
    if time.monotonic() - resolved_at <= _geoip_cache_ttl_seconds():
        return result
    _cache.pop(key, None)
    return None


def _valid_ip(value: object) -> str | None:
    return public_geoip_ip(value)


def _parse_ip_api_response(data: object) -> GeoIPResult:
    if not isinstance(data, dict) or data.get("status") != "success":
        logger.warning("GeoIP provider returned failure source=ip-api")
        return GeoIPResult(None, None, None, None, "ip-api")

    timezone = data.get("timezone") if isinstance(data.get("timezone"), str) else None
    country = data.get("countryCode") if isinstance(data.get("countryCode"), str) else None
    country_code = public_geoip_country_code(country)
    locale = public_geoip_locale(COUNTRY_LOCALE_MAP.get(country_code)) if country_code else None
    return GeoIPResult(
        timezone=public_geoip_timezone(timezone),
        locale=locale,
        ip=_valid_ip(data.get("query")),
        country_code=country_code,
        source="ip-api",
    )


def _first_language_locale(value: object, country_code: str | None) -> str | None:
    if isinstance(value, str):
        for item in value.split(","):
            candidate = item.strip().replace("_", "-")
            if not candidate:
                continue
            if "-" in candidate:
                return candidate
            if country_code:
                return COUNTRY_LOCALE_MAP.get(country_code)
    if country_code:
        return COUNTRY_LOCALE_MAP.get(country_code)
    return None


def _parse_ipapi_response(data: object) -> GeoIPResult:
    if not isinstance(data, dict) or data.get("error") is True:
        logger.warning("GeoIP provider returned failure source=ipapi.co")
        return GeoIPResult(None, None, None, None, "ipapi.co")

    timezone = data.get("timezone") if isinstance(data.get("timezone"), str) else None
    country = data.get("country_code") if isinstance(data.get("country_code"), str) else None
    country_code = public_geoip_country_code(country)
    return GeoIPResult(
        timezone=public_geoip_timezone(timezone),
        locale=public_geoip_locale(_first_language_locale(data.get("languages"), country_code)),
        ip=_valid_ip(data.get("ip")),
        country_code=country_code,
        source="ipapi.co",
    )


def _parse_ipwhois_response(data: object) -> GeoIPResult:
    if not isinstance(data, dict) or data.get("success") is False:
        logger.warning("GeoIP provider returned failure source=ipwho.is")
        return GeoIPResult(None, None, None, None, "ipwho.is")

    timezone_data = data.get("timezone")
    timezone = None
    if isinstance(timezone_data, dict) and isinstance(timezone_data.get("id"), str):
        timezone = timezone_data["id"]
    elif isinstance(timezone_data, str):
        timezone = timezone_data
    country = data.get("country_code") if isinstance(data.get("country_code"), str) else None
    country_code = public_geoip_country_code(country)
    return GeoIPResult(
        timezone=public_geoip_timezone(timezone),
        locale=public_geoip_locale(_first_language_locale(data.get("languages"), country_code)),
        ip=_valid_ip(data.get("ip")),
        country_code=country_code,
        source="ipwho.is",
    )


_GEOIP_PROVIDERS = (
    ("ip-api", IP_API_URL, {"fields": IP_API_FIELDS}, _parse_ip_api_response),
    ("ipapi.co", "https://ipapi.co/json/", {}, _parse_ipapi_response),
    ("ipwho.is", "https://ipwho.is/", {}, _parse_ipwhois_response),
)


async def resolve_network_geo(proxy_url: str | None = None) -> GeoIPResult:
    """Resolve timezone/locale from the active network path.

    When *proxy_url* is provided, the GeoIP request is sent through that proxy,
    so the result reflects the proxy exit IP instead of the manager host.
    """
    proxy_url = _normalize_proxy_url(proxy_url)
    key = _cache_key(proxy_url)
    cached = _cached_result(key)
    if cached is not None:
        return cached

    timeout = _geoip_timeout_seconds()
    try:
        client_context = httpx.AsyncClient(
            proxy=proxy_url,
            timeout=timeout,
            transport=_transport_for_tests,
        )
    except Exception as exc:
        logger.warning("GeoIP client initialization failed: %s", type(exc).__name__)
        return GeoIPResult(None, None, None, None, "failed")

    async with client_context as client:
        for provider_name, url, params, parser in _GEOIP_PROVIDERS:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = parser(response.json())
            except Exception as exc:
                logger.warning(
                    "GeoIP %s lookup failed: error_type=%s",
                    provider_name,
                    type(exc).__name__,
                )
                continue

            if not any((result.timezone, result.locale, result.ip)):
                continue

            _cache[key] = (time.monotonic(), result)
            public_result = result.as_dict()
            logger.debug(
                "GeoIP resolved source=%s ip=%s country=%s timezone=%s locale=%s",
                public_result["source"],
                public_result["ip"],
                public_result["country_code"],
                public_result["timezone"],
                public_result["locale"],
            )
            return result

    return GeoIPResult(None, None, None, None, "failed")


def _nonempty(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _geoip_enabled(value: object) -> bool:
    if value in (False, 0, "0"):
        return False
    return True


async def resolve_profile_network_fingerprint(profile: dict[str, Any]) -> dict[str, Any]:
    """Return a profile copy with missing timezone/locale filled from GeoIP."""
    resolved = dict(profile)
    timezone = _nonempty(profile.get("timezone"))
    locale = _nonempty(profile.get("locale"))

    if not _geoip_enabled(profile.get("geoip", True)):
        resolved["timezone"] = timezone
        resolved["locale"] = locale
        return resolved

    geo = await resolve_network_geo(_normalize_proxy_url(profile.get("proxy") or None))
    geo_data = geo.as_dict()
    if any((geo_data["timezone"], geo_data["locale"], geo_data["ip"], geo_data["country_code"])):
        resolved["_geoip_result"] = geo_data
    if timezone:
        resolved["timezone"] = timezone
    elif geo_data["timezone"]:
        resolved["timezone"] = geo_data["timezone"]

    if locale:
        resolved["locale"] = locale
    elif geo_data["locale"]:
        resolved["locale"] = geo_data["locale"]

    return resolved
