"""Parsing the Tagesschau endpoints against recorded fixtures."""

from __future__ import annotations

import copy
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.eilwacht.model import Source
from custom_components.eilwacht.tagesschau import (
    TagesschauError,
    parse_api2u,
    parse_date,
    parse_headerapp,
)
from tests.conftest import load_fixture

BERLIN = ZoneInfo("Europe/Berlin")

# Shape of a running alert as the Telegram alert bot reads it (handler/check.go).
# Not yet seen in a recording: replace with a real fixture once one exists.
HEADERAPP_ALERT = {
    "liveStream": {},
    "breakingNews": [
        {
            "id": "eil-2",
            "headline": "Zweite Eilmeldung",
            "text": "",
            "url": "/inland/eil-zwei-100.html",
            "date": "Stand: 20.10.2026 18:05 Uhr",
        },
        {
            "id": "eil-1",
            "headline": "Erste Eilmeldung",
            "text": "Mehr in Kürze.",
            "url": "https://www.tagesschau.de/ausland/eil-eins-100.html",
            "date": "Stand: 20.10.2026 17:30 Uhr",
        },
        {"id": "", "headline": "ohne id und url"},
        "kein Objekt",
    ],
}


def test_headerapp_without_alert() -> None:
    assert parse_headerapp(load_fixture("headerapp.json")) == []


def test_headerapp_alert() -> None:
    first, second = parse_headerapp(HEADERAPP_ALERT)
    assert first.id == "eil-2"
    assert first.source is Source.HEADERAPP
    assert first.breaking
    assert first.summary is None
    assert first.url == "https://www.tagesschau.de/inland/eil-zwei-100.html"
    assert first.published == datetime(2026, 10, 20, 18, 5, tzinfo=BERLIN)
    assert second.summary == "Mehr in Kürze."
    assert second.key == "/ausland/eil-eins-100.html"


def test_headerapp_unexpected_response() -> None:
    with pytest.raises(TagesschauError):
        parse_headerapp(["kein", "Objekt"])


def test_homepage() -> None:
    items = parse_api2u(load_fixture("homepage.json"), Source.HOMEPAGE)
    assert items
    assert all(item.source is Source.HOMEPAGE for item in items)
    assert all(item.published and item.published.tzinfo for item in items)
    assert all(item.url and item.url.startswith("https://") for item in items)
    assert not any(item.breaking for item in items)
    # Regional items carry exactly one federal state, top news none.
    assert any(len(item.region_ids) == 1 for item in items)
    assert any(item.region_ids == () for item in items)


def test_homepage_breaking_news_flag() -> None:
    data = copy.deepcopy(load_fixture("homepage.json"))
    data["news"][0]["breakingNews"] = True
    items = parse_api2u(data, Source.HOMEPAGE)
    assert [item.breaking for item in items].count(True) == 1


def test_regional_news() -> None:
    items = parse_api2u(load_fixture("news_bw.json"), Source.NEWS)
    assert items
    assert all(item.region_ids == (1,) for item in items)
    assert all(item.ressort is None for item in items)
    assert all(item.tags for item in items)


def test_news_videos_have_no_article_url() -> None:
    data = load_fixture("news.json")
    items = parse_api2u(data, Source.NEWS)
    assert len(items) == len(data["news"])
    ids = [item.id for item in items]
    assert len(ids) == len(set(ids))


def test_api2u_unexpected_response() -> None:
    with pytest.raises(TagesschauError):
        parse_api2u({"type": "error"}, Source.NEWS)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "2026-10-20T14:23:47.761+02:00",
            datetime(2026, 10, 20, 14, 23, 47, 761000, tzinfo=BERLIN),
        ),
        ("Stand: 20.10.2026 17:30 Uhr", datetime(2026, 10, 20, 17, 30, tzinfo=BERLIN)),
        ("20.10.2026, 9:05 Uhr", datetime(2026, 10, 20, 9, 5, tzinfo=BERLIN)),
        ("Stand: gestern", None),
        ("31.02.2026 10:00", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_date(value: object, expected: datetime | None) -> None:
    assert parse_date(value) == expected
