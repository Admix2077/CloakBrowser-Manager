"""Opt-in live verifier for the runtime session and VNC path.

This test intentionally skips by default. It is only for a real CloakBrowser
runtime service that has been provisioned with a safe test profile/template.
"""

from __future__ import annotations

import json
import os
import uuid
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
import pytest
import websockets


if os.environ.get("RUN_LIVE_RUNTIME_WORKSPACE") != "1":
    pytest.skip(
        "Set RUN_LIVE_RUNTIME_WORKSPACE=1 to run the live runtime verifier",
        allow_module_level=True,
    )


_SENSITIVE_RESPONSE_KEYS = {
    "viewer_token_hash",
    "wallet",
    "order",
    "billing",
    "cookie",
    "proxy_password",
    "runtime_service_token",
}


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    pytest.fail(f"Missing required environment variable: {name}")


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
async def test_live_runtime_session_viewer_token_and_vnc_websocket_are_available():
    base_url = _required_env("CLOAKBROWSER_RUNTIME_API_BASE_URL")
    service_token = _required_env("CLOAKBROWSER_RUNTIME_SERVICE_TOKEN")
    external_session_id = f"pm-live-runtime-{uuid.uuid4()}"
    headers = {"X-Runtime-Service-Token": service_token}

    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        create_resp = await client.post(
            "/api/runtime/sessions",
            headers=headers,
            json={
                "external_session_id": external_session_id,
                "lease_seconds": 900,
                **_runtime_profile_source(),
            },
        )
        assert create_resp.status_code == 201
        created = create_resp.json()
        _assert_runtime_session_is_safe(created)
        assert created["external_session_id"] == external_session_id

        get_resp = await client.get(
            f"/api/runtime/sessions/{created['id']}",
            headers=headers,
        )
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        _assert_runtime_session_is_safe(fetched)
        assert fetched == created

        token_resp = await client.post(
            f"/api/runtime/sessions/{created['id']}/viewer-token",
            headers=headers,
            json={"ttl_seconds": 60},
        )
        assert token_resp.status_code == 201
        token_data = token_resp.json()
        assert set(token_data) == {"viewer_url", "viewer_token", "expires_at"}
        assert isinstance(token_data["viewer_token"], str)
        assert token_data["viewer_token"]
        assert token_data["viewer_url"].startswith(
            f"/api/runtime/sessions/{created['id']}/vnc?"
        )
        assert token_data["viewer_token"] in token_data["viewer_url"]
        assert service_token not in json.dumps(
            {"created": created, "fetched": fetched, "token": token_data["viewer_url"]},
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
