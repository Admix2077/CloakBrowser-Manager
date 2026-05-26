"""SQLite database operations for browser profiles."""

from __future__ import annotations

import datetime
import json
import random
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .proxies import normalize_proxy_asset_url

DATA_DIR = Path("/data")
DB_PATH = DATA_DIR / "profiles.db"


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
                last_check_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
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
                last_check_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        "last_check_at",
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
