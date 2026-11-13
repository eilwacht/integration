#!/usr/bin/env python3
"""Build the data of the demo (docs/demo/): made-up news, real logic.

Usage (from the repo root):
    uv run tools/make_demo.py

Everything here is invented: places like "Musterstadt" or "Exempelingen",
clubs, unions and companies that do not exist, harmless odd events, links to
example.invalid. Nothing comes from tagesschau.de, nothing may resemble real
news or real people (terms of use, docs/ENTWICKLUNG.md section 4).

The invented items run through the integration's own code, as raw api2u and
headerapp responses: parse_api2u/parse_headerapp, Watch and KeywordFilter,
NewItemTracker (which items fire an event), count_since, item_attributes and
the lists of recent items (recent.py).
Breaking news is polled every minute, news every 15 minutes, over two days.
The texts of push and announcement repeat the templates of the blueprints.

Output:
    docs/demo/data/demo.json      items, watches and two moments (quiet
                                  afternoon, breaking news alert running)
    docs/demo/data/selftest.json  keyword examples with Python's results; the
                                  page checks its JavaScript port of
                                  KeywordFilter against them (?selftest)
"""

from __future__ import annotations

import dataclasses
import json
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from custom_components.eilwacht.changes import NewItemTracker  # noqa: E402
from custom_components.eilwacht.const import REGIONS, VERSION  # noqa: E402
from custom_components.eilwacht.keywords import KeywordFilter  # noqa: E402
from custom_components.eilwacht.model import NewsItem, Source  # noqa: E402
from custom_components.eilwacht.recent import (  # noqa: E402
    RECENT,
    RECENT_LIMIT,
    add_recent,
    merge_recent,
    recent_entry,
)
from custom_components.eilwacht.tagesschau import (  # noqa: E402
    BERLIN,
    parse_api2u,
    parse_headerapp,
)
from custom_components.eilwacht.watch import (  # noqa: E402
    NATIONAL,
    Match,
    Watch,
    count_since,
    item_attributes,
)

OUT = ROOT / "docs" / "demo" / "data"
LINK = "https://example.invalid/demo/"
# Teaser images: never real or real-looking ones. Every second story gets a
# placeholder the page draws itself ("placeholder:<slug>", no request); alerts
# have none, as in headerapp.
PLACEHOLDER = "placeholder:"

# The demo runs from START (polls learn silently, as after a long pause) to
# the later moment. Both moments are on the same Wednesday.
START = datetime(2026, 10, 12, 12, 0, tzinfo=BERLIN)
MOMENTS = {
    "quiet": datetime(2026, 10, 14, 17, 30, tzinfo=BERLIN),
    "breaking": datetime(2026, 10, 14, 19, 20, tzinfo=BERLIN),
}
NEWS_EVERY = 15  # minutes, NEWS_INTERVAL

# Watches as the subentry flow stores them: name, regions, keywords.
WATCHES = {
    "stuttgart": ("Stuttgart", [1], "Stuttgart"),
    "streik": ("Streik", [NATIONAL, 1], "*streik, -Fußball"),
}

# Blueprint defaults for the quiet times. The announcement uses its own intro:
# the default "Eilmeldung der Tagesschau:" in front of a made-up headline would
# credit invented news to the Tagesschau (the page names the default).
PUSH_QUIET = (time(22, 0), time(7, 0))
TTS_QUIET = (time(21, 30), time(7, 30))
TTS_INTRO = "Eilmeldung:"


def _at(day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=BERLIN)


