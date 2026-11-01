"""Pure helpers for the admin screen: table rows and CSV exports.

The database never holds an email address, only its keyed hash, so nothing
here can reveal one. The on-screen table shortens the hash further.
"""

from __future__ import annotations

import csv
import io
import sqlite3
from collections.abc import Iterable, Mapping

from placement.i18n import t

HASH_PREFIX = 10
SESSION_COLUMNS = ("session_id", "user_hash", "attempt_no", "mode", "status", "started_at", "completed_at",
                   "level", "scaled_score", "theta", "se", "test_length")
RESPONSE_COLUMNS = ("session_id", "position", "item_id", "item_version", "stage", "chosen_option", "is_correct",
                    "response_time_s", "changes", "answered_at")


def session_table(rows: Iterable[sqlite3.Row], lang: str) -> list[dict[str, object]]:
    """Rows for the on-screen session list (hash shortened, localised headers)."""
    return [
        {
            t("col_user", lang): f"{row['user_hash'][:HASH_PREFIX]}…",
            t("col_started", lang): row["started_at"],
            t("col_attempt", lang): row["attempt_no"],
            t("col_status", lang): row["status"],
            t("col_level", lang): row["level"] or "–",
            t("col_score", lang): row["scaled_score"] if row["scaled_score"] is not None else "–",
        }
        for row in rows
    ]


def exposure_table(counts: Mapping[str, int], n_sessions: int, item_ids: Iterable[str],
                   lang: str) -> list[dict[str, object]]:
    """How often each item was shown, most exposed first (unused items included)."""
    rows = [(item_id, counts.get(item_id, 0)) for item_id in item_ids]
    rows.sort(key=lambda r: (-r[1], r[0]))
    return [
        {
            t("col_item", lang): item_id,
            t("col_count", lang): count,
            t("col_rate", lang): f"{100 * count / n_sessions:.0f}%" if n_sessions else "–",
        }
        for item_id, count in rows
    ]


def to_csv(rows: Iterable[sqlite3.Row], columns: tuple[str, ...]) -> str:
    """CSV text with a fixed header row."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row[c] for c in columns])
    return buffer.getvalue()
