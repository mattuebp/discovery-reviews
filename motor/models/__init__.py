"""Core data shapes shared across the pipeline.

These are plain dataclasses passed in memory between pipeline stages, not
database rows. `motor/db/schema.sql` mirrors `Review`'s fields as flat SQL
columns, but `App` and `Project` are config concepts used to drive and label
the pipeline - they aren't persisted anywhere yet.
"""

from dataclasses import dataclass, field
from typing import Literal

Platform = Literal["google_play", "app_store"]


@dataclass
class Review:
    """One canonical review - the shape every adapter's raw output gets
    converted into by the `normalize` pipeline stage. Field meanings are
    documented in CLAUDE.md under "Data contract - Canonical review".
    """

    dedup_id: str
    platform: Platform
    app_id: str
    country: str
    rating: int
    title: str
    body: str
    author_hash: str  # pseudonymized PII - never the raw review author
    app_version: str
    review_date: str  # ISO 8601
    helpful_votes: int
    dev_reply: str | None
    lang: str
    collected_at: str  # ISO 8601

    # Enrichment fields: filled in by the `enrich` pipeline stage. A
    # freshly-normalized review is still a valid Review, just "not yet
    # enriched" - hence these default to empty/None instead of being required.
    themes: list[str] = field(default_factory=list)
    sentiment: str | None = None
    is_feature_request: bool | None = None
    opportunity_tag: str | None = None


@dataclass
class App:
    """One app to analyze, from one platform/storefront.

    `role` is only read when the `report` stage assembles the competitive
    section - the collect/normalize/enrich/store stages treat every App
    identically regardless of its role.
    """

    app_id: str
    platform: Platform
    country: str
    role: Literal["primary", "competitor"]


@dataclass
class Project:
    """An analysis project: the primary app you care about, plus the
    competitors to compare it against. Exactly one entry in `apps` should
    have role="primary" - deliberately not duplicated as a separate
    `primary_app_id` field, which could drift out of sync with `apps`.
    """

    name: str
    apps: list[App]
