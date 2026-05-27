"""Tests for profile bulk import and operations APIs."""

from __future__ import annotations

import json

from starlette.testclient import TestClient

from backend import database as db


def _bulk_audit_events() -> list[dict]:
    return [
        event
        for event in db.list_audit_events()
        if event["event_type"].startswith("profile.") and event["event_type"].endswith(("imported", "exported"))
    ]


def _csv_import_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "csv_text": "\n".join(
            [
                "name,proxy,tags,notes,platform,locale,timezone",
                "Confirmed Import,http://user:hiddenpass@import.example:8080,asia,secret-note,linux,ja-JP,Asia/Tokyo",
            ]
        )
    }
    payload.update(overrides)
    return payload


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
    assert _bulk_audit_events() == []


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
            "confirm_import": True,
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


def test_profile_csv_import_requires_explicit_confirmation_without_side_effects(app_client: TestClient):
    for payload in (
        _csv_import_payload(),
        _csv_import_payload(confirm_import=False),
        _csv_import_payload(confirm_import="true"),
    ):
        resp = app_client.post("/api/profiles/import", json=payload)

        assert resp.status_code == 422
        assert resp.json() == {"detail": "Profile import requires explicit confirmation"}
        assert "hiddenpass" not in resp.text
        assert "import.example" not in resp.text
        assert "secret-note" not in resp.text
        assert db.list_profiles() == []
        assert _bulk_audit_events() == []


def test_profile_csv_import_writes_redacted_bulk_audit_event(app_client: TestClient):
    resp = app_client.post(
        "/api/profiles/import",
        json={
            "confirm_import": True,
            "csv_text": "\n".join(
                [
                    "name,proxy,tags,notes,platform,locale,timezone",
                    "Imported Audit,http://user:hiddenpass@audit-import.example:8080,asia,secret-note,linux,ja-JP,Asia/Tokyo",
                    ",http://user:hiddenpass@bad-import.example:8080,bad,Broken row,ios,en-US,America/Chicago",
                ]
            ),
        },
    )

    assert resp.status_code == 200
    events = _bulk_audit_events()
    assert [event["event_type"] for event in events] == ["profile.imported"]
    assert events[0]["actor_type"] == "local_admin"
    assert events[0]["metadata"] == {
        "source_format": "csv",
        "total": 2,
        "created_count": 1,
        "failed_count": 1,
    }
    serialized_event = json.dumps(events[0], sort_keys=True)
    assert "hiddenpass" not in serialized_event
    assert "audit-import.example" not in serialized_event
    assert "bad-import.example" not in serialized_event
    assert "secret-note" not in serialized_event
    assert "Asia/Tokyo" not in serialized_event


def test_profile_csv_import_rejects_headerless_csv_without_creating_profiles(app_client: TestClient):
    resp = app_client.post(
        "/api/profiles/import",
        json={"csv_text": "just-one-cell", "confirm_import": True},
    )

    assert resp.status_code == 422
    assert resp.json()["detail"] == "CSV header with profile columns is required"
    assert db.list_profiles() == []


