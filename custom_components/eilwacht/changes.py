"""Detecting new items between polls. Pure Python, no Home Assistant imports."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from .model import NewsItem

_OLDEST = datetime.min.replace(tzinfo=UTC)


class NewItemTracker:
    """Remembers which items were seen, by NewsItem.key.

    The first update only learns the current state: after a (re)start nothing
    is reported that was already there, as the Telegram alert bot does. Keys
    are shared across sources, so an alert seen in headerapp is not reported
    again when it shows up in api2u.
    """

    def __init__(self, max_size: int = 2000) -> None:
        self._seen: dict[str, None] = {}
        self._initialized = False
        self._max_size = max_size

    def update(self, items: Iterable[NewsItem]) -> list[NewsItem]:
        """Remember the items; return the unseen ones, oldest first."""
        new = []
        for item in items:
            if item.key in self._seen:
                continue
            self._seen[item.key] = None
            new.append(item)
        while len(self._seen) > self._max_size:
            del self._seen[next(iter(self._seen))]
        if not self._initialized:
            self._initialized = True
            return []
        return sorted(new, key=lambda item: item.published or _OLDEST)
