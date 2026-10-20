"""Sensors: last breaking news alert, last item and 24-hour count of a news watch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import EilwachtConfigEntry
from .coordinator import watch_subentries
from .entity import BreakingEntity, WatchEntity
from .model import NewsItem
from .watch import ITEM_KEYS, count_since, item_attributes

# HA truncates longer states; titles rarely come close.
MAX_STATE_LENGTH = 255


def _state(item: NewsItem) -> str:
    return item.title[:MAX_STATE_LENGTH]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EilwachtConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Last alert, plus last item and count per news watch."""
    async_add_entities([LastBreakingNewsSensor(entry, "last_breaking")])
    for subentry in watch_subentries(entry):
        async_add_entities(
            [
                LastNewsSensor(entry, subentry, "last_news"),
                NewsCountSensor(entry, subentry, "news_24h"),
            ],
            config_subentry_id=subentry.subentry_id,
        )


class LastBreakingNewsSensor(BreakingEntity, SensorEntity, RestoreEntity):
    """Title of the newest alert; kept after the alert ends and across restarts."""

    def __init__(self, entry: EilwachtConfigEntry, key: str) -> None:
        super().__init__(entry, key)
        self._attr_native_value: str | None = None
        self._attr_extra_state_attributes: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        """Restore the last alert; without one, take a running alert."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._attr_native_value = last.state
            self._attr_extra_state_attributes = {
                k: v for k, v in last.attributes.items() if k in ITEM_KEYS
            }
        data = self.coordinator.data
        if self._attr_native_value is None and data and data.active:
            self._show(data.active[0])

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if data and data.new:
            self._show(data.new[-1])  # new alerts come oldest first
        super()._handle_coordinator_update()

    def _show(self, item: NewsItem) -> None:
        self._attr_native_value = _state(item)
        self._attr_extra_state_attributes = item_attributes(item)


class LastNewsSensor(WatchEntity, SensorEntity):
    """Title of the newest item the watch shows."""

    @property
    def native_value(self) -> str | None:
        matches = self.watch.matches(self.items)
        return _state(matches[0].item) if matches else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        matches = self.watch.matches(self.items)
        return item_attributes(matches[0].item, matches[0].keywords) if matches else {}


class NewsCountSensor(WatchEntity, SensorEntity):
    """Number of items the watch shows from the last 24 hours."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return count_since(self.watch.matches(self.items), dt_util.utcnow())
