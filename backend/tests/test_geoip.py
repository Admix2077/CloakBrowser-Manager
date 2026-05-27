"""Tests for GeoIP-based timezone/locale resolution."""

from __future__ import annotations

import httpx
import pytest

from backend import geoip


@pytest.mark.asyncio
async def test_resolve_network_geo_uses_direct_exit_ip(monkeypatch: pytest.MonkeyPatch):
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "status": "success",
                "query": "23.144.4.92",
                "countryCode": "US",
                "timezone": "America/Los_Angeles",
            },
        )

    monkeypatch.setattr(geoip, "_transport_for_tests", httpx.MockTransport(handler))
    geoip.clear_geoip_cache()

    result = await geoip.resolve_network_geo(None)

    assert result.timezone == "America/Los_Angeles"
    assert result.locale == "en-US"
    assert result.ip == "23.144.4.92"
    assert requests[0].url.host == "ip-api.com"


@pytest.mark.asyncio
async def test_resolve_network_geo_uses_proxy_for_lookup(monkeypatch: pytest.MonkeyPatch):
    captured_proxy: list[str | None] = []

    class FakeAsyncClient:
        def __init__(self, *, proxy=None, timeout=None, transport=None):
            captured_proxy.append(proxy)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

        async def get(self, url: str, params: dict[str, str]):
            request = httpx.Request("GET", url, params=params)
            return httpx.Response(
                200,
                request=request,
                json={
                    "status": "success",
                    "query": "203.0.113.10",
                    "countryCode": "JP",
                    "timezone": "Asia/Tokyo",
                },
            )

    monkeypatch.setattr(geoip.httpx, "AsyncClient", FakeAsyncClient)
    geoip.clear_geoip_cache()

    result = await geoip.resolve_network_geo("http://user:pass@proxy.example:8080")

    assert captured_proxy == ["http://user:pass@proxy.example:8080"]
    assert result.timezone == "Asia/Tokyo"
    assert result.locale == "ja-JP"
    assert result.ip == "203.0.113.10"


@pytest.mark.asyncio
async def test_resolve_network_geo_falls_back_when_proxy_client_cannot_start(
    monkeypatch: pytest.MonkeyPatch,
):
    class BrokenAsyncClient:
        def __init__(self, *, proxy=None, timeout=None, transport=None):
            raise ImportError("socksio missing for proxy.example:1080")

    monkeypatch.setattr(geoip.httpx, "AsyncClient", BrokenAsyncClient)
    geoip.clear_geoip_cache()

    result = await geoip.resolve_network_geo("socks5://user:pass@proxy.example:1080")

    assert result == geoip.GeoIPResult(None, None, None, None, "failed")


@pytest.mark.asyncio
async def test_resolve_network_geo_falls_back_to_second_provider(monkeypatch: pytest.MonkeyPatch):
    hosts: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host or "")
        if request.url.host == "ip-api.com":
            return httpx.Response(200, json={"status": "fail", "message": "rate limited"})
        return httpx.Response(
            200,
            json={
                "ip": "198.51.100.25",
                "country_code": "DE",
                "timezone": "Europe/Berlin",
                "languages": "de-DE,en",
            },
        )

    monkeypatch.setattr(geoip, "_transport_for_tests", httpx.MockTransport(handler))
    geoip.clear_geoip_cache()

    result = await geoip.resolve_network_geo(None)

    assert hosts[:2] == ["ip-api.com", "ipapi.co"]
    assert result.source == "ipapi.co"
    assert result.timezone == "Europe/Berlin"
    assert result.locale == "de-DE"
    assert result.ip == "198.51.100.25"


@pytest.mark.asyncio
async def test_resolve_network_geo_falls_back_to_ipwhois_country_locale(
    monkeypatch: pytest.MonkeyPatch,
):
    hosts: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host or "")
        if request.url.host in {"ip-api.com", "ipapi.co"}:
            return httpx.Response(500, json={"error": True})
        return httpx.Response(
            200,
            json={
                "success": True,
                "ip": "203.0.113.20",
                "country_code": "JP",
                "timezone": {"id": "Asia/Tokyo"},
            },
        )

    monkeypatch.setattr(geoip, "_transport_for_tests", httpx.MockTransport(handler))
    geoip.clear_geoip_cache()

    result = await geoip.resolve_network_geo(None)

    assert hosts[:3] == ["ip-api.com", "ipapi.co", "ipwho.is"]
    assert result.source == "ipwho.is"
    assert result.timezone == "Asia/Tokyo"
    assert result.locale == "ja-JP"
    assert result.ip == "203.0.113.20"


