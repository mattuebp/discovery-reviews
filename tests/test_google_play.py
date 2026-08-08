"""Tests for `GooglePlaySource` (motor/sources/google_play.py) - the only
`ReviewSource` adapter implemented so far (see CLAUDE.md's "ports and
adapters" decision).

None of these tests ever call the real `google_play_scraper` library or hit
the network: the underlying fetch function is monkeypatched in every test,
per the governance rule that tests must never depend on live external
services.
"""

from unittest.mock import MagicMock

import motor.sources.google_play as google_play_module
from motor.sources.base import ReviewSource
from motor.sources.google_play import GooglePlaySource


def test_google_play_source_satisfies_the_review_source_contract():
    # Confirms GooglePlaySource actually implements the ReviewSource ABC,
    # not just something that happens to have a similarly-named method.
    assert isinstance(GooglePlaySource(), ReviewSource)


def test_collect_calls_the_underlying_library_with_app_id_and_country(monkeypatch):
    fake_fetch = MagicMock(return_value=([{"reviewId": "abc"}], None))
    monkeypatch.setattr(google_play_module, "_fetch_reviews", fake_fetch)

    list(GooglePlaySource().collect(app_id="com.hevy.app", country="br"))

    fake_fetch.assert_called_once()
    call_args, call_kwargs = fake_fetch.call_args
    assert call_args[0] == "com.hevy.app"
    assert call_kwargs["country"] == "br"


def test_collect_returns_the_raw_dicts_unchanged(monkeypatch):
    # Per ReviewSource.collect's docstring: converting to the canonical
    # shape is normalize's job, not the adapter's. The adapter is a
    # pass-through over whatever the library hands back.
    raw_reviews = [
        {"reviewId": "abc", "content": "otimo app", "score": 5},
        {"reviewId": "def", "content": "trava direto", "score": 1},
    ]
    monkeypatch.setattr(
        google_play_module, "_fetch_reviews", MagicMock(return_value=(raw_reviews, None))
    )

    result = list(GooglePlaySource().collect(app_id="com.hevy.app", country="br"))

    assert result == raw_reviews


def test_collect_requests_a_bounded_pool_size_by_default(monkeypatch):
    # Governance rule: low request rate, no "fetch everything unbounded"
    # calls. google_play_scraper.reviews() satisfies a single request
    # internally up to MAX_COUNT_EACH_FETCH=4500 reviews before it would
    # need to loop for more - so that's the real ceiling for "still one
    # bounded call," not an arbitrary smaller number.
    fake_fetch = MagicMock(return_value=([], None))
    monkeypatch.setattr(google_play_module, "_fetch_reviews", fake_fetch)

    list(GooglePlaySource().collect(app_id="com.hevy.app", country="br"))

    count = fake_fetch.call_args.kwargs.get("count")
    assert count is not None, "collect() must request a bounded number of reviews, not unbounded"
    assert 0 < count <= 4500


def test_collect_accepts_a_custom_pool_size(monkeypatch):
    # Pool size (how many raw reviews to fetch) must be configurable by the
    # caller, not just accepted and silently ignored in favor of a fixed
    # default - this is what random_sample() draws its subsample from.
    fake_fetch = MagicMock(return_value=([], None))
    monkeypatch.setattr(google_play_module, "_fetch_reviews", fake_fetch)

    list(GooglePlaySource().collect(app_id="com.hevy.app", country="br", count=250))

    assert fake_fetch.call_args.kwargs.get("count") == 250
