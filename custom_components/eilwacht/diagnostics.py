"""Diagnostics download (Settings > Devices & services > Eilwacht > ⋮).

Contains the last recorded raw breaking news response (sample.py): it is the
only way to learn the real alert format so far.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import EilwachtConfigEntry
from .const import VERSION
from .coordinator import diagnostics
from .watch import item_attributes

SAMPLE_ITEMS = 3


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EilwachtConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for the config entry."""
    runtime = entry.runtime_data
    breaking = runtime.breaking
    news = runtime.news
    return {
        "version": VERSION,
        "watches": {
            subentry_id: {"title": subentry.title, "data": dict(subentry.data)}
            for subentry_id, subentry in entry.subentries.items()
        },
        "breaking": {
            **diagnostics(breaking),
            "homepage_error": breaking.homepage_error,
            "active": [item_attributes(i) for i in breaking.data.active]
            if breaking.data
            else [],
            "recorded_sample": breaking.sample.data,
        },
        "news": {
            **diagnostics(news),
            "regions": sorted(news.regions),
            "items": len(news.data.items) if news.data else None,
            "sample_items": [item_attributes(i) for i in news.data.items[:SAMPLE_ITEMS]]
            if news.data
            else [],
        }
        if news
        else None,
    }