# (slug, published, region ids, ressort, topline, title, first sentence, tags)
STORIES: list[tuple[Any, ...]] = [
    # National (no federal state)
    ("baeckerei-warnstreik", _at(13, 8, 10), (), "wirtschaft", "Beispiel-Bäckereien",
     "Warnstreik in Bäckereien: Brezeln nur noch bis Mittag",
     "Die erfundene Gewerkschaft der Beispielberufe ruft in allen Musterbäckereien zu einem Warnstreik auf.",
     ("Warnstreik", "Bäckerei")),
    ("gartenzwerg-studie", _at(13, 11, 30), (), "wissen", "Erfundene Forschung",
     "Studie: Gartenzwerge schauen am liebsten nach Süden",
     "Ein Institut aus Beispielhausen hat dafür 4000 Vorgärten vermessen.",
     ("Gartenzwerge",)),
    ("fc-musterstadt-training", _at(13, 15, 45), (), "sport", "Fußball",
     "FC Musterstadt: Spieler streiken beim Lauftraining",
     "Statt zehn Runden drehten die Profis nur eine – aus Protest gegen das neue Trikot in Senfgelb.",
     ("Fußball", "FC Musterstadt")),
    ("modellbahn-streik", _at(14, 7, 20), (), "wirtschaft", "Kleiner Maßstab",
     "Bahnstreik der Modelleisenbahner: Miniaturzüge stehen still",
     "Im erfundenen Verband der Beispiel-Modellbahnen bleiben am Wochenende alle Anlagen aus.",
     ("Modellbahn",)),
    ("briefmarke-brezel", _at(14, 9, 0), (), "inland", "Philatelie",
     "Neue Beispiel-Briefmarke zeigt eine Brezel",
     "Die Marke zu 95 Cent gibt es nur in dieser Vorführung.",
     ("Briefmarke",)),
    ("exempelingen-herbst", _at(14, 12, 15), (), "wissen", "Wetterkuriosum",
     "Exempelingen meldet den ruhigsten Herbst seit Beginn der Beispielmessungen",
     "Seit drei Wochen ist dort kein einziges Blatt quer über die Straße geweht.",
     ()),
    ("baeckerei-einigung", _at(14, 16, 40), (), "wirtschaft", "Beispiel-Bäckereien",
     "Streiks in Bäckereien vorerst beendet",
     "Gewerkschaft und Innung einigen sich auf längere Pausen für die Teigruhe.",
     ("Streik", "Bäckerei")),
    ("musterstadt-bibliothek", _at(14, 18, 5), (), "inland", "Musterstadt",
     "Musterstadt verlängert die Öffnungszeiten ihrer Beispielbibliothek",
     "Künftig darf bis Mitternacht geblättert werden, aber nur leise.",
     ()),
    ("fusion-fragen", _at(14, 19, 15), (), "inland", "Beispielmusterstadt",
     "Was die Fusion von Musterstadt und Beispielhausen bedeutet",
     "Postleitzahlen und Ortsschilder bleiben vorerst, die Brezeln auch.",
     ("Musterstadt", "Beispielhausen")),
    # Baden-Württemberg
    ("tulpen-musterplatz", _at(13, 6, 30), (1,), None, "Stuttgart",
     "Stuttgarter Beispielgärtner pflanzen 500 Probe-Tulpen am Musterplatz",
     "Im April sollen die Zwiebeln in den Vereinsfarben Senfgelb und Lila blühen.",
     ("Baden-Württemberg",)),
    ("neckarfaehre", _at(13, 10, 0), (1,), None, "Musterhausen am Neckar",
     "Erfundene Neckarfähre fährt jetzt auch sonntags",
     "Fahrgäste mit Gartenzwerg zahlen den halben Preis.",
     ("Baden-Württemberg",)),
    ("brezel-automat", _at(13, 13, 20), (1,), None, "Exempelingen",
     "Bahnhof Exempelingen bekommt den ersten Brezel-Automaten",
     "Der Automat backt auf Knopfdruck und sagt dabei „Bitte schön“.",
     ("Baden-Württemberg",)),
    ("brezel-akademie", _at(13, 16, 0), (1,), None, "Stuttgart",
     "Stuttgarter Brezel-Akademie sucht die längste Brezel des Landes",
     "Bewerbungen sind bis Freitag möglich, Mindestlänge ein Meter.",
     ("Baden-Württemberg", "Brezel")),
    ("gartenzwerg-abteil", _at(13, 19, 40), (1,), None, "Verkehr",
     "S-Bahn Stuttgart testet ein Abteil nur für Gartenzwerge",
     "Der erfundene Probebetrieb läuft auf der Beispiellinie S0 bis zum Jahresende.",
     ("Baden-Württemberg", "Gartenzwerge")),
    ("freibad-warnstreik", _at(14, 6, 45), (1,), None, "Musterhausen am Neckar",
     "Warnstreik im Freibad: Bademeister fordern wärmeres Wasser",
     "Die Beispiel-Bademeister wollen erst ab 31 Grad wieder pfeifen.",
     ("Baden-Württemberg",)),
    ("regenschirme", _at(14, 8, 30), (1,), None, "Stuttgart",
     "Beispielbibliothek am Stuttgarter Musterplatz verleiht jetzt Regenschirme",
     "Ausleihe wie bei Büchern: vier Wochen, einmal verlängerbar.",
     ("Baden-Württemberg",)),
    ("kickers-sieg", _at(14, 11, 10), (1,), None, "Fußball",
     "Musterhausener Kickers gewinnen 7:6 nach Verlängerung",
     "Den Siegtreffer köpfte der Torwart in der letzten Sekunde.",
     ("Baden-Württemberg", "Fußball")),
    ("musterbrunnen", _at(14, 13, 50), (1,), None, "Stuttgart",
     "Erfundener Musterbrunnen in Stuttgart sprudelt wieder",
     "Nach zwei Jahren Pause fließt das Wasser jetzt wahlweise links- oder rechtsherum.",
     ("Baden-Württemberg",)),
    ("kuerbisfest", _at(14, 15, 30), (1,), None, "Exempelingen",
     "Exempelinger Kürbisfest: Rekordkürbis wiegt 812 Kilo",
     "Besucher sollen über die Autobahnausfahrt Exempelingen-Süd anreisen.",
     ("Baden-Württemberg",)),
    ("kegelverein", _at(14, 17, 10), (1,), None, "Stuttgart",
     "Stuttgarter Musterverein feiert 100 Jahre Beispielkegeln",
     "Zum Jubiläum rollen die Kugeln einen Abend lang rückwärts.",
     ("Baden-Württemberg",)),
    ("fussballer-kuerbis", _at(14, 18, 40), (1,), None, "Stuttgart",
     "Stuttgarter Fußballer sammeln für den Kürbisfest-Verein",
     "Für jedes Tor im Training spendet die Mannschaft einen Euro.",
     ("Baden-Württemberg", "Fußball")),
    ("abteil-verlaengert", _at(14, 19, 10), (1,), None, "Verkehr",
     "S-Bahn in Stuttgart: Gartenzwerg-Abteil wird verlängert",
     "Wegen großer Nachfrage gibt es ab Montag zwei Abteile.",
     ("Baden-Württemberg", "Gartenzwerge")),
    # Bayern: outside both watches
    ("maibaum", _at(13, 12, 0), (2,), None, "Beispielhausen",
     "Der Maibaum von Beispielhausen steht im Oktober noch",
     "Niemand im Ort weiß mehr, wer ihn eigentlich abbauen sollte.",
     ("Bayern",)),
    ("seilbahn-warnstreik", _at(14, 10, 30), (2,), None, "Musterberg",
     "Warnstreik bei der Beispiel-Seilbahn am Musterberg",
     "Die Gondeln bleiben unten, die Wanderer gehen zu Fuß.",
     ("Bayern",)),
]  # fmt: skip

