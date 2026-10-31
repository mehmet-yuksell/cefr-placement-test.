"""SQLite persistence for sessions, responses and item exposure.

Only a keyed hash of the normalised email is stored, never the email itself.
The key is a random secret created on first use and kept in a local file
outside version control, so the same email always maps to the same id on
this installation. This is pseudonymisation, not anonymisation: anyone with
both the database and the key file could test whether a given email was used.

Every response is written as soon as it is given, so the log survives an
abandoned session and can later be used for item calibration.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from placement.models import Response, Result

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_DB_PATH = DATA_DIR / "placement.db"
DEFAULT_KEY_PATH = DATA_DIR / "secret.key"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id       TEXT PRIMARY KEY,
    user_hash        TEXT NOT NULL,
    attempt_no       INTEGER NOT NULL,
    mode             TEXT NOT NULL,
    seed             INTEGER NOT NULL,
    test_length      INTEGER NOT NULL,
    status           TEXT NOT NULL,
    started_at       TEXT NOT NULL,
    last_activity_at TEXT NOT NULL,
    completed_at     TEXT,
    theta            REAL,
    se               REAL,
    level            TEXT,
    scaled_score     INTEGER,
    flags_json       TEXT NOT NULL DEFAULT '[]',
    engine_json      TEXT
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions (user_hash);
CREATE TABLE IF NOT EXISTS responses (
    session_id      TEXT NOT NULL REFERENCES sessions (session_id),
    position        INTEGER NOT NULL,
    item_id         TEXT NOT NULL,
    item_version    INTEGER NOT NULL,
    stage           INTEGER NOT NULL,
    chosen_option   TEXT NOT NULL,
    is_correct      INTEGER NOT NULL,
    response_time_s REAL NOT NULL,
    answered_at     TEXT NOT NULL,
    PRIMARY KEY (session_id, position)
);
CREATE TABLE IF NOT EXISTS item_exposure (
    item_id TEXT PRIMARY KEY,
    count   INTEGER NOT NULL
);
"""


def now_iso() -> str:
    """Current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def normalise_email(email: str) -> str:
    """Trim and lower-case an email; raise ValueError if it is not plausible."""
    normalised = email.strip().lower()
    if not _EMAIL_RE.match(normalised):
        raise ValueError("not a valid email address")
    return normalised


def load_or_create_key(path: Path = DEFAULT_KEY_PATH) -> bytes:
    """Return the installation's hashing key, creating it on first use."""
    if path.exists():
        return bytes.fromhex(path.read_text(encoding="ascii").strip())
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_bytes(32)
    path.write_text(key.hex(), encoding="ascii")
    return key


def hash_email(email: str, key: bytes) -> str:
    """Keyed hash (HMAC-SHA256) of the normalised email."""
    return hmac.new(key, normalise_email(email).encode("utf-8"), hashlib.sha256).hexdigest()


def connect(path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open (and if needed create) the database."""
    path_str = str(path)
    if path_str != ":memory:":
        Path(path_str).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path_str, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def mark_abandoned(conn: sqlite3.Connection, user_hash: str) -> int:
    """Mark the user's unfinished sessions as abandoned; return how many."""
    with conn:
        cur = conn.execute(
            "UPDATE sessions SET status = 'abandoned' WHERE user_hash = ? AND status = 'in_progress'",
            (user_hash,),
        )
    return cur.rowcount


def next_attempt_no(conn: sqlite3.Connection, user_hash: str) -> int:
    """Attempt number for the user's next session (1 for a new user)."""
    row = conn.execute("SELECT MAX(attempt_no) FROM sessions WHERE user_hash = ?", (user_hash,)).fetchone()
    return (row[0] or 0) + 1


def seen_items(conn: sqlite3.Connection, user_hash: str) -> dict[str, int]:
    """Items the user has been shown: item id -> latest attempt number."""
    rows = conn.execute(
        """SELECT r.item_id, MAX(s.attempt_no) FROM responses r
           JOIN sessions s ON s.session_id = r.session_id
           WHERE s.user_hash = ? GROUP BY r.item_id""",
        (user_hash,),
    ).fetchall()
    return {item_id: attempt for item_id, attempt in rows}


def create_session(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    user_hash: str,
    attempt_no: int,
    mode: str,
    seed: int,
    test_length: int,
) -> None:
    """Insert a new in-progress session."""
    stamp = now_iso()
    with conn:
        conn.execute(
            """INSERT INTO sessions (session_id, user_hash, attempt_no, mode, seed, test_length,
                                     status, started_at, last_activity_at)
               VALUES (?, ?, ?, ?, ?, ?, 'in_progress', ?, ?)""",
            (session_id, user_hash, attempt_no, mode, seed, test_length, stamp, stamp),
        )


def record_response(conn: sqlite3.Connection, session_id: str, response: Response, item_version: int) -> None:
    """Store one answer and count the item's exposure."""
    stamp = now_iso()
    with conn:
        conn.execute(
            """INSERT INTO responses (session_id, position, item_id, item_version, stage,
                                      chosen_option, is_correct, response_time_s, answered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                response.position,
                response.item_id,
                item_version,
                response.stage,
                response.chosen_option,
                int(response.is_correct),
                response.response_time_s,
                stamp,
            ),
        )
        conn.execute(
            """INSERT INTO item_exposure (item_id, count) VALUES (?, 1)
               ON CONFLICT (item_id) DO UPDATE SET count = count + 1""",
            (response.item_id,),
        )
        conn.execute("UPDATE sessions SET last_activity_at = ? WHERE session_id = ?", (stamp, session_id))


def finish_session(
    conn: sqlite3.Connection,
    session_id: str,
    *,
    status: str,
    result: Result | None,
    flags: list[str],
    engine_state: dict[str, Any],
) -> None:
    """Close a session as ``completed`` or ``abandoned`` with its outcome."""
    if status not in ("completed", "abandoned"):
        raise ValueError(f"cannot finish a session as {status!r}")
    with conn:
        conn.execute(
            """UPDATE sessions SET status = ?, completed_at = ?, theta = ?, se = ?, level = ?,
                      scaled_score = ?, flags_json = ?, engine_json = ?
               WHERE session_id = ?""",
            (
                status,
                now_iso(),
                result.theta if result else None,
                result.se if result else None,
                result.level if result else None,
                result.scaled_score if result else None,
                json.dumps(flags),
                json.dumps(engine_state),
                session_id,
            ),
        )


def session_row(conn: sqlite3.Connection, session_id: str) -> sqlite3.Row | None:
    """Return a session's row, or None."""
    return conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()


def exposure_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """How many times each item has been shown across all sessions."""
    return {row[0]: row[1] for row in conn.execute("SELECT item_id, count FROM item_exposure")}
