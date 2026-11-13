"""Static checks for the bundled automation blueprints (run locally and in CI).

The message templates are rendered here with plain Jinja and stand-ins for
HA's template functions (integration_entities, device_id, device_attr,
is_state_attr, slugify); tests/ha/test_blueprints.py runs them in Home
Assistant.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.util import slugify
from homeassistant.util.yaml import load_yaml
from jinja2.sandbox import ImmutableSandboxedEnvironment

BLUEPRINTS = Path(__file__).parent.parent / "blueprints" / "automation" / "eilwacht"
FILES = sorted(BLUEPRINTS.glob("*.yaml"))
PUSH = ["eilmeldung_push.yaml", "neue_meldung_push.yaml"]

# Input keys of the first releases: existing automations rely on them.
KEYS_BEFORE = {
    "eilmeldung_ansage.yaml": {
        "event_entity",
        "tts_entity",
        "media_players",
        "intro",
        "only_when_home",
        "quiet_enabled",
        "quiet_start",
        "quiet_end",
    },
    "eilmeldung_push.yaml": {
        "event_entity",
        "notify_device",
        "quiet_enabled",
        "quiet_start",
        "quiet_end",
    },
    "neue_meldung_push.yaml": {
        "event_entity",
        "notify_device",
        "quiet_enabled",
        "quiet_start",
        "quiet_end",
    },
}
# Inputs without a default (the user must fill them). The phone became
# optional; existing automations have one, so they keep working.
REQUIRED = {
    "eilmeldung_ansage.yaml": {"event_entity", "tts_entity", "media_players"},
    "eilmeldung_push.yaml": {"event_entity"},
    "neue_meldung_push.yaml": {"event_entity"},
}


def load(name: str) -> Blueprint:
    return Blueprint(
        load_yaml(BLUEPRINTS / name),
        expected_domain="automation",
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )


def substitute(name: str, **inputs: Any) -> dict[str, Any]:
    return BlueprintInputs(
        load(name), {"use_blueprint": {"path": name, "input": inputs}}
    ).async_substitute()


def test_blueprints_exist() -> None:
    assert [f.name for f in FILES] == [
        "eilmeldung_ansage.yaml",
        "eilmeldung_push.yaml",
        "neue_meldung_push.yaml",
    ]


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_blueprint_is_valid(path: Path) -> None:
    blueprint = load(path.name)
    meta = blueprint.metadata
    assert meta["name"].startswith("Eilwacht")
    # The import button and HA's "re-import" use this URL.
    assert meta["source_url"] == (
        "https://github.com/eilwacht/integration/blob/main/"
        f"blueprints/automation/eilwacht/{path.name}"
    )
    assert meta["homeassistant"]["min_version"] == "2026.3.0"


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_texts_in_german_and_english(path: Path) -> None:
    meta = load(path.name).metadata
    # name "Eilwacht – <German> / <English>", description German --- English
    assert " / " in meta["name"]
    german, english = meta["description"].split("---")
    assert "Eilmeldung" in german or "Meldung" in german
    assert " the " in english
    sections = [v for v in meta["input"].values() if v and "input" in v]
    for section in sections:
        assert " / " in section["name"]
    for key, field in load(path.name).inputs.items():
        assert " / " in field["name"], key
        if "description" in field:
            assert " / " in field["description"], key


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_existing_inputs_unchanged(path: Path) -> None:
    inputs = load(path.name).inputs
    assert KEYS_BEFORE[path.name] <= set(inputs)
    assert {k for k, v in inputs.items() if "default" not in v} == REQUIRED[path.name]


def test_announcement_keeps_its_intro() -> None:
    """A control blueprint: only the labels are bilingual, nothing new."""
    blueprint = load("eilmeldung_ansage.yaml")
    assert set(blueprint.inputs) == KEYS_BEFORE["eilmeldung_ansage.yaml"]
    assert blueprint.inputs["intro"]["default"] == "Eilmeldung der Tagesschau:"


@pytest.mark.parametrize("name", PUSH)
def test_push_inputs(name: str) -> None:
    blueprint = load(name)
    inputs = blueprint.inputs
    assert inputs["language"]["default"] == "de"
    # The phone is optional and empty by default.
    assert inputs["notify_device"]["default"] == ""
    assert inputs["notify_device"]["name"] == "Handy (optional) / Phone (optional)"
    selector = inputs["notify_device"]["selector"]["device"]
    assert selector["filter"] == [{"integration": "mobile_app"}]
    options = inputs["language"]["selector"]["select"]["options"]
    assert [o["value"] for o in options] == ["de", "en"]
    # The extra actions sit in a collapsed section.
    section = blueprint.metadata["input"]["more"]
    assert section["collapsed"] is True
    assert set(section["input"]) == {"extra_actions"}
    assert section["input"]["extra_actions"]["default"] == []
    assert section["input"]["extra_actions"]["selector"] == {"action": {}}


@pytest.mark.parametrize("name", PUSH)
def test_push_actions(name: str) -> None:
    extra = [{"action": "telegram_bot.send_message", "data": {"message": "x"}}]
    config = substitute(
        name, event_entity="event.x", notify_device="phone", extra_actions=extra
    )
    push, more = config["actions"]
    # No device action: an empty device would make the automation invalid.
    assert "domain" not in push
    assert "device_id" not in push
    assert push["if"] == [
        {"condition": "template", "value_template": "{{ phone_action != '' }}"}
    ]
    (send,) = push["then"]
    assert send["action"] == "{{ phone_action }}"
    assert send["data"] == {
        "title": "{{ title }}",
        "message": "{{ message }}",
        "data": {"group": "eilwacht", "url": "{{ url }}", "clickAction": "{{ url }}"},
    }
    assert more["sequence"] == extra
    assert config["variables"]["notify_device"] == "phone"
    assert {"title", "message", "url", "phone_action"} <= set(config["variables"])
    # Without extra actions an empty sequence. Whether HA accepts the actions
    # (templates need a running HA) tests/ha/test_blueprints.py checks.
    config = substitute(name, event_entity="event.x", notify_device="phone")
    assert config["actions"][1]["sequence"] == []
    # Without a phone, only the extra actions.
    config = substitute(name, event_entity="event.x", extra_actions=extra)
    assert config["variables"]["notify_device"] == ""
    assert config["actions"][1]["sequence"] == extra


# --- Rendering the message templates -------------------------------------------

PHONES = {"phone1": {"name": "Pixel von Max"}}
# The other entities of the integration (entity: device, attributes): the
# breaking news event, another entity of the triggering watch's device and,
# with others=1, the event of a second watch.
NEWS_EVENT = {"event_types": ["news"]}
OTHER_ENTITIES = {
    "event.eilwacht_eilmeldung": ("dev0", {"event_types": ["breaking_news"]}),
    "sensor.eilwacht_x_letzte_meldung": ("dev1", {}),
    "event.eilwacht_y_neue_meldung": ("dev2", NEWS_EVENT),
}


def render(
    name: str,
    attributes: dict[str, Any],
    *,
    language: str | None = None,
    device: dict[str, Any] | None = None,
    others: int = 0,
    phone: str | None = "phone1",
) -> dict[str, Any]:
    """The variables of the blueprint for one event, rendered in order.

    device is the device of the triggering entity event.x (None: it has no
    device); others is the number of further watches (0 or 1).
    """
    inputs: dict[str, Any] = {"event_entity": "event.x"}
    if phone:
        inputs["notify_device"] = phone
    if language:
        inputs["language"] = language
    config = substitute(name, **inputs)
    entities = {
        **dict(list(OTHER_ENTITIES.items())[: 2 + others]),
        "event.x": ("dev1" if device else None, {**NEWS_EVENT, **attributes}),
    }

    def device_id(entity: str) -> str | None:
        return entities.get(entity, (None, {}))[0]

    def is_state_attr(entity: str, attr: str, value: Any) -> bool:
        found = entities.get(entity, (None, {}))[1]
        return attr in found and found[attr] == value

    env = ImmutableSandboxedEnvironment()
    env.filters["slugify"] = slugify
    env.filters["device_id"] = device_id
    env.tests["is_state_attr"] = is_state_attr
    state = SimpleNamespace(
        state="2026-10-20T10:00:00.000+00:00", attributes=attributes
    )
    values: dict[str, Any] = {
        "trigger": SimpleNamespace(
            entity_id="event.x",
            to_state=state,
            from_state=SimpleNamespace(state="2026-10-20T09:00:00.000+00:00"),
        ),
        "integration_entities": lambda domain: (
            list(entities) if domain == "eilwacht" else []
        ),
        "device_id": device_id,
        "device_attr": lambda device_id, attr: (
            PHONES[device_id].get(attr)
            if device_id in PHONES
            else (device or {}).get(attr)
            if device_id == "dev1"
            else None
        ),
    }
    for key, value in config["variables"].items():
        values[key] = (
            env.from_string(value).render(values).strip()
            if isinstance(value, str)
            else value
        )
    return values


ALERT = {
    "event_type": "breaking_news",
    "title": "Erdbeben in Süditalien",
    "summary": "Mehr in Kürze.",
    "url": "https://www.tagesschau.de/eil-100.html",
}


@pytest.mark.parametrize(
    ("language", "title"),
    [(None, "Eilmeldung"), ("de", "Eilmeldung"), ("en", "Breaking news")],
)
def test_breaking_push_texts(language: str | None, title: str) -> None:
    values = render("eilmeldung_push.yaml", ALERT, language=language)
    assert values["title"] == title
    # The news text stays as tagesschau.de delivers it.
    assert values["message"] == "Erdbeben in Süditalien\nMehr in Kürze."
    assert values["url"] == ALERT["url"]


@pytest.mark.parametrize("name", PUSH)
def test_phone_action_from_the_device(name: str) -> None:
    values = render(name, ALERT)
    assert values["phone_action"] == "notify.mobile_app_pixel_von_max"
    # No phone chosen, or a device that is gone: nothing goes to a phone.
    assert render(name, ALERT, phone=None)["phone_action"] == ""
    assert render(name, ALERT, phone="gone")["phone_action"] == ""


def test_breaking_push_without_summary() -> None:
    values = render("eilmeldung_push.yaml", {**ALERT, "summary": None})
    assert values["message"] == "Erdbeben in Süditalien"


ITEM = {"event_type": "news", "title": "S-Bahn-Stammstrecke gesperrt", "url": "u"}
DEVICE = {"name": "Eilwacht Stuttgart", "name_by_user": None}


@pytest.mark.parametrize(
    ("attributes", "language", "device", "title"),
    [
        # no device found: the integration's name only
        ({"topline": "Verkehr"}, None, None, "Eilwacht: Verkehr"),
        ({"keywords": ["S-Bahn", "Streik*"]}, None, None, "Eilwacht: S-Bahn, Streik*"),
        ({"topline": None}, None, None, "Eilwacht: Neue Meldung"),
        ({"topline": None}, "en", None, "Eilwacht: New item"),
        # the watch's device "Eilwacht Stuttgart", next to a second watch
        ({"topline": "Verkehr"}, None, DEVICE, "Eilwacht · Stuttgart: Verkehr"),
        ({"topline": "Stuttgart"}, None, DEVICE, "Eilwacht · Stuttgart"),
        ({"keywords": ["S-Bahn"]}, "en", DEVICE, "Eilwacht · Stuttgart: S-Bahn"),
        ({}, "en", DEVICE, "Eilwacht · Stuttgart: New item"),
        ({}, "de", DEVICE, "Eilwacht · Stuttgart: Neue Meldung"),
        # renamed by the user
        (
            {"topline": "Verkehr"},
            None,
            {"name": "Eilwacht Stuttgart", "name_by_user": "Region"},
            "Eilwacht · Region: Verkehr",
        ),
    ],
)
def test_watch_push_texts(
    attributes: dict[str, Any],
    language: str | None,
    device: dict[str, Any] | None,
    title: str,
) -> None:
    values = render(
        "neue_meldung_push.yaml",
        {**ITEM, **attributes},
        language=language,
        device=device,
        others=1,
    )
    assert values["title"] == title
    assert values["message"] == "S-Bahn-Stammstrecke gesperrt"


@pytest.mark.parametrize(
    ("attributes", "language", "title"),
    [
        ({"topline": "Verkehr"}, None, "Eilwacht: Verkehr"),
        # the topline is shown even if it is the watch's name
        ({"topline": "Stuttgart"}, None, "Eilwacht: Stuttgart"),
        ({"keywords": ["S-Bahn"]}, "en", "Eilwacht: S-Bahn"),
        ({}, "en", "Eilwacht: New item"),
    ],
)
def test_watch_push_texts_with_one_watch(
    attributes: dict[str, Any], language: str | None, title: str
) -> None:
    """Only one watch: its name tells nothing, the title leaves it out."""
    values = render(
        "neue_meldung_push.yaml",
        {**ITEM, **attributes},
        language=language,
        device=DEVICE,
    )
    # The breaking news device and further entities of the watch do not count.
    assert values["watches"] == "1"
    assert values["title"] == title


def test_watches_are_counted_by_device() -> None:
    values = render("neue_meldung_push.yaml", ITEM, device=DEVICE, others=1)
    assert values["watches"] == "2"
    # An entity without a device is neither counted nor named.
    values = render("neue_meldung_push.yaml", ITEM, others=1)
    assert values["watches"] == "1"
    assert values["title"] == "Eilwacht: Neue Meldung"