# Breaking news alerts as json/headerapp shows them: (shown from, shown
# until or None, raw alert). The date is display text, as in the real feed.
ALERTS: list[tuple[datetime, datetime | None, dict[str, str]]] = [
    (
        _at(13, 21, 5),
        _at(13, 21, 41),
        {
            "id": "00000000-0000-4000-8000-000000000001",
            "headline": "Musterstadt meldet Rekord: 12.000 Laternen auf einmal unterwegs",
            "text": "So viele Kinder wie nie zogen am Abend durch die erfundene Altstadt.",
            "url": f"{LINK}eilmeldung-1.html",
            "date": "Stand: 13.10.2026 21:05 Uhr",
            "linkText": "Eilmeldung",
        },
    ),
    (
        _at(14, 19, 2),
        None,
        {
            "id": "00000000-0000-4000-8000-000000000002",
            "headline": "Musterstadt und Beispielhausen schließen sich zusammen",
            "text": "Beide erfundenen Gemeinderäte stimmten am Abend für die Fusion zu „Beispielmusterstadt“.",
            "url": f"{LINK}eilmeldung-2.html",
            "date": "Stand: 14.10.2026 19:02 Uhr",
            "linkText": "Eilmeldung",
        },
    ),
]

# Keyword examples for the self-test of the page's JavaScript port. The
# expected results come from KeywordFilter below, not from this list.
EXAMPLES: list[tuple[str, str]] = [
    # README table
    ("Stuttgart", "Stuttgart"),
    ("Stuttgart", "Stuttgarter Gänsheide"),
    ("Streik", "Streik, Streiks, Streikende"),
    ("Streik", "Warnstreik"),
    ("*streik", "Warnstreik"),
    ("*streik", "Bahnstreiks"),
    ("*streik", "Streik"),
    ("Bahn", "Bahnhof"),
    ("Bahn", "Autobahn"),
    ("Bahn", "S-Bahn"),
    ("S-Bahn Stuttgart", "S-Bahn Stuttgarts"),
    ("S-Bahn Stuttgart", "S-Bahn in Stuttgart"),
    ("S-Bahn Stuttgart", "Störung bei der S-Bahn\n Stuttgart"),
    ("-Fußball", "Fußballer"),
    ("-Fußball", "Wetter"),
    ("Stuttgart, -Fußball", "Fußball in Stuttgart"),
    ("Stuttgart, Ulm", "Ulm und Stuttgart"),
    # syntax corners
    ("", "irgendwas"),
    (" , ", "irgendwas"),
    ("*", "irgendwas"),
    ("-", "irgendwas"),
    ("- Fußball", "Fußball"),
    ("--Fußball", "Spiel ohne -Fußball"),
    ("Fußball -", "Fußball - Tore"),
    ("Streik*", "Streiks"),
    ("St*gart", "Stuttgart"),
    ("**gart", "Stuttgart"),
    ("bahn   hof", "Bahn \t Hof"),
    ("S-Bahn\tStuttgart", "S-Bahn Stuttgart"),
    ("warnstreik", "WARNSTREIK"),
    ("ÄRGER", "ärger im Verein"),
    ("große", "GROẞE Pause"),
    ("Straße", "STRASSE gesperrt"),
    ("café", "CAFÉ am Markt"),
    ("über", "gegenüber"),
    ("A8", "Unfall auf der A8."),
    ("A8", "A81"),
    ("8", "A8"),
    ("x", "-x"),
    ("_x", "a_x"),
    ("2026", "Jahr 2026"),
    ("(Test)", "(Test) bestanden"),
    ("a.b", "axb"),
    ("C++", "C++ Kurs"),
    ("$5", "kostet $5"),
    (
        "Musterstadt, Beispielhausen, -Brezel",
        "Musterstadt und Beispielhausen ohne Brezel",
    ),
    ("Exempelingen, Kürbis", "Kürbisfest in Exempelingen"),
]

