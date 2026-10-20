"""Base entities: one device for breaking news, one per news watch."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, VERSION
from .coordinator import BreakingCoordinator, NewsCoordinator

if TYPE_CHECKING:
    from . import EilwachtConfigEntry
    from .watch import Watch


def _device(identifier: str, name: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, identifier)},
        name=name,
        manufacturer="Eilwacht",
        sw_version=VERSION,
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://www.tagesschau.de",
    )


class BreakingEntity(CoordinatorEntity[BreakingCoordinator]):
    """An entity of the "Eilwacht" device (breaking news)."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, entry: EilwachtConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data.breaking)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = _device(entry.entry_id, "Eilwacht")


class WatchEntity(CoordinatorEntity[NewsCoordinator]):
    """An entity of a news watch device."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self, entry: EilwachtConfigEntry, subentry: ConfigSubentry, key: str
    ) -> None:
        news = entry.runtime_data.news
        assert news is not None  # exists whenever a watch exists
        super().__init__(news)
        self.watch: Watch = entry.runtime_data.watches[subentry.subentry_id]
        self._attr_unique_id = f"{subentry.subentry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = _device(
            subentry.subentry_id, f"Eilwacht {subentry.title}"
        )

    @property
    def items(self) -> tuple[Any, ...]:
        """Current news of the coordinator (empty before the first poll)."""
        data = self.coordinator.data
        return data.items if data else ()
