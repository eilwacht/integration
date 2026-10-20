"""Keyword filter."""

from __future__ import annotations

import pytest

from custom_components.eilwacht.keywords import KeywordFilter
from custom_components.eilwacht.model import NewsItem, Source


def item(title: str, tags: tuple[str, ...] = ()) -> NewsItem:
    return NewsItem(id="x", source=Source.NEWS, title=title, tags=tags)


def test_parse() -> None:
    parsed = KeywordFilter.parse(" Warnstreik,  S-Bahn   Stuttgart , ,-Fußball, *, - ")
    assert parsed.include == ("Warnstreik", "S-Bahn Stuttgart")
    assert parsed.exclude == ("Fußball",)


@pytest.mark.parametrize(
    ("terms", "title", "expected"),
    [
        ("Warnstreik", "Warnstreik bei der Bahn", ("Warnstreik",)),
        ("warnstreik", "WARNSTREIK", ("warnstreik",)),
        ("Warnstreik", "Warnstreiks angekündigt", None),
        ("Streik*", "Streiks angekündigt", ("Streik*",)),
        ("*streik", "Bahnstreik ab Montag", ("*streik",)),
        ("Bahn", "Autobahn gesperrt", None),
        ("Bahn", "S-Bahn fällt aus", None),
        ("S-Bahn", "S-Bahn fällt aus", ("S-Bahn",)),
        ("A8", "Unfall auf der A8.", ("A8",)),
        (
            "S-Bahn Stuttgart",
            "Störung bei der S-Bahn\n Stuttgart",
            ("S-Bahn Stuttgart",),
        ),
        ("S-Bahn Stuttgart", "S-Bahn in Stuttgart", None),
        ("Stuttgart, Ulm", "Ulm und Stuttgart", ("Stuttgart", "Ulm")),
        ("Stuttgart, -Fußball", "Fußball in Stuttgart", None),
        ("-Fußball", "Wetter in Stuttgart", ()),
        ("", "irgendwas", ()),
    ],
)
def test_matches(terms: str, title: str, expected: tuple[str, ...] | None) -> None:
    assert KeywordFilter.parse(terms).matches(item(title)) == expected


def test_matches_topline_summary_and_tags() -> None:
    news = NewsItem(
        id="x",
        source=Source.NEWS,
        title="Titel",
        topline="Baden-Württemberg",
        summary="Erster Satz über Ulm.",
        tags=("Verdi",),
    )
    found = KeywordFilter.parse("Baden-Württemberg, Ulm, Verdi").matches(news)
    assert found == ("Baden-Württemberg", "Ulm", "Verdi")


def test_bool() -> None:
    assert not KeywordFilter.parse(" , ")
    assert KeywordFilter.parse("-Fußball")
