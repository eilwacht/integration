"""Binary sensor: is a breaking news alert running?"""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EilwachtConfigEntry
from .entity import BreakingEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EilwachtConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """One binary sensor for breaking news."""
    async_add_entities([BreakingActiveBinarySensor(entry, "breaking_active")])


class BreakingActiveBinarySensor(BreakingEntity, BinarySensorEntity):
    """On while tagesschau.de shows at least one breaking news alert."""

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return bool(data.active) if data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        active = data.active if data else ()
        return {
            "titles": [item.title for item in active],
            "urls": [item.url for item in active],
        }