# Watch cases: every preset of the page's tester with several region sets,
# over all demo items (ids and matched terms, newest first).
PRESETS = [
    "",
    "Stuttgart",
    "Streik",
    "*streik",
    "Bahn",
    "S-Bahn Stuttgart",
    "-Fußball",
    "*streik, -Fußball",
    "Brezel*, Gartenzwerg",
    "stuttgart, -fußball, -s-bahn",
    "Musterstadt, Beispielhausen",
]
REGION_SETS = [[NATIONAL], [1], [NATIONAL, 1], [1, 2], [NATIONAL, 1, 2]]


def raw_story(row: tuple[Any, ...]) -> dict[str, Any]:
    """An api2u item as the news endpoint delivers it."""
    slug, published, regions, ressort, topline, title, sentence, tags = row
    return {
        "sophoraId": f"demo-{slug}",
        "externalId": f"demo-{slug}",
        "title": title,
        "topline": topline,
        "firstSentence": sentence,
        "date": published.isoformat(),
        "detailsweb": f"{LINK}{slug}.html",
        "shareURL": None,
        "breakingNews": False,
        "ressort": ressort,
        "regionId": regions[0] if regions else 0,
        "regionIds": list(regions),
        "tags": [{"tag": tag} for tag in tags],
        "type": "story",
    }


