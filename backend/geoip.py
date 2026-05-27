"""GeoIP helpers for aligning timezone and locale with the active exit IP."""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import math
import os
import time
from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True)
class GeoIPResult:
    timezone: str | None
    locale: str | None
    ip: str | None
    country_code: str | None
    source: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "timezone": self.timezone,
            "locale": self.locale,
            "ip": self.ip,
            "country_code": self.country_code,
            "source": self.source,
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
        logger.warning("Invalid %s=%r; using %.1fs", name, raw, default)
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
    if not isinstance(value, str):
        return None
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return None
    return value


def _parse_ip_api_response(data: object) -> GeoIPResult:
    if not isinstance(data, dict) or data.get("status") != "success":
        message = data.get("message") if isinstance(data, dict) else None
        logger.warning("GeoIP lookup returned failure: %s", message)
        return GeoIPResult(None, None, None, None, "ip-api")

    timezone = data.get("timezone") if isinstance(data.get("timezone"), str) else None
    country = data.get("countryCode") if isinstance(data.get("countryCode"), str) else None
    country_code = country.upper() if country else None
    locale = COUNTRY_LOCALE_MAP.get(country_code) if country_code else None
    return GeoIPResult(
        timezone=timezone,
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
        reason = data.get("reason") if isinstance(data, dict) else None
        logger.warning("GeoIP ipapi.co lookup returned failure: %s", reason)
        return GeoIPResult(None, None, None, None, "ipapi.co")

    timezone = data.get("timezone") if isinstance(data.get("timezone"), str) else None
    country = data.get("country_code") if isinstance(data.get("country_code"), str) else None
    country_code = country.upper() if country else None
    return GeoIPResult(
        timezone=timezone,
        locale=_first_language_locale(data.get("languages"), country_code),
        ip=_valid_ip(data.get("ip")),
        country_code=country_code,
        source="ipapi.co",
    )


def _parse_ipwhois_response(data: object) -> GeoIPResult:
    if not isinstance(data, dict) or data.get("success") is False:
        message = data.get("message") if isinstance(data, dict) else None
        logger.warning("GeoIP ipwho.is lookup returned failure: %s", message)
        return GeoIPResult(None, None, None, None, "ipwho.is")

    timezone_data = data.get("timezone")
    timezone = None
    if isinstance(timezone_data, dict) and isinstance(timezone_data.get("id"), str):
        timezone = timezone_data["id"]
    elif isinstance(timezone_data, str):
        timezone = timezone_data
    country = data.get("country_code") if isinstance(data.get("country_code"), str) else None
    country_code = country.upper() if country else None
    return GeoIPResult(
        timezone=timezone,
        locale=_first_language_locale(data.get("languages"), country_code),
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
                logger.warning("GeoIP %s lookup failed: %s", provider_name, exc)
                continue

            if not any((result.timezone, result.locale, result.ip)):
                continue

            _cache[key] = (time.monotonic(), result)
            logger.debug(
                "GeoIP resolved source=%s ip=%s country=%s timezone=%s locale=%s",
                result.source,
                result.ip,
                result.country_code,
                result.timezone,
                result.locale,
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
    if any((geo.timezone, geo.locale, geo.ip, geo.country_code)):
        resolved["_geoip_result"] = geo.as_dict()
    if timezone:
        resolved["timezone"] = timezone
    elif geo.timezone:
        resolved["timezone"] = geo.timezone

    if locale:
        resolved["locale"] = locale
    elif geo.locale:
        resolved["locale"] = geo.locale

    return resolved
