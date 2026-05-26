"""Tests for profile bulk import and operations APIs."""

from __future__ import annotations

from starlette.testclient import TestClient

from backend import database as db


def test_profile_csv_import_preview_applies_template_and_explicit_overrides(app_client: TestClient):
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

    resp = app_client.post(
        "/api/profiles/import/preview",
        json={
            "csv_text": "\n".join(
                [
                    "name,proxy,tags,notes,template,platform,locale,timezone",
                    "Imported A,http://user:hiddenpass@proxy.example:8080,client-a|warmup,Primary row,"
                    f"{template['name']},linux,en-US,America/New_York",
                ]
            ),
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["valid"] == 1
    assert data["invalid"] == 0
    assert "hiddenpass" not in str(data)

    row = data["rows"][0]
    assert row["line_number"] == 2
    assert row["ok"] is True
    assert row["errors"] == []
    assert row["source"]["proxy"] == "http://proxy.example:8080"

    profile = row["profile"]
    assert profile["name"] == "Imported A"
    assert profile["template_id"] == template["id"]
    assert profile["platform"] == "linux"
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
    assert profile["proxy"] == "http://proxy.example:8080"
    assert profile["locale"] == "en-US"
    assert profile["timezone"] == "America/New_York"
    assert profile["notes"] == "Primary row"
    assert profile["tags"] == [
        {"tag": "client-a", "color": None},
        {"tag": "warmup", "color": None},
    ]

    assert app_client.get("/api/profiles").json() == []


def test_profile_csv_import_preview_reports_row_errors_without_blocking_valid_rows(app_client: TestClient):
    template = app_client.post(
        "/api/profile-templates",
        json={"name": "Linux baseline", "platform": "linux"},
    ).json()

    resp = app_client.post(
        "/api/profiles/import/preview",
        json={
            "csv_text": "\n".join(
                [
                    "name,template,platform,locale,timezone",
                    f"Valid row,{template['id']},windows,en-US,America/Chicago",
                    ",missing,ios,en-US,America/Chicago",
                ]
            ),
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["valid"] == 1
    assert data["invalid"] == 1

    valid, invalid = data["rows"]
    assert valid["ok"] is True
    assert valid["profile"]["name"] == "Valid row"
    assert valid["profile"]["template_id"] == template["id"]
    assert valid["profile"]["platform"] == "windows"

    assert invalid["line_number"] == 3
    assert invalid["ok"] is False
    assert invalid["profile"] is None
    assert "name is required" in invalid["errors"]
    assert "Template not found: missing" in invalid["errors"]
    assert "platform must be one of: windows, macos, linux" in invalid["errors"]
    assert app_client.get("/api/profiles").json() == []


def test_profile_csv_import_preview_rejects_empty_or_headerless_csv(app_client: TestClient):
    empty = app_client.post("/api/profiles/import/preview", json={"csv_text": ""})
    assert empty.status_code == 422

    headerless = app_client.post("/api/profiles/import/preview", json={"csv_text": "just-one-cell"})
    assert headerless.status_code == 422
    assert headerless.json()["detail"] == "CSV header with profile columns is required"


def test_profile_csv_import_preview_has_no_database_side_effects(app_client: TestClient):
    app_client.post(
        "/api/profiles/import/preview",
        json={
            "csv_text": "\n".join(
                [
                    "name,proxy,tags,notes,platform,locale,timezone",
                    "Preview Only,http://proxy.example:8080,test,Notes,linux,en-US,America/Chicago",
                ]
            ),
        },
    )

    assert db.list_profiles() == []


def test_profile_csv_import_creates_valid_rows_and_keeps_invalid_row_errors(app_client: TestClient):
    template = app_client.post(
        "/api/profile-templates",
        json={
            "name": "Mac import",
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

    resp = app_client.post(
        "/api/profiles/import",
        json={
            "csv_text": "\n".join(
                [
                    "name,proxy,tags,notes,template,platform,locale,timezone",
                    f"Imported Good,http://user:hiddenpass@jp.proxy.example:8080,asia|warmup,Primary row,{template['name']},linux,ja-JP,Asia/Tokyo",
                    ",http://user:hiddenpass@bad.proxy.example:8080,bad,Broken row,missing,ios,en-US,America/Chicago",
                ]
            ),
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["succeeded"] == 1
    assert data["failed"] == 1

    good, bad = data["results"]
    assert good["line_number"] == 2
    assert good["ok"] is True
    assert good["errors"] == []
    assert good["profile"]["name"] == "Imported Good"
    assert good["profile"]["platform"] == "linux"
    assert good["profile"]["screen_width"] == 1440
    assert good["profile"]["screen_height"] == 900
    assert good["profile"]["gpu_renderer"] == "Apple M2"
    assert good["profile"]["proxy"] == "http://user:hiddenpass@jp.proxy.example:8080"
    assert good["profile"]["locale"] == "ja-JP"
    assert good["profile"]["timezone"] == "Asia/Tokyo"
    assert good["profile"]["tags"] == [
        {"tag": "asia", "color": None},
        {"tag": "warmup", "color": None},
    ]

    assert bad["line_number"] == 3
    assert bad["ok"] is False
    assert bad["profile"] is None
    assert "name is required" in bad["errors"]
    assert "Template not found: missing" in bad["errors"]
    assert "platform must be one of: windows, macos, linux" in bad["errors"]
    assert "hiddenpass" not in str(bad)

    profiles = app_client.get("/api/profiles").json()
    assert [profile["name"] for profile in profiles] == ["Imported Good"]


def test_profile_csv_import_rejects_headerless_csv_without_creating_profiles(app_client: TestClient):
    resp = app_client.post("/api/profiles/import", json={"csv_text": "just-one-cell"})

    assert resp.status_code == 422
    assert resp.json()["detail"] == "CSV header with profile columns is required"
    assert db.list_profiles() == []
