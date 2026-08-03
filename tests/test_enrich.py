"""Tests for the `enrich` pipeline stage (motor/pipeline/enrich.py).

`enrich()` sends a review's text to Claude and comes back with a labeled
copy: `themes`, `sentiment`, `is_feature_request`, `opportunity_tag`. The
Anthropic client is always a mock here - per the secrets/governance policy,
tests never hold a real API key or make a real network call.
"""

import json
from unittest.mock import MagicMock

from motor.pipeline.enrich import enrich


def _mock_client_returning(labels: dict) -> MagicMock:
    """Builds a fake Anthropic client whose `messages.create(...)` returns a
    response shaped like the real SDK's, with `labels` as the JSON payload
    in the first content block's `.text` - the shape `enrich()` must parse.
    """
    content_block = MagicMock()
    content_block.text = json.dumps(labels)

    response = MagicMock()
    response.content = [content_block]

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_enrich_populates_labels_from_the_llm_response(sample_review):
    client = _mock_client_returning(
        {
            "themes": ["sync", "reliability"],
            "sentiment": "negative",
            "is_feature_request": False,
            "opportunity_tag": "fix-sync-crashes",
        }
    )

    result = enrich(sample_review, client)

    assert result.themes == ["sync", "reliability"]
    assert result.sentiment == "negative"
    assert result.is_feature_request is False
    assert result.opportunity_tag == "fix-sync-crashes"


def test_enrich_calls_the_anthropic_client_exactly_once(sample_review):
    client = _mock_client_returning(
        {"themes": [], "sentiment": "neutral", "is_feature_request": False, "opportunity_tag": None}
    )

    enrich(sample_review, client)

    client.messages.create.assert_called_once()


def test_enrich_does_not_mutate_the_input_review(sample_review):
    client = _mock_client_returning(
        {"themes": ["pricing"], "sentiment": "positive", "is_feature_request": True, "opportunity_tag": "add-annual-plan"}
    )
    original_themes = list(sample_review.themes)
    original_sentiment = sample_review.sentiment

    enrich(sample_review, client)

    assert sample_review.themes == original_themes
    assert sample_review.sentiment == original_sentiment


def test_enrich_preserves_every_non_enrichment_field(sample_review):
    client = _mock_client_returning(
        {"themes": ["pricing"], "sentiment": "positive", "is_feature_request": True, "opportunity_tag": "add-annual-plan"}
    )

    result = enrich(sample_review, client)

    assert result.dedup_id == sample_review.dedup_id
    assert result.platform == sample_review.platform
    assert result.app_id == sample_review.app_id
    assert result.body == sample_review.body
    assert result.rating == sample_review.rating
    assert result.author_hash == sample_review.author_hash
    assert result.review_date == sample_review.review_date


def test_enrich_input_review_starts_with_empty_enrichment_fields(sample_review):
    # Documents the "not yet enriched" precondition this whole stage exists
    # to fill in - makes the before/after in the tests above obvious.
    assert sample_review.themes == []
    assert sample_review.sentiment is None
    assert sample_review.is_feature_request is None
    assert sample_review.opportunity_tag is None
