"""
Simpele SQLite-opslag om bij te houden welke events we al gemeld
hebben, zodat je nooit dubbele Discord-berichten krijgt. Ook wordt
opgeslagen wat de laatst bekende status/prijs was, zodat je (optioneel)
ook een melding kunt sturen als een event wijzigt (bv. tickets nu live,
of geannuleerd).
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_events (
    dedup_key TEXT PRIMARY KEY,
    artist TEXT,
    date TEXT,
    venue TEXT,
    city TEXT,
    status TEXT,
    price_min REAL,
    price_max REAL,
    first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class EventStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(SCHEMA)
            conn.commit()

    def is_new(self, dedup_key: str) -> bool:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT 1 FROM seen_events WHERE dedup_key = ?", (dedup_key,)
            ).fetchone()
            return row is None

    def has_changed(self, dedup_key: str, status: Optional[str], price_min, price_max) -> bool:
        """Geeft True als het event al bekend was maar status of prijs
        is gewijzigd sinds de vorige keer (bv. tickets net live, of
        event geannuleerd)."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT status, price_min, price_max FROM seen_events WHERE dedup_key = ?",
                (dedup_key,),
            ).fetchone()
            if row is None:
                return False
            old_status, old_min, old_max = row
            return (old_status != status) or (old_min != price_min) or (old_max != price_max)

    def upsert(self, event) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO seen_events
                    (dedup_key, artist, date, venue, city, status, price_min, price_max, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(dedup_key) DO UPDATE SET
                    status = excluded.status,
                    price_min = excluded.price_min,
                    price_max = excluded.price_max,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (
                    event.dedup_key(),
                    event.artist,
                    event.date,
                    event.venue,
                    event.city,
                    event.status,
                    event.price_min,
                    event.price_max,
                ),
            )
            conn.commit()
