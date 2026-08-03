"""Tests for the `report` pipeline stage (motor/pipeline/report.py).

Each test class below is the acceptance criterion for one PM-facing user
story from the DAY 3 plan (see the "Dashboard UX concept" section there for
how these functions feed the DAY 6 dashboard). Everything here operates on
plain `Review`/`Project` objects - no HTML, no database, no I/O.
"""

import pytest

from motor.models import App, Project, Review
from motor.pipeline.report import (
    NEGATIVE_SENTIMENT_GAP_THRESHOLD,
    assemble_report,
    compare_apps,
    reviews_for_theme,
    summarize_themes,
)


# ---------------------------------------------------------------------------
# "As a PM, I want to see which themes come up most and whether feedback
# skews positive/negative, so I understand the shape of feedback."
# ---------------------------------------------------------------------------
class TestSummarizeThemes:
    def test_orders_themes_by_review_count_descending(self, make_review):
        reviews = [
            make_review(dedup_id="1", themes=["sync"], sentiment="negative"),
            make_review(dedup_id="2", themes=["sync"], sentiment="negative"),
            make_review(dedup_id="3", themes=["pricing"], sentiment="neutral"),
        ]

        summaries = summarize_themes(reviews)

        assert [s.theme for s in summaries] == ["sync", "pricing"]
        assert summaries[0].count == 2
        assert summaries[1].count == 1

    def test_reports_sentiment_counts_per_theme(self, make_review):
        reviews = [
            make_review(dedup_id="1", themes=["sync"], sentiment="negative"),
            make_review(dedup_id="2", themes=["sync"], sentiment="negative"),
            make_review(dedup_id="3", themes=["sync"], sentiment="positive"),
        ]

        [sync_summary] = summarize_themes(reviews)

        assert sync_summary.negative == 2
        assert sync_summary.positive == 1
        assert sync_summary.neutral == 0

    def test_counts_a_multi_theme_review_under_every_one_of_its_themes(self, make_review):
        reviews = [
            make_review(dedup_id="1", themes=["sync", "pricing"], sentiment="negative"),
            make_review(dedup_id="2", themes=["sync"], sentiment="negative"),
        ]

        summaries = summarize_themes(reviews)
        total_theme_count = sum(s.count for s in summaries)

        # review "1" is counted under both "sync" and "pricing", so the sum
        # across themes (3) exceeds the number of reviews passed in (2).
        assert total_theme_count == 3
        assert total_theme_count > len(reviews)

    def test_reports_feature_request_count_per_theme(self, make_review):
        reviews = [
            make_review(dedup_id="1", themes=["sync"], sentiment="negative", is_feature_request=True),
            make_review(dedup_id="2", themes=["sync"], sentiment="negative", is_feature_request=False),
        ]

        [sync_summary] = summarize_themes(reviews)

        assert sync_summary.feature_request_count == 1

    def test_excludes_reviews_that_have_not_been_enriched_yet(self, make_review):
        not_yet_enriched = make_review(dedup_id="1", themes=[], sentiment=None, is_feature_request=None)

        summaries = summarize_themes([not_yet_enriched])

        assert summaries == []


# ---------------------------------------------------------------------------
# "As a PM, I want to click into a theme and read the actual review quotes
# behind it, so I trust the number and can use real quotes in a roadmap doc."
# ---------------------------------------------------------------------------
class TestReviewsForTheme:
    def test_returns_only_reviews_tagged_with_the_given_theme(self, enriched_reviews):
        results = reviews_for_theme(enriched_reviews, "pricing")

        assert results, "expected at least one pricing review in the fixture"
        assert all("pricing" in review.themes for review in results)

    def test_returns_full_review_objects_for_rendering_a_quote_card(self, enriched_reviews):
        results = [r for r in reviews_for_theme(enriched_reviews, "sync") if r.dedup_id == "hevy-1"]
        [result] = results

        assert result.body == "Trava toda vez que sincroniza."
        assert result.rating is not None
        assert result.review_date is not None
        assert result.helpful_votes is not None

    def test_returned_objects_are_genuine_reviews_carrying_only_a_pseudonymized_author(self, enriched_reviews):
        results = reviews_for_theme(enriched_reviews, "sync")

        assert results
        for review in results:
            # A real Review instance (not an ad-hoc dict) - the dataclass
            # itself, per DAY 2, has no raw-author field to smuggle through.
            assert isinstance(review, Review)
            assert review.author_hash

    def test_unknown_theme_returns_an_empty_list_not_an_error(self, enriched_reviews):
        assert reviews_for_theme(enriched_reviews, "does-not-exist") == []


