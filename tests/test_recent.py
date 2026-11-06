"""Lists of the most recent items (attribute "recent")."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from custom_components.eilwacht.model import NewsItem, Source
from custom_components.eilwacht.recent import (
    ENTRY_KEYS,
    RECENT_LIMIT,
    add_recent,
    merge_recent,
    recent_entry,
    restore_recent,
)
from custom_components.eilwacht.tagesschau import parse_api2u, parse_headerapp

from .conftest import load_fixture

BERLIN = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 10, 20, 18, 0, tzinfo=BERLIN)


def item(
    slug: str, hours_ago: float | None = 1, title: str = "Meldung", url: bool = True
) -> NewsItem:
    return NewsItem(
        id=slug,
        source=Source.NEWS,
        title=title,
        url=f"https://www.tagesschau.de/{slug}.html" if url else None,
        published=NOW - timedelta(hours=hours_ago) if hours_ago is not None else None,
    )


def titles(entries: list[dict]) -> list[str]:
    return [entry["title"] for entry in entries]


NO_IMAGE = {"image": None, "image_copyright": None, "image_alt": None}


def test_entry() -> None:
    assert recent_entry(item("a")) == {
        "title": "Meldung",
        "url": "https://www.tagesschau.de/a.html",
        "published": "2026-10-20T17:00:00+02:00",
        **NO_IMAGE,
    }
    assert recent_entry(item("a", None), ("Ulm",)) == {
        "title": "Meldung",
        "url": "https://www.tagesschau.de/a.html",
        "published": None,
        **NO_IMAGE,
        "keywords": ["Ulm"],
    }


def test_entries_from_fixtures() -> None:
    """Only fields the parsers fill: no invented API fields."""
    (alert,) = parse_headerapp(load_fixture("headerapp_breaking.json"))
    assert recent_entry(alert) == {
        "title": "Text 1",
        "url": "https://www.tagesschau.de/eilmeldung/eilmeldung-9580.html",
        "published": "2026-10-21T11:25:00+02:00",
        **NO_IMAGE,  # alerts have no teaser image
    }
    data = load_fixture("news_bw.json")
    items = parse_api2u(data, Source.NEWS)
    for raw, news in zip(data["news"], items, strict=True):
        entry = recent_entry(news)
        assert entry["title"] and entry["url"]
        assert datetime.fromisoformat(entry["published"]).tzinfo
        # Only the address of the small variant, with its copyright.
        assert entry["image"] == raw["teaserImage"]["imageVariants"]["1x1-144"]
        assert entry["image_copyright"] == raw["teaserImage"]["copyright"]
        assert entry["image_alt"] == raw["teaserImage"]["alttext"]


def test_entry_of_a_watch_without_keywords() -> None:
    assert recent_entry(item("a"), ())["keywords"] == []
    assert "keywords" not in recent_entry(item("a"))


def test_seeded_from_an_old_state() -> None:
    """Attributes of a 0.2.x state: no image keys, other keys to drop."""
    old = {
        "title": "Alt",
        "topline": None,
        "summary": "Satz",
        "url": "https://www.tagesschau.de/eilmeldung/eilmeldung-1.html",
        "published": "2026-10-25T18:02:00+01:00",
        "regions": [],
        "ressort": None,
        "attribution": "Quelle: tagesschau.de",
        "friendly_name": "Eilwacht Letzte Eilmeldung",
    }
    (entry,) = restore_recent([old])
    assert list(entry) == list(ENTRY_KEYS)
    assert entry["title"] == "Alt"
    assert entry["image"] is None


def test_add_newest_first_without_duplicates() -> None:
    recent: list[dict] = []
    for slug in ("a", "b", "c"):
        recent = add_recent(recent, recent_entry(item(slug, title=slug)))
    assert titles(recent) == ["c", "b", "a"]
    # The same alert again (same article path): moves up, not twice.
    recent = add_recent(recent, recent_entry(item("a", title="a neu")))
    assert titles(recent) == ["a neu", "c", "b"]


def test_add_keeps_the_limit() -> None:
    recent: list[dict] = []
    for n in range(RECENT_LIMIT + 2):
        recent = add_recent(recent, recent_entry(item(str(n), title=str(n))))
    assert titles(recent) == ["6", "5", "4", "3", "2"]
    assert len(add_recent(recent, recent_entry(item("x")), limit=3)) == 3


def test_add_without_url_by_title() -> None:
    recent = add_recent([], recent_entry(item("a", url=False, title="Video")))
    recent = add_recent(recent, recent_entry(item("b", url=False, title="Video")))
    assert len(recent) == 1


def test_merge_keeps_older_items_and_sorts() -> None:
    recent = merge_recent(
        [recent_entry(item(s, h, s)) for s, h in (("b", 2), ("a", 30))], []
    )
    assert titles(recent) == ["b", "a"]
    # "a" (30 h old) left the source window: it stays until newer ones come.
    recent = merge_recent([recent_entry(item("c", 1, "c"))], recent)
    assert titles(recent) == ["c", "b", "a"]
    # Unknown publication time sorts last.
    recent = merge_recent([recent_entry(item("d", None, "d"))], recent)
    assert titles(recent) == ["c", "b", "a", "d"]


def test_merge_updates_in_place_and_limits() -> None:
    recent = merge_recent([recent_entry(item("a", 2, "alt"))], [])
    recent = merge_recent([recent_entry(item("a", 2, "neu"))], recent)
    assert titles(recent) == ["neu"]

    many = [recent_entry(item(str(n), n, str(n))) for n in range(1, 9)]
    assert titles(merge_recent(many, [])) == ["1", "2", "3", "4", "5"]


def test_merge_compares_times_not_text() -> None:
    """Offsets differ (summer/winter time): compare instants."""
    summer = {"title": "s", "url": None, "published": "2026-10-25T02:30:00+02:00"}
    winter = {"title": "w", "url": None, "published": "2026-10-25T02:10:00+01:00"}
    assert titles(merge_recent([summer, winter], [])) == ["w", "s"]


def test_restore() -> None:
    saved = [
        {"title": "a", "url": "u", "published": None, "keywords": ["x"], "x": 1},
        {"title": "b", "image": "https://i/b.jpg", "image_copyright": "C"},
        {"url": "ohne Titel"},
        "kaputt",
    ]
    # Always the full set of keys, None if missing (Home Assistant's markdown
    # card is strict: a missing key empties the whole card).
    assert restore_recent(saved) == [
        {"title": "a", "url": "u", "published": None, **NO_IMAGE},
        {
            "title": "b",
            "url": None,
            "published": None,
            "image": "https://i/b.jpg",
            "image_copyright": "C",
            "image_alt": None,
        },
    ]
    assert restore_recent(saved, keywords=True) == [
        {"title": "a", "url": "u", "published": None, **NO_IMAGE, "keywords": ["x"]},
        {
            "title": "b",
            "url": None,
            "published": None,
            "image": "https://i/b.jpg",
            "image_copyright": "C",
            "image_alt": None,
            "keywords": [],
        },
    ]
    assert restore_recent(None) == []
    assert restore_recent({"title": "a"}) == []
    assert len(restore_recent([{"title": str(n)} for n in range(9)])) == RECENT_LIMIT