def quiet(moment: datetime, window: tuple[time, time]) -> bool:
    """The blueprints' time condition across midnight (after start, before end)."""
    local = moment.astimezone(BERLIN).time()
    start, end = window
    return local >= start or local < end


def watch_push_title(watch: str, heading: str) -> str:
    """Title of neue_meldung_push.yaml: the watch, then topline or keywords."""
    if heading.lower() == watch.lower():
        return f"Eilwacht · {watch}"
    return f"Eilwacht · {watch}: {heading}"


def iso(moment: datetime) -> str:
    return moment.astimezone(BERLIN).isoformat()


def with_placeholder_images(items: list[NewsItem]) -> list[NewsItem]:
    """Every second item with a placeholder instead of a teaser image."""
    return [
        dataclasses.replace(
            item,
            image=f"{PLACEHOLDER}{item.id}",
            image_copyright="Beispiel",
            image_alt="Beispielbild",
        )
        if n % 2 == 1
        else item
        for n, item in enumerate(items)
    ]


def item_json(item: NewsItem) -> dict[str, Any]:
    """An item for the page (the keyword tester searches these fields)."""
    return {
        "id": item.id,
        "title": item.title,
        "topline": item.topline,
        "summary": item.summary,
        "url": item.url,
        "published": iso(item.published) if item.published else None,
        "region_ids": list(item.region_ids),
        "ressort": item.ressort,
        "tags": list(item.tags),
    }


def attributes(item: NewsItem, keywords: tuple[str, ...] = ()) -> dict[str, Any]:
    """item_attributes() with local times, as the frontend shows them."""
    result = item_attributes(item, keywords)
    if item.published:
        result["published"] = iso(item.published)
    return result


def matches_json(found: list[Match]) -> list[list[Any]]:
    return [[m.item.id, list(m.keywords)] for m in found]


