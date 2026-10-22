"""Detecting new items between polls."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.eilwacht.changes import NewItemTracker
from custom_components.eilwacht.model import NewsItem, Source

BERLIN = ZoneInfo("Europe/Berlin")


def item(
    item_id: str,
    source: Source = Source.NEWS,
    url: str | None = None,
    hour: int | None = None,
) -> NewsItem:
    return NewsItem(
        id=item_id,
        source=source,
        title=item_id,
        url=url,
        published=datetime(2026, 10, 20, hour, tzinfo=BERLIN)
        if hour is not None
        else None,
    )


def test_first_update_only_learns() -> None:
    tracker = NewItemTracker()
    assert tracker.update([item("a"), item("b")]) == []
    assert tracker.update([item("a"), item("b")]) == []
    assert tracker.update([item("c"), item("a")]) == [item("c")]


def test_new_items_oldest_first() -> None:
    tracker = NewItemTracker()
    tracker.update([])
    new = tracker.update(
        [item("late", hour=18), item("undated"), item("early", hour=9)]
    )
    assert [n.id for n in new] == ["undated", "early", "late"]


def test_same_article_from_two_sources_is_reported_once() -> None:
    tracker = NewItemTracker()
    tracker.update([])
    url = "https://www.tagesschau.de/inland/eil-100.html"
    assert tracker.update([item("eil-1", Source.HEADERAPP, url)])
    assert tracker.update([item("eil-100", Source.HOMEPAGE, url + "?x=1")]) == []


def test_without_url_ids_of_different_sources_differ() -> None:
    tracker = NewItemTracker()
    tracker.update([item("a", Source.HEADERAPP)])
    assert tracker.update([item("a", Source.NEWS)]) == [item("a", Source.NEWS)]


def test_memory_is_bounded() -> None:
    tracker = NewItemTracker(max_size=2)
    tracker.update([item("a"), item("b"), item("c")])
    # "a" was forgotten and counts as new again.
    assert tracker.update([item("a")]) == [item("a")]


def test_restored_tracker_reports_items_since_the_restart() -> None:
    before = NewItemTracker()
    before.update([item("a", hour=8), item("b", hour=9)])

    after = NewItemTracker()
    after.restore(before.keys, datetime(2026, 10, 20, 10, tzinfo=BERLIN))
    new = after.update(
        [
            item("a", hour=8),  # seen before the restart
            item("old", hour=9),  # older than the cutoff: not news
            item("undated"),
            item("c", hour=11),  # appeared during the restart
        ]
    )
    assert [n.id for n in new] == ["c"]
    # The cutoff only applies to the first update after restoring.
    assert after.update([item("late", hour=7)]) == [item("late", hour=7)]


def test_keys_keep_order() -> None:
    tracker = NewItemTracker()
    tracker.update([item("a"), item("b")])
    tracker.update([item("c")])
    assert tracker.keys == ["news:a", "news:b", "news:c"]
