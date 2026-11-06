"""Lists of the most recent items, for the dashboard. Pure Python, no Home Assistant imports.

The sensors "last breaking news" and "last item" of a watch carry them in the
attribute RECENT, newest first, each entry with title, url, published, the
address of a small teaser image with its copyright and alt text (None without
one; never downloaded) and, for watches, the keywords found (empty without
keywords). Every entry has all these keys, None if unknown: Home Assistant's
markdown card renders templates strictly, a missing key breaks the card. The attribute is not recorded (the
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

# Keys of every entry, in this order; watch entries add KEYWORDS.
ENTRY_KEYS = (
    "title",
    "url",
    "published",
    "image",
    "image_copyright",
    "image_alt",
)
KEYWORDS = "keywords"
_OLDEST = datetime.min.replace(tzinfo=UTC)

type Entry = dict[str, Any]


def recent_entry(item: NewsItem, keywords: tuple[str, ...] | None = None) -> Entry:
    """An entry of the list; keywords (also empty ones) for watches only."""
    entry: Entry = {
        "title": item.title,
        "url": item.url,
        "published": item.published.isoformat() if item.published else None,
        "image": item.image,
        "image_copyright": item.image_copyright,
        "image_alt": item.image_alt,
    }
    if keywords is not None:
        entry[KEYWORDS] = list(keywords)
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


def restore_recent(
    value: Any, limit: int = RECENT_LIMIT, *, keywords: bool = False
) -> list[Entry]:
    """The list from a restored state attribute; unusable entries are skipped.

    Entries saved by older versions (or seeded from the attributes of a 0.2.x
    state) lack keys: they get all of them, None if unknown, and KEYWORDS
    (a list) if keywords is set.
    """
    if not isinstance(value, list):
        return []
    restored = []
    for saved in value:
        if not isinstance(saved, Mapping) or not isinstance(saved.get("title"), str):
            continue
        entry: Entry = {key: saved.get(key) for key in ENTRY_KEYS}
        if keywords:
            found = saved.get(KEYWORDS)
            entry[KEYWORDS] = (
                [k for k in found if isinstance(k, str)]
                if isinstance(found, list)
                else []
            )
        restored.append(entry)
    return restored[:limit]
