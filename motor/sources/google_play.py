"""`GooglePlaySource` - the Google Play adapter for the `ReviewSource` port
(see `motor/sources/base.py`).

Talks to the public Google Play store page via the `google-play-scraper`
library. Nothing here converts to the canonical `Review` shape - that's the
`normalize` pipeline stage's job (see `motor/pipeline/normalize.py`).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from google_play_scraper import reviews as _fetch_reviews
from google_play_scraper import search as _search_apps_raw
from google_play_scraper.utils.request import get as _fetch_search_page

from motor.sources.base import ReviewSource

# Governance rule (docs/governanca.md): low request rate, no unbounded
# "fetch everything" calls. google_play_scraper satisfies a single request
# internally up to MAX_COUNT_EACH_FETCH=4500 reviews before it would need to
# loop for more - 300 is a still-bounded pool, large enough for
# motor.pipeline.selection.random_sample() to draw a meaningful subsample
# from, in one single HTTP request.
DEFAULT_POOL_SIZE = 300


class GooglePlaySource(ReviewSource):
    """Fetches reviews for one app from the Google Play store page."""

    def collect(self, app_id: str, country: str, count: int = DEFAULT_POOL_SIZE) -> Iterable[dict[str, Any]]:
        # google_play_scraper.reviews() returns (list_of_raw_reviews, continuation_token).
        # The token is for paginating further - out of scope for this stage.
        raw_reviews, _continuation_token = _fetch_reviews(
            app_id, country=country, count=count
        )
        return raw_reviews


@dataclass
class AppSearchResult:
    """One app match from `search_apps()` - enough to show a picker (title,
    developer, icon) and, once clicked, enough to call `collect()` (app_id).
    """

    app_id: str
    title: str
    developer: str
    icon_url: str | None
    score: float | None


def search_apps(query: str, country: str = "us", limit: int = 8) -> list[AppSearchResult]:
    """Search Google Play for apps matching `query` - lets a PM type an
    app's name instead of already knowing its package id.

    google_play_scraper.search() has a real, verified bug: it loses the
    app id specifically for Google's "exact match" top result card (every
    other field on that entry - title, developer, icon, score - comes
    through fine). That card is usually the exact app someone searched
    for, so rather than show an unusable entry, this recovers the id via
    `_recover_top_result_app_id()` when it's missing, and only drops the
    result if that recovery genuinely fails too.
    """

    raw_results = _search_apps_raw(query, n_hits=limit, country=country)

    results = []
    for raw in raw_results:
        app_id = raw.get("appId")
        if app_id is None:
            app_id = _recover_top_result_app_id(query, country)
        if app_id is None:
            continue
        results.append(
            AppSearchResult(
                app_id=app_id,
                title=raw.get("title") or "",
                developer=raw.get("developer") or "",
                icon_url=raw.get("icon"),
                score=raw.get("score"),
            )
        )

    return results


def _recover_top_result_app_id(query: str, country: str) -> str | None:
    """Fallback for search_apps()'s top-result bug (see its docstring).

    Re-fetches the same search results as a plain HTML page and takes the
    first "store/apps/details?id=..." link on it - verified live to
    reliably be the same top-match app across multiple real queries. This
    deliberately avoids re-parsing the library's internal JSON indices
    (that's the part that's actually broken); a plain link on the page is
    far less likely to change than an internal data structure's exact
    shape.
    """

    url = f"https://play.google.com/store/search?q={quote(query)}&c=apps&hl=en&gl={country}"
    html = _fetch_search_page(url)
    match = re.search(r"store/apps/details\?id=([\w.]+)", html)
    return match.group(1) if match else None
