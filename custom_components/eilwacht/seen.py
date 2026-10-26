"""Keeps the seen items of every tracker across restarts.

After a restart, items that appeared meanwhile are announced instead of being
learned silently. After a longer pause (CATCH_UP) the trackers learn silently
again, so a day offline does not end in a flood of notifications.

Gentle on SD cards (headerapp is polled every minute, HA often runs on a
Raspberry Pi): written within SAVE_DELAY after new items, otherwise only every
HEARTBEAT to keep "saved_at" fresh for a restart after a crash, and always
when Home Assistant stops.
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
SAVE_DELAY = 600  # seconds, after new items
HEARTBEAT = 3 * 3600  # seconds, when only "saved_at" changed
CATCH_UP = timedelta(hours=6)
# Items may show up a little after their publication time ("Stand: 11:25 Uhr"
# for an alert seen at 11:27), so the restored cutoff reaches back this far.
PUBLISH_DELAY = timedelta(hours=1)
# Keys kept per tracker; the sources list far fewer items at a time.
KEEP_KEYS = 500


class SeenStore:
    """Stored as {"trackers": {name: {"fingerprint", "saved_at", "keys"}}}."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = {"trackers": {}}
        # Loop time of the pending write. Store postpones a delayed write on
        # every call, so it is only called when the write must come sooner.
        self._due: float | None = None

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
        """Note the tracker's state (called after every poll).

        Written within SAVE_DELAY if items or settings changed, else within
        HEARTBEAT; always when Home Assistant stops.
        """
        keys = tracker.keys[-KEEP_KEYS:]
        before = self.data["trackers"].get(name) or {}
        changed = before.get("keys") != keys or before.get("fingerprint") != fingerprint
        self.data["trackers"][name] = {
            "fingerprint": fingerprint,
            "saved_at": dt_util.utcnow().isoformat(),
            "keys": keys,
        }
        self._schedule(SAVE_DELAY if changed else HEARTBEAT)

    def _schedule(self, delay: float) -> None:
        due = self._hass.loop.time() + delay
        if self._due is not None and self._due <= due:
            return  # an earlier write is pending already
        self._due = due
        self._store.async_delay_save(self._data_to_save, delay)

    def _data_to_save(self) -> dict[str, Any]:
        self._due = None
        return self.data

    async def async_flush(self) -> None:
        """Write now (entry unloaded or reloaded)."""
        self._due = None
        await self._store.async_save(self.data)

    @staticmethod
    async def async_remove(hass: HomeAssistant) -> None:
        """Delete the stored state (integration removed)."""
        await Store(hass, STORAGE_VERSION, STORAGE_KEY).async_remove()
