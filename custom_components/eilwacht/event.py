"""Event entities: a new breaking news alert, a new item of a news watch."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EilwachtConfigEntry
from .changes import NewItemTracker
from .const import EVENT_BREAKING, EVENT_NEWS
from .coordinator import BreakingData, watch_subentries
from .entity import BreakingEntity, WatchEntity
from .watch import item_attributes


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EilwachtConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """The breaking news event plus one event entity per news watch."""
    async_add_entities([BreakingNewsEvent(entry, "breaking")])
    for subentry in watch_subentries(entry):
        async_add_entities(
            [WatchNewsEvent(entry, subentry, "news")],
            config_subentry_id=subentry.subentry_id,
        )


class BreakingNewsEvent(BreakingEntity, EventEntity):
    """Fires once per new alert; alerts running at startup are not announced."""

    def __init__(self, entry: EilwachtConfigEntry, key: str) -> None:
        super().__init__(entry, key)
        self._attr_event_types = [EVENT_BREAKING]
        # Each update's new alerts fire once, even if listeners run again.
        self._handled: BreakingData | None = entry.runtime_data.breaking.data

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if data is None or data is self._handled:
            return
        self._handled = data
        for item in data.new:
            # One state write per alert, so automations see each of them.
            self._trigger_event(EVENT_BREAKING, item_attributes(item))
            self.async_write_ha_state()


class WatchNewsEvent(WatchEntity, EventEntity):
    """Fires once per new item the watch shows.

    The first data after a (re)start is learned without announcements.
    """

    def __init__(
        self, entry: EilwachtConfigEntry, subentry: ConfigSubentry, key: str
    ) -> None:
        super().__init__(entry, subentry, key)
        self._attr_event_types = [EVENT_NEWS]
        self._tracker = NewItemTracker()
        if self.coordinator.data is not None:
            self._tracker.update(m.item for m in self.watch.matches(self.items))

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data is None:
            return
        matches = {m.item.key: m for m in self.watch.matches(self.items)}
        for item in self._tracker.update(m.item for m in matches.values()):
            self._trigger_event(
                EVENT_NEWS, item_attributes(item, matches[item.key].keywords)
            )
            self.async_write_ha_state()
        self.async_write_ha_state()
