"""Tests for the manual-labeling pipeline stage (motor/pipeline/manual_labeling.py).

This is the no-API-key alternative to `enrich()`: `export_for_labeling()`
writes not-yet-enriched reviews to a JSON file shaped for a human (or an
attached Claude Code conversation) to label directly, and `apply_labels()`
reads the labels back and merges them into `Review` objects the same way
`enrich()` does - via `dataclasses.replace`, so the original objects are
never mutated and every non-enrichment field carries over unchanged.
"""

import json

import pytest

from motor.pipeline.manual_labeling import apply_labels, export_for_labeling


def test_export_writes_instructions_and_reviews(tmp_path, make_review):
    reviews = [
        make_review(dedup_id="a", app_id="com.hevy", rating=5, body="Great app!"),
        make_review(dedup_id="b", app_id="com.hevy", rating=2, body="Sync is broken"),
    ]
    path = tmp_path / "export.json"

    export_for_labeling(reviews, path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "instructions" in data
    assert data["instructions"]  # a non-empty string explaining the expected labels shape
    assert data["reviews"] == [
        {"dedup_id": "a", "app_id": "com.hevy", "rating": 5, "body": "Great app!"},
        {"dedup_id": "b", "app_id": "com.hevy", "rating": 2, "body": "Sync is broken"},
    ]


def test_export_excludes_author_and_dates(tmp_path, sample_review):
    # The exported file may be pasted straight into a chat - keep it to only
    # what's needed to label a review, nothing else.
    path = tmp_path / "export.json"

    export_for_labeling([sample_review], path)

    data = json.loads(path.read_text(encoding="utf-8"))
    [entry] = data["reviews"]
    assert set(entry.keys()) == {"dedup_id", "app_id", "rating", "body"}


def test_apply_labels_sets_enrichment_fields_for_matched_reviews(tmp_path, make_review):
    review = make_review(dedup_id="a")
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(
        json.dumps(
            {"a": {"themes": ["sync"], "sentiment": "negative", "is_feature_request": False, "opportunity_tag": "fix-sync"}}
        ),
        encoding="utf-8",
    )

    [result] = apply_labels([review], labels_path)

    assert result.themes == ["sync"]
    assert result.sentiment == "negative"
    assert result.is_feature_request is False
    assert result.opportunity_tag == "fix-sync"


def test_apply_labels_leaves_unmatched_reviews_untouched(tmp_path, make_review):
    review = make_review(dedup_id="a")
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(json.dumps({}), encoding="utf-8")

    [result] = apply_labels([review], labels_path)

    assert result.themes == []
    assert result.sentiment is None
    assert result.is_feature_request is None
    assert result.opportunity_tag is None


def test_apply_labels_does_not_mutate_the_input_review(tmp_path, make_review):
    review = make_review(dedup_id="a")
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(
        json.dumps(
            {"a": {"themes": ["pricing"], "sentiment": "positive", "is_feature_request": True, "opportunity_tag": "add-plan"}}
        ),
        encoding="utf-8",
    )
    original_themes = list(review.themes)
    original_sentiment = review.sentiment

    apply_labels([review], labels_path)

    assert review.themes == original_themes
    assert review.sentiment == original_sentiment


def test_apply_labels_preserves_every_non_enrichment_field(tmp_path, make_review):
    review = make_review(dedup_id="a")
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(
        json.dumps(
            {"a": {"themes": ["pricing"], "sentiment": "positive", "is_feature_request": True, "opportunity_tag": "add-plan"}}
        ),
        encoding="utf-8",
    )

    [result] = apply_labels([review], labels_path)

    assert result.dedup_id == review.dedup_id
    assert result.platform == review.platform
    assert result.app_id == review.app_id
    assert result.body == review.body
    assert result.rating == review.rating
    assert result.author_hash == review.author_hash
    assert result.review_date == review.review_date


def test_apply_labels_ignores_unmatched_dedup_ids_in_the_labels_file(tmp_path, make_review):
    review = make_review(dedup_id="a")
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(
        json.dumps(
            {"does-not-exist": {"themes": ["x"], "sentiment": "neutral", "is_feature_request": False, "opportunity_tag": None}}
        ),
        encoding="utf-8",
    )

    result = apply_labels([review], labels_path)

    assert len(result) == 1
    assert result[0].themes == []  # review "a" itself was never labeled


def test_apply_labels_raises_on_an_incomplete_label_entry(tmp_path, make_review):
    review = make_review(dedup_id="a")
    labels_path = tmp_path / "labels.json"
    # missing "opportunity_tag" - a malformed label must fail loudly, not
    # silently write a half-enriched review.
    labels_path.write_text(
        json.dumps({"a": {"themes": ["sync"], "sentiment": "negative", "is_feature_request": False}}),
        encoding="utf-8",
    )

    with pytest.raises(KeyError):
        apply_labels([review], labels_path)


def test_export_then_apply_labels_round_trips(tmp_path, make_review):
    reviews = [
        make_review(dedup_id="a", body="Sync keeps failing"),
        make_review(dedup_id="b", body="Sync keeps failing too"),
    ]
    export_path = tmp_path / "export.json"
    labels_path = tmp_path / "labels.json"

    export_for_labeling(reviews, export_path)
    exported = json.loads(export_path.read_text(encoding="utf-8"))
    labels = {
        entry["dedup_id"]: {
            "themes": ["sync"],
            "sentiment": "negative",
            "is_feature_request": False,
            "opportunity_tag": "fix-sync",
        }
        for entry in exported["reviews"]
    }
    labels_path.write_text(json.dumps(labels), encoding="utf-8")

    result = apply_labels(reviews, labels_path)

    assert all(r.sentiment == "negative" for r in result)
    assert all(r.themes == ["sync"] for r in result)
