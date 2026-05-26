"""Tests for SQLite CRUD operations."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from backend import database as db


# ── init_db ──────────────────────────────────────────────────────────────────


def test_init_db_creates_tables(tmp_db: Path):
    with db.get_db() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r["name"] for r in tables}
    assert "profiles" in names
    assert "profile_tags" in names
    assert "automation_tasks" in names


def test_init_db_idempotent(tmp_db: Path):
    # Second call should not crash
    db.init_db()
    with db.get_db() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    assert len(tables) >= 2


# ── create_profile ───────────────────────────────────────────────────────────


def test_create_profile_minimal(tmp_db: Path):
    p = db.create_profile("Test")
    assert p["name"] == "Test"
    assert isinstance(p["id"], str) and len(p["id"]) == 36  # UUID
    assert 10000 <= p["fingerprint_seed"] <= 99999  # random default
    assert p["user_data_dir"].startswith(str(tmp_db))
    assert p["platform"] == "windows"
    assert p["created_at"] is not None
    assert p["updated_at"] is not None


def test_create_profile_with_seed(tmp_db: Path):
    p = db.create_profile("Seeded", fingerprint_seed=42)
    assert p["fingerprint_seed"] == 42


def test_create_profile_all_fields(tmp_db: Path):
    p = db.create_profile(
        "Full",
        fingerprint_seed=99999,
        proxy="http://host:8080",
        timezone="America/New_York",
        locale="en-US",
        platform="macos",
        user_agent="Test UA",
        screen_width=2560,
        screen_height=1440,
        gpu_vendor="NVIDIA",
        gpu_renderer="RTX 3070",
        hardware_concurrency=16,
        humanize=True,
        human_preset="careful",
        headless=True,
        geoip=True,
        color_scheme="dark",
        notes="test note",
    )
    assert p["proxy"] == "http://host:8080"
    assert p["platform"] == "macos"
    assert p["gpu_vendor"] == "NVIDIA"
    assert p["hardware_concurrency"] == 16
    assert p["humanize"] == 1  # SQLite stores bool as int
    assert p["human_preset"] == "careful"
    assert p["color_scheme"] == "dark"


def test_create_profile_with_tags(tmp_db: Path):
    p = db.create_profile(
        "Tagged",
        tags=[
            {"tag": "work", "color": "#ff0000"},
            {"tag": "dev", "color": "#00ff00"},
        ],
    )
    assert len(p["tags"]) == 2
    tag_names = {t["tag"] for t in p["tags"]}
    assert tag_names == {"work", "dev"}


def test_create_profile_defaults(tmp_db: Path):
    p = db.create_profile("Defaults")
    assert p["platform"] == "windows"
    assert p["screen_width"] == 1920
    assert p["screen_height"] == 1080
    assert p["humanize"] == 0
    assert p["headless"] == 0
    assert p["geoip"] == 1
    assert p["human_preset"] == "default"
    assert p["launch_args"] == []
    assert p["auto_launch"] == 0
    assert p["last_geoip_ip"] is None
    assert p["last_geoip_timezone"] is None
    assert p["last_geoip_locale"] is None


def test_init_db_enables_geoip_for_legacy_blank_profiles(tmp_db: Path):
    p = db.create_profile("Legacy")
    with db.get_db() as conn:
        conn.execute(
            "UPDATE profiles SET geoip = 0, timezone = NULL, locale = NULL WHERE id = ?",
            (p["id"],),
        )
        conn.commit()

    db.init_db()
    profiles = db.list_profiles()

    assert profiles
    assert profiles[0]["geoip"] == 1


def test_create_profile_with_auto_launch(tmp_db: Path):
    p = db.create_profile("Auto", auto_launch=True)
    assert p["auto_launch"] == 1


def test_update_profile_geoip_result_writes_last_resolved_values(tmp_db: Path):
    p = db.create_profile("GeoIP")

    updated = db.update_profile_geoip_result(
        p["id"],
        {
            "ip": "23.144.4.92",
            "country_code": "US",
            "timezone": "America/Los_Angeles",
            "locale": "en-US",
            "source": "ipapi.co",
        },
    )

    assert updated is not None
    assert updated["timezone"] is None
    assert updated["locale"] is None
    assert updated["last_geoip_ip"] == "23.144.4.92"
    assert updated["last_geoip_country_code"] == "US"
    assert updated["last_geoip_timezone"] == "America/Los_Angeles"
    assert updated["last_geoip_locale"] == "en-US"
    assert updated["last_geoip_source"] == "ipapi.co"
    assert updated["last_geoip_resolved_at"] is not None


def test_create_profile_with_launch_args(tmp_db: Path):
    p = db.create_profile("WithArgs", launch_args=["--load-extension=/tmp/ext", "--disable-features=Foo"])
    assert p["launch_args"] == ["--load-extension=/tmp/ext", "--disable-features=Foo"]


def test_get_profile_launch_args_roundtrip(tmp_db: Path):
    p = db.create_profile("Args", launch_args=["--flag1", "--flag2"])
    fetched = db.get_profile(p["id"])
    assert fetched["launch_args"] == ["--flag1", "--flag2"]


def test_update_profile_launch_args(tmp_db: Path):
    p = db.create_profile("Args")
    assert p["launch_args"] == []
    updated = db.update_profile(p["id"], launch_args=["--new-flag"])
    assert updated["launch_args"] == ["--new-flag"]


def test_update_profile_launch_args_none_becomes_empty(tmp_db: Path):
    p = db.create_profile("Args", launch_args=["--flag"])
    updated = db.update_profile(p["id"], launch_args=None)
    assert updated["launch_args"] == []


def test_list_profiles_includes_launch_args(tmp_db: Path):
    db.create_profile("A", launch_args=["--arg1"])
    db.create_profile("B")
    profiles = db.list_profiles()
    args_by_name = {p["name"]: p["launch_args"] for p in profiles}
    assert args_by_name["A"] == ["--arg1"]
    assert args_by_name["B"] == []


def test_list_profiles_includes_auto_launch(tmp_db: Path):
    db.create_profile("Auto", auto_launch=True)
    db.create_profile("Manual", auto_launch=False)
    profiles = db.list_profiles()
    auto_by_name = {p["name"]: p["auto_launch"] for p in profiles}
    assert auto_by_name == {"Auto": 1, "Manual": 0}


# ── get_profile ──────────────────────────────────────────────────────────────


def test_get_profile_exists(sample_profile: dict):
    p = db.get_profile(sample_profile["id"])
    assert p is not None
    assert p["name"] == "Test Profile"
    assert p["fingerprint_seed"] == 12345


def test_get_profile_not_found(tmp_db: Path):
    assert db.get_profile("nonexistent") is None


def test_get_profile_includes_tags(tmp_db: Path):
    p = db.create_profile("Tagged", tags=[{"tag": "test", "color": "#aaa"}])
    fetched = db.get_profile(p["id"])
    assert len(fetched["tags"]) == 1
    assert fetched["tags"][0]["tag"] == "test"


# ── list_profiles ────────────────────────────────────────────────────────────


def test_list_profiles_empty(tmp_db: Path):
    assert db.list_profiles() == []


def test_list_profiles_ordered(tmp_db: Path):
    db.create_profile("First")
    time.sleep(0.01)  # ensure different timestamps
    db.create_profile("Second")
    profiles = db.list_profiles()
    assert len(profiles) == 2
    assert profiles[0]["name"] == "Second"  # newest first


def test_list_profiles_includes_tags(tmp_db: Path):
    db.create_profile("Tagged", tags=[{"tag": "x"}])
    profiles = db.list_profiles()
    assert len(profiles[0]["tags"]) == 1


# ── automation tasks ─────────────────────────────────────────────────────────


def test_create_and_get_automation_task_roundtrip(tmp_db: Path):
    profile = db.create_profile("Automation Task")
    steps = [
        {"type": "open_url", "url": "https://example.com"},
        {"type": "wait", "ms": 1000},
    ]

    task = db.create_automation_task(profile_id=profile["id"], steps=steps)

    assert task["id"]
    assert task["profile_id"] == profile["id"]
    assert task["status"] == "queued"
    assert task["steps"] == steps
    assert task["result"] is None
    assert task["error"] is None
    assert task["created_at"] is not None
    assert task["started_at"] is None
    assert task["finished_at"] is None

    fetched = db.get_automation_task(task["id"])
    assert fetched == task


def test_update_automation_task_status_result_and_error(tmp_db: Path):
    profile = db.create_profile("Automation Task Update")
    task = db.create_automation_task(profile_id=profile["id"], steps=[{"type": "wait", "ms": 1}])

    updated = db.update_automation_task(
        task["id"],
        status="failed",
        result={"step_index": 0},
        error="step failed",
        started_at="2026-05-27T00:00:00+00:00",
        finished_at="2026-05-27T00:00:01+00:00",
    )

    assert updated is not None
    assert updated["status"] == "failed"
    assert updated["result"] == {"step_index": 0}
    assert updated["error"] == "step failed"
    assert updated["started_at"] == "2026-05-27T00:00:00+00:00"
    assert updated["finished_at"] == "2026-05-27T00:00:01+00:00"


def test_list_automation_tasks_for_profile(tmp_db: Path):
    first_profile = db.create_profile("Automation Task List A")
    second_profile = db.create_profile("Automation Task List B")
    first = db.create_automation_task(profile_id=first_profile["id"], steps=[{"type": "wait", "ms": 1}])
    db.create_automation_task(profile_id=second_profile["id"], steps=[{"type": "wait", "ms": 2}])

    tasks = db.list_automation_tasks(profile_id=first_profile["id"])

    assert [task["id"] for task in tasks] == [first["id"]]


def test_list_automation_tasks_paginates_after_profile_filter(tmp_db: Path):
    first_profile = db.create_profile("Automation Task Page A")
    second_profile = db.create_profile("Automation Task Page B")
    first = db.create_automation_task(profile_id=first_profile["id"], steps=[{"type": "wait", "ms": 1}])
    second = db.create_automation_task(profile_id=first_profile["id"], steps=[{"type": "wait", "ms": 2}])
    third = db.create_automation_task(profile_id=first_profile["id"], steps=[{"type": "wait", "ms": 3}])
    db.create_automation_task(profile_id=second_profile["id"], steps=[{"type": "wait", "ms": 4}])

    tasks = db.list_automation_tasks(profile_id=first_profile["id"], limit=2, offset=1)

    assert [task["id"] for task in tasks] == [second["id"], first["id"]]
    assert third["id"] not in [task["id"] for task in tasks]


# ── update_profile ───────────────────────────────────────────────────────────


def test_update_profile_partial(sample_profile: dict):
    updated = db.update_profile(sample_profile["id"], name="Renamed")
    assert updated["name"] == "Renamed"
    assert updated["fingerprint_seed"] == 12345  # unchanged


def test_update_profile_auto_launch(sample_profile: dict):
    updated = db.update_profile(sample_profile["id"], auto_launch=True)
    assert updated["auto_launch"] == 1


def test_update_profile_tags_replace(tmp_db: Path):
    p = db.create_profile("Tagged", tags=[{"tag": "old"}])
    updated = db.update_profile(p["id"], tags=[{"tag": "new", "color": "#fff"}])
    assert len(updated["tags"]) == 1
    assert updated["tags"][0]["tag"] == "new"


def test_update_profile_not_found(tmp_db: Path):
    assert db.update_profile("nonexistent", name="x") is None


def test_update_profile_no_fields(sample_profile: dict):
    # No-op update — profile should be unchanged
    updated = db.update_profile(sample_profile["id"])
    assert updated["name"] == sample_profile["name"]


def test_update_profile_updates_timestamp(sample_profile: dict):
    time.sleep(0.01)
    updated = db.update_profile(sample_profile["id"], name="New")
    assert updated["updated_at"] > sample_profile["created_at"]


# ── delete_profile ───────────────────────────────────────────────────────────


def test_delete_profile_exists(sample_profile: dict):
    assert db.delete_profile(sample_profile["id"]) is True
    assert db.get_profile(sample_profile["id"]) is None


def test_delete_profile_not_found(tmp_db: Path):
    assert db.delete_profile("nonexistent") is False


def test_delete_profile_cascades_tags(tmp_db: Path):
    p = db.create_profile("Tagged", tags=[{"tag": "a"}, {"tag": "b"}])
    db.delete_profile(p["id"])
    # Verify tags are gone
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM profile_tags WHERE profile_id = ?", (p["id"],)
        ).fetchall()
    assert len(rows) == 0
