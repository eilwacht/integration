"""Fetching and parsing the Tagesschau endpoints. Pure Python, no Home Assistant imports.

Field names are verified against tests/fixtures (docs/ENTWICKLUNG.md, section 2),
except the headerapp alert fields: known only from the Telegram alert bot
(id, headline, text, url, date) until a real alert has been recorded.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import aiohttp

from .const import (
    BASE_URL,
    HEADERAPP_URL,
    HOMEPAGE_URL,
    NEWS_URL,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from .model import NewsItem, Source

_LOGGER = logging.getLogger(__name__)

BERLIN = ZoneInfo("Europe/Berlin")
# headerapp "date" is display text, e.g. "Stand: 20.10.2026 17:30 Uhr" (format
# assumed from the alert bot, which strips "Stand: ").
_DISPLAY_DATE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4}),?\s+(\d{1,2}):(\d{2})")


class TagesschauError(Exception):
    """An endpoint could not be fetched or its data is unusable."""


def parse_date(value: Any) -> datetime | None:
    """ISO timestamp (api2u) or German display text (headerapp); None if neither."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        match = _DISPLAY_DATE.search(value)
        if not match:
            return None
        day, month, year, hour, minute = map(int, match.groups())
        try:
            return datetime(year, month, day, hour, minute, tzinfo=BERLIN)
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=BERLIN)


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def parse_headerapp(data: Any) -> list[NewsItem]:
    """Breaking news alerts from json/headerapp, newest first.

    The key "breakingNews" is missing while no alert is running.
    """
    if not isinstance(data, dict):
        raise TagesschauError("headerapp: unexpected response")
    items = []
    for raw in data.get("breakingNews") or ():
        if not isinstance(raw, dict):
            continue
        title = _text(raw.get("headline"))
        url = _text(raw.get("url"))
        item_id = _text(raw.get("id")) or url
        if not title or not item_id:
            _LOGGER.debug("Skipping headerapp alert without id or headline: %s", raw)
            continue
        items.append(
            NewsItem(
                id=item_id,
                source=Source.HEADERAPP,
                title=title,
                summary=_text(raw.get("text")),
                url=urljoin(BASE_URL, url) if url else None,
                published=parse_date(raw.get("date")),
                breaking=True,
            )
        )
    return items


def _api2u_item(raw: dict[str, Any], source: Source) -> NewsItem | None:
    title = _text(raw.get("title"))
    item_id = _text(raw.get("sophoraId")) or _text(raw.get("externalId"))
    if not title or not item_id:
        return None
    region_ids = tuple(
        region for region in raw.get("regionIds") or () if isinstance(region, int)
    )
    tags = tuple(
        tag["tag"]
        for tag in raw.get("tags") or ()
        if isinstance(tag, dict) and _text(tag.get("tag"))
    )
    return NewsItem(
        id=item_id,
        source=source,
        title=title,
        topline=_text(raw.get("topline")),
        summary=_text(raw.get("firstSentence")),
        url=_text(raw.get("detailsweb")) or _text(raw.get("shareURL")),
        published=parse_date(raw.get("date")),
        breaking=raw.get("breakingNews") is True,
        ressort=_text(raw.get("ressort")),
        region_ids=region_ids,
        tags=tags,
    )


def parse_api2u(data: Any, source: Source) -> list[NewsItem]:
    """Items of api2u/homepage or api2u/news ("news" and "regional" lists)."""
    if not isinstance(data, dict) or not isinstance(data.get("news"), list):
        raise TagesschauError(f"{source}: unexpected response")
    items = []
    for section in ("news", "regional"):
        for raw in data.get(section) or ():
            if isinstance(raw, dict) and (item := _api2u_item(raw, source)):
                items.append(item)
    return items


class TagesschauClient:
    """Fetches the three endpoints. One instance per Home Assistant instance."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def async_breaking_news(self) -> list[NewsItem]:
        """Running breaking news alerts (fast source)."""
        return parse_headerapp(await self._get_json(HEADERAPP_URL))

    async def async_homepage(self) -> list[NewsItem]:
        """Homepage items: top news and one regional item per state."""
        return parse_api2u(await self._get_json(HOMEPAGE_URL), Source.HOMEPAGE)

    async def async_news(self, regions: Iterable[int] = ()) -> list[NewsItem]:
        """Latest news, optionally only from the given federal states."""
        params = {"regions": ",".join(str(r) for r in sorted(regions))}
        data = await self._get_json(NEWS_URL, params if params["regions"] else None)
        return parse_api2u(data, Source.NEWS)

    async def _get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        """GET a URL and decode JSON, mapping every failure to TagesschauError."""
        try:
            async with self._session.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except TimeoutError as err:
            raise TagesschauError(f"Timeout fetching {url}") from err
        except aiohttp.ClientResponseError as err:
            raise TagesschauError(f"HTTP {err.status} fetching {url}") from err
        except aiohttp.ClientError as err:
            raise TagesschauError(f"Error fetching {url}: {err}") from err
        except ValueError as err:
            raise TagesschauError(f"Invalid JSON from {url}") from err
