"""The repo is public: fixtures must not contain Tagesschau prose."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from tests.conftest import FIXTURES

_spec = importlib.util.spec_from_file_location(
    "fetch_fixtures", Path(__file__).parent.parent / "tools" / "fetch_fixtures.py"
)
assert _spec and _spec.loader
fetch_fixtures = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_fixtures)


def test_scrub_replaces_prose_and_keeps_structure() -> None:
    raw = {
        "title": "Merz wirbt um Kapital",
        "topline": "Saarland",
        "date": "2026-10-20T14:23:47.761+02:00",
        "shareURL": "https://www.tagesschau.de/inland/x-114.html",
        "breakingNews": False,
        "regionId": 12,
    }
    assert fetch_fixtures.scrub(raw) == {**raw, "title": "Text 1"}


def test_scrub_keeps_dates() -> None:
    raw = {"headline": "Eilmeldung eins", "date": "Stand: 21.10.2026 11:25 Uhr"}
    assert fetch_fixtures.scrub(raw) == {**raw, "headline": "Text 1"}


def test_scrub_shortens_lists_but_keeps_breaking_news() -> None:
    items = [{"breakingNews": False, "n": i} for i in range(20)]
    items[15]["breakingNews"] = True
    result = fetch_fixtures.scrub(items)
    assert len(result) == fetch_fixtures.MAX_ITEMS + 1
    assert result[-1] == {"breakingNews": True, "n": 15}


def _strings(value: object) -> list[str]:
    if isinstance(value, dict):
        return [
            s
            for key, item in value.items()
            if key not in fetch_fixtures.KEEP_KEYS
            for s in _strings(item)
        ]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item)]
    return [value] if isinstance(value, str) else []


def test_committed_fixtures_contain_no_prose() -> None:
    for path in FIXTURES.glob("*.json"):
        if path.name == "_index.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        prose = [
            s for s in _strings(data) if " " in s.strip() and not s.startswith("Text ")
        ]
        assert not prose, f"{path.name}: {prose[:3]}"
