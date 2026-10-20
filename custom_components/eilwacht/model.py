"""Common data model. Pure Python, no Home Assistant imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit


class Source(StrEnum):
    """Endpoint an item was read from."""

    HEADERAPP = "headerapp"
    HOMEPAGE = "homepage"
    NEWS = "news"


@dataclass(frozen=True, slots=True)
class NewsItem:
    """A news item or breaking news alert."""

    id: str  # id within its source: headerapp "id", api2u "sophoraId"
    source: Source
    title: str
    topline: str | None = None
    # api2u "firstSentence" or the headerapp alert "text"
    summary: str | None = None
    url: str | None = None  # absolute; None for videos
    published: datetime | None = None  # timezone-aware
    breaking: bool = False
    ressort: str | None = None
    region_ids: tuple[int, ...] = ()
    tags: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        """Identity across sources: the article path, else the source id.

        headerapp and api2u use different ids for the same alert; both link to
        the same article on tagesschau.de.
        """
        if self.url:
            path = urlsplit(self.url).path.rstrip("/")
            if path:
                return path
        return f"{self.source}:{self.id}"

    @property
    def text(self) -> str:
        """All searchable text, for keyword matching."""
        parts = (self.topline, self.title, self.summary, *self.tags)
        return " ".join(part for part in parts if part)
