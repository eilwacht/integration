"""Keeps the seen items of every tracker across restarts.

After a restart, items that appeared meanwhile are announced instead of being
learned silently. After a longer pause (CATCH_UP) the trackers learn silently
again, so a day offline does not end in a flood of notifications.

Saved at most every SAVE_DELAY and when Home Assistant stops, not after every
poll: headerapp is polled every minute and HA often runs from an SD card.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .changes import NewItemTracker
from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.seen"
SAVE_DELAY = 600  # seconds
CATCH_UP = timedelta(hours=6)
# Items may show up a little after their publication time ("Stand: 11:25 Uhr"
# for an alert seen at 11:27), so the restored cutoff reaches back this far.
PUBLISH_DELAY = timedelta(hours=1)
# Keys kept per tracker; the sources list far fewer items at a time.
KEEP_KEYS = 500


class SeenStore:
    """Stored as {"trackers": {name: {"fingerprint", "saved_at", "keys"}}}."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = {"trackers": {}}
        self._pending = False

    async def async_load(self, keep: set[str]) -> None:
        """Load the stored state and drop trackers that no longer exist."""
        if stored := await self._store.async_load():
            self.data = stored
        trackers = self.data.setdefault("trackers", {})
        for name in set(trackers) - keep:
            del trackers[name]

    def restore(
        self, name: str, tracker: NewItemTracker, fingerprint: str = ""
    ) -> None:
        """Continue a tracker from its saved state, if recent and unchanged.

        A changed fingerprint (other federal states or keywords) means other
        items: they are learned silently, not announced as new.
        """
        saved = self.data["trackers"].get(name)
        if not saved or saved.get("fingerprint") != fingerprint:
            return
        saved_at = dt_util.parse_datetime(saved.get("saved_at") or "")
        if saved_at is None or dt_util.utcnow() - saved_at > CATCH_UP:
            return
        tracker.restore(saved.get("keys") or (), saved_at - PUBLISH_DELAY)

    def save(self, name: str, tracker: NewItemTracker, fingerprint: str = "") -> None:
        """Note the tracker's state; it is written within SAVE_DELAY."""
        self.data["trackers"][name] = {
            "fingerprint": fingerprint,
            "saved_at": dt_util.utcnow().isoformat(),
            "keys": tracker.keys[-KEEP_KEYS:],
        }
        if not self._pending:
            self._pending = True
            self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    def _data_to_save(self) -> dict[str, Any]:
        self._pending = False
        return self.data

    async def async_flush(self) -> None:
        """Write now (entry unloaded or reloaded)."""
        self._pending = False
        await self._store.async_save(self.data)

    @staticmethod
    async def async_remove(hass: HomeAssistant) -> None:
        """Delete the stored state (integration removed)."""
        await Store(hass, STORAGE_VERSION, STORAGE_KEY).async_remove()