class Simulation:
    """Polls the made-up feeds and records what Home Assistant would show."""

    def __init__(self, items: list[NewsItem]) -> None:
        self.items = items
        self.watches = {
            key: Watch(frozenset(regions), KeywordFilter.parse(text))
            for key, (_, regions, text) in WATCHES.items()
        }
        # Breaking news
        self.breaking_tracker = NewItemTracker()
        self.active: tuple[NewsItem, ...] = ()
        self.last_breaking: NewsItem | None = None
        self.breaking_recent: list[dict[str, Any]] = []
        self.breaking_event: dict[str, Any] | None = None
        self.breaking_history: list[tuple[datetime, bool]] = []
        # News watches
        self.trackers = {key: NewItemTracker() for key in WATCHES}
        self.visible: list[NewsItem] = []
        self.matches: dict[str, list[Match]] = {key: [] for key in WATCHES}
        self.counts: dict[str, list[tuple[datetime, int]]] = {k: [] for k in WATCHES}
        self.watch_events: dict[str, dict[str, Any] | None] = dict.fromkeys(WATCHES)
        self.watch_recent: dict[str, list[dict[str, Any]]] = {k: [] for k in WATCHES}
        # Blueprints
        self.pushes: list[dict[str, Any]] = []
        self.announcements: list[dict[str, Any]] = []

    def poll_breaking(self, now: datetime) -> None:
        shown = [
            raw
            for start, end, raw in ALERTS
            if start <= now and (end is None or now < end)
        ]
        response = {"breakingNews": shown} if shown else {"liveStream": {}}
        active: dict[str, NewsItem] = {}
        for item in parse_headerapp(response):
            active.setdefault(item.key, item)
        new = self.breaking_tracker.update(active.values())
        self.active = tuple(active.values())
        on = bool(self.active)
        if not self.breaking_history or self.breaking_history[-1][1] != on:
            self.breaking_history.append((now, on))
        for item in new:
            self.last_breaking = item
            self.breaking_recent = add_recent(self.breaking_recent, recent_entry(item))
            self.breaking_event = {"at": iso(now), "attributes": attributes(item)}
            if not quiet(now, PUSH_QUIET):  # eilmeldung_push.yaml
                message = item.title + (f"\n{item.summary}" if item.summary else "")
                self.pushes.append(
                    {
                        "at": iso(now),
                        "device": "Eilwacht",
                        "title": "Eilmeldung",
                        "title_en": "Breaking news",
                        "message": message,
                        "url": item.url,
                    }
                )
            if not quiet(now, TTS_QUIET):  # eilmeldung_ansage.yaml
                self.announcements.append(
                    {"at": iso(now), "message": f"{TTS_INTRO} {item.title}".strip()}
                )

    def poll_news(self, now: datetime) -> None:
        self.visible = [i for i in self.items if i.published and i.published <= now]
        for key, watch in self.watches.items():
            found = watch.matches(self.visible)
            self.matches[key] = found
            self.watch_recent[key] = merge_recent(
                [recent_entry(m.item, m.keywords) for m in found[:RECENT_LIMIT]],
                self.watch_recent[key],
            )
            by_key = {m.item.key: m for m in found}
            for item in self.trackers[key].update(m.item for m in by_key.values()):
                keywords = by_key[item.key].keywords
                self.watch_events[key] = {
                    "at": iso(now),
                    "attributes": attributes(item, keywords),
                }
                if not quiet(now, PUSH_QUIET):  # neue_meldung_push.yaml
                    name = WATCHES[key][0]
                    heading = item.topline or ", ".join(keywords)
                    self.pushes.append(
                        {
                            "at": iso(now),
                            "device": f"Eilwacht {name}",
                            "title": watch_push_title(name, heading or "Neue Meldung"),
                            "title_en": watch_push_title(name, heading or "New item"),
                            "message": item.title,
                            "url": item.url,
                        }
                    )
            self.counts[key].append((now, count_since(found, now)))

    def snapshot(self, now: datetime) -> dict[str, Any]:
        day_ago = now - timedelta(hours=24)

        def since(rows: list[tuple[datetime, Any]]) -> list[list[Any]]:
            before = [row for row in rows if row[0] <= day_ago]
            recent = [row for row in rows if day_ago < row[0] <= now]
            start = [(day_ago, before[-1][1])] if before else []
            return [[iso(t), v] for t, v in start + recent]

        last = self.last_breaking
        watches = []
        for key, (name, regions, text) in WATCHES.items():
            found = self.matches[key]
            watches.append(
                {
                    "key": key,
                    "name": name,
                    "regions": regions,
                    "keywords": text,
                    "last": {
                        "state": found[0].item.title,
                        "attributes": {
                            **attributes(found[0].item, found[0].keywords),
                            RECENT: self.watch_recent[key],
                        },
                    }
                    if found
                    else None,
                    "count": self.counts[key][-1][1],
                    "event": self.watch_events[key],
                    "matches": matches_json(found),
                    "history": since(self.counts[key]),
                }
            )
        recent_pushes = [p for p in self.pushes if p["at"] > iso(day_ago)]
        return {
            "now": iso(now),
            "breaking": {
                "active": bool(self.active),
                "titles": [item.title for item in self.active],
                "urls": [item.url for item in self.active],
                "last": {
                    "state": last.title,
                    "attributes": {**attributes(last), RECENT: self.breaking_recent},
                }
                if last
                else None,
                "event": self.breaking_event,
                "history": since(self.breaking_history),
            },
            "watches": watches,
            "pushes": recent_pushes[::-1][:6],
            "announcement": self.announcements[-1] if self.announcements else None,
        }


