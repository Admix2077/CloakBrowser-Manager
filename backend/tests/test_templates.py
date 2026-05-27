"""Tests for profile template storage and API."""

from __future__ import annotations

from pathlib import Path

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
