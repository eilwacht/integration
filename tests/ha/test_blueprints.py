"""The blueprints as real automations: triggers, conditions and message texts.

The phone is a mobile_app device "Pixel von Max"; its notify action
notify.mobile_app_pixel_von_max is a test service here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml import load_yaml
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.eilwacht.const import (
    CONF_KEYWORDS,
    CONF_REGIONS,
    DOMAIN,
    SUBENTRY_WATCH,
)

from .conftest import FakeClient

BLUEPRINTS = (
    Path(__file__).parent.parent.parent / "blueprints" / "automation" / "eilwacht"
)
BREAKING = "event.eilwacht_eilmeldung"
WATCH = "event.eilwacht_stuttgart_neue_meldung"
TTS = "tts.piper"
SPEAKERS = ["media_player.kueche", "media_player.wohnzimmer"]


@pytest.fixture(autouse=True)
async def noon_in_berlin(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Outside the default quiet hours, in the time zone the blueprints are for."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    freezer.move_to("2026-10-20T10:00:00+00:00")  # 12:00 in Berlin


def add_phone(hass: HomeAssistant) -> str:
    """A phone with the Home Assistant app, as mobile_app registers it."""
    entry = MockConfigEntry(domain="mobile_app")
    entry.add_to_hass(hass)
    return (
        dr.async_get(hass)
        .async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={("mobile_app", "pixel")},
            name="Pixel von Max",
        )
        .id
    )


async def setup_blueprint(
    hass: HomeAssistant, name: str, inputs: dict[str, Any], entity: str
) -> list[ServiceCall]:
    """Set up the blueprint; the calls of the phone (or the TTS) action.

    notify_device "phone" stands for the device of add_phone.
    """
    # The entity exists before the automation, as in a running system.
    if hass.states.get(entity) is None:
        hass.states.async_set(entity, STATE_UNKNOWN)
    if inputs.get("notify_device") == "phone":
        inputs = {**inputs, "notify_device": add_phone(hass)}
    blueprint = Blueprint(
        load_yaml(BLUEPRINTS / name),
        expected_domain="automation",
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )
    config = BlueprintInputs(
        blueprint, {"use_blueprint": {"path": name, "input": inputs}}
    ).async_substitute()
    config.pop("use_blueprint", None)
    if name.endswith("_push.yaml"):
        calls = async_mock_service(hass, "notify", "mobile_app_pixel_von_max")
    else:
        assert len(config["actions"]) == 1
        calls = async_mock_service(hass, "tts", "speak")
    assert await async_setup_component(hass, "automation", {"automation": [config]})
    await hass.async_block_till_done()
    return calls


async def fire(
    hass: HomeAssistant, entity: str, timestamp: str, **attributes: Any
) -> None:
    hass.states.async_set(entity, timestamp, attributes)
    await hass.async_block_till_done()


ALERT = {
    "event_type": "breaking_news",
    "title": "Erdbeben in Süditalien",
    "summary": "Mehr in Kürze.",
    "url": "https://www.tagesschau.de/eil-100.html",
}


async def test_breaking_news_push(hass: HomeAssistant) -> None:
    calls = await setup_blueprint(
        hass,
        "eilmeldung_push.yaml",
        {"event_entity": BREAKING, "notify_device": "phone"},
        BREAKING,
    )
    await fire(hass, BREAKING, "2026-10-20T10:00:00.000+00:00", **ALERT)
    assert len(calls) == 1
    assert calls[0].data["title"] == "Eilmeldung"
    assert calls[0].data["message"] == "Erdbeben in Süditalien\nMehr in Kürze."
    assert calls[0].data["data"] == {
        "group": "eilwacht",
        "url": "https://www.tagesschau.de/eil-100.html",
        "clickAction": "https://www.tagesschau.de/eil-100.html",
    }


async def test_old_event_after_outage_is_not_sent(hass: HomeAssistant) -> None:
    calls = await setup_blueprint(
        hass,
        "eilmeldung_push.yaml",
        {"event_entity": BREAKING, "notify_device": "phone"},
        BREAKING,
    )
    await fire(hass, BREAKING, STATE_UNAVAILABLE)
    await fire(hass, BREAKING, "2026-10-20T09:00:00.000+00:00", **ALERT)
    # the entity going away must not break the automation
    hass.states.async_remove(BREAKING)
    await hass.async_block_till_done()
    assert calls == []


@pytest.mark.parametrize(("quiet", "sent"), [(True, 0), (False, 1)])
async def test_quiet_hours(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, quiet: bool, sent: int
) -> None:
    freezer.move_to("2026-10-20T22:30:00+00:00")  # 00:30 in Berlin
    calls = await setup_blueprint(
        hass,
        "eilmeldung_push.yaml",
        {"event_entity": BREAKING, "notify_device": "phone", "quiet_enabled": quiet},
        BREAKING,
    )
    await fire(hass, BREAKING, "2026-10-20T22:30:00.000+00:00", **ALERT)
    assert len(calls) == sent


@pytest.mark.parametrize(("home", "sent"), [("0", 0), ("2", 1)])
async def test_announcement(hass: HomeAssistant, home: str, sent: int) -> None:
    hass.states.async_set("zone.home", home)
    calls = await setup_blueprint(
        hass,
        "eilmeldung_ansage.yaml",
        {"event_entity": BREAKING, "tts_entity": TTS, "media_players": SPEAKERS},
        BREAKING,
    )
    await fire(hass, BREAKING, "2026-10-20T10:00:00.000+00:00", **ALERT)
    assert len(calls) == sent
    if sent:
        assert calls[0].data["entity_id"] == [TTS]
        assert calls[0].data["media_player_entity_id"] == SPEAKERS
        assert calls[0].data["message"] == (
            "Eilmeldung der Tagesschau: Erdbeben in Süditalien"
        )


async def test_announcement_ignores_news_events(hass: HomeAssistant) -> None:
    calls = await setup_blueprint(
        hass,
        "eilmeldung_ansage.yaml",
        {
            "event_entity": WATCH,
            "tts_entity": TTS,
            "media_players": SPEAKERS,
            "only_when_home": False,
        },
        WATCH,
    )
    await fire(
        hass, WATCH, "2026-10-20T10:00:00.000+00:00", event_type="news", title="x"
    )
    assert calls == []


@pytest.mark.parametrize(
    ("attributes", "title"),
    [
        ({"topline": "Stuttgart", "keywords": ["S-Bahn"]}, "Eilwacht: Stuttgart"),
        (
            {"topline": None, "keywords": ["S-Bahn", "Streik*"]},
            "Eilwacht: S-Bahn, Streik*",
        ),
        ({"topline": None}, "Eilwacht: Neue Meldung"),
    ],
)
async def test_watch_push(hass: HomeAssistant, attributes: dict, title: str) -> None:
    calls = await setup_blueprint(
        hass,
        "neue_meldung_push.yaml",
        {"event_entity": WATCH, "notify_device": "phone"},
        WATCH,
    )
    await fire(
        hass,
        WATCH,
        "2026-10-20T10:00:00.000+00:00",
        event_type="news",
        title="S-Bahn-Stammstrecke gesperrt",
        url="https://www.tagesschau.de/x.html",
        **attributes,
    )
    assert len(calls) == 1
    assert calls[0].data["title"] == title
    assert calls[0].data["message"] == "S-Bahn-Stammstrecke gesperrt"


async def test_breaking_news_push_in_english(hass: HomeAssistant) -> None:
    calls = await setup_blueprint(
        hass,
        "eilmeldung_push.yaml",
        {"event_entity": BREAKING, "notify_device": "phone", "language": "en"},
        BREAKING,
    )
    await fire(hass, BREAKING, "2026-10-20T10:00:00.000+00:00", **ALERT)
    assert len(calls) == 1
    assert calls[0].data["title"] == "Breaking news"
    # The news text stays as tagesschau.de delivers it.
    assert calls[0].data["message"] == "Erdbeben in Süditalien\nMehr in Kürze."


@pytest.mark.parametrize("name", ["eilmeldung_push.yaml", "neue_meldung_push.yaml"])
async def test_extra_actions_get_the_texts(hass: HomeAssistant, name: str) -> None:
    extra = async_mock_service(hass, "test", "extra")
    entity = BREAKING if name == "eilmeldung_push.yaml" else WATCH
    calls = await setup_blueprint(
        hass,
        name,
        {
            "event_entity": entity,
            "notify_device": "phone",
            "extra_actions": [
                {
                    "action": "test.extra",
                    "data": {
                        "message": "{{ title }}: {{ message }}",
                        "url": "{{ url }}",
                    },
                }
            ],
        },
        entity,
    )
    attributes = (
        ALERT
        if entity == BREAKING
        else {
            "event_type": "news",
            "title": "S-Bahn-Stammstrecke gesperrt",
            "topline": "Verkehr",
            "url": "https://www.tagesschau.de/x.html",
        }
    )
    await fire(hass, entity, "2026-10-20T10:00:00.000+00:00", **attributes)
    assert len(calls) == 1
    assert len(extra) == 1
    assert extra[0].data["message"] == (
        f"{calls[0].data['title']}: {calls[0].data['message']}"
    )
    assert extra[0].data["url"] == attributes["url"]


@pytest.mark.parametrize("name", ["eilmeldung_push.yaml", "neue_meldung_push.yaml"])
async def test_without_phone_only_the_extra_actions(
    hass: HomeAssistant, name: str
) -> None:
    """The phone is optional: without one the automation is valid and the
    extra actions still get the texts."""
    extra = async_mock_service(hass, "test", "extra")
    entity = BREAKING if name == "eilmeldung_push.yaml" else WATCH
    phone = await setup_blueprint(
        hass,
        name,
        {
            "event_entity": entity,
            "extra_actions": [
                {"action": "test.extra", "data": {"text": "{{ title }}: {{ message }}"}}
            ],
        },
        entity,
    )
    attributes = (
        ALERT
        if entity == BREAKING
        else {"event_type": "news", "title": "S-Bahn gesperrt", "topline": "Verkehr"}
    )
    await fire(hass, entity, "2026-10-20T10:00:00.000+00:00", **attributes)
    assert phone == []
    expected = (
        "Eilmeldung: Erdbeben in Süditalien\nMehr in Kürze."
        if entity == BREAKING
        else "Eilwacht: Verkehr: S-Bahn gesperrt"
    )
    assert [c.data["text"] for c in extra] == [expected]


# --- The watch's name in the title, with the real integration ------------------


async def setup_watches(hass: HomeAssistant, *names: str) -> MockConfigEntry:
    """Eilwacht with these news watches (Baden-Württemberg, no keywords)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Eilwacht",
        data={},
        subentries_data=[
            ConfigSubentryData(
                data={CONF_REGIONS: [1], CONF_KEYWORDS: ""},
                subentry_type=SUBENTRY_WATCH,
                title=name,
                unique_id=None,
            )
            for name in names
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def watch_event(hass: HomeAssistant, entry: MockConfigEntry, title: str) -> str:
    """The entity "New item" of the watch with this title."""
    (subentry_id,) = (
        s.subentry_id for s in entry.subentries.values() if s.title == title
    )
    found = er.async_get(hass).async_get_entity_id(
        "event", DOMAIN, f"{subentry_id}_news"
    )
    assert found is not None
    return found


async def push_title(
    hass: HomeAssistant, entity: str, language: str | None, **attributes: Any
) -> str:
    inputs: dict[str, Any] = {"event_entity": entity, "notify_device": "phone"}
    if language:
        inputs["language"] = language
    calls = await setup_blueprint(hass, "neue_meldung_push.yaml", inputs, entity)
    # The attributes of a real event of the watch.
    await fire(
        hass,
        entity,
        "2026-10-20T10:00:00.000+00:00",
        event_types=["news"],
        event_type="news",
        title="S-Bahn-Stammstrecke gesperrt",
        url="https://www.tagesschau.de/x.html",
        **attributes,
    )
    assert len(calls) == 1
    assert calls[0].data["message"] == "S-Bahn-Stammstrecke gesperrt"
    return calls[0].data["title"]


@pytest.mark.parametrize(
    ("language", "attributes", "title"),
    [
        (None, {"topline": "Verkehr"}, "Eilwacht: Verkehr"),
        # the topline is shown even if it is the watch's name
        (None, {"topline": "Stuttgart"}, "Eilwacht: Stuttgart"),
        ("en", {"topline": None}, "Eilwacht: New item"),
    ],
)
async def test_one_watch_is_not_named(
    hass: HomeAssistant,
    client: FakeClient,
    language: str | None,
    attributes: dict,
    title: str,
) -> None:
    """One watch (plus the breaking news device): its name tells nothing."""
    entry = await setup_watches(hass, "Stuttgart")
    entity = watch_event(hass, entry, "Stuttgart")
    assert await push_title(hass, entity, language, **attributes) == title


@pytest.mark.parametrize(
    ("name_by_user", "language", "attributes", "title"),
    [
        (None, None, {"topline": "Verkehr"}, "Eilwacht · Stuttgart: Verkehr"),
        (None, None, {"topline": "Stuttgart"}, "Eilwacht · Stuttgart"),
        (None, "en", {"topline": None}, "Eilwacht · Stuttgart: New item"),
        ("Region", None, {"topline": "Verkehr"}, "Eilwacht · Region: Verkehr"),
    ],
)
async def test_two_watches_are_named(
    hass: HomeAssistant,
    client: FakeClient,
    name_by_user: str | None,
    language: str | None,
    attributes: dict,
    title: str,
) -> None:
    entry = await setup_watches(hass, "Stuttgart", "Streik")
    entity = watch_event(hass, entry, "Stuttgart")
    if name_by_user:
        device_id = er.async_get(hass).async_get(entity).device_id
        dr.async_get(hass).async_update_device(device_id, name_by_user=name_by_user)
    assert await push_title(hass, entity, language, **attributes) == title
