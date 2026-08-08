"""`GooglePlaySource` - the Google Play adapter for the `ReviewSource` port
(see `motor/sources/base.py`).

Talks to the public Google Play store page via the `google-play-scraper`
library. Nothing here converts to the canonical `Review` shape - that's the
`normalize` pipeline stage's job (see `motor/pipeline/normalize.py`).
"""

from collections.abc import Iterable
from typing import Any

from google_play_scraper import reviews as _fetch_reviews

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
