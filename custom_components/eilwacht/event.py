"""Event entities: a new breaking news alert, a new item of a news watch."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EilwachtConfigEntry
from .changes import NewItemTracker
from .const import EVENT_BREAKING, EVENT_NEWS
from .coordinator import (
    BreakingData,
    watch_fingerprint,
    watch_seen_name,
    watch_subentries,
)
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


def _after_first_state(entity: EventEntity, job: Callable[[], None]) -> None:
    """Run job once Home Assistant has written the entity's first state.

    Events fired while the entity is being added would be its first state,
    a change "from nothing". Automations (and the bundled blueprints) ignore
    exactly that, as it is what a restart looks like.
    """
    handle = entity.hass.loop.call_soon(job)
    entity.async_on_remove(handle.cancel)


class BreakingNewsEvent(BreakingEntity, EventEntity):
    """Fires once per new alert.

    Alerts that appeared while Home Assistant restarted are already in the
    data of the first update (seen.py), so it is handled when added.
    """

    def __init__(self, entry: EilwachtConfigEntry, key: str) -> None:
        super().__init__(entry, key)
        self._attr_event_types = [EVENT_BREAKING]
        # Each update's new alerts fire once, even if listeners run again.
        self._handled: BreakingData | None = None

    async def async_added_to_hass(self) -> None:
        """Announce alerts of the first update, once the entity is in place."""
        await super().async_added_to_hass()
        _after_first_state(self, self._handle_coordinator_update)

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

    Items that appeared while Home Assistant restarted are announced (seen.py);
    without a recent saved state, or after the watch was changed, the first
    data is learned without announcements.
    """

    def __init__(
        self, entry: EilwachtConfigEntry, subentry: ConfigSubentry, key: str
    ) -> None:
        super().__init__(entry, subentry, key)
        self._attr_event_types = [EVENT_NEWS]
        self._tracker = NewItemTracker()
        self._seen = entry.runtime_data.seen
        self._seen_name = watch_seen_name(subentry.subentry_id)
        self._fingerprint = watch_fingerprint(subentry)

    async def async_added_to_hass(self) -> None:
        """Continue from the saved state, then handle the current data."""
        await super().async_added_to_hass()
        self._seen.restore(self._seen_name, self._tracker, self._fingerprint)
        _after_first_state(self, self._handle_coordinator_update)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._process()
        self.async_write_ha_state()

    @callback
    def _process(self) -> None:
        if self.coordinator.data is None:
            return
        matches = {m.item.key: m for m in self.watch.matches(self.items)}
        for item in self._tracker.update(m.item for m in matches.values()):
            # One state write per item, so automations see each of them.
            self._trigger_event(
                EVENT_NEWS, item_attributes(item, matches[item.key].keywords)
            )
            self.async_write_ha_state()
        self._seen.save(self._seen_name, self._tracker, self._fingerprint)
