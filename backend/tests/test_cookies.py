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
    build_netscape_cookie_export,
    netscape_cookie_audit_summary,
    parse_netscape_cookies,
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


def test_cookies_for_playwright_uses_url_or_domain_path_shape():
    doc = CookieJsonDocument.model_validate(
        {
            "schema_version": 1,
            "cookies": [
                {
                    "name": "url_cookie",
                    "value": "url-cookie-value",
                    "url": "https://app.example.test/account?token=hidden",
                    "path": "/ignored-for-playwright-url-scope",
                    "secure": True,
                    "sameSite": "Lax",
                },
                {
                    "name": "domain_cookie",
                    "value": "domain-cookie-value",
                    "domain": ".example.test",
                    "path": "/account",
                    "httpOnly": True,
                },
            ],
        }
    )

    playwright_cookies = cookies_for_playwright(doc)

    assert playwright_cookies == [
        {
            "name": "url_cookie",
            "value": "url-cookie-value",
            "url": "https://app.example.test/account?token=hidden",
            "secure": True,
            "httpOnly": False,
            "sameSite": "Lax",
        },
        {
            "name": "domain_cookie",
            "value": "domain-cookie-value",
            "domain": ".example.test",
            "path": "/account",
            "secure": False,
            "httpOnly": True,
        },
    ]


def test_parse_netscape_cookies_to_cookie_json_without_leaking_values_in_summary():
    text = "\n".join(
        [
            "# Netscape HTTP Cookie File",
            ".sensitive.example.com\tTRUE\t/\tTRUE\t1893456000\tsid\tsuper-secret-cookie-value",
            "example.org\tFALSE\t/account\tFALSE\t0\tanalytics_id\tanother-secret-cookie-value",
        ]
    )

    doc = parse_netscape_cookies(text, profile_id="profile-123", exported_at="2026-05-27T00:00:00+00:00")
    dumped = doc.model_dump(mode="json", by_alias=True, exclude_none=True)

    assert dumped["format"] == COOKIE_JSON_FORMAT
    assert dumped["schema_version"] == 1
    assert dumped["profile_id"] == "profile-123"
    assert dumped["exported_at"] == "2026-05-27T00:00:00+00:00"
    assert dumped["cookies"] == [
        {
            "name": "sid",
            "value": "super-secret-cookie-value",
            "domain": ".sensitive.example.com",
            "path": "/",
            "expires": 1_893_456_000,
            "secure": True,
            "httpOnly": False,
        },
        {
            "name": "analytics_id",
            "value": "another-secret-cookie-value",
            "domain": "example.org",
            "path": "/account",
            "expires": 0,
            "secure": False,
            "httpOnly": False,
        },
    ]
    summary = netscape_cookie_audit_summary(doc)
    assert summary == {
        "format": "netscape-cookie-file",
        "cookie_count": 2,
        "secure_count": 1,
        "session_cookie_count": 1,
        "persistent_cookie_count": 1,
        "http_only_count": 0,
    }
    summary_text = str(summary)
    assert "super-secret-cookie-value" not in summary_text
    assert "another-secret-cookie-value" not in summary_text
    assert "sid" not in summary_text
    assert "analytics_id" not in summary_text
    assert "sensitive.example.com" not in summary_text


def test_parse_netscape_cookies_rejects_malformed_line_without_echoing_payload():
    text = "sensitive.example.com\tTRUE\t/\tTRUE\t1893456000\tsid"

    with pytest.raises(ValueError) as excinfo:
        parse_netscape_cookies(text)

    message = str(excinfo.value)
    assert message == "Invalid Netscape cookie line 1"
    assert "sensitive.example.com" not in message
    assert "sid" not in message


def test_build_netscape_cookie_export_preserves_supported_cookie_shape():
    doc = CookieJsonDocument.model_validate(
        {
            "schema_version": 1,
            "cookies": [
                {
                    "name": "sid",
                    "value": "super-secret-cookie-value",
                    "domain": ".example.com",
                    "path": "/",
                    "expires": 1_893_456_000,
                    "secure": True,
                },
                {
                    "name": "session",
                    "value": "session-secret",
                    "url": "https://app.example.org/dashboard?token=hidden",
                    "path": "/dashboard",
                    "secure": False,
                    "httpOnly": True,
                },
            ],
        }
    )

    text = build_netscape_cookie_export(doc)

    assert text.splitlines() == [
        "# Netscape HTTP Cookie File",
        ".example.com\tTRUE\t/\tTRUE\t1893456000\tsid\tsuper-secret-cookie-value",
        "#HttpOnly_app.example.org\tFALSE\t/dashboard\tFALSE\t0\tsession\tsession-secret",
    ]
    assert "token=hidden" not in text
