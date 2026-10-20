"""Fixtures for Home Assistant tests.

pytest-homeassistant-custom-component needs Linux (fcntl). Without it (local
Windows development) these tests are not collected; CI runs them.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from datetime import datetime
from typing import Any
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from custom_components.eilwacht.model import NewsItem, Source

BERLIN = ZoneInfo("Europe/Berlin")


def news_item(
    item_id: str,
    *,
    source: Source = Source.NEWS,
    title: str = "Meldung",
    regions: tuple[int, ...] = (),
    breaking: bool = False,
    hour: int = 12,
    day: int = 20,
) -> NewsItem:
    return NewsItem(
        id=item_id,
        source=source,
        title=title,
        url=f"https://www.tagesschau.de/{item_id}.html",
        published=datetime(2026, 10, day, hour, tzinfo=BERLIN),
        breaking=breaking,
        region_ids=regions,
    )


class FakeClient:
    """Stands in for TagesschauClient: set lists, or an exception to raise."""

    def __init__(self) -> None:
        self.breaking: list[NewsItem] | Exception = []
        self.homepage: list[NewsItem] | Exception = []
        self.news: dict[tuple[int, ...], list[NewsItem]] | Exception = {}
        self.last_headerapp: Any = None
        self.calls: list[str] = []

    async def async_breaking_news(self) -> list[NewsItem]:
        self.calls.append("headerapp")
        if isinstance(self.breaking, Exception):
            raise self.breaking
        self.last_headerapp = (
            {"breakingNews": [{"id": i.id, "headline": i.title} for i in self.breaking]}
            if self.breaking
            else {"liveStream": {}}
        )
        return list(self.breaking)

    async def async_homepage(self) -> list[NewsItem]:
        self.calls.append("homepage")
        if isinstance(self.homepage, Exception):
            raise self.homepage
        return list(self.homepage)

    async def async_news(self, regions: Any = ()) -> list[NewsItem]:
        key = tuple(sorted(regions))
        self.calls.append(f"news{list(key)}")
        if isinstance(self.news, Exception):
            raise self.news
        return list(self.news.get(key, []))


if importlib.util.find_spec("pytest_homeassistant_custom_component") is None:
    collect_ignore_glob = ["test_*.py"]
else:

    @pytest.fixture(autouse=True)
    def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
        """Allow loading custom_components/eilwacht in every test."""

    @pytest.fixture
    def client() -> Iterator[FakeClient]:
        """The Tagesschau client used by the integration."""
        fake = FakeClient()
        with patch("custom_components.eilwacht.TagesschauClient", return_value=fake):
            yield fake
