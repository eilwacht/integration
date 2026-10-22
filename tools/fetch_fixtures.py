#!/usr/bin/env python3
"""Lädt echte Antworten der Tagesschau-API und speichert sie bereinigt als Test-Fixtures.

Aufruf (aus dem Repo-Root):
    uv run tools/fetch_fixtures.py                          # Live-Endpunkte
    uv run tools/fetch_fixtures.py --from DATEI NAME        # vorhandene Rohdatei, z. B.
                                                            # eine Aufnahme aus dem Webarchiv

Warum bereinigt: Die Nutzungsbedingungen erlauben privaten Gebrauch, aber keine
Veröffentlichung der Inhalte. Das Repo ist öffentlich. Deshalb ersetzt
scrub() jeden Fließtext (jeder String mit Leerzeichen) durch einen Platzhalter
und kürzt lange Listen. Struktur, Feldnamen, IDs, URLs, Zeitstempel und
Aufzählungswerte (ressort, type, breakingNews …) bleiben echt, und genau das
brauchen die Tests. Die ungekürzten Rohantworten landen in raw/ (nicht im Repo).

Ergebnis: tests/fixtures/<name>.json plus Übersicht tests/fixtures/_index.json.
Nur Python-Standardbibliothek.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

USER_AGENT = "Eilwacht/0.1.0 (+https://github.com/eilwacht/integration)"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "fixtures"
RAW = ROOT / "raw"
TIMEOUT = 30

API = "https://www.tagesschau.de/api2u"
ENDPOINTS = {
    "headerapp": "https://www.tagesschau.de/json/headerapp",
    "homepage": f"{API}/homepage",
    # 1 = Baden-Württemberg (regions 1–16 alphabetisch, siehe docs/ENTWICKLUNG.md)
    "news_bw": f"{API}/news?regions=1",
    "news": f"{API}/news",
}

# Längere Listen werden auf so viele Einträge gekürzt; Eilmeldungen bleiben immer.
MAX_ITEMS = 6

# Felder ohne Fließtext, die trotz Leerzeichen echt bleiben, z. B. die
# Zeitangabe einer Eilmeldung („Stand: 21.10.2026 11:25 Uhr“).
KEEP_KEYS = frozenset({"date"})


def scrub(value: Any, counter: list[int] | None = None) -> Any:
    """Fließtext durch Platzhalter ersetzen, lange Listen kürzen."""
    if counter is None:
        counter = [0]
    if isinstance(value, dict):
        return {
            key: item if key in KEEP_KEYS else scrub(item, counter)
            for key, item in value.items()
        }
    if isinstance(value, list):
        if len(value) > MAX_ITEMS:
            keep = [
                item
                for i, item in enumerate(value)
                if i < MAX_ITEMS
                or (isinstance(item, dict) and item.get("breakingNews") is True)
            ]
            value = keep
        return [scrub(item, counter) for item in value]
    if isinstance(value, str) and any(ch.isspace() for ch in value.strip()):
        counter[0] += 1
        return f"Text {counter[0]}"
    return value


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def store(name: str, body: bytes, source: str, index: dict) -> None:
    RAW.mkdir(exist_ok=True)
    (RAW / f"{name}.json").write_bytes(body)
    cleaned = scrub(json.loads(body))
    (OUT / f"{name}.json").write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    index[name] = {
        "source": source,
        "stored": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    print(f"{name}: {len(body):>8} Bytes roh -> tests/fixtures/{name}.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from", dest="source", nargs=2, metavar=("DATEI", "NAME"))
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    index_path = OUT / "_index.json"
    index = (
        json.loads(index_path.read_text(encoding="utf-8"))
        if index_path.exists()
        else {}
    )

    if args.source:
        path, name = args.source
        store(name, Path(path).read_bytes(), f"Datei {Path(path).name}", index)
    else:
        for name, url in ENDPOINTS.items():
            store(name, fetch(url), url, index)

    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
