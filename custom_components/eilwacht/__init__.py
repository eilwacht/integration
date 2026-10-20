"""Eilwacht: Tagesschau breaking news and regional news for Home Assistant."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import (
    BreakingCoordinator,
    NewsCoordinator,
    issue_id,
    watch_from_subentry,
    watch_subentries,
)
from .sample import BreakingSample
from .tagesschau import TagesschauClient
from .watch import Watch

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.SENSOR]


@dataclass
class EilwachtRuntimeData:
    """Runtime data of the config entry."""

    breaking: BreakingCoordinator
    news: NewsCoordinator | None
    watches: dict[str, Watch]  # subentry_id -> watch


type EilwachtConfigEntry = ConfigEntry[EilwachtRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: EilwachtConfigEntry) -> bool:
    """Set up Eilwacht from a config entry."""
    client = TagesschauClient(async_get_clientsession(hass))
    sample = BreakingSample(hass)
    await sample.async_load()

    watches = {s.subentry_id: watch_from_subentry(s) for s in watch_subentries(entry)}
    regions = frozenset(r for watch in watches.values() for r in watch.regions)
    breaking = BreakingCoordinator(hass, entry, client, sample)
    news = NewsCoordinator(hass, entry, client, regions) if regions else None
    if news is None:
        ir.async_delete_issue(hass, DOMAIN, issue_id("news"))

    # Deliberately not async_config_entry_first_refresh(): an unreachable
    # endpoint must not keep the integration from loading.
    await asyncio.gather(*(c.async_refresh() for c in (breaking, news) if c))

    entry.runtime_data = EilwachtRuntimeData(
        breaking=breaking, news=news, watches=watches
    )
    # Subentry (watch) changes trigger a reload.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EilwachtConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: EilwachtConfigEntry) -> None:
    """Remove repair issues and the stored alert sample."""
    for key in ("headerapp", "news"):
        ir.async_delete_issue(hass, DOMAIN, issue_id(key))
    await BreakingSample.async_remove(hass)


async def _async_update_listener(
    hass: HomeAssistant, entry: EilwachtConfigEntry
) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
