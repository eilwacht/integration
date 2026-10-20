"""Keeps the latest raw headerapp response with a running alert.

Its format is only known from a third-party bot so far (docs/ENTWICKLUNG.md,
section 2). The diagnostics download shows the recorded response, which then
becomes a test fixture.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.breaking_sample"
SAVE_DELAY = 10  # seconds


class BreakingSample:
    """Stored as {"recorded": ISO timestamp, "response": raw JSON}."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] | None = None

    async def async_load(self) -> None:
        """Load the stored sample, if any."""
        self.data = await self._store.async_load()

    def record(self, response: Any) -> bool:
        """Keep the response if it differs from the stored one; True if it did."""
        if self.data and self.data.get("response") == response:
            return False
        self.data = {"recorded": dt_util.utcnow().isoformat(), "response": response}
        self._store.async_delay_save(lambda: self.data or {}, SAVE_DELAY)
        return True

    @staticmethod
    async def async_remove(hass: HomeAssistant) -> None:
        """Delete the stored sample (integration removed)."""
        await Store(hass, STORAGE_VERSION, STORAGE_KEY).async_remove()
