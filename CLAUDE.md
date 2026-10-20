# Eilwacht – Projektkontext für Claude

Home-Assistant-Custom-Integration (HACS), Domain `eilwacht`. Eilmeldungen und Regionalnachrichten der Tagesschau als Auslöser für Automationen, mit Stichwortwächter. Schwesterprojekt von Streckenwacht (`../streckenwacht`) – dessen Muster übernehmen, wo es passt.

## Dokumentation

- **`docs/ENTWICKLUNG.md`** – Umfang, verifizierte Eigenheiten der Datenquellen, Entscheidungen, Risiken, offene Fragen. Vor größeren Arbeiten lesen.
- **`CHANGELOG.md`** – Projektstand und Versionsgeschichte. Hier stehen keine Statusberichte.
- **`docs/BRAND.md`** – Farben, Schrift, Bilddateien, Regenerierung. Brand-Bilder nicht verändern oder neu erzeugen, außer auf ausdrücklichen Wunsch.

## Verbindliche Entscheidungen

- Nur Tagesschau (`json/headerapp` + `api2u`). Kein allgemeines RSS, keine anderen Sender, keine Volltexte oder Bilder.
- Nur UI-Config-Flow, kein YAML. `DataUpdateCoordinator`, durchgängig async, `async_get_clientsession(hass)`. Ein Coordinator je Endpunkt, gemeinsam für alle Config-Entries.
- Höchstens 60 api2u-Abrufe pro Stunde für die gesamte Instanz (Abfrageplan in `docs/ENTWICKLUNG.md` Abschnitt 2).
- Lizenz MIT. Repo: `github.com/eilwacht/integration` (privat bis zur ersten Veröffentlichung). `codeowners`: `@n42net`.

## Arbeitsregeln

1. **Feldnamen nie raten.** Die Dateien in `tests/fixtures/` sind die Wahrheit über Formate. Weicht die Live-API von `docs/ENTWICKLUNG.md` ab, gilt die API – und die Abweichung wird dort nachgetragen.
2. **Keine Tagesschau-Inhalte ins Repo.** Fixtures nur über `tools/fetch_fixtures.py` (bereinigt), Rohdaten nur in `raw/`. `tests/test_fixtures.py` muss grün sein.
3. Entwickelt wird gegen eine produktive Home-Assistant-Instanz. Logik (Abruf, Parsing, Stichworte, Änderungserkennung) erst als reines Python ohne HA-Importe testen. Ein Fehler einer Quelle darf nie die Integration oder HA blockieren: pro Quelle fangen, über Repairs melden.
4. Alle HTTP-Requests mit User-Agent `Eilwacht/<version> (+https://github.com/eilwacht/integration)`. Quellenangabe „Quelle: tagesschau.de“ an allen Entities.
5. Code, Kommentare, Entity-IDs auf Englisch; UI-Texte über `strings.json` + `translations/de.json` und `en.json`. Werkzeuge in `tools/` und Doku auf Deutsch.
6. Tests gegen Fixtures, nicht gegen Live-APIs. HA-Tests (`tests/ha/`, `pytest-homeassistant-custom-component`) nur in GitHub Actions.
7. **Branches:** Entwickelt wird auf `dev`; `main` erhält nur freigegebene Stände (Versions-Bump in `manifest.json`, `const.py` und `pyproject.toml` + GitHub-Release).
8. **Werkzeuge:** `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`. `homeassistant` (dev) und `pytest-homeassistant-custom-component` (ha-tests) immer gemeinsam anheben. Rechnerspezifisches steht in `CLAUDE.local.md`.
