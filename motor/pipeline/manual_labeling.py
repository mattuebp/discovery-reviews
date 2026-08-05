"""The manual-labeling pipeline stage - a no-API-key alternative to `enrich()`.

`export_for_labeling()` writes not-yet-enriched reviews to a single,
self-describing JSON file - meant to be attached directly to a Claude Code
conversation and labeled by hand, instead of calling the (separately billed)
Anthropic API. `apply_labels()` reads the labels back and merges them into
`Review` objects the same way `enrich()` does: via `dataclasses.replace`, so
the originals are never mutated and every non-enrichment field is preserved.
"""

import json
from dataclasses import replace
from pathlib import Path

from motor.models import Review

INSTRUCTIONS = (
    "For each review below, return a JSON object mapping its dedup_id to: "
    "themes (array of short lowercase tags), sentiment "
    "('positive'|'negative'|'neutral'), is_feature_request (true/false), and "
    "opportunity_tag (short kebab-case string, or null). Example: "
    '{"<dedup_id>": {"themes": [...], "sentiment": "...", '
    '"is_feature_request": false, "opportunity_tag": null}}'
)


def export_for_labeling(reviews: list[Review], path: str | Path) -> None:
    """Write `reviews` to `path` as a self-describing JSON file for manual labeling.

    Only the fields a labeler actually needs (dedup_id, app_id, rating, body)
    are included - no author_hash or dates, since this file may be pasted
    straight into a chat.
    """

    data = {
        "instructions": INSTRUCTIONS,
        "reviews": [
            {"dedup_id": review.dedup_id, "app_id": review.app_id, "rating": review.rating, "body": review.body}
            for review in reviews
        ],
    }
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def apply_labels(reviews: list[Review], labels_path: str | Path) -> list[Review]:
    """Merge hand-written labels from `labels_path` into `reviews`.

    `labels_path` is a flat JSON object: dedup_id -> {themes, sentiment,
    is_feature_request, opportunity_tag}. A review whose dedup_id isn't in
    the file is returned unchanged (still "not yet enriched"); an extra
    dedup_id in the file that matches no review is simply ignored.
    """

    labels_by_dedup_id = json.loads(Path(labels_path).read_text(encoding="utf-8"))

    result = []
    for review in reviews:
        labels = labels_by_dedup_id.get(review.dedup_id)
        if labels is None:
            result.append(review)
            continue
        result.append(
            replace(
                review,
                themes=labels["themes"],
                sentiment=labels["sentiment"],
                is_feature_request=labels["is_feature_request"],
                opportunity_tag=labels["opportunity_tag"],
            )
        )
    return result
