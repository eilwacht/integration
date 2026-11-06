"""Sensors: last breaking news alert, last item and 24-hour count of a news watch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import (
    ExtraStoredData,
    RestoredExtraData,
    RestoreEntity,
)
from homeassistant.util import dt as dt_util

from . import EilwachtConfigEntry
from .coordinator import watch_fingerprint, watch_subentries
from .entity import BreakingEntity, WatchEntity
from .model import NewsItem
from .recent import (
    RECENT,
    RECENT_LIMIT,
    Entry,
    add_recent,
    merge_recent,
    recent_entry,
    restore_recent,
)
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
    """Title of the newest alert; kept after the alert ends and across restarts.

    The attribute "recent" lists the last alerts shown (recent.py): not
    recorded, restored with the state.
    """

    _unrecorded_attributes = frozenset({RECENT})

    def __init__(self, entry: EilwachtConfigEntry, key: str) -> None:
        super().__init__(entry, key)
        self._attr_native_value: str | None = None
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._recent: list[Entry] = []

    async def async_added_to_hass(self) -> None:
        """Restore the last alert, then show the alerts of the first update.

        Those appeared while Home Assistant restarted (seen.py). Without them
        and without a restored alert, a running alert is shown.
        """
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._attr_native_value = last.state
            # Saved before the list existed: start it with the restored alert.
            self._recent = restore_recent(last.attributes.get(RECENT)) or (
                restore_recent([last.attributes])
            )
            # All keys, None if missing (a state of an older version).
            self._attr_extra_state_attributes = {
                **{k: last.attributes.get(k) for k in ITEM_KEYS if k != "keywords"},
                RECENT: self._recent,
            }
        data = self.coordinator.data
        if data and data.new:
            self._show_new(data.new)
        elif self._attr_native_value is None and data and data.active:
            self._show(data.active[0])

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if data and data.new:
            self._show_new(data.new)
        super()._handle_coordinator_update()

    def _show_new(self, items: tuple[NewsItem, ...]) -> None:
        for item in items:  # oldest first: the newest ends up on top
            self._show(item)

    def _show(self, item: NewsItem) -> None:
        self._recent = add_recent(self._recent, recent_entry(item))
        self._attr_native_value = _state(item)
        self._attr_extra_state_attributes = {
            **item_attributes(item),
            RECENT: self._recent,
        }


class LastNewsSensor(WatchEntity, SensorEntity, RestoreEntity):
    """Title of the newest item the watch shows.

    The attribute "recent" lists the newest matches (recent.py), including
    those the source no longer lists: not recorded, restored with the state
    unless the watch was changed.
    """

    _unrecorded_attributes = frozenset({RECENT})

    def __init__(
        self, entry: EilwachtConfigEntry, subentry: ConfigSubentry, key: str
    ) -> None:
        super().__init__(entry, subentry, key)
        self._fingerprint = watch_fingerprint(subentry)
        self._recent: list[Entry] = []

    async def async_added_to_hass(self) -> None:
        """Restore the list if the watch is unchanged, then add current matches."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        extra = await self.async_get_last_extra_data()
        if (
            last is not None
            and extra is not None
            and extra.as_dict().get("fingerprint") == self._fingerprint
        ):
            self._recent = restore_recent(last.attributes.get(RECENT), keywords=True)
        self._update_recent()

    @property
    def extra_restore_state_data(self) -> ExtraStoredData:
        """The settings the list belongs to: other ones show other items."""
        return RestoredExtraData({"fingerprint": self._fingerprint})

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_recent()
        super()._handle_coordinator_update()

    def _update_recent(self) -> None:
        if self.coordinator.data is None:
            return
        newest = self.watch.matches(self.items)[:RECENT_LIMIT]
        self._recent = merge_recent(
            [recent_entry(m.item, m.keywords) for m in newest], self._recent
        )

    @property
    def native_value(self) -> str | None:
        matches = self.watch.matches(self.items)
        return _state(matches[0].item) if matches else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        matches = self.watch.matches(self.items)
        attributes = (
            item_attributes(matches[0].item, matches[0].keywords) if matches else {}
        )
        return {**attributes, RECENT: self._recent}


class NewsCountSensor(WatchEntity, SensorEntity):
    """Number of items the watch shows from the last 24 hours.

    Deliberately without state_class: long-term statistics would add rows
    every 5 minutes and every hour for a number that rarely changes, a
    burden on SD cards for little use. The recorder history still has it.
    """

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return count_since(self.watch.matches(self.items), dt_util.utcnow())
