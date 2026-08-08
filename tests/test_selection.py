"""Tests for the selection pipeline stage (motor/pipeline/selection.py).

`random_sample()` and `filter_by_rating()` narrow down an already-collected,
normalized list of reviews before enrichment - adapter-agnostic, so they
work identically regardless of which ReviewSource produced the reviews.
"""

from motor.pipeline.selection import filter_by_rating, random_sample


def test_random_sample_returns_exactly_sample_size_when_pool_is_larger(make_review):
    reviews = [make_review(dedup_id=str(i)) for i in range(20)]

    result = random_sample(reviews, sample_size=5)

    assert len(result) == 5


def test_random_sample_returns_every_review_when_sample_size_covers_the_whole_pool(make_review):
    reviews = [make_review(dedup_id=str(i)) for i in range(3)]

    result = random_sample(reviews, sample_size=10)

    assert len(result) == 3
    assert {r.dedup_id for r in result} == {"0", "1", "2"}


def test_random_sample_never_returns_a_duplicate_review(make_review):
    reviews = [make_review(dedup_id=str(i)) for i in range(20)]

    result = random_sample(reviews, sample_size=10)

    ids = [r.dedup_id for r in result]
    assert len(ids) == len(set(ids))


def test_random_sample_only_returns_reviews_that_were_in_the_input(make_review):
    reviews = [make_review(dedup_id=str(i)) for i in range(20)]
    input_ids = {r.dedup_id for r in reviews}

    result = random_sample(reviews, sample_size=8)

    assert all(r.dedup_id in input_ids for r in result)


def test_filter_by_rating_keeps_only_matching_ratings(make_review):
    reviews = [
        make_review(dedup_id="a", rating=5),
        make_review(dedup_id="b", rating=1),
        make_review(dedup_id="c", rating=3),
    ]

    result = filter_by_rating(reviews, ratings=[1])

    assert [r.dedup_id for r in result] == ["b"]


def test_filter_by_rating_accepts_multiple_ratings_at_once(make_review):
    reviews = [
        make_review(dedup_id="a", rating=5),
        make_review(dedup_id="b", rating=1),
        make_review(dedup_id="c", rating=2),
    ]

    result = filter_by_rating(reviews, ratings=[1, 2])

    assert {r.dedup_id for r in result} == {"b", "c"}


def test_filter_by_rating_returns_an_empty_list_when_nothing_matches(make_review):
    reviews = [make_review(dedup_id="a", rating=5)]

    result = filter_by_rating(reviews, ratings=[1, 2])

    assert result == []
