"""The selection pipeline stage.

Narrows down an already-collected, normalized list of reviews before
enrichment. Both functions here work on plain `Review` objects and know
nothing about any particular store - they run identically no matter which
`ReviewSource` produced the reviews (see motor/sources/base.py).
"""

import random

from motor.models import Review


def random_sample(reviews: list[Review], sample_size: int) -> list[Review]:
    """Return `sample_size` reviews drawn at random from `reviews`.

    If `sample_size` is at least as large as the pool, every review is
    returned unchanged - there's nothing to narrow down.
    """

    if sample_size >= len(reviews):
        return list(reviews)
    return random.sample(reviews, sample_size)


def filter_by_rating(reviews: list[Review], ratings: list[int]) -> list[Review]:
    """Keep only reviews whose star rating is in `ratings`, in order."""

    return [review for review in reviews if review.rating in ratings]
