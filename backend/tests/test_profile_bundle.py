"""Tests for profile bundle manifest helpers."""

from __future__ import annotations

from backend.profile_bundle import (
    PROFILE_BUNDLE_FORMAT,
    build_profile_config_bundle,
)


def test_build_profile_config_bundle_defaults_to_safe_manifest_without_sensitive_fields():
    profile = {
        "id": "profile-123",
        "name": "Bundle Source",
        "fingerprint_seed": 424242,
        "proxy": "http://user:super-secret-proxy-password@proxy.example.com:8080",
        "timezone": "America/New_York",
        "locale": "en-US",
        "platform": "macos",
        "user_agent": "Mozilla/5.0",
        "screen_width": 1440,
        "screen_height": 900,
        "gpu_vendor": "Apple",
        "gpu_renderer": "Apple M2",
        "hardware_concurrency": 8,
        "humanize": True,
        "human_preset": "careful",
        "headless": False,
        "geoip": True,
        "clipboard_sync": True,
        "auto_launch": False,
        "color_scheme": "light",
        "launch_args": ["--private-window"],
        "notes": "Bundle notes",
        "tags": [{"tag": "ops", "color": "#2563eb"}],
        "user_data_dir": "/data/profiles/profile-123",
        "status": "running",
        "vnc_ws_port": 5901,
        "automation_url": "http://127.0.0.1:9222",
        "viewer_token": "viewer-token-secret",
        "viewer_token_hash": "viewer-token-hash",
        "runtime_session_id": "runtime-session-secret",
        "lease_owner": "worker-secret",
        "cookies": [{"name": "sid", "value": "super-secret-cookie-value"}],
        "local_storage": [{"key": "token", "value": "local-storage-secret"}],
        "wallet": {"balance": 100},
        "order_id": "order-secret",
        "payment_id": "payment-secret",
        "permission": "admin",
        "audit_events": [{"event": "secret"}],
    }

    bundle = build_profile_config_bundle(
        profile,
        exported_at="2026-05-27T00:00:00+00:00",
        app_version="test-version",
    )
    dumped = bundle.model_dump(mode="json", by_alias=True, exclude_none=True)
    full_dumped = bundle.model_dump(mode="json", by_alias=True)

    assert dumped["format"] == PROFILE_BUNDLE_FORMAT
    assert dumped["schema_version"] == 1
    assert dumped["exported_at"] == "2026-05-27T00:00:00+00:00"
    assert dumped["profile"]["config"] == {
        "name": "Bundle Source",
        "fingerprint_seed": 424242,
        "proxy": "http://proxy.example.com:8080",
        "timezone": "America/New_York",
        "locale": "en-US",
        "platform": "macos",
        "user_agent": "Mozilla/5.0",
        "screen_width": 1440,
        "screen_height": 900,
        "gpu_vendor": "Apple",
        "gpu_renderer": "Apple M2",
        "hardware_concurrency": 8,
        "humanize": True,
        "human_preset": "careful",
        "headless": False,
        "geoip": True,
        "clipboard_sync": True,
        "auto_launch": False,
        "color_scheme": "light",
        "launch_args": ["--private-window"],
        "notes": "Bundle notes",
        "tags": [{"tag": "ops", "color": "#2563eb"}],
    }
    assert dumped["cookies"] == {
        "included": False,
        "format": "cloakbrowser.cookie-json.v1",
        "schema_version": 1,
        "summary": {"cookie_count": 0},
    }
    assert dumped["local_storage"] == {"included": False, "origin_count": 0}
    assert full_dumped["profile_dir"] == {
        "included": False,
        "file_count": 0,
        "total_bytes": 0,
        "excluded_file_count": 0,
        "archive": None,
    }
    assert dumped["metadata"] == {
        "app_name": "cloakbrowser-invisible-manager",
        "app_version": "test-version",
        "source_profile_id": "profile-123",
        "source_profile_name": "Bundle Source",
        "fingerprint_seed_included": True,
        "sensitive_proxy_included": False,
        "cookies_included": False,
        "local_storage_included": False,
        "profile_dir_archive_included": False,
    }

    serialized = str(dumped)
    assert "/data/profiles/profile-123" not in serialized
    assert "super-secret-proxy-password" not in serialized
    assert "viewer-token-secret" not in serialized
    assert "viewer-token-hash" not in serialized
    assert "runtime-session-secret" not in serialized
    assert "worker-secret" not in serialized
    assert "super-secret-cookie-value" not in serialized
    assert "local-storage-secret" not in serialized
    assert "order-secret" not in serialized
    assert "payment-secret" not in serialized
    assert "wallet" not in serialized
    assert "audit_events" not in serialized


def test_build_profile_config_bundle_sanitizes_non_public_fingerprint_seed():
    leak_marker = "bundle-seed-super-secret"
    profile = {
        "id": "profile-123",
        "name": "Bundle Source",
        "fingerprint_seed": f"https://seed.example/profile?token={leak_marker}",
        "proxy": None,
        "timezone": "America/New_York",
        "locale": "en-US",
        "platform": "windows",
        "screen_width": 1920,
        "screen_height": 1080,
        "launch_args": [],
        "tags": [],
    }

    bundle = build_profile_config_bundle(
        profile,
        exported_at="2026-05-27T00:00:00+00:00",
    )
    dumped = bundle.model_dump(mode="json", by_alias=True)

    assert dumped["profile"]["config"]["fingerprint_seed"] == 0
    assert leak_marker not in str(dumped)
    assert "seed.example" not in str(dumped)


def test_build_profile_config_bundle_can_include_sensitive_proxy_only_when_explicit():
    profile = {
        "id": "profile-123",
        "name": "Bundle Source",
        "fingerprint_seed": 424242,
        "proxy": "http://user:super-secret-proxy-password@proxy.example.com:8080",
        "tags": [],
    }

    bundle = build_profile_config_bundle(
        profile,
        exported_at="2026-05-27T00:00:00+00:00",
        include_sensitive_proxy=True,
    )
    dumped = bundle.model_dump(mode="json", by_alias=True, exclude_none=True)

    assert dumped["profile"]["config"]["proxy"] == (
        "http://user:super-secret-proxy-password@proxy.example.com:8080"
    )
    assert dumped["metadata"]["sensitive_proxy_included"] is True


def test_build_profile_config_bundle_repr_does_not_expose_sensitive_proxy_or_cookie_values():
    profile = {
        "id": "profile-123",
        "name": "Bundle Source",
        "fingerprint_seed": 424242,
        "proxy": "http://user:super-secret-proxy-password@proxy.example.com:8080",
        "cookies": [{"name": "sid", "value": "super-secret-cookie-value"}],
        "tags": [],
    }

    bundle = build_profile_config_bundle(
        profile,
        exported_at="2026-05-27T00:00:00+00:00",
    )

    assert "super-secret-proxy-password" not in repr(bundle)
    assert "super-secret-cookie-value" not in repr(bundle)


def test_build_profile_config_bundle_repr_hides_explicit_sensitive_proxy():
    profile = {
        "id": "profile-123",
        "name": "Bundle Source",
        "fingerprint_seed": 424242,
        "proxy": "http://user:super-secret-proxy-password@proxy.example.com:8080",
        "tags": [],
    }

    bundle = build_profile_config_bundle(
        profile,
        exported_at="2026-05-27T00:00:00+00:00",
        include_sensitive_proxy=True,
    )

    assert "super-secret-proxy-password" not in repr(bundle)
