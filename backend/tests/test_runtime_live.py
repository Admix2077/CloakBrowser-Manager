"""Opt-in live verifier for the runtime session and VNC path.

This test intentionally skips by default. It is only for a real CloakBrowser
runtime service that has been provisioned with a safe test profile/template.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
import pytest
import websockets


_SENSITIVE_RESPONSE_KEYS = {
    "viewer_token_hash",
    "wallet",
    "order",
    "billing",
    "cookie",
    "proxy_password",
    "runtime_service_token",
}
_REQUIRED_LIVE_ENV = (
    "CLOAKBROWSER_RUNTIME_API_BASE_URL",
    "CLOAKBROWSER_RUNTIME_SERVICE_TOKEN",
)
_OPTIONAL_POSITIVE_INTEGER_ENV = (
    "CLOAKBROWSER_RUNTIME_LEASE_SECONDS",
    "CLOAKBROWSER_RUNTIME_VIEWER_TOKEN_TTL_SECONDS",
)
_REPORT_ROOT = Path("test-reports")
_REPORT_SENSITIVE_MARKERS = (
    "runtime-service-token-secret",
    "viewer_token",
    "viewer-token",
    "cookie",
    "proxy_password",
    "proxy-password",
    "Authorization",
    "Bearer ",
    "X-Runtime-Service-Token",
)


def _assert_http_api_base_url(value: str | None, name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    parsed = urlsplit(value.strip())
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.path not in {"", "/"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Invalid live runtime environment variable: {name}")


def _assert_optional_positive_integer_env(name: str) -> None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return
    if not value.strip().isdigit() or int(value.strip()) <= 0:
        raise ValueError(f"Invalid live runtime environment variable: {name}")


def _env_presence_status(name: str) -> str:
    return "SET" if os.environ.get(name, "").strip() else "EMPTY"


def _api_base_url_status(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        return "EMPTY"
    try:
        _assert_http_api_base_url(value, name)
    except ValueError:
        return "INVALID"
    return "SET"


def _optional_positive_integer_status(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        return "EMPTY"
    if not value.isdigit() or int(value) <= 0:
        return "INVALID"
    return "SET"


def _runtime_profile_source_status() -> str:
    has_profile = bool(os.environ.get("CLOAKBROWSER_RUNTIME_PROFILE_ID", "").strip())
    has_template = bool(os.environ.get("CLOAKBROWSER_RUNTIME_TEMPLATE_ID", "").strip())
    if has_profile == has_template:
        return "INVALID"
    return "SET"


def _assert_no_sensitive_report_text(text: str) -> None:
    for marker in _REPORT_SENSITIVE_MARKERS:
        assert marker not in text


def _build_runtime_live_not_verified_report() -> str:
    rows = [
        ("CLOAKBROWSER_RUNTIME_API_BASE_URL", _api_base_url_status("CLOAKBROWSER_RUNTIME_API_BASE_URL")),
        ("CLOAKBROWSER_RUNTIME_SERVICE_TOKEN", _env_presence_status("CLOAKBROWSER_RUNTIME_SERVICE_TOKEN")),
        ("CLOAKBROWSER_RUNTIME_PROFILE_SOURCE", _runtime_profile_source_status()),
        (
            "CLOAKBROWSER_RUNTIME_LEASE_SECONDS",
            _optional_positive_integer_status("CLOAKBROWSER_RUNTIME_LEASE_SECONDS"),
        ),
        (
            "CLOAKBROWSER_RUNTIME_VIEWER_TOKEN_TTL_SECONDS",
            _optional_positive_integer_status("CLOAKBROWSER_RUNTIME_VIEWER_TOKEN_TTL_SECONDS"),
        ),
    ]
    lines = [
        "# CloakBrowser Runtime Live Preflight Report",
        "",
        "RUNTIME_LIVE_WORKSPACE_E2E_READY: NOT VERIFIED",
        "RUNTIME_LIVE_WORKSPACE_PREFLIGHT=FAIL",
        "",
        "## Environment Status",
        "",
        *(f"- {name}={status}" for name, status in rows),
        "",
        "## Safety",
        "",
        "- No environment values are written.",
        "- No secret values or raw runtime responses are written.",
    ]
    text = "\n".join(lines) + "\n"
    _assert_no_sensitive_report_text(text)
    return text


def _write_runtime_live_not_verified_report(
    text: str,
    report_root: Path = _REPORT_ROOT,
) -> Path:
    _assert_no_sensitive_report_text(text)
    run_date = datetime.now(timezone.utc).date().isoformat()
    report_dir = report_root / f"{run_date}-runtime-live-preflight"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "REPORT.md"
    report_path.write_text(text)
    return report_path


def _assert_live_runtime_workspace_env() -> None:
    missing = [
        name for name in _REQUIRED_LIVE_ENV if not os.environ.get(name, "").strip()
    ]
    if missing:
        raise ValueError(
            f"Missing live runtime workspace environment variables: {', '.join(missing)}"
        )

    _assert_http_api_base_url(
        os.environ.get("CLOAKBROWSER_RUNTIME_API_BASE_URL"),
        "CLOAKBROWSER_RUNTIME_API_BASE_URL",
    )
    for name in _OPTIONAL_POSITIVE_INTEGER_ENV:
        _assert_optional_positive_integer_env(name)

    profile_id = os.environ.get("CLOAKBROWSER_RUNTIME_PROFILE_ID")
    template_id = os.environ.get("CLOAKBROWSER_RUNTIME_TEMPLATE_ID")
    if bool(profile_id and profile_id.strip()) == bool(template_id and template_id.strip()):
        raise ValueError(
            "Set exactly one of CLOAKBROWSER_RUNTIME_PROFILE_ID or "
            "CLOAKBROWSER_RUNTIME_TEMPLATE_ID"
        )


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    pytest.fail(f"Missing required environment variable: {name}")


def _optional_positive_int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value or not value.strip():
        return default
    return int(value.strip())


def _runtime_profile_source() -> dict[str, str]:
    profile_id = os.environ.get("CLOAKBROWSER_RUNTIME_PROFILE_ID")
    template_id = os.environ.get("CLOAKBROWSER_RUNTIME_TEMPLATE_ID")
    if bool(profile_id) == bool(template_id):
        pytest.fail(
            "Set exactly one of CLOAKBROWSER_RUNTIME_PROFILE_ID or "
            "CLOAKBROWSER_RUNTIME_TEMPLATE_ID"
        )
    if profile_id:
        return {"profile_id": profile_id}
    return {"template_id": template_id or ""}


def test_live_runtime_workspace_env_guard_rejects_invalid_values(monkeypatch: pytest.MonkeyPatch):
    for name in (
        *_REQUIRED_LIVE_ENV,
        *_OPTIONAL_POSITIVE_INTEGER_ENV,
        "CLOAKBROWSER_RUNTIME_PROFILE_ID",
        "CLOAKBROWSER_RUNTIME_TEMPLATE_ID",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("CLOAKBROWSER_RUNTIME_SERVICE_TOKEN", "runtime-service-token-secret")
    monkeypatch.setenv("CLOAKBROWSER_RUNTIME_PROFILE_ID", "profile-live")
    with pytest.raises(ValueError, match="CLOAKBROWSER_RUNTIME_API_BASE_URL"):
        _assert_live_runtime_workspace_env()

    monkeypatch.setenv(
        "CLOAKBROWSER_RUNTIME_API_BASE_URL",
        "https://runtime.example.test?token=leak",
    )
    with pytest.raises(ValueError, match="CLOAKBROWSER_RUNTIME_API_BASE_URL"):
        _assert_live_runtime_workspace_env()

    monkeypatch.setenv("CLOAKBROWSER_RUNTIME_API_BASE_URL", "https://runtime.example.test")
    monkeypatch.setenv("CLOAKBROWSER_RUNTIME_VIEWER_TOKEN_TTL_SECONDS", "0")
    with pytest.raises(ValueError, match="CLOAKBROWSER_RUNTIME_VIEWER_TOKEN_TTL_SECONDS"):
        _assert_live_runtime_workspace_env()

    monkeypatch.setenv("CLOAKBROWSER_RUNTIME_VIEWER_TOKEN_TTL_SECONDS", "60")
    _assert_live_runtime_workspace_env()


def test_runtime_live_env_failure_report_is_low_sensitive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    for name in (
        *_REQUIRED_LIVE_ENV,
        *_OPTIONAL_POSITIVE_INTEGER_ENV,
        "CLOAKBROWSER_RUNTIME_PROFILE_ID",
        "CLOAKBROWSER_RUNTIME_TEMPLATE_ID",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("CLOAKBROWSER_RUNTIME_SERVICE_TOKEN", "runtime-service-token-secret")
    monkeypatch.setenv("CLOAKBROWSER_RUNTIME_API_BASE_URL", "https://runtime.example.test/path")
    monkeypatch.setenv("CLOAKBROWSER_RUNTIME_PROFILE_ID", "profile-live")
    monkeypatch.setenv("CLOAKBROWSER_RUNTIME_TEMPLATE_ID", "template-live")
    monkeypatch.setenv("CLOAKBROWSER_RUNTIME_LEASE_SECONDS", "0")

    report = _write_runtime_live_not_verified_report(
        _build_runtime_live_not_verified_report(),
        report_root=tmp_path,
    )
    text = report.read_text()

    assert report.name == "REPORT.md"
    assert "RUNTIME_LIVE_WORKSPACE_E2E_READY: NOT VERIFIED" in text
    assert "RUNTIME_LIVE_WORKSPACE_PREFLIGHT=FAIL" in text
    assert "CLOAKBROWSER_RUNTIME_API_BASE_URL=INVALID" in text
    assert "CLOAKBROWSER_RUNTIME_SERVICE_TOKEN=SET" in text
    assert "CLOAKBROWSER_RUNTIME_PROFILE_SOURCE=INVALID" in text
    assert "CLOAKBROWSER_RUNTIME_LEASE_SECONDS=INVALID" in text
    assert "runtime-service-token-secret" not in text
    assert "https://runtime.example.test/path" not in text
    assert "profile-live" not in text
    assert "template-live" not in text
    assert "viewer_token" not in text
    assert "cookie" not in text
    assert "proxy_password" not in text


def _absolute_api_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def _websocket_url(base_url: str, viewer_url: str) -> str:
    parsed = urlsplit(_absolute_api_url(base_url, viewer_url))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunsplit((scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _assert_runtime_session_is_safe(data: dict[str, object]) -> None:
    assert {
        "id",
        "profile_id",
        "external_session_id",
        "status",
        "lease_expires_at",
        "created_at",
        "updated_at",
    } <= set(data)
    assert data["status"] == "active"
    serialized = json.dumps(data, sort_keys=True)
    for key in _SENSITIVE_RESPONSE_KEYS:
        assert key not in data
        assert key not in serialized


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_RUNTIME_WORKSPACE") != "1",
    reason="Set RUN_LIVE_RUNTIME_WORKSPACE=1 to run the live runtime verifier",
)
async def test_live_runtime_session_viewer_token_and_vnc_websocket_are_available():
    try:
        _assert_live_runtime_workspace_env()
    except ValueError:
        _write_runtime_live_not_verified_report(_build_runtime_live_not_verified_report())
        raise
    base_url = _required_env("CLOAKBROWSER_RUNTIME_API_BASE_URL")
    service_token = _required_env("CLOAKBROWSER_RUNTIME_SERVICE_TOKEN")
    lease_seconds = _optional_positive_int_env("CLOAKBROWSER_RUNTIME_LEASE_SECONDS", 900)
    viewer_token_ttl_seconds = _optional_positive_int_env(
        "CLOAKBROWSER_RUNTIME_VIEWER_TOKEN_TTL_SECONDS",
        60,
    )
    external_session_id = f"pm-live-runtime-{uuid.uuid4()}"
    headers = {"X-Runtime-Service-Token": service_token}
    created_session_id: str | None = None

    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        try:
            create_resp = await client.post(
                "/api/runtime/sessions",
                headers=headers,
                json={
                    "external_session_id": external_session_id,
                    "lease_seconds": lease_seconds,
                    **_runtime_profile_source(),
                },
            )
            assert create_resp.status_code == 201
            created = create_resp.json()
            _assert_runtime_session_is_safe(created)
            created_session_id = str(created["id"])
            assert created["external_session_id"] == external_session_id

            get_resp = await client.get(
                f"/api/runtime/sessions/{created_session_id}",
                headers=headers,
            )
            assert get_resp.status_code == 200
            fetched = get_resp.json()
            _assert_runtime_session_is_safe(fetched)
            assert fetched == created

            token_resp = await client.post(
                f"/api/runtime/sessions/{created_session_id}/viewer-token",
                headers=headers,
                json={"ttl_seconds": viewer_token_ttl_seconds},
            )
            assert token_resp.status_code == 201
            token_data = token_resp.json()
            assert set(token_data) == {"viewer_url", "viewer_token", "expires_at"}
            assert isinstance(token_data["viewer_token"], str)
            assert token_data["viewer_token"]
            assert token_data["viewer_url"].startswith(
                f"/api/runtime/sessions/{created_session_id}/vnc?"
            )
            assert token_data["viewer_token"] in token_data["viewer_url"]
            assert service_token not in json.dumps(
                {
                    "created": created,
                    "fetched": fetched,
                    "token": token_data["viewer_url"],
                },
                sort_keys=True,
            )

            async with websockets.connect(
                _websocket_url(base_url, token_data["viewer_url"]),
                subprotocols=["binary"],
                open_timeout=15,
                close_timeout=5,
                ping_interval=None,
                compression=None,
            ) as websocket:
                assert websocket.subprotocol in {None, "binary"}
                first_frame = await asyncio.wait_for(websocket.recv(), timeout=10)
                assert isinstance(first_frame, bytes)
                assert first_frame.startswith(b"RFB ")
        finally:
            if created_session_id is not None:
                terminate_resp = await client.post(
                    f"/api/runtime/sessions/{created_session_id}/terminate",
                    headers=headers,
                    json={"confirm_terminate": True},
                )
                assert terminate_resp.status_code == 200
