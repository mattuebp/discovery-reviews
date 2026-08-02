"""The `ReviewSource` port: the neutral contract every platform adapter must
implement (the "ports and adapters" decision in CLAUDE.md).

Today only Google Play is implemented (GooglePlaySource, added on DAY 4). An
App Store adapter can be added later by implementing this same interface,
without changing anything else in the pipeline.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any


class ReviewSource(ABC):
    """Fetches reviews for one app from one review platform.

    `collect` intentionally returns raw, platform-specific dicts - exactly
    what the underlying store/library hands back - not the canonical
    `Review` shape. Converting raw data into a canonical `Review` is the
    `normalize` pipeline stage's job, so each adapter only has to know how
    to talk to its own platform, not about the rest of the system.
    """

    @abstractmethod
    def collect(self, app_id: str, country: str) -> Iterable[dict[str, Any]]:
        """Fetch raw reviews for one app.

        Args:
            app_id: the store's identifier for the app (e.g. a Google Play
                package name like "com.hevy.app").
            country: storefront/country code (e.g. "br").

        Returns:
            An iterable of raw review records, in whatever shape the
            underlying platform/library returns them.
        """
        raise NotImplementedError
