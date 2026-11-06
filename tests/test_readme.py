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
        as_local=lambda moment: moment.astimezone(BERLIN),
        state_attr=lambda entity, name: states.get(entity, {}).get(name),
    )
    return env.from_string(card_template()).render()


def news_entries() -> list[dict[str, Any]]:
    items = parse_api2u(load_fixture("news_bw.json"), Source.NEWS)
    return [recent_entry(item, ("Stuttgart",)) for item in items]


IMAGE_ENTRY = {
    "title": "Mit Bild",
    "url": "https://www.tagesschau.de/inland/mit-bild-100.html",
    "published": (NOW - timedelta(minutes=30)).isoformat(),
    "image": "https://images.tagesschau.de/image/x/1x1-144.jpg",
    "image_copyright": "SWR",
    "image_alt": 'Ein "Bild"',
}


@pytest.mark.parametrize(
    ("breaking", "images"),
    [
        ([OLD_ENTRY], 0),  # as 0.3.0 seeded it, without image keys
        (restore_recent([OLD_ENTRY]), 0),  # as it is seeded now
        ([IMAGE_ENTRY, OLD_ENTRY], 1),
        ([{"title": "Nur ein Titel"}], 0),
        ([], 0),
    ],
)
def test_card_renders_strictly(breaking: list[dict[str, Any]], images: int) -> None:
    out = render({BREAKING: {"recent": breaking}, WATCH: {"recent": news_entries()}})
    rows = min(len(breaking), 3) + 3
    assert out.count("<tr>") == rows
    # Image left in a cell of its own, with its credit; else one wide cell.
    assert out.count('<td width="52"><img ') == images + 3
    assert out.count(" · Bild: ") == images + 3
    assert out.count('<td colspan="2">') == rows - images - 3
    if not breaking:
        assert "Keine Eilmeldung." in out
        assert out.count("<table>") == 1


def test_card_contents() -> None:
    old = {**OLD_ENTRY, "published": "2026-11-05T18:05:00+01:00"}
    week = {**OLD_ENTRY, "url": None, "published": "2026-10-30T08:15:00+01:00"}
    out = render({BREAKING: {"recent": [IMAGE_ENTRY, OLD_ENTRY, old, week]}})
    assert (
        '<tr><td width="52"><img src="https://images.tagesschau.de/image/x/1x1-144.jpg"'
        ' alt="Ein &#34;Bild&#34;" width="44" height="44"></td>'
        '<td><a href="https://www.tagesschau.de/inland/mit-bild-100.html">Mit Bild</a>'
        "<br><small>vor 30 Min. · Bild: SWR</small></td></tr>"
    ) in out
    assert (
        f'<tr><td colspan="2"><a href="{OLD_ENTRY["url"]}">Alte Eilmeldung</a>'
        "<br><small>vor 2 Std.</small></td></tr>"
    ) in out
    assert "<small>gestern 18:05</small>" in out
    assert "Keine Meldung." in out
    assert "Quelle: tagesschau.de" in out
    # Only three per list.
    assert "30.10." not in out
    out = render({BREAKING: {"recent": [week]}})
    assert '<td colspan="2">Alte Eilmeldung<br><small>30.10. 08:15</small>' in out
