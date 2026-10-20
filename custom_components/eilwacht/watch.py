"""Which news items a news watch shows. Pure Python, no Home Assistant imports."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from .const import REGIONS
from .keywords import KeywordFilter
from .model import NewsItem

# Region id for national news: items without a federal state.
NATIONAL = 0

_OLDEST = datetime.min.replace(tzinfo=UTC)

# Keys of item_attributes(), e.g. for restoring them.
ITEM_KEYS = frozenset(
    {
        "title",
        "topline",
        "summary",
        "url",
        "published",
        "regions",
        "ressort",
        "keywords",
    }
)


@dataclass(frozen=True, slots=True)
class Match:
    """A news item shown by a watch, with the keywords it matched."""

    item: NewsItem
    keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Watch:
    """Federal states (or national news) plus an optional keyword filter."""

    regions: frozenset[int]
    keywords: KeywordFilter = field(default_factory=KeywordFilter)

    def match(self, item: NewsItem) -> Match | None:
        """The match if the watch shows this item, else None."""
        if item.region_ids:
            if not self.regions.intersection(item.region_ids):
                return None
        elif NATIONAL not in self.regions:
            return None
        found = self.keywords.matches(item)
        return None if found is None else Match(item, found)

    def matches(self, items: Iterable[NewsItem]) -> list[Match]:
        """All matches, newest first."""
        found = [m for item in items if (m := self.match(item))]
        return sorted(found, key=lambda m: m.item.published or _OLDEST, reverse=True)


def count_since(matches: Iterable[Match], now: datetime, hours: int = 24) -> int:
    """Number of matches published within the last hours."""
    since = now - timedelta(hours=hours)
    return sum(1 for m in matches if m.item.published and m.item.published >= since)


def item_attributes(
    item: NewsItem, keywords: tuple[str, ...] = ()
) -> dict[str, object]:
    """State and event attributes of a news item."""
    attributes: dict[str, object] = {
        "title": item.title,
        "topline": item.topline,
        "summary": item.summary,
        "url": item.url,
        "published": item.published.isoformat() if item.published else None,
        "regions": [REGIONS[r] for r in item.region_ids if r in REGIONS],
        "ressort": item.ressort,
    }
    if keywords:
        attributes["keywords"] = list(keywords)
    return attributes