@pytest.mark.asyncio
async def test_resolve_profile_network_fingerprint_fills_only_missing_fields(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_resolve(proxy_url: str | None):
        assert proxy_url == "http://proxy.example:8080"
        return geoip.GeoIPResult(
            timezone="Europe/Berlin",
            locale="de-DE",
            ip="198.51.100.25",
            country_code="DE",
            source="test",
        )

    monkeypatch.setattr(geoip, "resolve_network_geo", fake_resolve)

    profile = {
        "proxy": "proxy.example:8080",
        "timezone": "America/New_York",
        "locale": None,
    }

    resolved = await geoip.resolve_profile_network_fingerprint(profile)

    assert resolved["timezone"] == "America/New_York"
    assert resolved["locale"] == "de-DE"
    assert resolved["_geoip_result"]["source"] == "test"
    assert profile["locale"] is None


@pytest.mark.asyncio
async def test_resolve_profile_network_fingerprint_uses_direct_geoip_without_proxy(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_resolve(proxy_url: str | None):
        assert proxy_url is None
        return geoip.GeoIPResult(
            timezone="America/Los_Angeles",
            locale="en-US",
            ip="23.144.4.92",
            country_code="US",
            source="test-direct",
        )

    monkeypatch.setattr(geoip, "resolve_network_geo", fake_resolve)

    resolved = await geoip.resolve_profile_network_fingerprint({
        "geoip": True,
        "proxy": None,
        "timezone": None,
        "locale": None,
    })

    assert resolved["timezone"] == "America/Los_Angeles"
    assert resolved["locale"] == "en-US"
    assert resolved["_geoip_result"] == {
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "ip": "23.144.4.92",
        "country_code": "US",
        "source": "test-direct",
    }


@pytest.mark.asyncio
async def test_resolve_profile_network_fingerprint_keeps_explicit_fields(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_resolve(proxy_url: str | None):
        assert proxy_url is None
        return geoip.GeoIPResult(
            timezone="America/Los_Angeles",
            locale="en-US",
            ip="23.144.4.92",
            country_code="US",
            source="test-direct",
        )

    monkeypatch.setattr(geoip, "resolve_network_geo", fake_resolve)

    profile = {
        "geoip": True,
        "proxy": None,
        "timezone": "Asia/Shanghai",
        "locale": "zh-CN",
    }

    resolved = await geoip.resolve_profile_network_fingerprint(profile)

    assert resolved["timezone"] == "Asia/Shanghai"
    assert resolved["locale"] == "zh-CN"


@pytest.mark.asyncio
async def test_resolve_profile_network_fingerprint_keeps_explicit_fields_but_records_exit_ip(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_resolve(proxy_url: str | None):
        assert proxy_url is None
        return geoip.GeoIPResult(
            timezone="America/Los_Angeles",
            locale="en-US",
            ip="23.144.4.92",
            country_code="US",
            source="test-direct",
        )

    monkeypatch.setattr(geoip, "resolve_network_geo", fake_resolve)

    resolved = await geoip.resolve_profile_network_fingerprint({
        "geoip": True,
        "proxy": None,
        "timezone": "Asia/Shanghai",
        "locale": "zh-CN",
    })

    assert resolved["timezone"] == "Asia/Shanghai"
    assert resolved["locale"] == "zh-CN"
    assert resolved["_geoip_result"] == {
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "ip": "23.144.4.92",
        "country_code": "US",
        "source": "test-direct",
    }


@pytest.mark.asyncio
async def test_resolve_profile_network_fingerprint_honors_disabled_geoip(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fail_if_called(proxy_url: str | None):
        raise AssertionError("GeoIP lookup should not run when geoip is disabled")

    monkeypatch.setattr(geoip, "resolve_network_geo", fail_if_called)

    resolved = await geoip.resolve_profile_network_fingerprint({
        "geoip": False,
        "proxy": None,
        "timezone": None,
        "locale": None,
    })

    assert resolved["timezone"] is None
    assert resolved["locale"] is None


@pytest.mark.asyncio
async def test_resolve_profile_network_fingerprint_falls_back_without_blocking(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_resolve(proxy_url: str | None):
        return geoip.GeoIPResult(
            timezone=None,
            locale=None,
            ip=None,
            country_code=None,
            source="failed",
        )

    monkeypatch.setattr(geoip, "resolve_network_geo", fake_resolve)

    resolved = await geoip.resolve_profile_network_fingerprint({
        "proxy": None,
        "timezone": None,
        "locale": None,
    })

    assert resolved["timezone"] is None
    assert resolved["locale"] is None
