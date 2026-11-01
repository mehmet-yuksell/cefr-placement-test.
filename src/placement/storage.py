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
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from placement.models import Response, Result

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_DB_PATH = DATA_DIR / "placement.db"
DEFAULT_KEY_PATH = DATA_DIR / "secret.key"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# One lock serialises every use of a connection made through this module.
# Streamlit runs each user session in its own thread and the app shares one
# connection, so statements and transactions must not interleave. WAL mode and
# a busy timeout additionally let separate connections (other processes,
# tools) wait for each other instead of failing with "database is locked".
_DB_LOCK = threading.RLock()
BUSY_TIMEOUT_MS = 5000
F = TypeVar("F", bound=Callable[..., Any])


def _locked(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with _DB_LOCK:
            return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]

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
    engine_json      TEXT,
    resume_token_hash TEXT
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
    changes         INTEGER NOT NULL DEFAULT 0,
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


def new_resume_token() -> str:
    """Random token that lets only the browser that started a test resume it."""
    return secrets.token_urlsafe(18)


def hash_token(token: str) -> str:
    """SHA-256 of a resume token (only the hash is stored)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(row: sqlite3.Row, token: str | None) -> bool:
    """Whether ``token`` is the resume token of the session ``row``."""
    stored = row["resume_token_hash"]
    return bool(token) and stored is not None and hmac.compare_digest(stored, hash_token(token))


def hash_email(email: str, key: bytes) -> str:
    """Keyed hash (HMAC-SHA256) of the normalised email."""
    return hmac.new(key, normalise_email(email).encode("utf-8"), hashlib.sha256).hexdigest()


def connect(path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open (and if needed create) the database."""
    path_str = str(path)
    if path_str != ":memory:":
        Path(path_str).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path_str, check_same_thread=False, timeout=BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    with _DB_LOCK:
        conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
        if path_str != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Bring databases created by older versions up to the current schema."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(responses)")}
    if "changes" not in columns:
        with conn:
            conn.execute("ALTER TABLE responses ADD COLUMN changes INTEGER NOT NULL DEFAULT 0")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
    if "resume_token_hash" not in columns:
        with conn:
            conn.execute("ALTER TABLE sessions ADD COLUMN resume_token_hash TEXT")


@_locked
def mark_abandoned(conn: sqlite3.Connection, user_hash: str) -> int:
    """Mark the user's unfinished sessions as abandoned; return how many."""
    with conn:
        cur = conn.execute(
            "UPDATE sessions SET status = 'abandoned' WHERE user_hash = ? AND status = 'in_progress'",
            (user_hash,),
        )
    return cur.rowcount


@_locked
def next_attempt_no(conn: sqlite3.Connection, user_hash: str) -> int:
    """Attempt number for the user's next session (1 for a new user)."""
    row = conn.execute("SELECT MAX(attempt_no) FROM sessions WHERE user_hash = ?", (user_hash,)).fetchone()
    return (row[0] or 0) + 1


@_locked
def seen_items(conn: sqlite3.Connection, user_hash: str, before_attempt: int | None = None) -> dict[str, int]:
    """Items the user has been shown: item id -> latest attempt number.

    With ``before_attempt``, only attempts numbered below it count (used to
    rebuild a resumed session exactly as it started).
    """
    limit = before_attempt if before_attempt is not None else 2**31
    rows = conn.execute(
        """SELECT r.item_id, MAX(s.attempt_no) FROM responses r
           JOIN sessions s ON s.session_id = r.session_id
           WHERE s.user_hash = ? AND s.attempt_no < ? GROUP BY r.item_id""",
        (user_hash, limit),
    ).fetchall()
    return {item_id: attempt for item_id, attempt in rows}


@_locked
def latest_in_progress(conn: sqlite3.Connection, user_hash: str) -> sqlite3.Row | None:
    """The user's most recent unfinished session, if any."""
    return conn.execute(
        """SELECT * FROM sessions WHERE user_hash = ? AND status = 'in_progress'
           ORDER BY attempt_no DESC LIMIT 1""",
        (user_hash,),
    ).fetchone()


@_locked
def session_answers(conn: sqlite3.Connection, session_id: str) -> list[tuple[str, str]]:
    """(item id, chosen option) for every stored answer of a session, in order."""
    rows = conn.execute(
        "SELECT item_id, chosen_option FROM responses WHERE session_id = ? ORDER BY position",
        (session_id,),
    ).fetchall()
    return [(item_id, chosen) for item_id, chosen in rows]


@_locked
def session_time_spent(conn: sqlite3.Connection, session_id: str) -> float:
    """Total seconds spent on a session's answered items."""
    row = conn.execute("SELECT SUM(response_time_s) FROM responses WHERE session_id = ?", (session_id,)).fetchone()
    return float(row[0] or 0.0)


@_locked
def create_session(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    user_hash: str,
    attempt_no: int,
    mode: str,
    seed: int,
    test_length: int,
    resume_token: str | None = None,
) -> None:
    """Insert a new in-progress session (storing only a hash of the resume token)."""
    stamp = now_iso()
    token_hash = hash_token(resume_token) if resume_token else None
    with conn:
        conn.execute(
            """INSERT INTO sessions (session_id, user_hash, attempt_no, mode, seed, test_length,
                                     status, started_at, last_activity_at, resume_token_hash)
               VALUES (?, ?, ?, ?, ?, ?, 'in_progress', ?, ?, ?)""",
            (session_id, user_hash, attempt_no, mode, seed, test_length, stamp, stamp, token_hash),
        )


@_locked
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


@_locked
def update_response(
    conn: sqlite3.Connection,
    session_id: str,
    position: int,
    chosen_option: str,
    is_correct: bool,
    extra_time_s: float,
) -> None:
    """Change a stored answer in place (the user went back and changed it).

    The time spent on the revisit is added to ``response_time_s``. Exposure is
    not counted again: the item was already shown. Raises KeyError if there
    is no such answer.
    """
    stamp = now_iso()
    with conn:
        cur = conn.execute(
            """UPDATE responses SET chosen_option = ?, is_correct = ?, response_time_s = response_time_s + ?,
                      answered_at = ?, changes = changes + 1
               WHERE session_id = ? AND position = ?""",
            (chosen_option, int(is_correct), max(0.0, extra_time_s), stamp, session_id, position),
        )
        if cur.rowcount != 1:
            raise KeyError(f"no stored answer at position {position} of session {session_id}")
        conn.execute("UPDATE sessions SET last_activity_at = ? WHERE session_id = ?", (stamp, session_id))


@_locked
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


@_locked
def session_row(conn: sqlite3.Connection, session_id: str) -> sqlite3.Row | None:
    """Return a session's row, or None."""
    return conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()


@_locked
def exposure_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """How many times each item has been shown across all sessions."""
    return {row[0]: row[1] for row in conn.execute("SELECT item_id, count FROM item_exposure")}


@_locked
def all_sessions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every session, newest first (for the admin screen and exports)."""
    return conn.execute(
        """SELECT session_id, user_hash, attempt_no, mode, status, started_at, completed_at,
                  level, scaled_score, theta, se, test_length
           FROM sessions ORDER BY started_at DESC, session_id"""
    ).fetchall()


@_locked
def all_responses(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every stored answer, for calibration exports."""
    return conn.execute(
        """SELECT session_id, position, item_id, item_version, stage, chosen_option, is_correct,
                  response_time_s, changes, answered_at
           FROM responses ORDER BY session_id, position"""
    ).fetchall()
