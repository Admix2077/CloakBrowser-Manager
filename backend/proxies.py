"""Proxy asset helpers shared by database and API layers."""

from __future__ import annotations

from .browser_manager import _normalize_proxy, _redact_proxy_url, _validate_proxy


def normalize_proxy_asset_url(raw: str) -> str:
    value = raw.strip()
    has_explicit_scheme = "://" in value
    has_supported_scheme = value.startswith(("http://", "https://", "socks5://"))
    normalized = value if has_explicit_scheme and not has_supported_scheme else _normalize_proxy(value)
    _validate_proxy(normalized)
    return normalized


def redact_proxy_asset_url(url: str) -> str:
    return _redact_proxy_url(url)
