"""Tests for setup, coordinators, entities, events and repair issues."""

from __future__ import annotations

from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.const import (
    EVENT_STATE_CHANGED,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eilwacht.const import (
    CONF_KEYWORDS,
    CONF_REGIONS,
    DOMAIN,
    FAILURES_BEFORE_ISSUE,
    SUBENTRY_WATCH,
)
from custom_components.eilwacht.diagnostics import async_get_config_entry_diagnostics
from custom_components.eilwacht.model import Source
from custom_components.eilwacht.tagesschau import TagesschauError

from .conftest import FakeClient, news_item

ALERT = news_item(
    "eil-1", source=Source.HEADERAPP, title="Eilmeldung eins", breaking=True
)


def make_entry(*watches: tuple[str, list[int], str]) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Eilwacht",
        data={},
        subentries_data=[
            ConfigSubentryData(
                data={CONF_REGIONS: regions, CONF_KEYWORDS: keywords},
                subentry_type=SUBENTRY_WATCH,
                title=title,
                unique_id=None,
            )
            for title, regions, keywords in watches
        ],
    )


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def entity_id(hass: HomeAssistant, platform: str, unique_id: str) -> str:
    found = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)
    assert found is not None, unique_id
    return found


def breaking_ids(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, str]:
    return {
        "event": entity_id(hass, "event", f"{entry.entry_id}_breaking"),
        "active": entity_id(hass, "binary_sensor", f"{entry.entry_id}_breaking_active"),
        "last": entity_id(hass, "sensor", f"{entry.entry_id}_last_breaking"),
    }


