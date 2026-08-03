"""Shared pytest fixtures for the whole `tests/` suite.

Centralizing fixtures here means each test file only has to describe what's
*different* about its input data, instead of rebuilding a full raw review or
canonical `Review` from scratch every time. See CLAUDE.md's "Data contract"
table for what every field means.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from motor.models import App, Project, Review


@pytest.fixture(autouse=True)
def author_hash_salt(monkeypatch):
    """Every test gets the same fixed AUTHOR_HASH_SALT, so author_hash
    values are deterministic across test runs and never depend on a real
    `.env` file being present on the machine running the tests. See
    `.env.example` for what this variable is for.
    """
    monkeypatch.setenv("AUTHOR_HASH_SALT", "test-salt-do-not-use-in-production")


@pytest.fixture
def raw_google_play_review() -> dict:
    """One raw review dict, shaped exactly like a single entry from what
    `google_play_scraper.reviews()` actually returns. This fixture pins
    down the exact raw input `normalize()` has to handle - if the real
    library's field names ever differ from this, the DAY 4 implementation
    (and this fixture) need updating together.
    """
    return {
        "reviewId": "gp-review-001",
        "userName": "Maria Silva",
        "content": "O app trava toda vez que tento sincronizar meu treino.",
        "score": 2,
        "at": datetime(2026, 6, 15, 10, 30, tzinfo=timezone.utc),
        "reviewCreatedVersion": "4.12.0",
        "thumbsUpCount": 7,
        "replyContent": None,
        "repliedAt": None,
    }


@pytest.fixture
def make_review():
    """Factory fixture: builds a fully-populated canonical `Review`, with
    sane defaults for every field, overridable via kwargs. Enrichment
    fields default to their "not yet enriched" dataclass defaults
    (`themes=[]`, `sentiment=None`, ...) unless a test overrides them.
    """

    def _make(**overrides) -> Review:
        defaults = dict(
            dedup_id="dedup-0001",
            platform="google_play",
            app_id="com.hevy.app",
            country="br",
            rating=4,
            title="",
            body="Great app, but sync is flaky.",
            author_hash="a" * 64,
            app_version="4.12.0",
            review_date="2026-06-15T10:30:00+00:00",
            helpful_votes=3,
            dev_reply=None,
            lang="pt",
            collected_at="2026-06-16T09:00:00+00:00",
        )
        defaults.update(overrides)
        return Review(**defaults)

    return _make


@pytest.fixture
def sample_review(make_review) -> Review:
    """A single, fully-populated, not-yet-enriched Review."""
    return make_review()


@pytest.fixture
def db_path(tmp_path) -> Path:
    """Path to a throwaway SQLite file, unique per test - `test_store.py`
    never touches a shared or real database.
    """
    return tmp_path / "reviews.db"


@pytest.fixture
def sample_project() -> Project:
    """One analysis project: Hevy as the primary app, one competitor.
    Mirrors CLAUDE.md's "primary app + N competitors" concept.
    """
    return Project(
        name="Hevy vs. Strong",
        apps=[
            App(app_id="com.hevy.app", platform="google_play", country="br", role="primary"),
            App(app_id="com.strong.app", platform="google_play", country="br", role="competitor"),
        ],
    )


@pytest.fixture
def enriched_reviews(make_review) -> list[Review]:
    """A small, hand-built set of fully-enriched reviews spanning both apps
    in `sample_project`. Deliberately covers more than one theme, more than
    one sentiment, and at least one feature request - this is the "given"
    half of every `test_report.py` user story, so its exact numbers are
    referenced directly in that file's assertions/comments.

    Intentional shape (see test_report.py for the math this sets up):
    - primary "sync" complaints skew heavily negative (3 of 4 negative);
      competitor's single "sync" review is positive -> primary is at risk
      of losing users to the competitor here.
    - primary "pricing" feedback is a 50/50 split; competitor's "pricing"
      reviews are both negative -> primary has an advantage here.
    - one primary review (`hevy-6`) is not yet enriched, so it must be
      excluded from every theme aggregation.
    """
    return [
        make_review(
            dedup_id="hevy-1", app_id="com.hevy.app",
            body="Trava toda vez que sincroniza.",
            themes=["sync"], sentiment="negative", is_feature_request=False,
        ),
        make_review(
            dedup_id="hevy-2", app_id="com.hevy.app",
            body="Sync perdeu meu treino de novo.",
            themes=["sync"], sentiment="negative", is_feature_request=False,
        ),
        make_review(
            dedup_id="hevy-3", app_id="com.hevy.app",
            body="Sincroniza bem quando estou no wifi.",
            themes=["sync"], sentiment="positive", is_feature_request=False,
        ),
        make_review(
            dedup_id="hevy-4", app_id="com.hevy.app",
            body="Gostaria de um plano anual mais barato, com sync automatico.",
            themes=["sync", "pricing"], sentiment="negative", is_feature_request=True,
        ),
        make_review(
            dedup_id="hevy-5", app_id="com.hevy.app",
            body="Preco esta ok, mas achei que teria desconto no plano anual.",
            themes=["pricing"], sentiment="neutral", is_feature_request=False,
        ),
        make_review(
            dedup_id="hevy-6", app_id="com.hevy.app",
            body="Ainda estou testando o app.",
            themes=[], sentiment=None, is_feature_request=None,
        ),
        make_review(
            dedup_id="strong-1", app_id="com.strong.app",
            body="Sync funciona perfeitamente aqui.",
            themes=["sync"], sentiment="positive", is_feature_request=False,
        ),
        make_review(
            dedup_id="strong-2", app_id="com.strong.app",
            body="Muito caro pelo que oferece.",
            themes=["pricing"], sentiment="negative", is_feature_request=False,
        ),
        make_review(
            dedup_id="strong-3", app_id="com.strong.app",
            body="Assinatura cara demais para o que entrega.",
            themes=["pricing"], sentiment="negative", is_feature_request=False,
        ),
    ]


@pytest.fixture
def reviews_by_app(enriched_reviews) -> dict[str, list[Review]]:
    """`enriched_reviews`, grouped by `app_id` - the shape `compare_apps()`
    and `assemble_report()` take as input.
    """
    grouped: dict[str, list[Review]] = {}
    for review in enriched_reviews:
        grouped.setdefault(review.app_id, []).append(review)
    return grouped
