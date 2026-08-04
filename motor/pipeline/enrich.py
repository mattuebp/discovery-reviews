"""The `enrich` pipeline stage.

`enrich()` sends a review's text to Claude and returns a labeled copy:
`themes`, `sentiment`, `is_feature_request`, `opportunity_tag`. The caller
supplies the Anthropic client (production code passes a real
`anthropic.Anthropic()`; tests pass a mock) - this module never constructs
one itself, so it never needs to touch `ANTHROPIC_API_KEY` directly.
"""

import json
from dataclasses import replace
from typing import Any

from motor.models import Review

# Model used for labeling. A plain constant (not buried in the prompt logic)
# so it's a one-line change if a cheaper/stronger model makes more sense
# later - see CLAUDE.md rule 3 (optimization is a DAY 5 concern, not DAY 4).
ENRICH_MODEL = "claude-sonnet-5"

PROMPT_TEMPLATE = """You are labeling a single app store review for a product team.

Review rating: {rating}/5
Review text: {body}

Respond with ONLY a JSON object (no other text) with these fields:
- "themes": array of short lowercase theme strings (e.g. "sync", "pricing", "onboarding")
- "sentiment": one of "positive", "negative", "neutral"
- "is_feature_request": true or false
- "opportunity_tag": a short kebab-case tag summarizing the product opportunity, or null if none
"""


def enrich(review: Review, client: Any) -> Review:
    """Return a copy of `review` with enrichment fields filled in by Claude."""

    prompt = PROMPT_TEMPLATE.format(rating=review.rating, body=review.body)
    response = client.messages.create(
        model=ENRICH_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    labels = json.loads(response.content[0].text)

    # dataclasses.replace() builds a new Review, leaving `review` untouched
    # and carrying every non-enrichment field over unchanged.
    return replace(
        review,
        themes=labels["themes"],
        sentiment=labels["sentiment"],
        is_feature_request=labels["is_feature_request"],
        opportunity_tag=labels["opportunity_tag"],
    )
