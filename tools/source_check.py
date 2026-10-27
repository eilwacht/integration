#!/usr/bin/env python3
"""Check the three Tagesschau endpoints against the live API with the real client.

Usage (from the repo root):
    uv run tools/source_check.py [--markdown report.md]

One request per endpoint (news: all federal states), well below the 60 per
hour of the terms of use. An endpoint counts as a problem if it fails twice,
its format is no longer recognised, it returns no items (api2u) or no item
has a date (date field changed). headerapp has alerts only while one is
running: then every alert must be parsed (id and headline found). Exit code 1
if any endpoint has a problem. Run weekly by
.github/workflows/source-check.yml; nothing is written except the report,
which holds counts only: no Tagesschau content (it ends up in an issue).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.eilwacht.const import REGIONS
from custom_components.eilwacht.model import NewsItem, Source
from custom_components.eilwacht.tagesschau import TagesschauClient, TagesschauError

RETRY_AFTER_S = 60


@dataclass
class Result:
    source: Source
    items: list[NewsItem] | None = None
    raw_alerts: int = 0  # headerapp: entries in "breakingNews"
    error: str | None = None

    @property
    def problem(self) -> str | None:
        if self.error:
            return f"Fehler: {self.error}"
        if self.items is None:
            return "keine Antwort"
        if self.source is Source.HEADERAPP:
            if len(self.items) < self.raw_alerts:
                return "Eilmeldung nicht erkannt (Felder id/headline geändert?)"
            return None
        if not self.items:
            return "keine Meldungen (Quelle leer oder Format geändert?)"
        if not any(i.published for i in self.items):
            return "keine Zeitangaben erkannt (Datumsfeld geändert?)"
        if self.source is Source.NEWS and not any(i.region_ids for i in self.items):
            return "keine Bundesländer erkannt (regionIds geändert?)"
        return None

    def share(self, test: Callable[[NewsItem], bool]) -> str:
        if not self.items:
            return "–"
        return f"{round(100 * sum(map(test, self.items)) / len(self.items))} %"


async def check(
    client: TagesschauClient, source: Source, fetch: Callable[[], Awaitable[Any]]
) -> Result:
    for attempt in range(2):
        try:
            items = await fetch()
        except TagesschauError as err:
            if attempt == 0:
                await asyncio.sleep(RETRY_AFTER_S)
                continue
            return Result(source, error=str(err) or type(err).__name__)
        raw_alerts = 0
        if source is Source.HEADERAPP:
            raw_alerts = len(client.last_headerapp.get("breakingNews") or ())
        return Result(source, items, raw_alerts)
    raise AssertionError("unreachable")


def report(results: list[Result]) -> str:
    problems = [r for r in results if r.problem]
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"## Quellen-Check {now}",
        "",
        f"**{len(problems)} von {len(results)} Endpunkten mit Problemen.**"
        if problems
        else f"Alle {len(results)} Endpunkte liefern Daten.",
        "",
        "| Endpunkt | Meldungen | mit Zeit | mit Link | mit Bundesland | Befund |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for r in results:
        lines.append(
            f"| {r.source.value} | {len(r.items) if r.items is not None else '–'}"
            f" | {r.share(lambda i: bool(i.published))}"
            f" | {r.share(lambda i: bool(i.url))}"
            f" | {r.share(lambda i: bool(i.region_ids))}"
            f" | {r.problem or 'ok'} |"
        )
    lines += [
        "",
        "headerapp führt Eilmeldungen nur, solange eine läuft – 0 Meldungen ist dort normal.",
    ]
    return "\n".join(lines) + "\n"


async def check_all() -> list[Result]:
    # Windows: aiodns (installed with Home Assistant) cannot find the DNS servers.
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    async with aiohttp.ClientSession(connector=connector) as session:
        client = TagesschauClient(session)
        return [
            await check(client, Source.HEADERAPP, client.async_breaking_news),
            await check(client, Source.HOMEPAGE, client.async_homepage),
            await check(client, Source.NEWS, lambda: client.async_news(REGIONS)),
        ]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--markdown", help="also write the report to this file")
    args = parser.parse_args()
    results = asyncio.run(check_all())
    text = report(results)
    print(text)
    if args.markdown:
        Path(args.markdown).write_text(text, encoding="utf-8")
    sys.exit(1 if any(r.problem for r in results) else 0)
