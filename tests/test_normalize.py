"""Tests for the `normalize` pipeline stage (motor/pipeline/normalize.py).

`normalize()` turns one raw, platform-specific review dict into the
canonical `Review` shape described in CLAUDE.md's "Data contract" table.
`deduplicate()` collapses raw entries that resolve to the same `dedup_id`
(e.g. overlapping pages from pagination) down to one `Review`.
"""

from datetime import datetime

from motor.pipeline.normalize import deduplicate, normalize


def test_normalize_maps_google_play_fields_to_the_canonical_review(raw_google_play_review):
    review = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")

    assert review.platform == "google_play"
    assert review.app_id == "com.hevy.app"
    assert review.country == "br"
    assert review.rating == raw_google_play_review["score"]
    assert review.body == raw_google_play_review["content"]
    assert review.app_version == raw_google_play_review["reviewCreatedVersion"]
    assert review.helpful_votes == raw_google_play_review["thumbsUpCount"]
    assert review.review_date == "2026-06-15T10:30:00+00:00"


def test_normalize_title_is_always_empty_for_google_play(raw_google_play_review):
    # Google Play reviews have no title field at all - per CLAUDE.md's data
    # contract, title "can be empty on Google Play".
    review = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")

    assert review.title == ""


def test_normalize_maps_dev_reply_when_present(raw_google_play_review):
    raw = {**raw_google_play_review, "replyContent": "Obrigado pelo feedback!"}

    review = normalize(raw, platform="google_play", app_id="com.hevy.app", country="br")

    assert review.dev_reply == "Obrigado pelo feedback!"


def test_normalize_dev_reply_is_none_when_absent(raw_google_play_review):
    review = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")

    assert review.dev_reply is None


def test_normalize_dedup_id_is_deterministic_for_the_same_input(raw_google_play_review):
    first = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")
    second = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")

    assert first.dedup_id == second.dedup_id


def test_normalize_dedup_id_changes_when_the_review_text_changes(raw_google_play_review):
    base = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")
    changed_raw = {**raw_google_play_review, "content": "Texto completamente diferente."}
    changed = normalize(changed_raw, platform="google_play", app_id="com.hevy.app", country="br")

    assert base.dedup_id != changed.dedup_id


def test_normalize_author_hash_never_contains_the_raw_username(raw_google_play_review):
    review = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")

    raw_username = raw_google_play_review["userName"]
    assert raw_username != review.author_hash
    assert raw_username not in review.author_hash


def test_normalize_author_hash_is_deterministic_for_the_same_author(raw_google_play_review):
    first = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")

    other_review_by_same_author = {
        **raw_google_play_review,
        "reviewId": "gp-review-002",
        "content": "Um comentario completamente diferente.",
    }
    second = normalize(other_review_by_same_author, platform="google_play", app_id="com.hevy.app", country="br")

    assert first.author_hash == second.author_hash


def test_normalize_author_hash_differs_across_different_authors(raw_google_play_review):
    first = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")

    other_author_raw = {**raw_google_play_review, "userName": "Joao Pereira"}
    second = normalize(other_author_raw, platform="google_play", app_id="com.hevy.app", country="br")

    assert first.author_hash != second.author_hash


def test_normalize_sets_lang_from_the_country_map(raw_google_play_review):
    review = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")

    assert review.lang == "pt"


def test_normalize_falls_back_to_english_for_an_unmapped_country(raw_google_play_review):
    review = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="zz")

    assert review.lang == "en"


def test_normalize_sets_collected_at_to_a_valid_iso_timestamp(raw_google_play_review):
    review = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")

    # Must not raise - the exact "now" value isn't something a test should
    # pin down, but it must be a real, parseable ISO 8601 timestamp.
    datetime.fromisoformat(review.collected_at)


def test_normalize_leaves_enrichment_fields_unset(raw_google_play_review):
    # normalize() runs before enrich() in the pipeline - a freshly
    # normalized review must still look "not yet enriched".
    review = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")

    assert review.themes == []
    assert review.sentiment is None
    assert review.is_feature_request is None
    assert review.opportunity_tag is None


def test_deduplicate_collapses_reviews_with_the_same_dedup_id(raw_google_play_review):
    review = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")
    duplicate_from_another_page = normalize(
        raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br"
    )

    result = deduplicate([review, duplicate_from_another_page])

    assert len(result) == 1
    assert result[0].dedup_id == review.dedup_id


def test_deduplicate_keeps_distinct_reviews(raw_google_play_review):
    review = normalize(raw_google_play_review, platform="google_play", app_id="com.hevy.app", country="br")
    other_raw = {
        **raw_google_play_review,
        "reviewId": "gp-review-002",
        "content": "Outra reclamacao, bem diferente.",
    }
    other_review = normalize(other_raw, platform="google_play", app_id="com.hevy.app", country="br")

    result = deduplicate([review, other_review])

    assert len(result) == 2
