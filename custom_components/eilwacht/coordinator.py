"""Data update coordinators: breaking news (headerapp + homepage) and news by state."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .changes import NewItemTracker
from .const import (
    CONF_KEYWORDS,
    CONF_REGIONS,
    DOMAIN,
    FAILURES_BEFORE_ISSUE,
    HEADERAPP_INTERVAL,
    HOMEPAGE_FALLBACK_INTERVAL,
    NEWS_INTERVAL,
    SUBENTRY_WATCH,
)
from .keywords import KeywordFilter
from .model import NewsItem
from .sample import BreakingSample
from .seen import SeenStore
from .tagesschau import TagesschauClient, TagesschauError
from .watch import NATIONAL, Watch

_LOGGER = logging.getLogger(__name__)

SOURCE_NAMES = {
    "headerapp": "tagesschau.de (Eilmeldungen)",
    "news": "tagesschau.de (Nachrichten)",
}


@dataclass(frozen=True, slots=True)
class BreakingData:
    """Running alerts, and those that appeared with this update."""

    active: tuple[NewsItem, ...] = ()
    new: tuple[NewsItem, ...] = ()


@dataclass(frozen=True, slots=True)
class NewsData:
    """Latest news of all federal states any watch uses (and national news)."""

    items: tuple[NewsItem, ...] = ()


def watch_subentries(entry: ConfigEntry) -> list[ConfigSubentry]:
    """The news watch subentries of an entry.

    ConfigEntry.get_subentries_of_type() does not exist in HA 2026.3, the oldest
    supported version, so filter by hand.
    """
    return [s for s in entry.subentries.values() if s.subentry_type == SUBENTRY_WATCH]


def watch_from_subentry(subentry: ConfigSubentry) -> Watch:
    """Build the watch stored in a "watch" subentry."""
    return Watch(
        regions=frozenset(int(r) for r in subentry.data.get(CONF_REGIONS, ())),
        keywords=KeywordFilter.parse(subentry.data.get(CONF_KEYWORDS)),
    )


def watch_seen_name(subentry_id: str) -> str:
    """Name of a watch's tracker in the SeenStore."""
    return f"watch:{subentry_id}"


def watch_fingerprint(subentry: ConfigSubentry) -> str:
    """Settings that decide which items a watch shows (seen.py)."""
    regions = ",".join(str(r) for r in sorted(subentry.data.get(CONF_REGIONS, ())))
    return f"{regions}|{subentry.data.get(CONF_KEYWORDS, '')}"


def issue_id(key: str) -> str:
    """Repair issue id for a failing endpoint ("headerapp" or "news")."""
    return f"source_failed_{key}"


class _FailureTracking:
    """Counts failed polls in a row and raises/removes a repair issue."""

    hass: HomeAssistant
    failures: int = 0
    _key: str

    def _record_failure(self, error: str) -> None:
        self.failures += 1
        if self.failures < FAILURES_BEFORE_ISSUE[self._key]:
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id(self._key),
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="source_failed",
            translation_placeholders={
                "source": SOURCE_NAMES[self._key],
                "failures": str(self.failures),
                "error": error,
            },
        )

    def _record_success(self) -> None:
        if self.failures:
            _LOGGER.info("%s is reachable again", SOURCE_NAMES[self._key])
        self.failures = 0
        ir.async_delete_issue(self.hass, DOMAIN, issue_id(self._key))


