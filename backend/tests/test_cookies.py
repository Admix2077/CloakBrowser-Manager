"""Tests for cookie import/export format helpers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.cookie_formats import (
    COOKIE_JSON_FORMAT,
    CookieJsonDocument,
    build_cookie_json_export,
    cookie_json_audit_summary,
    cookies_for_playwright,
)


def test_cookie_json_document_accepts_v1_cookie_fields_without_exposing_value_in_repr():
    doc = CookieJsonDocument.model_validate(
        {
            "format": COOKIE_JSON_FORMAT,
            "schema_version": 1,
            "cookies": [
                {
                    "name": "sid",
                    "value": "super-secret-cookie-value",
                    "domain": "example.com",
                    "path": "/app",
                    "expires": 1_893_456_000,
                    "secure": True,
                    "httpOnly": True,
                    "sameSite": "Lax",
                }
            ],
        }
    )

    dumped = doc.model_dump(mode="json", by_alias=True, exclude_none=True)

    assert dumped["format"] == "cloakbrowser.cookie-json.v1"
    assert dumped["schema_version"] == 1
    assert dumped["cookies"][0]["httpOnly"] is True
    assert dumped["cookies"][0]["sameSite"] == "Lax"
    assert dumped["cookies"][0]["value"] == "super-secret-cookie-value"
    assert "super-secret-cookie-value" not in repr(doc)


def test_cookie_json_document_rejects_cookie_without_domain_or_url():
    with pytest.raises(ValidationError, match="domain or url"):
        CookieJsonDocument.model_validate(
            {
                "schema_version": 1,
                "cookies": [
                    {
                        "name": "sid",
                        "value": "super-secret-cookie-value",
                    }
                ],
            }
        )


def test_cookie_json_audit_summary_never_includes_cookie_value_name_or_domain():
    doc = CookieJsonDocument.model_validate(
        {
            "schema_version": 1,
            "cookies": [
                {
                    "name": "sid",
                    "value": "super-secret-cookie-value",
                    "domain": "sensitive.example.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                    "sameSite": "None",
                    "expires": -1,
                },
                {
                    "name": "analytics_id",
                    "value": "another-secret-cookie-value",
                    "url": "https://example.org/account?token=hidden",
                    "expires": 1_893_456_000,
                    "secure": False,
                },
            ],
        }
    )

    summary = cookie_json_audit_summary(doc)

    assert summary == {
        "format": "cloakbrowser.cookie-json.v1",
        "schema_version": 1,
        "cookie_count": 2,
        "domain_scoped_count": 1,
        "url_scoped_count": 1,
        "secure_count": 1,
        "http_only_count": 1,
        "session_cookie_count": 1,
        "persistent_cookie_count": 1,
        "same_site_counts": {"Strict": 0, "Lax": 0, "None": 1, "unset": 1},
    }
    summary_text = str(summary)
    assert "super-secret-cookie-value" not in summary_text
    assert "another-secret-cookie-value" not in summary_text
    assert "sid" not in summary_text
    assert "analytics_id" not in summary_text
    assert "sensitive.example.com" not in summary_text
    assert "token=hidden" not in summary_text


def test_build_cookie_json_export_and_playwright_payload_preserve_cookie_shape():
    doc = build_cookie_json_export(
        [
            {
                "name": "sid",
                "value": "super-secret-cookie-value",
                "domain": "example.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "Strict",
            }
        ],
        profile_id="profile-123",
        exported_at="2026-05-27T00:00:00+00:00",
    )

    exported = doc.model_dump(mode="json", by_alias=True, exclude_none=True)
    playwright_cookies = cookies_for_playwright(doc)

    assert exported["profile_id"] == "profile-123"
    assert exported["exported_at"] == "2026-05-27T00:00:00+00:00"
    assert exported["cookies"][0]["value"] == "super-secret-cookie-value"
    assert playwright_cookies == [
        {
            "name": "sid",
            "value": "super-secret-cookie-value",
            "domain": "example.com",
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "Strict",
        }
    ]
