"""Tests for the `store` pipeline stage (motor/pipeline/store.py).

`store()` persists a list of canonical `Review` objects into the SQLite
table defined by `motor/db/schema.sql`, keyed by `dedup_id` - safe to call
repeatedly with overlapping data (CLAUDE.md: "persists idempotently").
Every test opens a fresh, throwaway SQLite file (`db_path` fixture), never
a shared or real database.
"""

import sqlite3
from dataclasses import replace

from motor.pipeline.store import store


def test_store_creates_the_table_and_inserts_a_review(db_path, sample_review):
    conn = sqlite3.connect(db_path)

    store([sample_review], conn)

    row = conn.execute(
        "SELECT dedup_id, platform, app_id, rating, body FROM reviews"
    ).fetchone()
    assert row == (
        sample_review.dedup_id,
        sample_review.platform,
        sample_review.app_id,
        sample_review.rating,
        sample_review.body,
    )
    conn.close()


def test_store_is_idempotent_for_the_same_dedup_id(db_path, sample_review):
    conn = sqlite3.connect(db_path)

    store([sample_review], conn)
    store([sample_review], conn)  # re-running the pipeline must not duplicate rows

    count = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    assert count == 1
    conn.close()


def test_store_upserts_changed_fields_for_the_same_dedup_id(db_path, sample_review):
    conn = sqlite3.connect(db_path)
    store([sample_review], conn)

    updated = replace(sample_review, helpful_votes=sample_review.helpful_votes + 5)
    store([updated], conn)

    stored_votes = conn.execute(
        "SELECT helpful_votes FROM reviews WHERE dedup_id = ?", (sample_review.dedup_id,)
    ).fetchone()[0]
    assert stored_votes == sample_review.helpful_votes + 5

    count = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    assert count == 1  # still one row, not an extra one alongside the stale copy
    conn.close()


def test_store_leaves_enrichment_columns_null_for_unenriched_reviews(db_path, sample_review):
    conn = sqlite3.connect(db_path)

    store([sample_review], conn)

    themes, sentiment, is_feature_request, opportunity_tag = conn.execute(
        "SELECT themes, sentiment, is_feature_request, opportunity_tag FROM reviews WHERE dedup_id = ?",
        (sample_review.dedup_id,),
    ).fetchone()
    assert (themes, sentiment, is_feature_request, opportunity_tag) == (None, None, None, None)
    conn.close()


def test_store_persists_multiple_distinct_reviews(db_path, make_review):
    conn = sqlite3.connect(db_path)
    reviews = [make_review(dedup_id="a"), make_review(dedup_id="b"), make_review(dedup_id="c")]

    store(reviews, conn)

    count = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    assert count == 3
    conn.close()
