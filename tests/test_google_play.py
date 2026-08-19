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
from motor.sources.google_play import AppSearchResult, GooglePlaySource, search_apps


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


# ---------------------------------------------------------------------------
# search_apps() - lets a PM type an app's name instead of having to already
# know its Google Play package id. Verified live against real search
# results before being built here (see docs/session-history.md): the
# underlying library loses the app id specifically for Google's "exact
# match" top card, which is usually the exact app someone searched for.
# ---------------------------------------------------------------------------
def test_search_apps_calls_the_underlying_library_with_query_and_country(monkeypatch):
    fake_search = MagicMock(return_value=[])
    monkeypatch.setattr(google_play_module, "_search_apps_raw", fake_search)

    search_apps("hevy", country="br")

    fake_search.assert_called_once()
    call_args, call_kwargs = fake_search.call_args
    assert call_args[0] == "hevy"
    assert call_kwargs["country"] == "br"


def test_search_apps_maps_fields_into_appsearchresult_objects(monkeypatch):
    raw_results = [
        {"appId": "com.hevy", "title": "Hevy", "developer": "Hevy Inc", "icon": "http://icon", "score": 4.9},
    ]
    monkeypatch.setattr(google_play_module, "_search_apps_raw", MagicMock(return_value=raw_results))

    [result] = search_apps("hevy")

    assert result == AppSearchResult(
        app_id="com.hevy", title="Hevy", developer="Hevy Inc", icon_url="http://icon", score=4.9
    )


def test_search_apps_recovers_a_missing_top_result_app_id(monkeypatch):
    # The library's real, verified bug: the top result's appId comes back
    # None even though the app genuinely exists and every other field
    # (title, developer, ...) is correct.
    raw_results = [{"appId": None, "title": "Hevy", "developer": "Hevy Inc", "icon": None, "score": 4.9}]
    monkeypatch.setattr(google_play_module, "_search_apps_raw", MagicMock(return_value=raw_results))
    monkeypatch.setattr(google_play_module, "_recover_top_result_app_id", MagicMock(return_value="com.hevy"))

    [result] = search_apps("hevy")

    assert result.app_id == "com.hevy"


def test_search_apps_drops_a_result_when_the_id_cannot_be_recovered(monkeypatch):
    raw_results = [{"appId": None, "title": "Ghost App", "developer": "?", "icon": None, "score": None}]
    monkeypatch.setattr(google_play_module, "_search_apps_raw", MagicMock(return_value=raw_results))
    monkeypatch.setattr(google_play_module, "_recover_top_result_app_id", MagicMock(return_value=None))

    result = search_apps("ghost")

    # An entry with no usable id would be a dead end in the UI (unclickable),
    # so it's excluded rather than passed through broken.
    assert result == []


def test_search_apps_passes_limit_through_as_n_hits(monkeypatch):
    fake_search = MagicMock(return_value=[])
    monkeypatch.setattr(google_play_module, "_search_apps_raw", fake_search)

    search_apps("hevy", limit=5)

    assert fake_search.call_args.kwargs.get("n_hits") == 5


def test_search_apps_returns_empty_list_when_the_library_returns_no_matches(monkeypatch):
    monkeypatch.setattr(google_play_module, "_search_apps_raw", MagicMock(return_value=[]))

    assert search_apps("xyzzynonexistentapp123") == []


def test_recover_top_result_app_id_extracts_the_first_details_link(monkeypatch):
    fake_html = """
    <html><body>
      <a href="/store/apps/details?id=com.hevy&hl=en">Hevy</a>
      <a href="/store/apps/details?id=com.hevycoach.app&hl=en">Hevy Coach</a>
    </body></html>
    """
    monkeypatch.setattr(google_play_module, "_fetch_search_page", MagicMock(return_value=fake_html))

    app_id = google_play_module._recover_top_result_app_id("hevy", "us")

    assert app_id == "com.hevy"


def test_recover_top_result_app_id_returns_none_when_no_link_is_found(monkeypatch):
    monkeypatch.setattr(google_play_module, "_fetch_search_page", MagicMock(return_value="<html></html>"))

    assert google_play_module._recover_top_result_app_id("nothing", "us") is None
