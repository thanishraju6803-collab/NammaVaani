from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DB_PATH
from .pipeline import new_ticket_id


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS farmer_profiles (
                profile_id TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                profile_json TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                language TEXT NOT NULL,
                reporter_alias TEXT,
                village TEXT NOT NULL,
                equipment TEXT NOT NULL,
                problem TEXT NOT NULL,
                duration TEXT,
                specification TEXT,
                operating_condition TEXT,
                description TEXT,
                priority TEXT NOT NULL DEFAULT 'Normal',
                status TEXT NOT NULL DEFAULT 'New',
                technician TEXT,
                transcript TEXT,
                confirmation_text TEXT,
                source_mode TEXT NOT NULL DEFAULT 'demo'
            )"""
        )
        conn.commit()


def create_ticket(data: dict[str, Any]) -> str:
    ticket_id = new_ticket_id()
    created_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """INSERT INTO tickets (
                ticket_id, created_at, language, reporter_alias, village, equipment,
                problem, duration, specification, operating_condition, description,
                priority, status, technician, transcript, confirmation_text, source_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'New', NULL, ?, ?, ?)""",
            (
                ticket_id, created_at, data.get("language", "Kannada"), data.get("reporter_alias", ""),
                data["village"], data["equipment"], data["problem"], data.get("duration"),
                data.get("specification"), data.get("operating_condition"), data.get("description"),
                data.get("priority", "Normal"), data.get("transcript", ""),
                data.get("confirmation_text", ""), data.get("source_mode", "demo"),
            ),
        )
        conn.commit()
    return ticket_id


def list_tickets() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_ticket(ticket_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
    return dict(row) if row else None


def update_ticket(ticket_id: str, status: str, technician: str | None, operator_note: str | None = None) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE tickets SET status = ?, technician = ?, description = COALESCE(?, description) WHERE ticket_id = ?",
            (status, technician, operator_note, ticket_id),
        )
        conn.commit()


# A local single-user profile is suitable for the competition prototype.
# A production deployment must add farmer authentication and per-user access control.
def get_farmer_profile(profile_id: str = "pilot-farmer") -> dict[str, Any]:
    import json

    defaults: dict[str, Any] = {
        "location": "Bengaluru, Karnataka, India",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "taluk": "",
        "hobli": "",
        "village": "",
        "land_acres": None,
        "soil_type": None,
        "irrigation": None,
        "current_crop": None,
        "sowing_date": None,
        "preferred_language": "kn",
        "latitude": None,
        "longitude": None,
        "gps_consent": False,
    }
    with _connect() as conn:
        row = conn.execute(
            "SELECT profile_json FROM farmer_profiles WHERE profile_id = ?", (profile_id,)
        ).fetchone()
    if not row:
        return defaults
    try:
        saved = json.loads(row["profile_json"])
    except (TypeError, ValueError):
        return defaults
    return {**defaults, **saved}


def save_farmer_profile(profile: dict[str, Any], profile_id: str = "pilot-farmer") -> None:
    import json

    updated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            "INSERT INTO farmer_profiles(profile_id, updated_at, profile_json) VALUES (?, ?, ?) "
            "ON CONFLICT(profile_id) DO UPDATE SET updated_at=excluded.updated_at, profile_json=excluded.profile_json",
            (profile_id, updated_at, json.dumps(profile, ensure_ascii=False)),
        )
        conn.commit()
