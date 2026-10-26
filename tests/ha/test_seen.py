"""The seen items are written rarely: SD cards on a Raspberry Pi."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant

from custom_components.eilwacht.changes import NewItemTracker
from custom_components.eilwacht.seen import HEARTBEAT, SAVE_DELAY, SeenStore

from .conftest import news_item


async def test_writes_soon_after_new_items_otherwise_rarely(
    hass: HomeAssistant,
) -> None:
    seen = SeenStore(hass)
    await seen.async_load(keep={"t"})
    tracker = NewItemTracker()
    delays: list[float] = []

    with patch.object(
        seen._store,
        "async_delay_save",
        side_effect=lambda func, delay: delays.append(delay),
    ):
        tracker.update([news_item("a")])
        seen.save("t", tracker)  # new item: written soon
        seen.save("t", tracker)  # every poll; the pending write stays
        assert delays == [SAVE_DELAY]

        seen._data_to_save()  # the write took place
        seen.save("t", tracker)  # nothing new: only the timestamp
        seen.save("t", tracker)
        assert delays == [SAVE_DELAY, HEARTBEAT]

        tracker.update([news_item("a"), news_item("b")])
        seen.save("t", tracker)  # new item: sooner than the heartbeat
        assert delays == [SAVE_DELAY, HEARTBEAT, SAVE_DELAY]


async def test_changed_settings_are_written_soon(hass: HomeAssistant) -> None:
    seen = SeenStore(hass)
    await seen.async_load(keep={"t"})
    tracker = NewItemTracker()
    tracker.update([news_item("a")])
    seen.save("t", tracker, "1|Streik")
    seen._data_to_save()
    delays: list[float] = []

    with patch.object(
        seen._store,
        "async_delay_save",
        side_effect=lambda func, delay: delays.append(delay),
    ):
        seen.save("t", tracker, "1|")
    assert delays == [SAVE_DELAY]
