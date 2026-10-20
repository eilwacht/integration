"""Which items a news watch shows."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from custom_components.eilwacht.keywords import KeywordFilter
from custom_components.eilwacht.model import NewsItem, Source
from custom_components.eilwacht.watch import (
    NATIONAL,
    Match,
    Watch,
    count_since,
    item_attributes,
)

BERLIN = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 10, 20, 18, 0, tzinfo=BERLIN)


def item(
    item_id: str,
    regions: tuple[int, ...] = (),
    hours_ago: float | None = 1,
    title: str = "Meldung",
) -> NewsItem:
    return NewsItem(
        id=item_id,
        source=Source.NEWS,
        title=title,
        region_ids=regions,
        published=NOW - timedelta(hours=hours_ago) if hours_ago is not None else None,
    )


def test_regions() -> None:
    watch = Watch(frozenset({1, 2}))
    assert watch.match(item("bw", (1,)))
    assert watch.match(item("by-bw", (2, 9)))
    assert watch.match(item("nrw", (10,))) is None
    assert watch.match(item("national")) is None


def test_national() -> None:
    watch = Watch(frozenset({NATIONAL}))
    assert watch.match(item("national"))
    assert watch.match(item("bw", (1,))) is None


def test_keywords() -> None:
    watch = Watch(frozenset({1}), KeywordFilter.parse("Streik*"))
    assert watch.match(item("a", (1,), title="Streiks in Ulm")) == Match(
        item("a", (1,), title="Streiks in Ulm"), ("Streik*",)
    )
    assert watch.match(item("b", (1,), title="Wetter")) is None


def test_matches_newest_first() -> None:
    watch = Watch(frozenset({1}))
    found = watch.matches(
        [
            item("old", (1,), 5),
            item("undated", (1,), None),
            item("new", (1,), 1),
            item("nrw", (10,)),
        ]
    )
    assert [m.item.id for m in found] == ["new", "old", "undated"]


def test_count_since() -> None:
    watch = Watch(frozenset({1}))
    found = watch.matches(
        [
            item("a", (1,), 1),
            item("b", (1,), 23),
            item("c", (1,), 25),
            item("d", (1,), None),
        ]
    )
    assert count_since(found, NOW) == 2


def test_item_attributes() -> None:
    news = NewsItem(
        id="x",
        source=Source.NEWS,
        title="Titel",
        topline="Ulm",
        url="https://www.tagesschau.de/x.html",
        published=NOW,
        region_ids=(1, 99),
    )
    assert item_attributes(news, ("Ulm",)) == {
        "title": "Titel",
        "topline": "Ulm",
        "summary": None,
        "url": "https://www.tagesschau.de/x.html",
        "published": "2026-10-20T18:00:00+02:00",
        "regions": ["Baden-Württemberg"],
        "ressort": None,
        "keywords": ["Ulm"],
    }
    assert "keywords" not in item_attributes(news)
