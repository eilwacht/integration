"""Static checks for the bundled automation blueprints (run locally and in CI).

The message templates are rendered here with plain Jinja and stand-ins for
device_id/device_attr; tests/ha/test_blueprints.py runs them in Home Assistant.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.helpers import config_validation as cv
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
# Inputs without a default (the user must fill them), unchanged.
REQUIRED = {
    "eilmeldung_ansage.yaml": {"event_entity", "tts_entity", "media_players"},
    "eilmeldung_push.yaml": {"event_entity", "notify_device"},
    "neue_meldung_push.yaml": {"event_entity", "notify_device"},
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
    assert push["device_id"] == "phone"
    assert push["title"] == "{{ title }}"
    assert push["message"] == "{{ message }}"
    assert more["sequence"] == extra
    assert {"title", "message", "url"} <= set(config["variables"])
    cv.SCRIPT_SCHEMA(config["actions"])
    # Without extra actions an empty sequence, which is valid.
    config = substitute(name, event_entity="event.x", notify_device="phone")
    assert config["actions"][1]["sequence"] == []
    cv.SCRIPT_SCHEMA(config["actions"])


# --- Rendering the message templates -------------------------------------------

ENV = ImmutableSandboxedEnvironment()


def render(
    name: str,
    attributes: dict[str, Any],
    *,
    language: str | None = None,
    device: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The variables of the blueprint for one event, rendered in order."""
    inputs: dict[str, Any] = {"event_entity": "event.x", "notify_device": "phone"}
    if language:
        inputs["language"] = language
    config = substitute(name, **inputs)
    state = SimpleNamespace(
        state="2026-10-20T10:00:00.000+00:00", attributes=attributes
    )
    values: dict[str, Any] = {
        "trigger": SimpleNamespace(
            entity_id="event.x",
            to_state=state,
            from_state=SimpleNamespace(state="2026-10-20T09:00:00.000+00:00"),
        ),
        "device_id": lambda entity: "dev1" if device else None,
        "device_attr": lambda device_id, attr: (device or {}).get(attr),
    }
    for key, value in config["variables"].items():
        values[key] = (
            ENV.from_string(value).render(values).strip()
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
        # the watch's device "Eilwacht Stuttgart"
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
    )
    assert values["title"] == title
    assert values["message"] == "S-Bahn-Stammstrecke gesperrt"