async def refresh_breaking(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.breaking.async_refresh()
    await hass.async_block_till_done()


# --- Breaking news ------------------------------------------------------------


async def test_setup_without_watches(hass: HomeAssistant, client: FakeClient) -> None:
    entry = make_entry()
    await setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.news is None
    assert client.calls == ["headerapp"]  # the homepage only while it fails

    ids = breaking_ids(hass, entry)
    assert hass.states.get(ids["event"]).state == STATE_UNKNOWN
    assert hass.states.get(ids["active"]).state == STATE_OFF
    assert hass.states.get(ids["last"]).state == STATE_UNKNOWN
    assert hass.states.get(ids["active"]).attributes["attribution"] == (
        "Quelle: tagesschau.de"
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_new_alert_fires_once(hass: HomeAssistant, client: FakeClient) -> None:
    entry = make_entry()
    await setup(hass, entry)
    ids = breaking_ids(hass, entry)

    client.breaking = [ALERT]
    await refresh_breaking(hass, entry)
    event = hass.states.get(ids["event"])
    assert event.state != STATE_UNKNOWN
    assert event.attributes["event_type"] == "breaking_news"
    assert event.attributes["title"] == "Eilmeldung eins"
    assert event.attributes["url"] == "https://www.tagesschau.de/eil-1.html"
    assert hass.states.get(ids["active"]).state == STATE_ON
    assert hass.states.get(ids["active"]).attributes["titles"] == ["Eilmeldung eins"]
    assert hass.states.get(ids["last"]).state == "Eilmeldung eins"

    # still running: no second event
    fired_at = event.state
    await refresh_breaking(hass, entry)
    assert hass.states.get(ids["event"]).state == fired_at

    # over: the sensor keeps the last alert
    client.breaking = []
    await refresh_breaking(hass, entry)
    assert hass.states.get(ids["active"]).state == STATE_OFF
    assert hass.states.get(ids["last"]).state == "Eilmeldung eins"


async def test_alert_running_at_startup_is_not_announced(
    hass: HomeAssistant, client: FakeClient
) -> None:
    client.breaking = [ALERT]
    entry = make_entry()
    await setup(hass, entry)
    ids = breaking_ids(hass, entry)
    assert hass.states.get(ids["event"]).state == STATE_UNKNOWN
    assert hass.states.get(ids["active"]).state == STATE_ON
    assert hass.states.get(ids["last"]).state == "Eilmeldung eins"


async def test_homepage_is_ignored_while_headerapp_works(
    hass: HomeAssistant, client: FakeClient, freezer: FrozenDateTimeFactory
) -> None:
    entry = make_entry()
    await setup(hass, entry)
    ids = breaking_ids(hass, entry)

    client.breaking = [ALERT]
    await refresh_breaking(hass, entry)
    fired_at = hass.states.get(ids["event"]).state

    # The homepage flags the same alert under the article URL: polled together,
    # it would be announced twice.
    client.homepage = [news_item("artikel-100", source=Source.HOMEPAGE, breaking=True)]
    freezer.tick(timedelta(minutes=11))
    await refresh_breaking(hass, entry)
    assert "homepage" not in client.calls
    assert hass.states.get(ids["event"]).state == fired_at
    assert len(entry.runtime_data.breaking.data.active) == 1


async def test_homepage_is_the_fallback(
    hass: HomeAssistant,
    client: FakeClient,
    issue_registry: ir.IssueRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    client.breaking = TagesschauError("headerapp down")
    entry = make_entry()
    await setup(hass, entry)
    ids = breaking_ids(hass, entry)
    assert hass.states.get(ids["active"]).state == STATE_OFF  # homepage answered

    # while headerapp fails, the homepage is polled every 2 minutes
    client.homepage = [
        news_item("eil-2", source=Source.HOMEPAGE, title="Zwei", breaking=True)
    ]
    freezer.tick(timedelta(minutes=2))
    await refresh_breaking(hass, entry)
    assert hass.states.get(ids["active"]).state == STATE_ON
    assert hass.states.get(ids["event"]).attributes["title"] == "Zwei"

    coordinator = entry.runtime_data.breaking
    while coordinator.failures < FAILURES_BEFORE_ISSUE["headerapp"]:
        assert issue_registry.async_get_issue(DOMAIN, "source_failed_headerapp") is None
        await refresh_breaking(hass, entry)
    issue = issue_registry.async_get_issue(DOMAIN, "source_failed_headerapp")
    assert issue is not None
    assert issue.translation_key == "source_failed"

    # headerapp is back: the homepage's alert no longer counts
    client.breaking = []
    await refresh_breaking(hass, entry)
    assert issue_registry.async_get_issue(DOMAIN, "source_failed_headerapp") is None
    assert hass.states.get(ids["active"]).state == STATE_OFF


async def test_both_sources_down(hass: HomeAssistant, client: FakeClient) -> None:
    client.breaking = TagesschauError("down")
    client.homepage = RuntimeError("bug")
    entry = make_entry()
    await setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert not entry.runtime_data.breaking.last_update_success
    ids = breaking_ids(hass, entry)
    assert hass.states.get(ids["active"]).state == STATE_UNAVAILABLE


async def test_recorded_sample_in_diagnostics(
    hass: HomeAssistant, client: FakeClient
) -> None:
    entry = make_entry(("BW", [1], ""))
    await setup(hass, entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["breaking"]["recorded_sample"] is None

    client.breaking = [ALERT]
    await refresh_breaking(hass, entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    sample = diagnostics["breaking"]["recorded_sample"]
    assert sample["response"] == {
        "breakingNews": [{"id": "eil-1", "headline": "Eilmeldung eins"}]
    }
    assert diagnostics["news"]["regions"] == [1]
    assert diagnostics["watches"][next(iter(entry.subentries))]["title"] == "BW"


async def test_unknown_alert_format_is_recorded_and_logged(
    hass: HomeAssistant, client: FakeClient, caplog: pytest.LogCaptureFixture
) -> None:
    entry = make_entry()
    await setup(hass, entry)
    # The parser finds nothing usable, e.g. after a format change.
    client.raw = {"breakingNews": [{"headlineText": "Neu", "link": "/x.html"}]}
    await refresh_breaking(hass, entry)
    await refresh_breaking(hass, entry)
    assert entry.runtime_data.breaking.sample.data["response"] == client.raw
    assert caplog.text.count("breaking news in an unknown format") == 1


# --- News watches ---------------------------------------------------------------


def watch_ids(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, str]:
    (subentry_id,) = entry.subentries
    return {
        "event": entity_id(hass, "event", f"{subentry_id}_news"),
        "last": entity_id(hass, "sensor", f"{subentry_id}_last_news"),
        "count": entity_id(hass, "sensor", f"{subentry_id}_news_24h"),
    }


async def refresh_news(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.news.async_refresh()
    await hass.async_block_till_done()


@pytest.mark.freeze_time("2026-10-20T16:00:00+00:00")
async def test_watch(hass: HomeAssistant, client: FakeClient) -> None:
    client.news = {
        (1, 2): [
            news_item("streik", title="Streiks in Ulm", regions=(1,), hour=11),
            news_item("wetter", title="Wetter", regions=(1,), hour=12),
            news_item("alt", title="Streik vor drei Tagen", regions=(2,), day=17),
        ]
    }
    entry = make_entry(("Streik", [1, 2], "Streik*"))
    await setup(hass, entry)
    assert client.calls[-1] == "news[1, 2]"
    ids = watch_ids(hass, entry)
    assert hass.states.get(ids["event"]).state == STATE_UNKNOWN  # learned silently
    last = hass.states.get(ids["last"])
    assert last.state == "Streiks in Ulm"
    assert last.attributes["keywords"] == ["Streik*"]
    assert last.attributes["regions"] == ["Baden-Württemberg"]
    assert hass.states.get(ids["count"]).state == "1"  # "alt" is older than 24 hours

    client.news[(1, 2)] = [
        news_item("neu", title="Streik bei der SSB", regions=(1,), hour=17),
        news_item("anders", title="Fußball", regions=(1,), hour=17),
        *client.news[(1, 2)],
    ]
    await refresh_news(hass, entry)
    event = hass.states.get(ids["event"])
    assert event.attributes["event_type"] == "news"
    assert event.attributes["title"] == "Streik bei der SSB"
    assert hass.states.get(ids["last"]).state == "Streik bei der SSB"
    assert hass.states.get(ids["count"]).state == "2"


async def test_national_watch(hass: HomeAssistant, client: FakeClient) -> None:
    client.news = {
        (): [
            news_item("bund", title="Bundestag", hour=13),
            news_item("land", title="Landtag", regions=(10,), hour=14),
        ]
    }
    entry = make_entry(("Bund", [0], ""))
    await setup(hass, entry)
    assert client.calls[-1] == "news[]"
    assert hass.states.get(watch_ids(hass, entry)["last"]).state == "Bundestag"


async def test_news_failure_raises_issue(
    hass: HomeAssistant, client: FakeClient, issue_registry: ir.IssueRegistry
) -> None:
    client.news = TagesschauError("down")
    entry = make_entry(("BW", [1], ""))
    await setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(watch_ids(hass, entry)["last"]).state == STATE_UNAVAILABLE
    await refresh_news(hass, entry)
    assert issue_registry.async_get_issue(DOMAIN, "source_failed_news") is not None

    client.news = {}
    await refresh_news(hass, entry)
    assert issue_registry.async_get_issue(DOMAIN, "source_failed_news") is None
    assert hass.states.get(watch_ids(hass, entry)["count"]).state == "0"


# --- Restarts (seen.py) -----------------------------------------------------------

# 12:30 in Berlin, half an hour after the test items are published.
NOON = "2026-10-20T10:30:00+00:00"


async def restart(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Unload and set up again, as Home Assistant does on a restart."""
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.freeze_time(NOON)
async def test_alert_during_restart_is_announced(
    hass: HomeAssistant, client: FakeClient
) -> None:
    entry = make_entry()
    await setup(hass, entry)
    ids = breaking_ids(hass, entry)

    changes: list[dict] = []

    @callback
    def record(event: Event) -> None:
        if event.data["entity_id"] == ids["event"]:
            changes.append(event.data)

    hass.bus.async_listen(EVENT_STATE_CHANGED, record)

    client.breaking = [ALERT]  # appears while Home Assistant restarts
    await restart(hass, entry)
    event = hass.states.get(ids["event"])
    assert event.state != STATE_UNKNOWN
    assert event.attributes["title"] == "Eilmeldung eins"

    # The bundled blueprints skip changes from nothing or from "unavailable"
    # (what a restart looks like): the caught-up alert must not be one.
    (announced,) = [
        c for c in changes if c["new_state"] and c["new_state"].attributes.get("title")
    ]
    assert announced["old_state"] is not None
    assert announced["old_state"].state != STATE_UNAVAILABLE

    # known now: the next restart does not announce it again
    fired_at = event.state
    await restart(hass, entry)
    assert hass.states.get(ids["event"]).state == fired_at


@pytest.mark.freeze_time(NOON)
async def test_after_a_long_pause_nothing_is_caught_up(
    hass: HomeAssistant, client: FakeClient, freezer: FrozenDateTimeFactory
) -> None:
    entry = make_entry()
    await setup(hass, entry)
    ids = breaking_ids(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)

    freezer.tick(timedelta(hours=7))
    client.breaking = [news_item("eil-2", source=Source.HEADERAPP, hour=18)]
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ids["event"]).state == STATE_UNKNOWN


@pytest.mark.freeze_time(NOON)
async def test_watch_item_during_restart_is_announced(
    hass: HomeAssistant, client: FakeClient
) -> None:
    client.news = {
        (1,): [news_item("alt", title="Streik gestern", regions=(1,), hour=9)]
    }
    entry = make_entry(("Streik", [1], "Streik"))
    await setup(hass, entry)
    ids = watch_ids(hass, entry)
    assert hass.states.get(ids["event"]).state == STATE_UNKNOWN

    client.news[(1,)].insert(
        0, news_item("neu", title="Streiks bei der SSB", regions=(1,), hour=12)
    )
    await restart(hass, entry)
    event = hass.states.get(ids["event"])
    assert event.attributes["title"] == "Streiks bei der SSB"
    assert event.attributes["keywords"] == ["Streik"]


@pytest.mark.freeze_time(NOON)
async def test_changed_watch_learns_silently(
    hass: HomeAssistant, client: FakeClient
) -> None:
    client.news = {(1,): [news_item("a", title="Streik", regions=(1,), hour=12)]}
    entry = make_entry(("Streik", [1], "Streik"))
    await setup(hass, entry)
    ids = watch_ids(hass, entry)

    # Without keywords the watch shows other items: no flood of "new" ones.
    client.news[(1,)].append(news_item("b", title="Wetter", regions=(1,), hour=12))
    (subentry,) = entry.subentries.values()
    hass.config_entries.async_update_subentry(
        entry, subentry, data={CONF_REGIONS: [1], CONF_KEYWORDS: ""}
    )
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(ids["event"]).state == STATE_UNKNOWN