def test_bulk_export_profile_configs_returns_partial_results(app_client: TestClient):
    first = app_client.post(
        "/api/profiles",
        json={
            "name": "Export A",
            "proxy": "http://user:hiddenpass@export-a.example:8080",
            "platform": "macos",
            "screen_width": 1440,
            "screen_height": 900,
            "gpu_vendor": "Apple",
            "gpu_renderer": "Apple M2",
            "hardware_concurrency": 8,
            "humanize": True,
            "human_preset": "careful",
            "color_scheme": "light",
            "launch_args": ["--private-window"],
            "notes": "Export notes",
            "tags": [{"tag": "export", "color": "#2563eb"}],
        },
    ).json()
    second = app_client.post("/api/profiles", json={"name": "Export B"}).json()

    resp = app_client.post(
        "/api/profiles/export",
        json={"profile_ids": [first["id"], "missing", second["id"]]},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["schema_version"] == 1
    assert data["total"] == 3
    assert data["exported"] == 2
    assert data["failed"] == 1

    first_result, missing_result, second_result = data["results"]
    assert first_result["profile_id"] == first["id"]
    assert first_result["ok"] is True
    assert first_result["error"] is None
    assert first_result["config"]["name"] == "Export A"
    assert first_result["config"]["proxy"] == "http://export-a.example:8080"
    assert first_result["config"]["platform"] == "macos"
    assert first_result["config"]["screen_width"] == 1440
    assert first_result["config"]["screen_height"] == 900
    assert first_result["config"]["gpu_vendor"] == "Apple"
    assert first_result["config"]["gpu_renderer"] == "Apple M2"
    assert first_result["config"]["hardware_concurrency"] == 8
    assert first_result["config"]["humanize"] is True
    assert first_result["config"]["human_preset"] == "careful"
    assert first_result["config"]["color_scheme"] == "light"
    assert first_result["config"]["launch_args"] == ["--private-window"]
    assert first_result["config"]["notes"] == "Export notes"
    assert first_result["config"]["tags"] == [{"tag": "export", "color": "#2563eb"}]
    assert "status" not in first_result["config"]
    assert "automation_url" not in first_result["config"]
    assert "vnc_ws_port" not in first_result["config"]
    assert "user_data_dir" not in first_result["config"]
    assert "hiddenpass" not in resp.text

    assert missing_result == {
        "profile_id": "missing",
        "ok": False,
        "error": "Profile not found",
        "config": None,
    }
    assert second_result["profile_id"] == second["id"]
    assert second_result["ok"] is True
    assert second_result["config"]["name"] == "Export B"


def test_bulk_export_profile_configs_requires_at_least_one_profile_id(app_client: TestClient):
    resp = app_client.post("/api/profiles/export", json={"profile_ids": []})

    assert resp.status_code == 422


def test_bulk_export_profile_configs_writes_redacted_audit_event(app_client: TestClient):
    profile = app_client.post(
        "/api/profiles",
        json={
            "name": "Export Audit",
            "proxy": "http://user:hiddenpass@export-audit.example:8080",
            "notes": "export-secret-note",
        },
    ).json()

    resp = app_client.post(
        "/api/profiles/export",
        json={
            "profile_ids": [profile["id"], "missing"],
            "include_sensitive": True,
            "confirm_sensitive_export": True,
        },
    )

    assert resp.status_code == 200
    events = _bulk_audit_events()
    assert [event["event_type"] for event in events] == ["profile.config_exported"]
    assert events[0]["metadata"] == {
        "source_format": "profile_config_json",
        "schema_version": 1,
        "include_sensitive": True,
        "total": 2,
        "exported_count": 1,
        "failed_count": 1,
    }
    serialized_event = json.dumps(events[0], sort_keys=True)
    assert "hiddenpass" not in serialized_event
    assert "export-audit.example" not in serialized_event
    assert "export-secret-note" not in serialized_event


def test_profile_config_export_can_round_trip_through_config_import(app_client: TestClient):
    created = app_client.post(
        "/api/profiles",
        json={
            "name": "Round Trip Source",
            "proxy": "http://user:hiddenpass@roundtrip.example:8080",
            "platform": "macos",
            "screen_width": 1440,
            "screen_height": 900,
            "tags": [{"tag": "roundtrip", "color": "#0f766e"}],
        },
    ).json()
    exported = app_client.post(
        "/api/profiles/export",
        json={
            "profile_ids": [created["id"]],
            "include_sensitive": True,
            "confirm_sensitive_export": True,
        },
    ).json()

    import_resp = app_client.post(
        "/api/profiles/config/import",
        json={
            "schema_version": exported["schema_version"],
            "confirm_import": True,
            "configs": [exported["results"][0]["config"]],
        },
    )

    assert import_resp.status_code == 200
    data = import_resp.json()
    assert data["imported"] == 1
    imported = data["results"][0]["profile"]
    assert imported["id"] != created["id"]
    assert imported["name"] == "Round Trip Source"
    assert imported["proxy"] == "http://user:hiddenpass@roundtrip.example:8080"
    assert imported["platform"] == "macos"
    assert imported["screen_width"] == 1440
    assert imported["screen_height"] == 900
    assert imported["tags"] == [{"tag": "roundtrip", "color": "#0f766e"}]
    assert imported["status"] == "stopped"


def test_profile_config_import_writes_redacted_bulk_audit_event(app_client: TestClient):
    resp = app_client.post(
        "/api/profiles/config/import",
        json={
            "schema_version": 1,
            "confirm_import": True,
            "configs": [
                {
                    "name": "Config Import Audit",
                    "proxy": "http://user:hiddenpass@config-import.example:8080",
                    "notes": "config-secret-note",
                },
                {
                    "name": "",
                    "proxy": "http://user:hiddenpass@bad-config-import.example:8080",
                    "notes": "bad-config-secret-note",
                },
            ],
        },
    )

    assert resp.status_code == 200
    events = _bulk_audit_events()
    assert [event["event_type"] for event in events] == ["profile.config_imported"]
    assert events[0]["metadata"] == {
        "source_format": "profile_config_json",
        "schema_version": 1,
        "total": 2,
        "created_count": 1,
        "failed_count": 1,
    }
    serialized_event = json.dumps(events[0], sort_keys=True)
    assert "hiddenpass" not in serialized_event
    assert "config-import.example" not in serialized_event
    assert "bad-config-import.example" not in serialized_event
    assert "config-secret-note" not in serialized_event
    assert "bad-config-secret-note" not in serialized_event
