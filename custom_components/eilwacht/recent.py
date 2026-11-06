"""Lists of the most recent items, for the dashboard. Pure Python, no Home Assistant imports.

The sensors "last breaking news" and "last item" of a watch carry them in the
attribute RECENT, newest first, each entry with title, url, published (and the
keywords found, for watches with keywords). The attribute is not recorded (the
newest item is in the history already, the list would only bloat the
database); it survives restarts through the entity's restored state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from .model import NewsItem

RECENT = "recent"
RECENT_LIMIT = 5

_ENTRY_KEYS = ("title", "url", "published", "keywords")
_OLDEST = datetime.min.replace(tzinfo=UTC)

type Entry = dict[str, Any]


def recent_entry(item: NewsItem, keywords: tuple[str, ...] = ()) -> Entry:
    """An entry of the list."""
    entry: Entry = {
        "title": item.title,
        "url": item.url,
        "published": item.published.isoformat() if item.published else None,
    }
    if keywords:
        entry["keywords"] = list(keywords)
    return entry


def _identity(entry: Mapping[str, Any]) -> str:
    """Same item: the article path, as NewsItem.key; else the title."""
    url = entry.get("url")
    if isinstance(url, str) and (path := urlsplit(url).path.rstrip("/")):
        return path
    return f"title:{entry.get('title')}"


def _published(entry: Mapping[str, Any]) -> datetime:
    value = entry.get("published")
    if not isinstance(value, str):
        return _OLDEST
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return _OLDEST
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def add_recent(
    recent: Iterable[Entry], entry: Entry, limit: int = RECENT_LIMIT
) -> list[Entry]:
    """The list with entry first (the alert just shown).

    An older entry of the same item is dropped, so no item appears twice.
    """
    key = _identity(entry)
    return [entry, *(e for e in recent if _identity(e) != key)][:limit]


def merge_recent(
    entries: Iterable[Entry], recent: Iterable[Entry], limit: int = RECENT_LIMIT
) -> list[Entry]:
    """Current entries merged into the list, newest published first.

    A current entry replaces the listed one of the same item (e.g. a changed
    headline); listed items no longer in the source stay until newer ones
    push them out.
    """
    merged: dict[str, Entry] = {}
    for entry in (*entries, *recent):
        merged.setdefault(_identity(entry), entry)
    return sorted(merged.values(), key=_published, reverse=True)[:limit]


def restore_recent(value: Any, limit: int = RECENT_LIMIT) -> list[Entry]:
    """The list from a restored state attribute; unusable entries are skipped."""
    if not isinstance(value, list):
        return []
    restored = [
        {key: entry[key] for key in _ENTRY_KEYS if key in entry}
        for entry in value
        if isinstance(entry, Mapping) and isinstance(entry.get("title"), str)
    ]
    return restored[:limit]
