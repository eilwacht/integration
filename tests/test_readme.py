"""The README's markdown card for the lists, rendered strictly.

Home Assistant's markdown card renders templates in strict mode: a key missing
in one entry ("'dict object' has no attribute 'image'") empties the whole
card. That happened in 0.3.0 with an entry seeded from a 0.2.x state.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import jinja2
import pytest
import yaml

from custom_components.eilwacht.model import Source
from custom_components.eilwacht.recent import recent_entry, restore_recent
from custom_components.eilwacht.tagesschau import parse_api2u

from .conftest import load_fixture

README = Path(__file__).parent.parent / "README.md"
BERLIN = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 11, 6, 19, 0, tzinfo=BERLIN)
BREAKING = "sensor.eilwacht_letzte_eilmeldung"
WATCH = "sensor.eilwacht_stuttgart_letzte_meldung"
# Attributes of a 0.2.x state: no image keys.
OLD_ENTRY = {
    "title": "Alte Eilmeldung",
    "url": "https://www.tagesschau.de/eilmeldung/eilmeldung-1.html",
    "published": (NOW - timedelta(hours=2)).isoformat(),
}


def card_template() -> str:
    text = README.read_text(encoding="utf-8")
    section = text.split("### Die letzten Meldungen als Liste", 1)[1]
    block = section.split("```yaml\n", 1)[1].split("```", 1)[0]
    return yaml.safe_load(block)["content"]


def render(states: dict[str, Any]) -> str:
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.globals.update(
        now=lambda: NOW,
        as_datetime=datetime.fromisoformat,
        state_attr=lambda entity, name: states.get(entity, {}).get(name),
    )
    return env.from_string(card_template()).render()


def news_entries() -> list[dict[str, Any]]:
    items = parse_api2u(load_fixture("news_bw.json"), Source.NEWS)
    return [recent_entry(item, ("Stuttgart",)) for item in items]


@pytest.mark.parametrize(
    "breaking",
    [
        [OLD_ENTRY],  # as 0.3.0 seeded it
        restore_recent([OLD_ENTRY]),  # as it is seeded now
        [{"title": "Nur ein Titel"}],
        [],
    ],
)
def test_card_renders_strictly(breaking: list[dict[str, Any]]) -> None:
    out = render({BREAKING: {"recent": breaking}, WATCH: {"recent": news_entries()}})
    assert out.count("\n- ") == min(len(breaking), 3) + 3
    if not breaking:
        assert "Keine Eilmeldung." in out
    # Images with their copyright.
    assert out.count("<img ") == 3
    assert out.count("<small>Bild: ") == 3


def test_card_contents() -> None:
    out = render({BREAKING: {"recent": restore_recent([OLD_ENTRY])}})
    assert f"- [Alte Eilmeldung]({OLD_ENTRY['url']}) · vor 2 Std." in out
    assert "Keine Meldung." in out
    assert "<img " not in out
    assert "Quelle: tagesschau.de" in out
