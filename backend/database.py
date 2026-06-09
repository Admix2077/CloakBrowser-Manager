"""SQLite database operations for browser profiles."""

from __future__ import annotations

import datetime
import ipaddress
import json
import random
import re
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .proxies import normalize_proxy_asset_url

DATA_DIR = Path("/data")
DB_PATH = DATA_DIR / "profiles.db"
_PUBLIC_RUNTIME_SESSION_STATUSES = frozenset({"active", "terminated"})
_PUBLIC_AUTOMATION_TASK_STATUSES = frozenset({
    "cancel_requested",
    "cancelled",
    "failed",
    "queued",
    "running",
    "succeeded",
})


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                fingerprint_seed INTEGER NOT NULL,
                proxy TEXT,
                timezone TEXT,
                locale TEXT,
                platform TEXT DEFAULT 'windows',
                user_agent TEXT,
                screen_width INTEGER DEFAULT 1920,
                screen_height INTEGER DEFAULT 1080,
                gpu_vendor TEXT,
                gpu_renderer TEXT,
                hardware_concurrency INTEGER,
                humanize BOOLEAN DEFAULT 0,
                human_preset TEXT DEFAULT 'default',
                headless BOOLEAN DEFAULT 0,
                geoip BOOLEAN DEFAULT 1,
                clipboard_sync BOOLEAN DEFAULT 1,
                auto_launch BOOLEAN DEFAULT 0,
                color_scheme TEXT,
                last_geoip_ip TEXT,
                last_geoip_country_code TEXT,
                last_geoip_timezone TEXT,
                last_geoip_locale TEXT,
                last_geoip_source TEXT,
                last_geoip_resolved_at TEXT,
                notes TEXT,
                user_data_dir TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS profile_tags (
                profile_id TEXT REFERENCES profiles(id) ON DELETE CASCADE,
                tag TEXT NOT NULL,
                color TEXT,
                PRIMARY KEY (profile_id, tag)
            );

            CREATE TABLE IF NOT EXISTS proxies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                country_code TEXT,
                city TEXT,
                asn TEXT,
                provider TEXT,
                tags TEXT DEFAULT '[]',
                notes TEXT,
                last_check_status TEXT,
                last_check_ip TEXT,
                last_check_country_code TEXT,
                last_check_timezone TEXT,
                last_check_locale TEXT,
                last_check_source TEXT,
                last_check_error TEXT,
                last_check_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS proxy_provider_presets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                provider TEXT,
                country_code TEXT,
                tags TEXT DEFAULT '[]',
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS profile_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT DEFAULT 'windows',
                screen_width INTEGER DEFAULT 1920,
                screen_height INTEGER DEFAULT 1080,
                gpu_vendor TEXT,
                gpu_renderer TEXT,
                hardware_concurrency INTEGER,
                color_scheme TEXT,
                humanize BOOLEAN DEFAULT 0,
                human_preset TEXT DEFAULT 'default',
                launch_args TEXT DEFAULT '[]',
                geoip BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runtime_sessions (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                external_session_id TEXT NOT NULL,
                status TEXT NOT NULL,
                lease_expires_at TEXT NOT NULL,
                viewer_token_hash TEXT,
                viewer_token_expires_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                runtime_session_id TEXT,
                profile_id TEXT,
                external_session_id TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS automation_tasks (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                steps TEXT NOT NULL,
                result TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                lease_owner TEXT,
                lease_expires_at TEXT
            );
        """)
        conn.commit()

        # Migrations for existing databases
        cols = {row[1] for row in conn.execute("PRAGMA table_info(profiles)").fetchall()}
        if "clipboard_sync" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN clipboard_sync BOOLEAN DEFAULT 1")
            conn.commit()
        if "launch_args" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN launch_args TEXT DEFAULT '[]'")
            conn.commit()
        if "auto_launch" not in cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN auto_launch BOOLEAN DEFAULT 0")
            conn.commit()
        for col in (
            "last_geoip_ip",
            "last_geoip_country_code",
            "last_geoip_timezone",
            "last_geoip_locale",
            "last_geoip_source",
            "last_geoip_resolved_at",
        ):
            if col not in cols:
                conn.execute(f"ALTER TABLE profiles ADD COLUMN {col} TEXT")
                conn.commit()
        conn.execute(
            """
            UPDATE profiles
            SET geoip = 1
            WHERE (geoip IS NULL OR geoip = 0)
              AND timezone IS NULL
              AND locale IS NULL
            """
        )
        conn.commit()

        proxy_cols = {row[1] for row in conn.execute("PRAGMA table_info(proxies)").fetchall()}
        if "last_check_error" not in proxy_cols:
            conn.execute("ALTER TABLE proxies ADD COLUMN last_check_error TEXT")
            conn.commit()

        runtime_cols = {row[1] for row in conn.execute("PRAGMA table_info(runtime_sessions)").fetchall()}
        if "viewer_token_expires_at" not in runtime_cols:
            conn.execute("ALTER TABLE runtime_sessions ADD COLUMN viewer_token_expires_at TEXT")
            conn.commit()

        automation_cols = {row[1] for row in conn.execute("PRAGMA table_info(automation_tasks)").fetchall()}
        if "lease_owner" not in automation_cols:
            conn.execute("ALTER TABLE automation_tasks ADD COLUMN lease_owner TEXT")
            conn.commit()
        if "lease_expires_at" not in automation_cols:
            conn.execute("ALTER TABLE automation_tasks ADD COLUMN lease_expires_at TEXT")
            conn.commit()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _decode_tags(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        tags = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(tags, list):
        return []
    return [tag for tag in tags if isinstance(tag, dict)]


def create_profile(
    name: str,
    fingerprint_seed: int | None = None,
    **fields: Any,
) -> dict[str, Any]:
    profile_id = str(uuid.uuid4())
    seed = fingerprint_seed if fingerprint_seed is not None else random.randint(10000, 99999)
    user_data_dir = str(DATA_DIR / "profiles" / profile_id)
    now = _now()
    tags = fields.pop("tags", None) or []

    with get_db() as conn:
        conn.execute(
            """INSERT INTO profiles (
                id, name, fingerprint_seed, proxy, timezone, locale, platform,
                user_agent, screen_width, screen_height, gpu_vendor, gpu_renderer,
                hardware_concurrency, humanize, human_preset, headless, geoip,
                clipboard_sync, auto_launch, color_scheme, launch_args, notes,
                user_data_dir, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                profile_id, name, seed,
                fields.get("proxy"),
                fields.get("timezone"),
                fields.get("locale"),
                fields.get("platform", "windows"),
                fields.get("user_agent"),
                fields.get("screen_width", 1920),
                fields.get("screen_height", 1080),
                fields.get("gpu_vendor"),
                fields.get("gpu_renderer"),
                fields.get("hardware_concurrency"),
                fields.get("humanize", False),
                fields.get("human_preset", "default"),
                fields.get("headless", False),
                fields.get("geoip", True),
                fields.get("clipboard_sync", True),
                fields.get("auto_launch", False),
                fields.get("color_scheme"),
                json.dumps(fields.get("launch_args") or []),
                fields.get("notes"),
                user_data_dir, now, now,
            ),
        )
        for t in tags:
            conn.execute(
                "INSERT INTO profile_tags (profile_id, tag, color) VALUES (?, ?, ?)",
                (profile_id, t["tag"], t.get("color")),
            )
        conn.commit()

    return get_profile(profile_id)  # type: ignore[return-value]


