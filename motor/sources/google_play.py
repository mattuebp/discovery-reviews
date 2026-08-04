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
# "fetch everything" calls. 100 is comfortably under the library's own max
# page size of 200 while still covering a normal collection run.
DEFAULT_PAGE_SIZE = 100


class GooglePlaySource(ReviewSource):
    """Fetches reviews for one app from the Google Play store page."""

    def collect(self, app_id: str, country: str) -> Iterable[dict[str, Any]]:
        # google_play_scraper.reviews() returns (list_of_raw_reviews, continuation_token).
        # The token is for paginating further - out of scope for this stage.
        raw_reviews, _continuation_token = _fetch_reviews(
            app_id, country=country, count=DEFAULT_PAGE_SIZE
        )
        return raw_reviews
