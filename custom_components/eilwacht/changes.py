"""Detecting new items between polls. Pure Python, no Home Assistant imports."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from .model import NewsItem

_OLDEST = datetime.min.replace(tzinfo=UTC)


class NewItemTracker:
    """Remembers which items were seen, by NewsItem.key.

    Without a restored state, the first update only learns the current state:
    nothing is reported that was already there, as the Telegram alert bot
    does. Keys are shared across sources, so an alert seen in headerapp is not
    reported again when it shows up in api2u.
    """

    def __init__(self, max_size: int = 2000) -> None:
        self._seen: dict[str, None] = {}
        self._initialized = False
        self._max_size = max_size
        self._not_before: datetime | None = None

    @property
    def keys(self) -> list[str]:
        """Seen keys, oldest first (for saving)."""
        return list(self._seen)

    def restore(self, keys: Iterable[str], not_before: datetime) -> None:
        """Continue from a saved state instead of learning silently.

        The next update reports the items not seen before, but only those
        published at or after not_before (when the state was saved): items
        that only now enter the window of the source are not news.
        """
        self._seen = dict.fromkeys(keys)
        self._initialized = True
        self._not_before = not_before

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
        if self._not_before is not None:
            cutoff, self._not_before = self._not_before, None
            new = [item for item in new if item.published and item.published >= cutoff]
        return sorted(new, key=lambda item: item.published or _OLDEST)
