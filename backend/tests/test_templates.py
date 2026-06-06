"""Tests for profile template storage and API."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from starlette.testclient import TestClient

from backend import database as db


def test_init_db_creates_profile_templates_table(tmp_db: Path):
    with db.get_db() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {row["name"] for row in tables}
    assert "profile_templates" in names


def test_profile_template_crud_roundtrips_fingerprint_fields(tmp_db: Path):
    template = db.create_profile_template(
        name="Amazon US warmup",
        platform="macos",
        screen_width=1440,
        screen_height=900,
        gpu_vendor="Apple",
        gpu_renderer="Apple M2",
        hardware_concurrency=8,
        color_scheme="light",
        humanize=True,
        human_preset="careful",
        launch_args=["--private-window"],
        geoip=True,
    )

    assert template["id"]
    assert template["name"] == "Amazon US warmup"
    assert template["platform"] == "macos"
    assert template["screen_width"] == 1440
    assert template["screen_height"] == 900
    assert template["gpu_vendor"] == "Apple"
    assert template["gpu_renderer"] == "Apple M2"
    assert template["hardware_concurrency"] == 8
    assert template["color_scheme"] == "light"
    assert template["humanize"] == 1
    assert template["human_preset"] == "careful"
    assert template["launch_args"] == ["--private-window"]
    assert template["geoip"] == 1
    assert template["created_at"] is not None
    assert template["updated_at"] is not None

    listed = db.list_profile_templates()
    assert [item["id"] for item in listed] == [template["id"]]

    updated = db.update_profile_template(
        template["id"],
        name="Amazon US steady",
        launch_args=["--private-window", "--lang=en-US"],
        gpu_renderer=None,
    )
    assert updated is not None
    assert updated["name"] == "Amazon US steady"
    assert updated["launch_args"] == ["--private-window", "--lang=en-US"]
    assert updated["gpu_renderer"] is None

    assert db.delete_profile_template(template["id"]) is True
    assert db.get_profile_template(template["id"]) is None
    assert db.delete_profile_template(template["id"]) is False


def test_updating_template_does_not_modify_existing_profiles(tmp_db: Path):
    template = db.create_profile_template(
        name="Mac light",
        platform="macos",
        screen_width=1440,
        screen_height=900,
        color_scheme="light",
    )
    profile = db.create_profile(
        name="Created from copied settings",
        platform=template["platform"],
        screen_width=template["screen_width"],
        screen_height=template["screen_height"],
        color_scheme=template["color_scheme"],
    )

    db.update_profile_template(
        template["id"],
        platform="linux",
        screen_width=1920,
        screen_height=1080,
        color_scheme="dark",
    )

    unchanged = db.get_profile(profile["id"])
    assert unchanged is not None
    assert unchanged["platform"] == "macos"
    assert unchanged["screen_width"] == 1440
    assert unchanged["screen_height"] == 900
    assert unchanged["color_scheme"] == "light"


def test_profile_template_crud_api(app_client: TestClient):
    create = app_client.post(
        "/api/profile-templates",
        json={
            "name": "Retail US",
            "platform": "linux",
            "screen_width": 1366,
            "screen_height": 768,
            "hardware_concurrency": 4,
            "color_scheme": "dark",
            "humanize": True,
            "human_preset": "careful",
            "launch_args": ["--private-window"],
            "geoip": False,
        },
    )
    assert create.status_code == 201
    data = create.json()
    assert data["id"]
    assert data["name"] == "Retail US"
    assert data["platform"] == "linux"
    assert data["launch_args"] == ["--private-window"]
    assert data["geoip"] is False

    listed = app_client.get("/api/profile-templates")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [data["id"]]

    update = app_client.put(
        f"/api/profile-templates/{data['id']}",
        json={
            "name": "Retail US steady",
            "launch_args": ["--private-window", "--lang=en-US"],
        },
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Retail US steady"
    assert update.json()["launch_args"] == ["--private-window", "--lang=en-US"]

    get = app_client.get(f"/api/profile-templates/{data['id']}")
    assert get.status_code == 200
    assert get.json()["name"] == "Retail US steady"

    delete = app_client.request(
        "DELETE",
        f"/api/profile-templates/{data['id']}",
        json={"confirm_delete": True},
    )
    assert delete.status_code == 200
    assert delete.json() == {"ok": True}
    assert app_client.get(f"/api/profile-templates/{data['id']}").status_code == 404


def test_profile_template_api_sanitizes_persisted_identity_fields(app_client: TestClient):
    leak_marker = "template-response-leak-marker"
    template = db.create_profile_template(
        name="Historical polluted response template",
        platform=f"linux-{leak_marker}",
        screen_width=f"1920\nAuthorization: Bearer {leak_marker}",
        screen_height=f"1080?token={leak_marker}",
        gpu_vendor=f"Google Inc. (NVIDIA)\nAuthorization: Bearer {leak_marker}",
        gpu_renderer=f"ANGLE (NVIDIA) https://gpu.invalid/?token={leak_marker}",
        hardware_concurrency=f"8 cookie={leak_marker}",
        color_scheme=f"dark-{leak_marker}",
        human_preset=f"careful-{leak_marker}",
        launch_args=[
            "--private-window",
            f"--user-agent={leak_marker}",
            f"Bearer {leak_marker}",
            "--runtime=runtime_service_token_template_response_marker",
            "--service=service_token_template_response_marker",
        ],
    )

    detail = app_client.get(f"/api/profile-templates/{template['id']}")
    listed = app_client.get("/api/profile-templates")

    assert detail.status_code == 200
    assert listed.status_code == 200
    for data in (detail.json(), listed.json()[0]):
        assert data["platform"] == "windows"
        assert data["screen_width"] == 1920
        assert data["screen_height"] == 1080
        assert data["gpu_vendor"] is None
        assert data["gpu_renderer"] is None
        assert data["hardware_concurrency"] is None
        assert data["color_scheme"] is None
        assert data["human_preset"] == "default"
        assert data["launch_args"] == ["--private-window"]
        serialized = json.dumps(data, sort_keys=True)
        assert leak_marker not in serialized
        assert "runtime_service_token_template_response_marker" not in serialized
        assert "service_token_template_response_marker" not in serialized


def test_profile_template_api_and_import_preview_sanitize_persisted_template_id(
    app_client: TestClient,
):
    leak_marker = "template-id-secret"
    template = db.create_profile_template(
        name="Historical polluted template id",
        platform="linux",
    )
    polluted_template_id = (
        f"template-id {leak_marker} "
        f"token={leak_marker} Authorization=Bearer {leak_marker}"
    )
    with db.get_db() as conn:
        conn.execute(
            "UPDATE profile_templates SET id = ? WHERE id = ?",
            (polluted_template_id, template["id"]),
        )
        conn.commit()

    encoded_template_id = quote(polluted_template_id, safe="")
    detail = app_client.get(f"/api/profile-templates/{encoded_template_id}")
    listed = app_client.get("/api/profile-templates")
    update = app_client.put(
        f"/api/profile-templates/{encoded_template_id}",
        json={"screen_width": 1366},
    )
    preview = app_client.post(
        "/api/profiles/import/preview",
        json={
            "csv_text": "\n".join(
                [
                    "name,template",
                    "Imported from polluted template id,Historical polluted template id",
                ]
            ),
        },
    )

    assert detail.status_code == 200
    assert listed.status_code == 200
    assert update.status_code == 200
    assert preview.status_code == 200

    listed_template = next(
        template
        for template in listed.json()
        if template["name"] == "Historical polluted template id"
    )
    for response in (detail.json(), listed_template, update.json()):
        assert response["id"] == "unknown"
        assert response["platform"] == "linux"

    preview_row = preview.json()["rows"][0]
    assert preview_row["ok"] is True
    assert preview_row["profile"]["template_id"] == "unknown"
    assert preview_row["profile"]["platform"] == "linux"

    serialized = json.dumps(
        {
            "template_responses": [detail.json(), listed_template, update.json()],
            "preview": preview.json(),
        },
        sort_keys=True,
    )
    for leaked in (
        leak_marker,
        "Authorization",
        "Bearer",
        "token=",
    ):
        assert leaked not in serialized


def test_profile_template_api_sanitizes_persisted_timestamp_fields(
    app_client: TestClient,
):
    template = db.create_profile_template(
        name="Historical template timestamps",
        platform="linux",
    )
    leak_marker = "template-timestamp-secret"
    with db.get_db() as conn:
        conn.execute(
            """UPDATE profile_templates
               SET created_at = ?, updated_at = ?
               WHERE id = ?""",
            (
                f"created Authorization=Bearer {leak_marker}",
                f"https://template.example/updated?token={leak_marker}",
                template["id"],
            ),
        )
        conn.commit()

    detail = app_client.get(f"/api/profile-templates/{template['id']}")
    listed = app_client.get("/api/profile-templates")

    assert detail.status_code == 200
    assert listed.status_code == 200
    for data in (detail.json(), listed.json()[0]):
        assert data["created_at"] == "unknown"
        assert data["updated_at"] == "unknown"
        serialized = json.dumps(data, sort_keys=True)
        for leaked in (leak_marker, "Authorization", "Bearer", "template.example"):
            assert leaked not in serialized


def test_delete_profile_template_requires_explicit_confirmation_without_side_effects(
    app_client: TestClient,
):
    create = app_client.post(
        "/api/profile-templates",
        json={
            "name": "Retail US",
            "platform": "linux",
            "screen_width": 1366,
            "screen_height": 768,
        },
    )
    assert create.status_code == 201
    template_id = create.json()["id"]

    for payload in ({}, {"confirm_delete": False}, {"confirm_delete": "true"}):
        resp = app_client.request(
            "DELETE",
            f"/api/profile-templates/{template_id}",
            json=payload,
        )
        assert resp.status_code == 422
        assert resp.json() == {
            "detail": "Profile template delete requires explicit confirmation"
        }

    get = app_client.get(f"/api/profile-templates/{template_id}")
    assert get.status_code == 200
    assert get.json()["id"] == template_id


def test_create_profile_from_template_copies_template_fields(app_client: TestClient):
    template = app_client.post(
        "/api/profile-templates",
        json={
            "name": "Mac warmup",
            "platform": "macos",
            "screen_width": 1440,
            "screen_height": 900,
            "gpu_vendor": "Apple",
            "gpu_renderer": "Apple M2",
            "hardware_concurrency": 8,
            "color_scheme": "light",
            "humanize": True,
            "human_preset": "careful",
            "launch_args": ["--private-window"],
            "geoip": False,
        },
    ).json()

    create = app_client.post(
        "/api/profiles",
        json={"name": "From template", "template_id": template["id"]},
    )

    assert create.status_code == 201
    profile = create.json()
    assert profile["name"] == "From template"
    assert profile["platform"] == "macos"
    assert profile["screen_width"] == 1440
    assert profile["screen_height"] == 900
    assert profile["gpu_vendor"] == "Apple"
    assert profile["gpu_renderer"] == "Apple M2"
    assert profile["hardware_concurrency"] == 8
    assert profile["color_scheme"] == "light"
    assert profile["humanize"] is True
    assert profile["human_preset"] == "careful"
    assert profile["launch_args"] == ["--private-window"]
    assert profile["geoip"] is False


def test_create_profile_from_template_sanitizes_persisted_identity_fields(app_client: TestClient):
    leak_marker = "template-identity-leak-marker"
    template = db.create_profile_template(
        name="Historical polluted template",
        platform=f"linux-{leak_marker}",
        screen_width=f"1920\nAuthorization: Bearer {leak_marker}",
        screen_height=f"1080?token={leak_marker}",
        gpu_vendor=f"Google Inc. (NVIDIA)\nAuthorization: Bearer {leak_marker}",
        gpu_renderer=f"ANGLE (NVIDIA) https://gpu.invalid/?token={leak_marker}",
        hardware_concurrency=f"8 cookie={leak_marker}",
        color_scheme=f"dark-{leak_marker}",
        human_preset=f"careful-{leak_marker}",
        launch_args=[
            "--private-window",
            f"--user-agent={leak_marker}",
            f"Bearer {leak_marker}",
        ],
    )

    create = app_client.post(
        "/api/profiles",
        json={"name": "From polluted template", "template_id": template["id"]},
    )

    assert create.status_code == 201
    profile = create.json()
    assert profile["platform"] == "windows"
    assert profile["screen_width"] == 1920
    assert profile["screen_height"] == 1080
    assert profile["gpu_vendor"] is None
    assert profile["gpu_renderer"] is None
    assert profile["hardware_concurrency"] is None
    assert profile["color_scheme"] is None
    assert profile["human_preset"] == "default"
    assert profile["launch_args"] == ["--private-window"]
    assert leak_marker not in json.dumps(profile, sort_keys=True)


def test_create_profile_template_fields_can_be_overridden(app_client: TestClient):
    template = app_client.post(
        "/api/profile-templates",
        json={
            "name": "Default Linux",
            "platform": "linux",
            "screen_width": 1366,
            "screen_height": 768,
            "launch_args": ["--template"],
        },
    ).json()

    create = app_client.post(
        "/api/profiles",
        json={
            "name": "Override template",
            "template_id": template["id"],
            "platform": "windows",
            "screen_width": 1920,
            "screen_height": 1080,
            "launch_args": ["--profile"],
        },
    )

    assert create.status_code == 201
    profile = create.json()
    assert profile["platform"] == "windows"
    assert profile["screen_width"] == 1920
    assert profile["screen_height"] == 1080
    assert profile["launch_args"] == ["--profile"]


def test_create_profile_from_missing_template_returns_404(app_client: TestClient):
    create = app_client.post(
        "/api/profiles",
        json={"name": "Missing template", "template_id": "missing"},
    )

    assert create.status_code == 404
    assert create.json()["detail"] == "Profile template not found"


def test_profile_template_api_not_found(app_client: TestClient):
    assert app_client.get("/api/profile-templates/missing").status_code == 404
    assert app_client.put("/api/profile-templates/missing", json={"name": "x"}).status_code == 404
    assert app_client.request(
        "DELETE",
        "/api/profile-templates/missing",
        json={"confirm_delete": True},
    ).status_code == 404