class BreakingCoordinator(_FailureTracking, DataUpdateCoordinator[BreakingData]):
    """Polls headerapp every minute; api2u/homepage only stands in while it fails.

    Never both at once: a headerapp alert links to a page of its own
    (/eilmeldung/...), the homepage to the article, so one alert from both
    sources would be announced twice. Alerts that appeared while Home
    Assistant was restarting are announced (seen.py); without a recent saved
    state the first update learns running alerts silently.
    """

    _key = "headerapp"
    SEEN_NAME = "breaking"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: TagesschauClient,
        sample: BreakingSample,
        seen: SeenStore,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} breaking news",
            update_interval=HEADERAPP_INTERVAL,
            always_update=False,
        )
        self.client = client
        self.sample = sample
        self.failures = 0
        self.seen = seen
        self._tracker = NewItemTracker()
        seen.restore(self.SEEN_NAME, self._tracker)
        self._homepage_at: datetime | None = None
        self._homepage_breaking: tuple[NewsItem, ...] = ()
        self.homepage_error: str | None = None

    async def _async_update_data(self) -> BreakingData:
        now = dt_util.utcnow()
        fast: list[NewsItem] | None = None
        try:
            fast = await self.client.async_breaking_news()
        except TagesschauError as err:
            self._record_failure(str(err))
        except Exception as err:
            # A bug or an unexpected API change must not break anything else.
            _LOGGER.exception("Unexpected error polling headerapp")
            self._record_failure(repr(err))
        else:
            self._record_success()
            self._record_sample(fast)

        if fast is not None:
            self._homepage_at = None
            self._homepage_breaking = ()
            items: Iterable[NewsItem] = fast
        else:
            await self._async_poll_homepage(now)
            if self._homepage_at is None:
                raise UpdateFailed(
                    "tagesschau.de: neither headerapp nor homepage available"
                )
            items = self._homepage_breaking

        active: dict[str, NewsItem] = {}
        for item in items:
            active.setdefault(item.key, item)
        new = self._tracker.update(active.values())
        self.seen.save(self.SEEN_NAME, self._tracker)
        return BreakingData(active=tuple(active.values()), new=tuple(new))

    def _record_sample(self, parsed: list[NewsItem]) -> None:
        """Keep every response with an alert, even one the parser cannot read.

        The endpoint is undocumented; should its format change, a response
        that holds "breakingNews" but yields no alert is the one to record.
        """
        raw = self.client.last_headerapp
        if not isinstance(raw, dict) or not raw.get("breakingNews"):
            return
        if self.sample.record(raw) and not parsed:
            _LOGGER.warning(
                "tagesschau.de reports breaking news in an unknown format; "
                "please report it with the diagnostics download"
            )

    async def _async_poll_homepage(self, now: datetime) -> None:
        # A few seconds of tolerance: polls are not exactly one minute apart.
        if self._homepage_at and now - self._homepage_at < (
            HOMEPAGE_FALLBACK_INTERVAL - timedelta(seconds=5)
        ):
            return
        try:
            items = await self.client.async_homepage()
        except TagesschauError as err:
            self.homepage_error = str(err)
            return
        except Exception as err:
            _LOGGER.exception("Unexpected error polling homepage")
            self.homepage_error = repr(err)
            return
        self.homepage_error = None
        self._homepage_at = now
        self._homepage_breaking = tuple(item for item in items if item.breaking)


class NewsCoordinator(_FailureTracking, DataUpdateCoordinator[NewsData]):
    """Polls api2u/news once for all federal states the watches use.

    Listeners are called after every poll (always_update), so counts over the
    last 24 hours age even when no news arrives.
    """

    _key = "news"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: TagesschauClient,
        regions: frozenset[int],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} news",
            update_interval=NEWS_INTERVAL,
        )
        self.client = client
        self.regions = regions
        self.failures = 0

    async def _async_update_data(self) -> NewsData:
        states = sorted(r for r in self.regions if r != NATIONAL)
        items: dict[str, NewsItem] = {}
        try:
            if states:
                for item in await self.client.async_news(states):
                    items.setdefault(item.id, item)
            if NATIONAL in self.regions:
                for item in await self.client.async_news():
                    if not item.region_ids:
                        items.setdefault(item.id, item)
        except TagesschauError as err:
            self._record_failure(str(err))
            raise UpdateFailed(f"tagesschau.de: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error polling news")
            self._record_failure(repr(err))
            raise UpdateFailed(f"tagesschau.de: {err!r}") from err
        self._record_success()
        return NewsData(items=tuple(items.values()))


def diagnostics(coordinator: DataUpdateCoordinator[Any]) -> dict[str, Any]:
    """Common diagnostics of a coordinator."""
    return {
        "last_update_success": coordinator.last_update_success,
        "consecutive_failures": getattr(coordinator, "failures", None),
        "last_exception": (
            repr(coordinator.last_exception) if coordinator.last_exception else None
        ),
        "update_interval_seconds": (
            coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None
        ),
    }
