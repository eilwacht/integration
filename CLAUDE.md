# Eilwacht – Projektkontext für Claude

Home-Assistant-Custom-Integration (HACS), Domain `eilwacht`. Eilmeldungen und Regionalnachrichten der Tagesschau als Auslöser für Automationen, mit Stichwortwächter. Schwesterprojekt von Streckenwacht (`../streckenwacht`) – dessen Muster übernehmen, wo es passt.

## Dokumentation

- **`docs/ENTWICKLUNG.md`** – Umfang, verifizierte Eigenheiten der Datenquellen, Entscheidungen, Risiken, offene Fragen. Vor größeren Arbeiten lesen.
- **`CHANGELOG.md`** – Projektstand und Versionsgeschichte. Hier stehen keine Statusberichte.
- **`docs/BRAND.md`** – Farben, Schrift, Bilddateien, Regenerierung. Brand-Bilder nicht verändern oder neu erzeugen, außer auf ausdrücklichen Wunsch.
- **`NOTES.md`** (lokal, nicht im Repo) – aktueller Arbeitsstand und offene Punkte. Zu Beginn einer Sitzung lesen, am Ende aktualisieren.

## Verbindliche Entscheidungen

- Nur Tagesschau (`json/headerapp` + `api2u`). Kein allgemeines RSS, keine anderen Sender, keine Volltexte oder Bilder.
- Nur UI-Config-Flow, kein YAML. `DataUpdateCoordinator`, durchgängig async, `async_get_clientsession(hass)`. Ein Coordinator je Endpunkt, gemeinsam für alle Config-Entries.
- Höchstens 60 api2u-Abrufe pro Stunde für die gesamte Instanz (Abfrageplan in `docs/ENTWICKLUNG.md` Abschnitt 2).
- `homepage` nur als Ersatz, solange `headerapp` ausfällt – nie beide zugleich (Eilmeldung verweist auf `/eilmeldung/…`, homepage auf den Artikel → Doppelmeldung).
- Nichts doppelt, nichts verpasst: gesehene Meldungen in `SeenStore` (`seen.py`), nach Neustart bis 6 h nachmelden, sonst still lernen.
- SD-Karten schonen: selten schreiben, keine `state_class` für selten wechselnde Zähler (Details `docs/ENTWICKLUNG.md` Abschnitt 3).
- Lizenz MIT. Repo: `github.com/eilwacht/integration` (öffentlich). `codeowners`: `@n42net`.

## Arbeitsregeln

1. **Feldnamen nie raten.** Die Dateien in `tests/fixtures/` sind die Wahrheit über Formate. Weicht die Live-API von `docs/ENTWICKLUNG.md` ab, gilt die API – und die Abweichung wird dort nachgetragen.
2. **Keine Tagesschau-Inhalte ins Repo.** Fixtures nur über `tools/fetch_fixtures.py` (bereinigt), Rohdaten nur in `raw/`. `tests/test_fixtures.py` muss grün sein.
3. Entwickelt wird gegen eine produktive Home-Assistant-Instanz. Logik (Abruf, Parsing, Stichworte, Änderungserkennung) erst als reines Python ohne HA-Importe testen. Ein Fehler einer Quelle darf nie die Integration oder HA blockieren: pro Quelle fangen, über Repairs melden.
4. Alle HTTP-Requests mit User-Agent `Eilwacht/<version> (+https://github.com/eilwacht/integration)`. Quellenangabe „Quelle: tagesschau.de“ an allen Entities.
5. Code, Kommentare, Entity-IDs auf Englisch; UI-Texte über `strings.json` + `translations/de.json` und `en.json`. Werkzeuge in `tools/` und Doku auf Deutsch.
6. Tests gegen Fixtures, nicht gegen Live-APIs. HA-Tests (`tests/ha/`, `pytest-homeassistant-custom-component`) nur in GitHub Actions.
7. **Branches:** Entwickelt wird auf `dev`; `main` erhält nur freigegebene Stände (Ablauf unter „Release“), weil die HACS-Installationen daran hängen. Ein Ruleset erzwingt grüne CI (`test`, `hassfest`, `compat`) für `main`. Kein Force-Push, Tags `v*` sind unveränderlich.
8. **Werkzeuge:** `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`. `homeassistant` (dev) und `pytest-homeassistant-custom-component` (ha-tests) immer gemeinsam anheben. Rechnerspezifisches steht in `CLAUDE.local.md`.

