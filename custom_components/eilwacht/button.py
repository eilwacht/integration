"""Button: a short report for a bug report (issue_report.py), on the Eilwacht device.

Without the watches' names and keywords: names are often places, keywords
free text. The report shows the federal states and how many keywords a watch
has.
"""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EilwachtConfigEntry, EilwachtRuntimeData
from .const import DOMAIN, REGIONS, VERSION
from .coordinator import watch_subentries
from .entity import _device
from .issue_report import Lines, build, show
from .watch import NATIONAL, Watch

NAME = "Eilwacht"
# Errors name the URL and the cause; longer ones are cut.
MAX_ERROR = 160


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EilwachtConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """The report button of the Eilwacht device."""
    async_add_entities([IssueReport(entry)])


class IssueReport(ButtonEntity):
    """A short report to copy into a bug report, as a notification: what an
    issue needs without the diagnostics download (issue_report.py).

    Not a coordinator entity: it stays available while tagesschau.de fails,
    which is when it is needed most.
    """

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "issue_report"

    def __init__(self, entry: EilwachtConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_issue_report"
        self._attr_device_info = _device(entry.entry_id, NAME)

    async def async_press(self) -> None:
        entry = self._entry
        runtime = entry.runtime_data
        watches = [
            runtime.watches[s.subentry_id]
            for s in watch_subentries(entry)
            if s.subentry_id in runtime.watches
        ]
        report = build(
            self.hass,
            DOMAIN,
            NAME,
            VERSION,
            entry,
            mapping={},
            extra=entry_lines(runtime),
            endpoints=endpoint_lines(runtime),
            settings_lines=watch_lines(watches),
        )
        show(self.hass, DOMAIN, NAME, entry, report)


def entry_lines(runtime: EilwachtRuntimeData) -> Lines:
    breaking = runtime.breaking.data
    news = runtime.news.data if runtime.news else None
    sample = runtime.breaking.sample.data
    return [
        ("watches", str(len(runtime.watches))),
        ("active alerts", "-" if breaking is None else str(len(breaking.active))),
        (
            "recorded alert sample",
            str(sample.get("recorded", "?"))[:10] if sample else "none",
        ),
        ("news items", "-" if news is None else str(len(news.items))),
    ]


def endpoint_lines(runtime: EilwachtRuntimeData) -> Lines:
    """Status of each tagesschau.de endpoint: ok, or failures and the error."""
    breaking = runtime.breaking
    if not breaking.failures:
        homepage = "not needed"
    elif breaking.homepage_error:
        homepage = f"failing ({_cut(breaking.homepage_error)})"
    elif breaking.homepage_active:
        homepage = "standing in"
    else:
        homepage = "-"
    news = runtime.news
    return [
        ("headerapp", _status(breaking.failures, breaking.error)),
        ("homepage", homepage),
        ("news", "no watch" if news is None else _status(news.failures, news.error)),
    ]


def watch_lines(watches: Iterable[Watch]) -> Lines:
    """Per watch the federal states and the number of keywords, never the
    keywords themselves or the watch's name."""
    return [
        (
            f"watch {number}",
            f"{_regions(watch.regions)}; keywords {len(watch.keywords.include)}, "
            f"excluded {len(watch.keywords.exclude)}",
        )
        for number, watch in enumerate(watches, 1)
    ]


def _regions(regions: Iterable[int]) -> str:
    names = [
        "national" if r == NATIONAL else REGIONS.get(r, str(r)) for r in sorted(regions)
    ]
    return ", ".join(names) or "-"


def _status(failures: int, error: str | None) -> str:
    if not failures:
        return "ok"
    text = f"{failures} failed polls in a row"
    return f"{text} ({_cut(error)})" if error else text


def _cut(text: str) -> str:
    return text if len(text) <= MAX_ERROR else text[: MAX_ERROR - 1] + "…"
