"""The `normalize` pipeline stage.

`normalize()` converts one raw, platform-specific review dict into the
canonical `Review` shape (CLAUDE.md's "Data contract" table).
`deduplicate()` collapses raw entries that resolve to the same `dedup_id`
(e.g. overlapping pages from pagination) down to one `Review`.
"""

import hashlib
import os
from datetime import datetime, timezone
from typing import Any

from motor.models import Platform, Review

# Storefront country -> detected review language. Not exhaustive by design -
# unmapped countries fall back to "en" rather than raising.
COUNTRY_LANG_MAP = {
    "br": "pt",
}


def normalize(raw: dict[str, Any], platform: Platform, app_id: str, country: str) -> Review:
    """Turn one raw Google Play review dict into a canonical `Review`."""

    # Read the salt at call time (not module import time) so tests that
    # monkeypatch AUTHOR_HASH_SALT per-test see their own value.
    salt = os.environ.get("AUTHOR_HASH_SALT", "")
    raw_username = raw["userName"]
    review_date = raw["at"].isoformat()
    content = raw["content"]

    # Pseudonymized per docs/governanca.md - the raw username is never
    # stored, only this salted hash of it.
    author_hash = hashlib.sha256(f"{salt}:{raw_username}".encode()).hexdigest()

    # Hash of platform+app+author+date+text (CLAUDE.md's data contract),
    # deterministic for identical input so duplicate collection runs
    # resolve to the same id.
    dedup_source = f"{platform}:{app_id}:{raw_username}:{review_date}:{content}"
    dedup_id = hashlib.sha256(dedup_source.encode()).hexdigest()

    return Review(
        dedup_id=dedup_id,
        platform=platform,
        app_id=app_id,
        country=country,
        rating=raw["score"],
        title="",  # Google Play reviews have no title field at all.
        body=content,
        author_hash=author_hash,
        app_version=raw.get("reviewCreatedVersion"),
        review_date=review_date,
        helpful_votes=raw.get("thumbsUpCount", 0),
        dev_reply=raw.get("replyContent") or None,
        lang=COUNTRY_LANG_MAP.get(country, "en"),
        collected_at=datetime.now(timezone.utc).isoformat(),
    )


def deduplicate(reviews: list[Review]) -> list[Review]:
    """Collapse reviews that share a `dedup_id` down to one entry each."""

    by_dedup_id = {review.dedup_id: review for review in reviews}
    return list(by_dedup_id.values())