def selftest(items: list[NewsItem]) -> dict[str, Any]:
    examples = []
    for text, title in EXAMPLES:
        item = NewsItem(id="x", source=Source.NEWS, title=title)
        found = KeywordFilter.parse(text).matches(item)
        examples.append(
            [text, {"title": title}, None if found is None else list(found)]
        )
    # Items with all searchable fields: topline, summary and tags count, too.
    for item in items:
        for text in ("Baden-Württemberg", "Gartenzwerg", "*streik, -Fußball"):
            found = KeywordFilter.parse(text).matches(item)
            fields = {
                "topline": item.topline,
                "title": item.title,
                "summary": item.summary,
                "tags": list(item.tags),
            }
            examples.append([text, fields, None if found is None else list(found)])
    watches = [
        [text, regions, matches_json(Watch(frozenset(regions), KeywordFilter.parse(text)).matches(items))]
        for text in PRESETS
        for regions in REGION_SETS
    ]  # fmt: skip
    return {"examples": examples, "watches": watches}


def write(name: str, data: dict[str, Any]) -> Path:
    path = OUT / name
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, ensure_ascii=False, separators=(",", ":"))
    return path


def main() -> None:
    national = [raw_story(row) for row in STORIES if not row[2]]
    regional = [raw_story(row) for row in STORIES if row[2]]
    items = parse_api2u({"news": national, "regional": regional}, Source.NEWS)
    assert len({i.published for i in items}) == len(items), "times must differ"
    assert all(i.url and i.url.startswith(LINK) for i in items)
    items = with_placeholder_images(items)
    assert all(i.image is None or i.image.startswith(PLACEHOLDER) for i in items)

    sim = Simulation(items)
    moments: dict[str, Any] = {}
    pending = sorted(MOMENTS.items(), key=lambda kv: kv[1])
    now = START
    while pending:
        sim.poll_breaking(now)
        if now.minute % NEWS_EVERY == 0:
            sim.poll_news(now)
        while pending and now >= pending[0][1]:
            key, _ = pending.pop(0)
            moments[key] = sim.snapshot(now)
        now += timedelta(minutes=1)

    OUT.mkdir(parents=True, exist_ok=True)
    demo = {
        "version": VERSION,
        "regions": {str(k): v for k, v in REGIONS.items()},
        "items": [item_json(item) for item in items],
        "watches": [
            {"key": key, "name": name, "regions": regions, "keywords": text}
            for key, (name, regions, text) in WATCHES.items()
        ],
        "moments": moments,
    }
    demo_path = write("demo.json", demo)
    test = selftest(items)
    test_path = write("selftest.json", test)

    print(f"{len(items)} Meldungen, {demo_path.stat().st_size // 1024} KB")
    for key, view in moments.items():
        watches = ", ".join(
            f"{w['name']}: {w['count']} in 24 h, {len(w['matches'])} Treffer"
            for w in view["watches"]
        )
        last = view["breaking"]["last"]
        print(
            f"  {key} ({view['now']}): Eilmeldung aktiv {view['breaking']['active']}, "
            f"letzte „{last['state'] if last else '–'}“; {watches}; "
            f"{len(view['pushes'])} Push-Nachrichten"
        )
    print(
        f"Selbsttest: {len(test['examples'])} Beispiele, "
        f"{len(test['watches'])} Wächter-Fälle ({test_path.stat().st_size // 1024} KB)"
    )


if __name__ == "__main__":
    main()