## Release

Gleicher Ablauf in allen Schwesterprojekten (Eilwacht, Einspeisewacht, Streckenwacht, Tarifwacht). Neue Erkenntnisse zum Ablauf hier eintragen und für die Schwestern melden.

1. Version in `manifest.json`, `const.py` und `pyproject.toml` anheben (dazu den User-Agent in `tools/fetch_fixtures.py`), `uv lock`; `tests/test_manifest.py` prüft die Gleichheit. „Unveröffentlicht“ in `CHANGELOG.md` zur Version machen.
2. `dev` pushen und auf den CI-Lauf **genau dieses Commits** warten (`gh run list --commit <sha>`): Push-CI startet manchmal Minuten verspätet, ein älterer grüner Lauf täuscht.
3. `main` vorspulen mit `git push origin dev:main` – **ohne Branch-Wechsel** im Arbeitsverzeichnis (auf dem Netzlaufwerk hat `git switch` schon Dateien verloren, ein Release entstand so auf altem Stand). Danach prüfen, dass `origin/main` auf dem Versions-Commit steht.
4. `gh release create vX --target main --latest --notes-file …` (Text aus dem Changelog). Ziel `main`, kein Kurz-SHA (gibt 422). Immer ein **reguläres** Release, auch für Betas, nie `--prerelease`: Sonst nimmt HACS den letzten Commit und sucht dort vergeblich die ZIP. Blockiert der Auto-Modus das Veröffentlichen: Befehl nennen, der Inhaber führt ihn aus – nie umgehen.
5. Workflow „Release-ZIP“ prüfen: `eilwacht.zip` muss am Release hängen. Der Workflow bricht ab, wenn Tag und `manifest.json` nicht passen; fehlt die ZIP, ihn per Hand mit dem Tag starten. Ohne ZIP scheitern HACS-Installationen.
6. Prüfen, dass HACS die neue Version sieht: `gh api repos/eilwacht/integration/releases --jq '.[0].tag_name'` muss das neue Tag sein – HACS nimmt den **ersten** Eintrag dieser Liste, nicht „Latest“. GitHub sortiert sie offenbar nach der Basisversion; innerhalb derselben Basis (`0.1.0b1` … `0.1.0b10`, `0.1.0`) ist die Reihenfolge willkürlich (Tarifwacht 2026-10-27: b10 und 0.1.0 landeten hinter b6, HACS bot keine von beiden an). **Regel:** Nach Vorabversionen die nächste Version mit **höherer Basis** veröffentlichen (`0.1.1` statt `0.1.0` nach `0.1.0b…`), und Vorabnummern zweistellig gar nicht erst erreichen.
7. Bricht eine Sitzung mitten im Release ab: erst den Stand prüfen (`git log origin/dev origin/main`, CI des Commits, `gh release list`), dann weitermachen.

„Unveränderliche Releases“ bleibt in GitHub aus, weil der Workflow die ZIP erst nach dem Veröffentlichen anhängt; die Tags `v*` schützt das Ruleset.

## Fallstricke

- Event-Entities: Nachgeholte Events erst nach dem ersten geschriebenen Zustand auslösen (`_after_first_state`), sonst fallen sie unter den Neustart-Filter der Blueprints („von nichts“/„unavailable“).
- `Store.async_delay_save` verschiebt einen anstehenden Schreibvorgang bei jedem Aufruf – nicht pro Abruf aufrufen (siehe `SeenStore._schedule`).
- `unit_of_measurement` übersetzt nur die Oberfläche; State/API zeigen die englische Standardsprache. Nach der Oberfläche beurteilen, nicht nach dem State.
- Dependabot meldet Pillow-Lücken in `uv.lock`: nur Entwicklungsumgebung über den HA-Pin, die Integration hat keine Abhängigkeiten. Begründet abhaken („tolerable_risk“); beheben, sobald ein HA-Release Pillow ≥ 13 pinnt.
- Screenshots (`assets/screenshots/`): echte Schlagzeilen nur in der Browser-Anzeige durch Beispieltexte ersetzen und im README so kennzeichnen.
- Home Assistant des Nutzers: MCP nur lesend; Browser (Playwright) braucht seine eigene Anmeldung. Konto- und Organisationseinstellungen bei GitHub klickt der Nutzer selbst.
