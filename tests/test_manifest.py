"""Consistency checks for manifest.json, hacs.json, pyproject.toml and translations."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from custom_components.eilwacht.const import DOMAIN, REGIONS, USER_AGENT, VERSION
from custom_components.eilwacht.model import NewsItem, Source
from custom_components.eilwacht.watch import ITEM_KEYS, item_attributes

ROOT = Path(__file__).parent.parent
INTEGRATION = ROOT / "custom_components" / DOMAIN


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest() -> dict:
    return load(INTEGRATION / "manifest.json")


def test_versions_match() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert manifest()["version"] == VERSION == pyproject["project"]["version"]
    assert VERSION in USER_AGENT


def test_domain_matches_folder() -> None:
    assert manifest()["domain"] == DOMAIN == INTEGRATION.name


def test_manifest_key_order() -> None:
    # hassfest requires domain, name first, then the remaining keys sorted.
    keys = list(manifest())
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])


def test_brand_images_present() -> None:
    for name in ("icon", "logo", "dark_icon", "dark_logo"):
        for suffix in (".png", "@2x.png"):
            assert (INTEGRATION / "brand" / f"{name}{suffix}").is_file()


def test_hacs_json() -> None:
    hacs = load(ROOT / "hacs.json")
    assert hacs["name"] == manifest()["name"]
    assert hacs["filename"] == f"{DOMAIN}.zip"


def _keys(data: object, prefix: str = "") -> set[str]:
    if isinstance(data, dict):
        return {
            k for key, value in data.items() for k in _keys(value, f"{prefix}{key}.")
        }
    return {prefix.rstrip(".")}


def test_translations_complete() -> None:
    strings = load(INTEGRATION / "strings.json")
    assert load(INTEGRATION / "translations" / "en.json") == strings
    assert _keys(load(INTEGRATION / "translations" / "de.json")) == _keys(strings)


def test_region_options_translated() -> None:
    options = load(INTEGRATION / "strings.json")["selector"]["regions"]["options"]
    assert set(options) == {"0", *(str(r) for r in REGIONS)}


def test_item_keys() -> None:
    item = NewsItem(id="x", source=Source.NEWS, title="t")
    assert set(item_attributes(item, ("k",))) == ITEM_KEYS
