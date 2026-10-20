"""Tests for the config flow and the news watch subentry flow."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    ConfigSubentryData,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eilwacht.const import (
    CONF_KEYWORDS,
    CONF_REGIONS,
    DOMAIN,
    SUBENTRY_WATCH,
)


@pytest.fixture(autouse=True)
def no_setup() -> Iterator[AsyncMock]:
    """Flows are tested without actually setting up the entry."""
    with patch(
        "custom_components.eilwacht.async_setup_entry", return_value=True
    ) as mock:
        yield mock


def entry_with(subentries: list[ConfigSubentryData] | None = None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, title="Eilwacht", data={}, subentries_data=subentries or []
    )


async def test_user_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Eilwacht"
    assert result["data"] == {}


async def test_single_instance(hass: HomeAssistant) -> None:
    entry_with().add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def start_watch_flow(hass: HomeAssistant, entry: MockConfigEntry) -> dict:
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_WATCH), context={"source": SOURCE_USER}
    )


async def configure(hass: HomeAssistant, result: dict, user_input: dict) -> dict:
    return await hass.config_entries.subentries.async_configure(
        result["flow_id"], user_input
    )


async def test_add_watch(hass: HomeAssistant) -> None:
    entry = entry_with()
    entry.add_to_hass(hass)
    result = await start_watch_flow(hass, entry)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await configure(
        hass,
        result,
        {
            "name": " Stuttgart ",
            CONF_REGIONS: ["1", "0"],
            CONF_KEYWORDS: " Stuttgart,, Streik* ,-Fußball ",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    (subentry,) = entry.subentries.values()
    assert subentry.title == "Stuttgart"
    assert dict(subentry.data) == {
        CONF_REGIONS: [0, 1],
        CONF_KEYWORDS: "Stuttgart, Streik*, -Fußball",
    }


async def test_keywords_are_optional(hass: HomeAssistant) -> None:
    entry = entry_with()
    entry.add_to_hass(hass)
    result = await start_watch_flow(hass, entry)
    result = await configure(hass, result, {"name": "Bayern", CONF_REGIONS: ["2"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    (subentry,) = entry.subentries.values()
    assert subentry.data[CONF_KEYWORDS] == ""


@pytest.mark.parametrize(
    ("user_input", "errors"),
    [
        ({"name": "  ", CONF_REGIONS: ["1"]}, {"name": "name_required"}),
        ({"name": "BW", CONF_REGIONS: []}, {CONF_REGIONS: "no_regions"}),
    ],
)
async def test_watch_validation(
    hass: HomeAssistant, user_input: dict, errors: dict
) -> None:
    entry = entry_with()
    entry.add_to_hass(hass)
    result = await start_watch_flow(hass, entry)
    result = await configure(hass, result, user_input)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors


async def test_reconfigure_watch(hass: HomeAssistant) -> None:
    entry = entry_with(
        [
            ConfigSubentryData(
                data={CONF_REGIONS: [1], CONF_KEYWORDS: "Ulm"},
                subentry_type=SUBENTRY_WATCH,
                title="Ulm",
                unique_id=None,
            )
        ]
    )
    entry.add_to_hass(hass)
    (subentry_id,) = entry.subentries
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_WATCH),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry_id},
    )
    assert result["step_id"] == "reconfigure"

    result = await configure(
        hass,
        result,
        {"name": "Ulm/Neu-Ulm", CONF_REGIONS: ["1", "2"], CONF_KEYWORDS: "Ulm"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    subentry = entry.subentries[subentry_id]
    assert subentry.title == "Ulm/Neu-Ulm"
    assert subentry.data[CONF_REGIONS] == [1, 2]
