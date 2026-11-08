"""Which items a news watch shows."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from custom_components.eilwacht.keywords import KeywordFilter
from custom_components.eilwacht.model import NewsItem, Source
from custom_components.eilwacht.watch import (
    NATIONAL,
    SUMMARY_KEYS,
    Match,
    Watch,
    count_since,
    item_attributes,
    settings_summary,
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
        "image": None,
        "image_copyright": None,
        "image_alt": None,
        "keywords": ["Ulm"],
    }
    assert "keywords" not in item_attributes(news)


def summary_texts(language: str) -> dict[str, str]:
    name = "strings.json" if language == "en" else f"translations/{language}.json"
    path = Path(__file__).parent.parent / "custom_components" / "eilwacht" / name
    strings = json.loads(path.read_text(encoding="utf-8"))
    return strings["selector"]["watch_summary"]["options"]


def test_summary_texts_complete() -> None:
    for language in ("en", "de"):
        assert set(summary_texts(language)) == set(SUMMARY_KEYS)


def test_summary_german() -> None:
    texts = summary_texts("de")
    assert settings_summary([1], "Stuttgart, *streik, -Fußball", texts) == (
        "- Regionalnachrichten aus Baden-Württemberg, keine bundesweiten Nachrichten\n"
        r"- Stichworte: Stuttgart, \*streik"
        " (eines genügt, Groß- und Kleinschreibung egal)\n"
        "- Ausgeschlossen: Fußball"
    )
    assert settings_summary([0, 2, 1], "", texts) == (
        "- Regionalnachrichten aus Baden-Württemberg, Bayern,"
        " dazu bundesweite Nachrichten\n"
        "- Keine Stichworte: jede Meldung"
    )


def test_summary_english() -> None:
    texts = summary_texts("en")
    assert settings_summary([NATIONAL], "-Fußball", texts) == (
        "- Only Germany-wide news (without a federal state)\n"
        "- No keywords: every item\n"
        "- Excluded: Fußball"
    )


def test_summary_shows_keywords_literally() -> None:
    texts = {key: "{regions}{keywords}" for key in SUMMARY_KEYS}
    lines = settings_summary([1], "a_b, [x](y), <b>", texts).splitlines()
    assert lines[1] == r"- {regions}a\_b, \[x\](y), \<b\>"