def get_profile(profile_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        if not row:
            return None
        profile = dict(row)
        profile["launch_args"] = json.loads(profile.get("launch_args") or "[]")
        tags = conn.execute(
            "SELECT tag, color FROM profile_tags WHERE profile_id = ?",
            (profile_id,),
        ).fetchall()
        profile["tags"] = [dict(t) for t in tags]
        return profile


def list_profiles() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM profiles ORDER BY created_at DESC").fetchall()
        profiles = []
        for row in rows:
            profile = dict(row)
            profile["launch_args"] = json.loads(profile.get("launch_args") or "[]")
            tags = conn.execute(
                "SELECT tag, color FROM profile_tags WHERE profile_id = ?",
                (profile["id"],),
            ).fetchall()
            profile["tags"] = [dict(t) for t in tags]
            profiles.append(profile)
        return profiles


def count_profiles() -> int:
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM profiles").fetchone()
    return int(row["count"] if row else 0)


def update_profile(profile_id: str, **fields: Any) -> dict[str, Any] | None:
    existing = get_profile(profile_id)
    if not existing:
        return None

    tags = fields.pop("tags", None)

    # Only update fields that were explicitly provided
    update_cols = []
    update_vals = []
    # Pre-serialize launch_args to JSON before the generic update loop
    if "launch_args" in fields:
        fields["launch_args"] = json.dumps(fields["launch_args"] or [])

    for col in (
        "name", "fingerprint_seed", "proxy", "timezone", "locale", "platform",
        "user_agent", "screen_width", "screen_height", "gpu_vendor", "gpu_renderer",
        "hardware_concurrency", "humanize", "human_preset", "headless", "geoip",
        "clipboard_sync", "auto_launch", "color_scheme", "launch_args", "notes",
    ):
        if col in fields:
            update_cols.append(f"{col} = ?")
            update_vals.append(fields[col])

    if update_cols:
        update_cols.append("updated_at = ?")
        update_vals.append(_now())
        update_vals.append(profile_id)
        with get_db() as conn:
            conn.execute(
                f"UPDATE profiles SET {', '.join(update_cols)} WHERE id = ?",
                update_vals,
            )
            conn.commit()

    if tags is not None:
        with get_db() as conn:
            conn.execute("DELETE FROM profile_tags WHERE profile_id = ?", (profile_id,))
            for t in tags:
                conn.execute(
                    "INSERT INTO profile_tags (profile_id, tag, color) VALUES (?, ?, ?)",
                    (profile_id, t["tag"], t.get("color")),
                )
            conn.commit()

    return get_profile(profile_id)


def update_profile_geoip_result(
    profile_id: str,
    result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not result:
        return get_profile(profile_id)

    with get_db() as conn:
        conn.execute(
            """
            UPDATE profiles
            SET last_geoip_ip = ?,
                last_geoip_country_code = ?,
                last_geoip_timezone = ?,
                last_geoip_locale = ?,
                last_geoip_source = ?,
                last_geoip_resolved_at = ?
            WHERE id = ?
            """,
            (
                result.get("ip"),
                result.get("country_code"),
                result.get("timezone"),
                result.get("locale"),
                result.get("source"),
                _now(),
                profile_id,
            ),
        )
        conn.commit()
    return get_profile(profile_id)


def delete_profile(profile_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        conn.commit()
        return cursor.rowcount > 0


def _template_from_row(row: sqlite3.Row) -> dict[str, Any]:
    template = dict(row)
    template["launch_args"] = json.loads(template.get("launch_args") or "[]")
    return template


def create_profile_template(name: str, **fields: Any) -> dict[str, Any]:
    template_id = str(uuid.uuid4())
    now = _now()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO profile_templates (
                id, name, platform, screen_width, screen_height, gpu_vendor,
                gpu_renderer, hardware_concurrency, color_scheme, humanize,
                human_preset, launch_args, geoip, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                template_id,
                name,
                fields.get("platform", "windows"),
                fields.get("screen_width", 1920),
                fields.get("screen_height", 1080),
                fields.get("gpu_vendor"),
                fields.get("gpu_renderer"),
                fields.get("hardware_concurrency"),
                fields.get("color_scheme"),
                fields.get("humanize", False),
                fields.get("human_preset", "default"),
                json.dumps(fields.get("launch_args") or []),
                fields.get("geoip", True),
                now,
                now,
            ),
        )
        conn.commit()

    return get_profile_template(template_id)  # type: ignore[return-value]


def get_profile_template(template_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM profile_templates WHERE id = ?",
            (template_id,),
        ).fetchone()
        return _template_from_row(row) if row else None


def list_profile_templates() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM profile_templates ORDER BY created_at DESC").fetchall()
        return [_template_from_row(row) for row in rows]


def update_profile_template(template_id: str, **fields: Any) -> dict[str, Any] | None:
    if not get_profile_template(template_id):
        return None

    if "launch_args" in fields:
        fields["launch_args"] = json.dumps(fields["launch_args"] or [])

    update_cols = []
    update_vals = []
    for col in (
        "name", "platform", "screen_width", "screen_height", "gpu_vendor",
        "gpu_renderer", "hardware_concurrency", "color_scheme", "humanize",
        "human_preset", "launch_args", "geoip",
    ):
        if col in fields:
            update_cols.append(f"{col} = ?")
            update_vals.append(fields[col])

    if update_cols:
        update_cols.append("updated_at = ?")
        update_vals.append(_now())
        update_vals.append(template_id)
        with get_db() as conn:
            conn.execute(
                f"UPDATE profile_templates SET {', '.join(update_cols)} WHERE id = ?",
                update_vals,
            )
            conn.commit()

    return get_profile_template(template_id)


def delete_profile_template(template_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM profile_templates WHERE id = ?", (template_id,))
        conn.commit()
        return cursor.rowcount > 0


def create_runtime_session(
    *,
    profile_id: str,
    external_session_id: str,
    lease_seconds: int,
    status: str = "active",
    viewer_token_hash: str | None = None,
) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    now = _now()
    lease_expires_at = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(seconds=lease_seconds)
    ).isoformat()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO runtime_sessions (
                id, profile_id, external_session_id, status, lease_expires_at,
                viewer_token_hash, viewer_token_expires_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                profile_id,
                external_session_id,
                status,
                lease_expires_at,
                viewer_token_hash,
                None,
                now,
                now,
            ),
        )
        conn.commit()

    return get_runtime_session(session_id)  # type: ignore[return-value]


def get_runtime_session(session_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM runtime_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def set_runtime_session_viewer_token(
    session_id: str,
    viewer_token_hash: str,
    viewer_token_expires_at: str,
) -> dict[str, Any] | None:
    with get_db() as conn:
        cursor = conn.execute(
            """UPDATE runtime_sessions
            SET viewer_token_hash = ?, viewer_token_expires_at = ?, updated_at = ?
            WHERE id = ?""",
            (viewer_token_hash, viewer_token_expires_at, _now(), session_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_runtime_session(session_id)


def count_runtime_sessions_by_status() -> dict[str, int]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM runtime_sessions GROUP BY status",
        ).fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row["status"] or "unknown")
        public_status = status if status in _PUBLIC_RUNTIME_SESSION_STATUSES else "unknown"
        counts[public_status] = counts.get(public_status, 0) + int(row["count"])
    return counts


def count_live_runtime_sessions(now: str | None = None) -> int:
    cutoff = now or datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS count FROM runtime_sessions
            WHERE status = ? AND lease_expires_at > ?""",
            ("active", cutoff),
        ).fetchone()
    return int(row["count"] or 0) if row else 0


def count_active_runtime_viewer_tokens(now: str | None = None) -> int:
    cutoff = now or datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS count FROM runtime_sessions
            WHERE status = ?
              AND viewer_token_hash IS NOT NULL
              AND viewer_token_expires_at IS NOT NULL
              AND viewer_token_expires_at > ?""",
            ("active", cutoff),
        ).fetchone()
    return int(row["count"] or 0) if row else 0


def terminate_runtime_session(session_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        cursor = conn.execute(
            """UPDATE runtime_sessions
            SET status = ?, viewer_token_hash = NULL, viewer_token_expires_at = NULL, updated_at = ?
            WHERE id = ?""",
            ("terminated", _now(), session_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_runtime_session(session_id)


def renew_runtime_session(session_id: str, lease_seconds: int) -> dict[str, Any] | None:
    now = _now()
    lease_expires_at = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(seconds=lease_seconds)
    ).isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            """UPDATE runtime_sessions
            SET lease_expires_at = ?, updated_at = ?
            WHERE id = ?""",
            (lease_expires_at, now, session_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_runtime_session(session_id)


def _automation_task_from_row(row: sqlite3.Row) -> dict[str, Any]:
    task = dict(row)
    try:
        steps = json.loads(task.get("steps") or "[]")
    except (TypeError, ValueError):
        steps = []
    try:
        result = json.loads(task["result"]) if task.get("result") is not None else None
    except (TypeError, ValueError):
        result = None
    task["steps"] = steps if isinstance(steps, list) else []
    task["result"] = result
    return task


def create_automation_task(
    *,
    profile_id: str,
    steps: list[dict[str, Any]],
    status: str = "queued",
) -> dict[str, Any]:
    task_id = str(uuid.uuid4())
    now = _now()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO automation_tasks (
                id, profile_id, status, steps, result, error, created_at, started_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                profile_id,
                status,
                json.dumps(steps),
                None,
                None,
                now,
                None,
                None,
            ),
        )
        conn.commit()
    task = get_automation_task(task_id)
    if task is None:
        raise RuntimeError("Automation task was not persisted")
    return task


def get_automation_task(task_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM automation_tasks WHERE id = ?", (task_id,)).fetchone()
    return _automation_task_from_row(row) if row else None


def list_automation_tasks(
    profile_id: str | None = None,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    pagination_clause = ""
    pagination_args: list[Any] = []
    if limit is not None:
        pagination_clause = " LIMIT ? OFFSET ?"
        pagination_args = [limit, offset]
    with get_db() as conn:
        if profile_id:
            rows = conn.execute(
                f"SELECT * FROM automation_tasks WHERE profile_id = ? ORDER BY created_at DESC{pagination_clause}",
                (profile_id, *pagination_args),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM automation_tasks ORDER BY created_at DESC{pagination_clause}",
                pagination_args,
            ).fetchall()
    return [_automation_task_from_row(row) for row in rows]


def count_automation_tasks_by_status() -> dict[str, int]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM automation_tasks GROUP BY status",
        ).fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row["status"] or "unknown")
        public_status = status if status in _PUBLIC_AUTOMATION_TASK_STATUSES else "unknown"
        counts[public_status] = counts.get(public_status, 0) + int(row["count"])
    return counts


def update_automation_task(
    task_id: str,
    *,
    status: str | None = None,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict[str, Any] | None:
    update_cols = []
    update_vals: list[Any] = []
    if status is not None:
        update_cols.append("status = ?")
        update_vals.append(status)
    if result is not None:
        update_cols.append("result = ?")
        update_vals.append(json.dumps(result))
    if error is not None:
        update_cols.append("error = ?")
        update_vals.append(error)
    if started_at is not None:
        update_cols.append("started_at = ?")
        update_vals.append(started_at)
    if finished_at is not None:
        update_cols.append("finished_at = ?")
        update_vals.append(finished_at)
    if not update_cols:
        return get_automation_task(task_id)

    update_vals.append(task_id)
    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE automation_tasks SET {', '.join(update_cols)} WHERE id = ?",
            update_vals,
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_automation_task(task_id)


def _lease_expires_at(now: str | None, lease_seconds: int) -> tuple[str, str]:
    if now is None:
        current = datetime.datetime.now(datetime.timezone.utc)
    else:
        current = datetime.datetime.fromisoformat(now)
        if current.tzinfo is None:
            current = current.replace(tzinfo=datetime.timezone.utc)
    return current.isoformat(), (current + datetime.timedelta(seconds=lease_seconds)).isoformat()


def claim_next_automation_task(
    *,
    lease_owner: str,
    lease_seconds: int,
    now: str | None = None,
) -> dict[str, Any] | None:
    now_value, lease_expires_at = _lease_expires_at(now, lease_seconds)
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT task.*
            FROM automation_tasks AS task
            WHERE (
                task.status = 'running'
                AND task.lease_expires_at IS NOT NULL
                AND task.lease_expires_at <= ?
            ) OR (
                task.status = 'queued'
                AND NOT EXISTS (
                    SELECT 1
                    FROM automation_tasks AS active
                    WHERE active.profile_id = task.profile_id
                      AND active.id != task.id
                      AND active.status IN ('running', 'cancel_requested')
                      AND (
                          active.status = 'cancel_requested'
                          OR active.lease_expires_at IS NULL
                          OR active.lease_expires_at > ?
                      )
                )
            )
            ORDER BY
                CASE WHEN task.status = 'running' THEN 0 ELSE 1 END,
                task.created_at ASC
            LIMIT 1
            """,
            (now_value, now_value),
        ).fetchone()
        if row is None:
            conn.commit()
            return None

        cursor = conn.execute(
            """
            UPDATE automation_tasks
            SET status = 'running',
                lease_owner = ?,
                lease_expires_at = ?,
                started_at = COALESCE(started_at, ?),
                finished_at = NULL
            WHERE id = ?
              AND (
                  status = 'queued'
                  OR (
                      status = 'running'
                      AND lease_expires_at IS NOT NULL
                      AND lease_expires_at <= ?
                  )
              )
            """,
            (lease_owner, lease_expires_at, now_value, row["id"], now_value),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_automation_task(row["id"])


def renew_automation_task_lease(
    task_id: str,
    *,
    lease_owner: str,
    lease_seconds: int,
    now: str | None = None,
    allowed_statuses: set[str] | None = None,
) -> dict[str, Any] | None:
    statuses = allowed_statuses or {"running"}
    if not statuses:
        return None
    now_value, lease_expires_at = _lease_expires_at(now, lease_seconds)
    placeholders = ", ".join("?" for _ in statuses)
    with get_db() as conn:
        cursor = conn.execute(
            f"""
            UPDATE automation_tasks
            SET lease_expires_at = ?
            WHERE id = ?
              AND lease_owner = ?
              AND status IN ({placeholders})
            """,
            (lease_expires_at, task_id, lease_owner, *sorted(statuses)),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_automation_task(task_id)


def finish_claimed_automation_task(
    task_id: str,
    *,
    lease_owner: str,
    status: str,
    result: dict[str, Any] | None,
    error: str | None,
    now: str | None = None,
    allowed_statuses: set[str] | None = None,
) -> dict[str, Any] | None:
    if status not in {"cancelled", "failed", "succeeded"}:
        return None
    source_statuses = allowed_statuses or {"running"}
    if not source_statuses:
        return None
    placeholders = ", ".join("?" for _ in source_statuses)
    finished_at, _ = _lease_expires_at(now, 0)
    with get_db() as conn:
        cursor = conn.execute(
            f"""
            UPDATE automation_tasks
            SET status = ?,
                result = ?,
                error = ?,
                finished_at = ?,
                lease_owner = NULL,
                lease_expires_at = NULL
            WHERE id = ?
              AND lease_owner = ?
              AND status IN ({placeholders})
            """,
            (
                status,
                json.dumps(result) if result is not None else None,
                error,
                finished_at,
                task_id,
                lease_owner,
                *sorted(source_statuses),
            ),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_automation_task(task_id)


_AUDIT_SENSITIVE_KEYS = {
    "access-token",
    "access_token",
    "api-key",
    "api_key",
    "authorization",
    "auth-token",
    "auth_token",
    "client-secret",
    "client_secret",
    "cookie",
    "cookies",
    "private-key",
    "private_key",
    "proxy_url",
    "refresh-token",
    "refresh_token",
    "runtime-service-token",
    "runtime_service_token",
    "service-token",
    "service_token",
    "session-id",
    "session_id",
    "token",
    "viewer-token",
    "viewer_token",
    "viewer_token_hash",
    "viewer_url",
    "x-api-key",
    "x_api_key",
}

_AUDIT_SENSITIVE_KEY_PARTS = ("cookie", "password", "secret")
_AUDIT_PROXY_URL_RE = re.compile(r"\b(?:http|https|socks5)://[^\s\"'<>]+", re.IGNORECASE)
_AUDIT_AUTHORIZATION_RE = re.compile(
    r"\bAuthorization\s*[:=]\s*(?:Bearer\s+)?[A-Za-z0-9._~+/\-=]+",
    re.IGNORECASE,
)
_AUDIT_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"\b(access[_-]?token|api[_-]?key|auth[_-]?token|client[_-]?secret|cookie|password|"
    r"private[_-]?key|refresh[_-]?token|runtime[_-]?service[_-]?token|secret|"
    r"service[_-]?token|session[_-]?id|token|viewer[_-]?token|x[_-]?api[_-]?key)"
    r"\s*[:=]\s*([^\s&#,;]+)",
    re.IGNORECASE,
)
_AUDIT_SENSITIVE_MARKER_RE = re.compile(
    r"\b(?:access[_-]?token|api[_-]?key|auth[_-]?token|client[_-]?secret|private[_-]?key|"
    r"refresh[_-]?token|runtime[_-]?service[_-]?token|service[_-]?token|session[_-]?id|"
    r"viewer[_-]?token|x[_-]?api[_-]?key)(?!\s*[:=])[A-Za-z0-9_.-]*\b",
    re.IGNORECASE,
)
_AUDIT_BEARER_TOKEN_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/\-=]+", re.IGNORECASE)
_AUDIT_LOCAL_PATH_RE = re.compile(
    r"(?:/(?:data|tmp|home)/|(?<![A-Za-z0-9])[A-Za-z]:[\\/])[^\s\"'<>),;]+",
    re.IGNORECASE,
)
_AUDIT_IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_AUDIT_BRACKETED_IP_RE = re.compile(r"\[([0-9A-Fa-f:.%]+)\]")
_AUDIT_IPV6_RE = re.compile(
    r"(?<![A-Za-z0-9:.])(?:[0-9A-Fa-f]{0,4}:){2,}[0-9A-Fa-f:.%]*(?![A-Za-z0-9:.])"
)
_AUDIT_SENSITIVE_KEY_RE = re.compile(
    r"https?://|socks[45]://|[/\\?&#@]|"
    r"\b(?:authorization|bearer)\b|"
    r"\b(?:access[_-]?token|api[_-]?key|auth[_-]?token|client[_-]?secret|cookie|"
    r"password|passwd|private[_-]?key|refresh[_-]?token|runtime[_-]?service[_-]?token|"
    r"secret|service[_-]?token|session[_-]?id|token|viewer[_-]?token|"
    r"x[_-]?api[_-]?key)\s*[:=]",
    re.IGNORECASE,
)
_PUBLIC_AUDIT_EVENT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){0,8}$")
_SENSITIVE_AUDIT_EVENT_TYPE_SEGMENT_RE = re.compile(
    r"(?:^|\.)(?:access_?token|api_?key|auth_?token|client_?secret|private_?key|"
    r"refresh_?token|runtime_?service_?token|service_?token|session_?id|viewer_?token|"
    r"x_?api_?key)(?:\.|$)",
    re.IGNORECASE,
)
_PUBLIC_AUDIT_EVENT_TYPE_EXCEPTIONS = frozenset({"runtime.viewer_token.created"})
_PUBLIC_AUDIT_ACTOR_TYPES = frozenset({"local_admin", "runtime_service", "runtime_viewer"})
_PUBLIC_AUDIT_EXTERNAL_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SENSITIVE_AUDIT_EXTERNAL_SESSION_ID_RE = re.compile(
    r"https?://|socks[45]://|@|[/?#=:]|\b(authorization|bearer)\b|"
    r"\b(access[_.-]?token|api[_.-]?key|auth[_.-]?token|client[_.-]?secret|private[_.-]?key|"
    r"refresh[_.-]?token|runtime[_.-]?service[_.-]?token|service[_.-]?token|"
    r"session[_.-]?id|viewer[_.-]?token|x[_.-]?api[_.-]?key)(?=$|[^A-Za-z0-9])|"
    r"\b(auth[_.-]?token|password|cookie|secret|token|viewer[_.-]?token)\s*=",
    re.IGNORECASE,
)


def _is_sensitive_audit_key(key: str) -> bool:
    normalized = key.lower()
    normalized_alias = normalized.replace("-", "_")
    return (
        normalized in _AUDIT_SENSITIVE_KEYS
        or normalized_alias in _AUDIT_SENSITIVE_KEYS
        or normalized_alias.endswith("_token")
        or normalized_alias.endswith("_token_hash")
        or _AUDIT_SENSITIVE_KEY_RE.search(key) is not None
        or _redact_audit_ip_literals(key) != key
        or any(
            part in normalized_alias for part in _AUDIT_SENSITIVE_KEY_PARTS
        )
    )


def _public_audit_url_label(url: str) -> str:
    try:
        parsed = urlsplit(url)
    except ValueError:
        scheme = url.split("://", 1)[0].lower()
        if scheme in {"http", "https", "socks5"}:
            return f"{scheme}://unknown"
        return "unknown"
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https", "socks5"} or not parsed.netloc:
        return url
    host = parsed.hostname or ""
    if not host:
        return f"{scheme}://unknown"
    host_part = f"[{host}]" if ":" in host and not host.startswith("[") else host
    try:
        port = parsed.port
    except ValueError:
        port = None
    port_part = f":{port}" if port else ""
    path_part = "" if parsed.path == "/" else parsed.path
    return f"{scheme}://{host_part}{port_part}{path_part}"


def _sanitize_audit_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if _is_sensitive_audit_key(str(key)):
                continue
            sanitized[key] = _sanitize_audit_metadata(item)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [_sanitize_audit_metadata(item) for item in value]
    if isinstance(value, str):
        sanitized = _AUDIT_PROXY_URL_RE.sub(
            lambda match: _public_audit_url_label(match.group(0)),
            value,
        )
        sanitized = _AUDIT_AUTHORIZATION_RE.sub("Authorization=[redacted]", sanitized)
        sanitized = _AUDIT_SENSITIVE_ASSIGNMENT_RE.sub(
            lambda match: f"{match.group(1)}=[redacted]",
            sanitized,
        )
        sanitized = _AUDIT_SENSITIVE_MARKER_RE.sub("[redacted]", sanitized)
        sanitized = _AUDIT_BEARER_TOKEN_RE.sub("Bearer [redacted]", sanitized)
        sanitized = _AUDIT_LOCAL_PATH_RE.sub("[redacted-path]", sanitized)
        return _redact_audit_ip_literals(sanitized)
    return value


def _redact_audit_ip_literals(value: str) -> str:
    sanitized = _AUDIT_BRACKETED_IP_RE.sub(
        lambda match: "[redacted-ip]" if _is_ip_literal(match.group(1)) else match.group(0),
        value,
    )
    sanitized = _AUDIT_IPV4_RE.sub(
        lambda match: "[redacted-ip]" if _is_ip_literal(match.group(0)) else match.group(0),
        sanitized,
    )
    return _AUDIT_IPV6_RE.sub(
        lambda match: "[redacted-ip]" if _is_ip_literal(match.group(0)) else match.group(0),
        sanitized,
    )


def _is_ip_literal(value: str) -> bool:
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError:
        return False
    return parsed.version in {4, 6}


def _public_uuid_identifier(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = uuid.UUID(text)
    except ValueError:
        return None
    return str(parsed)


def _public_audit_event_type(value: object) -> str:
    if not isinstance(value, str) or not _PUBLIC_AUDIT_EVENT_TYPE_RE.fullmatch(value):
        return "unknown"
    if (
        value not in _PUBLIC_AUDIT_EVENT_TYPE_EXCEPTIONS
        and _SENSITIVE_AUDIT_EVENT_TYPE_SEGMENT_RE.search(value)
    ):
        return "unknown"
    return value


def _public_audit_actor_type(value: object) -> str:
    if isinstance(value, str) and value in _PUBLIC_AUDIT_ACTOR_TYPES:
        return value
    return "unknown"


def _public_audit_external_session_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if not _PUBLIC_AUDIT_EXTERNAL_SESSION_ID_RE.fullmatch(text):
        return None
    if _SENSITIVE_AUDIT_EXTERNAL_SESSION_ID_RE.search(text):
        return None
    return text


def _public_audit_created_at(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    text = value.strip()
    if not text:
        return "unknown"
    try:
        datetime.datetime.fromisoformat(text)
    except ValueError:
        return "unknown"
    return text


def create_audit_event(
    *,
    event_type: str,
    actor_type: str,
    runtime_session_id: str | None = None,
    profile_id: str | None = None,
    external_session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event_id = str(uuid.uuid4())
    now = _now()
    sanitized_metadata = _sanitize_audit_metadata(metadata or {})
    with get_db() as conn:
        conn.execute(
            """INSERT INTO audit_events (
                id, event_type, actor_type, runtime_session_id, profile_id,
                external_session_id, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                event_type,
                actor_type,
                runtime_session_id,
                profile_id,
                external_session_id,
                json.dumps(sanitized_metadata, sort_keys=True),
                now,
            ),
        )
        conn.commit()
    event = get_audit_event(event_id)
    if event is None:
        raise RuntimeError("Audit event was not persisted")
    return event


def _audit_event_from_row(row: sqlite3.Row) -> dict[str, Any]:
    event = dict(row)
    try:
        metadata = json.loads(event.get("metadata") or "{}")
    except (TypeError, ValueError):
        metadata = {}
    event["id"] = _public_uuid_identifier(event.get("id")) or "unknown"
    event["event_type"] = _public_audit_event_type(event.get("event_type"))
    event["actor_type"] = _public_audit_actor_type(event.get("actor_type"))
    event["runtime_session_id"] = _public_uuid_identifier(event.get("runtime_session_id"))
    event["profile_id"] = _public_uuid_identifier(event.get("profile_id"))
    event["external_session_id"] = _public_audit_external_session_id(event.get("external_session_id"))
    event["created_at"] = _public_audit_created_at(event.get("created_at"))
    event["metadata"] = _sanitize_audit_metadata(metadata if isinstance(metadata, dict) else {})
    return event


def get_audit_event(event_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
    return _audit_event_from_row(row) if row else None


def list_audit_events(runtime_session_id: str | None = None) -> list[dict[str, Any]]:
    with get_db() as conn:
        if runtime_session_id:
            rows = conn.execute(
                "SELECT * FROM audit_events WHERE runtime_session_id = ? ORDER BY created_at ASC",
                (runtime_session_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM audit_events ORDER BY created_at ASC").fetchall()
    return [_audit_event_from_row(row) for row in rows]


def _proxy_from_row(row: sqlite3.Row) -> dict[str, Any]:
    proxy = dict(row)
    proxy["tags"] = _decode_tags(proxy.get("tags"))
    return proxy


def create_proxy(
    name: str,
    url: str,
    **fields: Any,
) -> dict[str, Any]:
    proxy_id = str(uuid.uuid4())
    now = _now()
    normalized_url = normalize_proxy_asset_url(url)
    tags = fields.get("tags") or []

    with get_db() as conn:
        conn.execute(
            """INSERT INTO proxies (
                id, name, url, country_code, city, asn, provider, tags, notes,
                last_check_status, last_check_ip, last_check_country_code,
                last_check_timezone, last_check_locale, last_check_source,
                last_check_error, last_check_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                proxy_id,
                name,
                normalized_url,
                fields.get("country_code"),
                fields.get("city"),
                fields.get("asn"),
                fields.get("provider"),
                json.dumps(tags),
                fields.get("notes"),
                fields.get("last_check_status"),
                fields.get("last_check_ip"),
                fields.get("last_check_country_code"),
                fields.get("last_check_timezone"),
                fields.get("last_check_locale"),
                fields.get("last_check_source"),
                fields.get("last_check_error"),
                fields.get("last_check_at"),
                now,
                now,
            ),
        )
        conn.commit()

    return get_proxy(proxy_id)  # type: ignore[return-value]


def list_proxies() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM proxies ORDER BY created_at DESC").fetchall()
    return [_proxy_from_row(row) for row in rows]


def count_proxies() -> int:
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM proxies").fetchone()
    return int(row["count"] if row else 0)


def get_proxy(proxy_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM proxies WHERE id = ?", (proxy_id,)).fetchone()
    if not row:
        return None
    return _proxy_from_row(row)


def update_proxy(proxy_id: str, **fields: Any) -> dict[str, Any] | None:
    if not get_proxy(proxy_id):
        return None

    update_cols = []
    update_vals = []
    if "url" in fields:
        fields["url"] = normalize_proxy_asset_url(fields["url"])
    if "tags" in fields:
        fields["tags"] = json.dumps(fields["tags"] or [])

    for col in (
        "name", "url", "country_code", "city", "asn", "provider", "tags", "notes",
        "last_check_status", "last_check_ip", "last_check_country_code",
        "last_check_timezone", "last_check_locale", "last_check_source",
        "last_check_error", "last_check_at",
    ):
        if col in fields:
            update_cols.append(f"{col} = ?")
            update_vals.append(fields[col])

    if update_cols:
        update_cols.append("updated_at = ?")
        update_vals.append(_now())
        update_vals.append(proxy_id)
        with get_db() as conn:
            conn.execute(
                f"UPDATE proxies SET {', '.join(update_cols)} WHERE id = ?",
                update_vals,
            )
            conn.commit()

    return get_proxy(proxy_id)


def delete_proxy(proxy_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM proxies WHERE id = ?", (proxy_id,))
        conn.commit()
        return cursor.rowcount > 0


def _proxy_provider_preset_from_row(row: sqlite3.Row) -> dict[str, Any]:
    preset = dict(row)
    preset["tags"] = _decode_tags(preset.get("tags"))
    return preset


def create_proxy_provider_preset(name: str, **fields: Any) -> dict[str, Any]:
    preset_id = str(uuid.uuid4())
    now = _now()
    tags = fields.get("tags") or []

    with get_db() as conn:
        conn.execute(
            """INSERT INTO proxy_provider_presets (
                id, name, provider, country_code, tags, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                preset_id,
                name,
                fields.get("provider"),
                fields.get("country_code"),
                json.dumps(tags),
                fields.get("notes"),
                now,
                now,
            ),
        )
        conn.commit()

    return get_proxy_provider_preset(preset_id)  # type: ignore[return-value]


def list_proxy_provider_presets() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM proxy_provider_presets ORDER BY created_at DESC"
        ).fetchall()
    return [_proxy_provider_preset_from_row(row) for row in rows]


def get_proxy_provider_preset(preset_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM proxy_provider_presets WHERE id = ?",
            (preset_id,),
        ).fetchone()
    if not row:
        return None
    return _proxy_provider_preset_from_row(row)


def update_proxy_provider_preset(preset_id: str, **fields: Any) -> dict[str, Any] | None:
    if not get_proxy_provider_preset(preset_id):
        return None

    update_cols = []
    update_vals = []
    if "tags" in fields:
        fields["tags"] = json.dumps(fields["tags"] or [])

    for col in ("name", "provider", "country_code", "tags", "notes"):
        if col in fields:
            update_cols.append(f"{col} = ?")
            update_vals.append(fields[col])

    if update_cols:
        update_cols.append("updated_at = ?")
        update_vals.append(_now())
        update_vals.append(preset_id)
        with get_db() as conn:
            conn.execute(
                f"UPDATE proxy_provider_presets SET {', '.join(update_cols)} WHERE id = ?",
                update_vals,
            )
            conn.commit()

    return get_proxy_provider_preset(preset_id)


def delete_proxy_provider_preset(preset_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM proxy_provider_presets WHERE id = ?",
            (preset_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
