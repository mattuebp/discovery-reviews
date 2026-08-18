"""The `report` pipeline stage.

Aggregates enriched `Review` objects into the insights and competitive
comparisons a PM reads in the DAY 6 dashboard. Pure functions over
`Review`/`Project` objects - no HTML, no database, no I/O (see
`tests/test_report.py` for the user stories each function answers).
"""

from dataclasses import dataclass, field
from typing import Literal

from motor.models import Project, Review

# A competitor beating (or losing to) the primary app by less than this many
# percentage points of negative sentiment isn't a meaningful signal - see
# TestCompareApps.test_does_not_flag_a_theme_within_the_gap_threshold.
NEGATIVE_SENTIMENT_GAP_THRESHOLD = 0.15

# How dominant one sentiment has to be, as a share of a theme's mentions,
# before the theme is labeled "pain" or "strength" rather than "mixed" - see
# TestClassifyTheme. Validated against a real 36-review Hevy batch (the
# Product Opportunity Report artifact) before being promoted here.
THEME_CLASSIFICATION_THRESHOLD = 0.65

BIAS_DISCLAIMER = (
    "This sample reflects only users who chose to write a public review, and "
    "is drawn from the most recently posted reviews rather than the app's "
    "full historical review base - it is not a representative survey of the "
    "full user base and must not be presented as one (see docs/governanca.md, "
    "'Honestidade metodologica')."
)


@dataclass
class ThemeSummary:
    """How one theme shows up across a set of reviews."""

    theme: str
    count: int = 0
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    feature_request_count: int = 0


@dataclass
class ComparisonRow:
    """Primary vs. competitor sentiment on one theme."""

    theme: str
    primary: ThemeSummary
    competitor: ThemeSummary
    flag: str | None  # "advantage" | "risk" | None


@dataclass
class ComparisonResult:
    rows: list[ComparisonRow] = field(default_factory=list)
    primary_themes: list[ThemeSummary] = field(default_factory=list)


def summarize_themes(reviews: list[Review]) -> list[ThemeSummary]:
    """Aggregate `reviews` into one `ThemeSummary` per theme, most-mentioned first.

    A review with no themes yet (not enriched) has nothing to iterate over,
    so it's excluded automatically - no explicit "is enriched" check needed.
    """

    summaries: dict[str, ThemeSummary] = {}
    for review in reviews:
        for theme in review.themes:
            summary = summaries.setdefault(theme, ThemeSummary(theme=theme))
            summary.count += 1
            if review.sentiment == "positive":
                summary.positive += 1
            elif review.sentiment == "negative":
                summary.negative += 1
            elif review.sentiment == "neutral":
                summary.neutral += 1
            if review.is_feature_request:
                summary.feature_request_count += 1

    return sorted(summaries.values(), key=lambda summary: summary.count, reverse=True)


def reviews_for_theme(reviews: list[Review], theme: str) -> list[Review]:
    """Every review tagged with `theme`, for showing real quotes behind a number."""

    return [review for review in reviews if theme in review.themes]


def classify_theme(summary: ThemeSummary) -> Literal["pain", "strength", "mixed"]:
    """Label a theme "pain" (negative-dominant), "strength" (positive-dominant),
    or "mixed" (neither), so a PM can scan themes without eyeballing the raw
    sentiment counts. A theme with zero mentions has no signal either way, so
    it classifies as "mixed" rather than raising a division-by-zero error.
    """

    if summary.count == 0:
        return "mixed"
    if summary.negative / summary.count >= THEME_CLASSIFICATION_THRESHOLD:
        return "pain"
    if summary.positive / summary.count >= THEME_CLASSIFICATION_THRESHOLD:
        return "strength"
    return "mixed"


@dataclass
class OpportunitySummary:
    """One distinct ask or fix, and how many reviews back it."""

    tag: str
    count: int
    themes: list[str]  # every theme any review carrying this tag also has
    is_feature_request: bool  # true if ANY review carrying this tag is a feature request
    sample_review: Review  # first review carrying this tag, for a real quote