# ---------------------------------------------------------------------------
# "As a PM, I want to see how my app's themes/sentiment compare to
# competitors, so I can spot gaps a competitor doesn't have."
# ---------------------------------------------------------------------------
class TestCompareApps:
    def test_pairs_up_primary_and_competitor_theme_summaries(self, sample_project, reviews_by_app):
        comparison = compare_apps(sample_project, reviews_by_app)

        themes_compared = {row.theme for row in comparison.rows}
        assert themes_compared == {"sync", "pricing"}

    def test_flags_a_theme_as_risk_when_the_competitor_notably_beats_primary(self, sample_project, reviews_by_app):
        comparison = compare_apps(sample_project, reviews_by_app)

        sync_row = next(row for row in comparison.rows if row.theme == "sync")

        # fixture: primary "sync" is 75% negative, competitor "sync" is 0%
        # negative - the competitor is doing notably better here, which is
        # a risk of losing users to them on this theme.
        assert sync_row.flag == "risk"

    def test_flags_a_theme_as_advantage_when_primary_notably_beats_the_competitor(self, sample_project, reviews_by_app):
        comparison = compare_apps(sample_project, reviews_by_app)

        pricing_row = next(row for row in comparison.rows if row.theme == "pricing")

        # fixture: primary "pricing" is 50% negative, competitor "pricing"
        # is 100% negative - primary is notably ahead here.
        assert pricing_row.flag == "advantage"

    def test_does_not_flag_a_theme_within_the_gap_threshold(self, make_review):
        project = Project(
            name="Close competitors",
            apps=[
                App(app_id="a", platform="google_play", country="br", role="primary"),
                App(app_id="b", platform="google_play", country="br", role="competitor"),
            ],
        )
        # both apps: exactly 50% negative on "onboarding" - identical, well
        # within the threshold of each other.
        reviews_by_app = {
            "a": [
                make_review(dedup_id="a1", app_id="a", themes=["onboarding"], sentiment="negative"),
                make_review(dedup_id="a2", app_id="a", themes=["onboarding"], sentiment="positive"),
            ],
            "b": [
                make_review(dedup_id="b1", app_id="b", themes=["onboarding"], sentiment="negative"),
                make_review(dedup_id="b2", app_id="b", themes=["onboarding"], sentiment="positive"),
            ],
        }

        comparison = compare_apps(project, reviews_by_app)

        [row] = comparison.rows
        assert row.flag is None

    def test_threshold_constant_is_pinned_at_fifteen_percentage_points(self):
        assert NEGATIVE_SENTIMENT_GAP_THRESHOLD == pytest.approx(0.15)

    def test_a_theme_only_the_competitor_has_still_appears_with_zero_primary_count(self, make_review):
        project = Project(
            name="One-sided data",
            apps=[
                App(app_id="a", platform="google_play", country="br", role="primary"),
                App(app_id="b", platform="google_play", country="br", role="competitor"),
            ],
        )
        reviews_by_app = {
            "a": [make_review(dedup_id="a1", app_id="a", themes=["pricing"], sentiment="neutral")],
            "b": [make_review(dedup_id="b1", app_id="b", themes=["community"], sentiment="positive")],
        }

        comparison = compare_apps(project, reviews_by_app)

        community_row = next(row for row in comparison.rows if row.theme == "community")
        assert community_row.primary.count == 0

    def test_works_for_a_project_with_no_competitor_apps(self, make_review):
        # CLAUDE.md's Project/App model already allows zero competitors -
        # compare_apps must not crash on that, just report an empty gap list.
        project = Project(
            name="Solo project",
            apps=[App(app_id="a", platform="google_play", country="br", role="primary")],
        )
        reviews_by_app = {"a": [make_review(dedup_id="a1", app_id="a", themes=["sync"], sentiment="negative")]}

        comparison = compare_apps(project, reviews_by_app)

        assert comparison.rows == []
        assert comparison.primary_themes[0].theme == "sync"


# ---------------------------------------------------------------------------
# Cross-cutting: methodological honesty (CLAUDE.md non-negotiable rule 5),
# tested once at the top level.
# ---------------------------------------------------------------------------
class TestAssembleReport:
    def test_always_includes_sample_size_and_bias_disclaimer(self, sample_project, reviews_by_app):
        report = assemble_report(sample_project, reviews_by_app)

        assert report["sample_size"]
        assert report["bias_disclaimer"]

    def test_sample_size_matches_the_true_total_review_count(self, sample_project, reviews_by_app):
        report = assemble_report(sample_project, reviews_by_app)

        expected_total = sum(len(reviews) for reviews in reviews_by_app.values())
        assert report["sample_size"] == expected_total

    def test_includes_theme_summary_and_competitive_comparison(self, sample_project, reviews_by_app):
        report = assemble_report(sample_project, reviews_by_app)

        assert "themes" in report
        assert "competitive_comparison" in report

    def test_bias_disclaimer_is_present_even_for_an_empty_sample(self, sample_project):
        report = assemble_report(sample_project, {"com.hevy.app": [], "com.strong.app": []})

        assert report["sample_size"] == 0
        assert report["bias_disclaimer"]  # rule 5: never silently dropped, even with no data
