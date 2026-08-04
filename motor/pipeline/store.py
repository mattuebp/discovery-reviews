"""The `store` pipeline stage.

`store()` persists canonical `Review` objects into the SQLite table defined
by `motor/db/schema.sql`, keyed by `dedup_id` - safe to call repeatedly with
overlapping data (re-running the pipeline upserts, never duplicates).
"""

import json
import sqlite3
from pathlib import Path

from motor.models import Review

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

# Every column in the `reviews` table, in insert order. Kept as one list so
# the INSERT and the "update every column on conflict" clause can't drift
# apart from each other.
COLUMNS = [
    "dedup_id",
    "platform",
    "app_id",
    "country",
    "rating",
    "title",
    "body",
    "author_hash",
    "app_version",
    "review_date",
    "helpful_votes",
    "dev_reply",
    "lang",
    "collected_at",
    "themes",
    "sentiment",
    "is_feature_request",
    "opportunity_tag",
]

_UPDATE_CLAUSE = ", ".join(f"{column} = excluded.{column}" for column in COLUMNS if column != "dedup_id")

UPSERT_SQL = f"""
INSERT INTO reviews ({", ".join(COLUMNS)})
VALUES ({", ".join(f":{column}" for column in COLUMNS)})
ON CONFLICT(dedup_id) DO UPDATE SET {_UPDATE_CLAUSE}
"""


def _row_params(review: Review) -> dict:
    return {
        "dedup_id": review.dedup_id,
        "platform": review.platform,
        "app_id": review.app_id,
        "country": review.country,
        "rating": review.rating,
        "title": review.title,
        "body": review.body,
        "author_hash": review.author_hash,
        "app_version": review.app_version,
        "review_date": review.review_date,
        "helpful_votes": review.helpful_votes,
        "dev_reply": review.dev_reply,
        "lang": review.lang,
        "collected_at": review.collected_at,
        # A freshly-normalized review has themes=[] - store that as NULL,
        # not the string "[]", so "not yet enriched" reads cleanly in SQL.
        "themes": json.dumps(review.themes) if review.themes else None,
        "sentiment": review.sentiment,
        "is_feature_request": None if review.is_feature_request is None else int(review.is_feature_request),
        "opportunity_tag": review.opportunity_tag,
    }


def store(reviews: list[Review], conn: sqlite3.Connection) -> None:
    """Persist `reviews` into `conn`, upserting on `dedup_id`."""

    conn.executescript(SCHEMA_PATH.read_text())
    conn.executemany(UPSERT_SQL, [_row_params(review) for review in reviews])
    conn.commit()