def summarize_opportunities(reviews: list[Review]) -> list[OpportunitySummary]:
    """Group reviews by `opportunity_tag`, most-mentioned first.

    A review with no opportunity_tag (not enriched, or enriched with nothing
    actionable to name) is excluded - there's nothing to group it under.
    """

    grouped: dict[str, list[Review]] = {}
    for review in reviews:
        if review.opportunity_tag:
            grouped.setdefault(review.opportunity_tag, []).append(review)

    summaries = [
        OpportunitySummary(
            tag=tag,
            count=len(tagged_reviews),
            themes=sorted({theme for review in tagged_reviews for theme in review.themes}),
            is_feature_request=any(review.is_feature_request for review in tagged_reviews),
            sample_review=tagged_reviews[0],
        )
        for tag, tagged_reviews in grouped.items()
    ]

    return sorted(summaries, key=lambda summary: summary.count, reverse=True)


def _negative_rate(summary: ThemeSummary) -> float:
    return summary.negative / summary.count if summary.count else 0.0


def compare_apps(project: Project, reviews_by_app: dict[str, list[Review]]) -> ComparisonResult:
    """Compare the primary app's theme sentiment against its competitors'."""

    primary_app = next(app for app in project.apps if app.role == "primary")
    competitor_apps = [app for app in project.apps if app.role == "competitor"]

    primary_themes = summarize_themes(reviews_by_app.get(primary_app.app_id, []))

    if not competitor_apps:
        return ComparisonResult(rows=[], primary_themes=primary_themes)

    competitor_reviews = [
        review
        for app in competitor_apps
        for review in reviews_by_app.get(app.app_id, [])
    ]
    competitor_themes = summarize_themes(competitor_reviews)

    primary_by_theme = {summary.theme: summary for summary in primary_themes}
    competitor_by_theme = {summary.theme: summary for summary in competitor_themes}
    all_theme_names = sorted(set(primary_by_theme) | set(competitor_by_theme))

    rows = []
    for theme in all_theme_names:
        primary_summary = primary_by_theme.get(theme, ThemeSummary(theme=theme))
        competitor_summary = competitor_by_theme.get(theme, ThemeSummary(theme=theme))

        # Positive gap = competitor is more negative than primary here (an
        # advantage for primary); negative gap = the reverse (a risk).
        gap = _negative_rate(competitor_summary) - _negative_rate(primary_summary)
        if gap >= NEGATIVE_SENTIMENT_GAP_THRESHOLD:
            flag = "advantage"
        elif gap <= -NEGATIVE_SENTIMENT_GAP_THRESHOLD:
            flag = "risk"
        else:
            flag = None

        rows.append(ComparisonRow(theme=theme, primary=primary_summary, competitor=competitor_summary, flag=flag))

    return ComparisonResult(rows=rows, primary_themes=primary_themes)


def assemble_report(project: Project, reviews_by_app: dict[str, list[Review]]) -> dict:
    """Build the full report dict the DAY 6 dashboard reads from."""

    all_reviews = [review for reviews in reviews_by_app.values() for review in reviews]
    themes = summarize_themes(all_reviews)

    # Partition every theme into exactly one of pain/strength/mixed, each
    # still ranked most-mentioned first (classify_theme never changes order,
    # only which bucket a theme lands in).
    pain_themes = [t for t in themes if classify_theme(t) == "pain"]
    strength_themes = [t for t in themes if classify_theme(t) == "strength"]
    mixed_themes = [t for t in themes if classify_theme(t) == "mixed"]

    return {
        "sample_size": len(all_reviews),
        "bias_disclaimer": BIAS_DISCLAIMER,
        "themes": themes,
        "pain_themes": pain_themes,
        "strength_themes": strength_themes,
        "mixed_themes": mixed_themes,
        "opportunities": summarize_opportunities(all_reviews),
        "competitive_comparison": compare_apps(project, reviews_by_app),
    }
