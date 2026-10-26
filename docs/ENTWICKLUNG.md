# Eilwacht – Entwicklerdokumentation

Stand: 2026-10-20 (Projektstart). Vor größeren Arbeiten lesen.

## 1. Ziel und Umfang

Eilwacht bringt die Tagesschau in Home Assistant – als Auslöser für Automationen, nicht als Nachrichtenleser:

1. **Eilmeldungen** – Event-Entity, Binärsensor „Eilmeldung aktiv“, Sensor „letzte Eilmeldung“.
2. **Regionalnachrichten** je Bundesland und Ressort – Event je neue Meldung.
3. **Stichwortwächter** auf beiden Quellen (z. B. „Warnstreik“, „S-Bahn“, „Stuttgart“).
4. **Blueprint** für Push und Sprachausgabe mit Ruhezeiten.

**Bewusst nicht:** allgemeines RSS (kann `feedreader` im Kern), andere Sender (ZDF, Dlf, SWR, n-tv haben kein maschinenlesbares Eilmeldungs-Kennzeichen, geprüft 2026-10-03), Volltexte und Bilder, offizielle Warnungen (NINA und DWD sind im Kern).

## 2. Datenquellen – verifizierte Eigenheiten (geprüft 2026-10-20)

### `https://www.tagesschau.de/json/headerapp` (inoffiziell)

- Interner Endpunkt der Website, nicht dokumentiert. Antwort ≈ 6 KB, `Cache-Control: max-age=30`.
- Ohne laufende Eilmeldung nur der Schlüssel `liveStream`. **`breakingNews` fehlt dann ganz** – kein leeres Array.
- Während einer Eilmeldung (**verifiziert 2026-10-21**, echte Aufnahme in `tests/fixtures/headerapp_breaking.json`): Die Antwort enthält dann **nur** `breakingNews` (kein `liveStream`), eine Liste mit `id` (UUID), `headline`, `text`, `url`, `date` und zusätzlich `linkText` ("Eilmeldung"). `url` ist relativ und zeigt auf eine eigene Seite (`/eilmeldung/eilmeldung-9580.html`), nicht auf den Artikel. `date` ist Anzeigetext „Stand: 21.10.2026 11:25 Uhr“, kein ISO-Zeitstempel. `text` endete mit ` 
` (wird getrimmt). Damit bestätigt sich, was der Telegram-Eilbot ([Brawl345/tagesschau-eilbot](https://github.com/Brawl345/tagesschau-eilbot), `handler/check.go`) annimmt; laut Eilbot steht die neueste Eilmeldung zuerst und `text` kann leer sein.
- Ein fester Abfrageabstand ist nirgends dokumentiert; der Eilbot nutzt 60 s.

### `https://www.tagesschau.de/api2u/…` (dokumentiert von [bundesAPI](https://github.com/bundesAPI/tagesschau-api))

- `/api2u/homepage/` antwortet mit **308** auf `/api2u/homepage` (ohne Schrägstrich) → direkt ohne Schrägstrich abfragen.
- `homepage`: Schlüssel `news` (10 Meldungen), `regional`, `newStoriesCountLink`, `type`. Antwort ≈ 0,5 MB.
- `news`: zusätzlich `nextPage`; ≈ 300 Meldungen, ≈ 1,2 MB. `news?regions=1` ≈ 0,2 MB, `Cache-Control: max-age≈250`.
- Jede Meldung hat `breakingNews` (bool; in `news` teils `null`), `sophoraId`, `externalId`, `title`, `topline`, `firstSentence`, `date` (mit Offset), `detailsweb`, `shareURL`, `ressort`, `regionId`, `regionIds`, `tags`, `updateCheckUrl`, `type`.
- `regions`: 1–16 alphabetisch (1 BW, 2 BY, 3 BE, 4 BB, 5 HB, 6 HH, 7 HE, 8 MV, 9 NI, 10 NW, 11 RP, 12 SL, 13 SN, 14 ST, 15 SH, 16 TH), kommagetrennt kombinierbar. Bundesweite Meldungen haben `regionId` 0 bzw. `null`.
- `shareURL` regionaler Meldungen zeigt oft auf den Landessender (z. B. sr.de), `detailsweb` auf tagesschau.de.
- **Bedingungen:** „Die Nutzung der Inhalte für den privaten, nicht-kommerziellen Gebrauch ist gestattet, die Veröffentlichung hingegen nicht“ (ausgenommen CC-Inhalte). „Es ist unzulässig, mehr als 60 Abrufe pro Stunde zu tätigen.“
- Der ioBroker-Adapter ([ticaki/ioBroker.tagesschau](https://github.com/ticaki/ioBroker.tagesschau), 127 Installationen) liest Eilmeldungen seit 0.6.0 aus `homepage` (`news` + `regional`, `breakingNews === true`).

### Übertragung

Kein ETag, kein `Last-Modified` – bedingte Abfragen wie bei Streckenwacht gehen nicht. Alle drei Endpunkte komprimieren (Brotli, gzip; aiohttp fragt gzip von selbst an). Mit gzip: `headerapp` ≈ 2,5 KB, `homepage` ≈ 100 KB, `news?regions=1` ≈ 33 KB. Beim Abfrageplan unten sind das zusammen ≈ 7 MB am Tag.

### Abfrageplan (Entwurf)

| Quelle | Abstand | Zweck | api2u-Abrufe/h |
| --- | --- | --- | --- |
| `headerapp` | 1 min | Eilmeldungen, schnell | – |
| `homepage` | nur bei Ausfall von `headerapp`, dann 2 min | Ausweichquelle für Eilmeldungen | 0 (30) |
| `news?regions=…` | 15 min | Regionalnachrichten, Stichworte | 4 |

Ein Coordinator je Endpunkt für alle Config-Entries – sonst vervielfacht jeder weitere Eintrag die Abrufe.

## 3. Entscheidungen

### Aufbau in Home Assistant

- **Ein Eintrag** „Eilwacht“ (`single_config_entry`), ohne Einstellungen. Gerät „Eilwacht“: `event` Eilmeldung (`breaking_news`), `binary_sensor` Eilmeldung aktiv, `sensor` Letzte Eilmeldung (bleibt nach dem Ende und über Neustarts erhalten).
- **Unter-Einträge** „Nachrichtenwächter“ (`watch`): Name, Bundesländer (`0` = bundesweit, nur Meldungen ohne Bundesland), Stichworte. Gerät je Wächter: `event` Neue Meldung (`news`), `sensor` Letzte Meldung, `sensor` Meldungen (24 h).
- **Coordinators:** `BreakingCoordinator` (headerapp jede Minute, homepage nur solange headerapp ausfällt, dann alle 2 Minuten – nie beide zugleich, weil eine headerapp-Eilmeldung auf `/eilmeldung/…` statt auf den Artikel verweist und sonst doppelt gemeldet würde) und `NewsCoordinator` (eine Abfrage für alle Bundesländer aller Wächter, eine bundesweite nur bei Bedarf). Nur ein `NewsCoordinator`, wenn es Wächter gibt.
- **Nichts doppelt, nichts verpasst:** Die gesehenen Meldungen jedes Trackers stehen im Store `eilwacht.seen` (`seen.py`). Nach einem Neustart wird nachgemeldet, was seitdem erschien (veröffentlicht ab Speicherzeit minus 1 Stunde, weil „Stand“-Zeiten vor dem Erscheinen liegen). Lag der letzte Stand mehr als 6 Stunden zurück, oder wurden Bundesländer/Stichworte eines Wächters geändert (Fingerprint), wird still gelernt. Nachgeholte Events feuern erst nach dem ersten geschriebenen Zustand der Entität (`_after_first_state`), sonst fielen sie unter den Neustart-Filter der Blueprints („von nichts“).
- **Repairs:** headerapp nach 30 Fehlversuchen in Folge, news nach 2.
- **SD-Karten schonen** (viele HA-Instanzen laufen auf einem Raspberry Pi): Eigene Dateien schreibt Eilwacht nur in `.storage/eilwacht.seen` – binnen 10 Minuten nach neuen Meldungen, sonst höchstens alle 3 Stunden (nur der Zeitstempel für die Rückkehr nach einem Absturz) und beim Beenden – und in `.storage/eilwacht.breaking_sample` nur bei einer Eilmeldung. `Store.async_delay_save` verschiebt einen anstehenden Schreibvorgang bei jedem Aufruf, deshalb ruft `SeenStore` ihn nur auf, wenn früher geschrieben werden muss. In der Datenbank landen nur echte Zustandsänderungen (Coordinator `always_update=False` für Eilmeldungen; unveränderte Zustände speichert HA nicht). „Meldungen (24 h)“ hat bewusst keine `state_class` – Langzeitstatistik legte alle 5 Minuten und stündlich Zeilen an, für einen Wert, der selten wechselt.
- **Einheiten übersetzen:** `unit_of_measurement` in `strings.json` übersetzt die Oberfläche („0 Meldungen“); im State und in der API steht dagegen die englische Standardsprache („items“). Nicht nach dem State beurteilen (Irrtum in 0.1.0).
- **Echte Eilmeldung festhalten:** `sample.py` speichert die letzte headerapp-Antwort mit Eilmeldung (Store `eilwacht.breaking_sample`); sie steht im Diagnose-Download.

- Gleiche Grundarchitektur wie Streckenwacht: UI-Config-Flow, `DataUpdateCoordinator`, async, `async_get_clientsession(hass)`, reine Logik ohne HA-Importe, Fehler pro Quelle über Repairs.
- **Kein gemeinsames Python-Paket mit Streckenwacht.** Ein PyPI-Paket als `requirements` wäre eine weitere Veröffentlichung mit eigener Versionierung; die Überschneidung (Coordinator-Gerüst, Event-Muster) ist dafür zu klein. Muster werden übernommen, nicht geteilt.
- README nur auf Deutsch (Zielgruppe ist deutschsprachig; Streckenwacht pflegt zwei vollständige READMEs à ≈ 29 KB). Ein kurzer englischer Absatz für das HACS-Verzeichnis genügt.
- Projektstand und Versionsgeschichte stehen in `CHANGELOG.md`, nicht in `CLAUDE.md`.

## 4. Risiken, Lizenzen, Recht (keine Rechtsberatung)

- **Fixtures:** Das Repo ist öffentlich, Tagesschau-Inhalte dürfen nicht veröffentlicht werden. Ins Repo kommen nur Antworten, die `tools/fetch_fixtures.py` bereinigt hat (Fließtext → „Text n“, Listen gekürzt); `tests/test_fixtures.py` prüft das. Rohdaten nur in `raw/` (ignoriert).
- **Inoffizieller Endpunkt:** `headerapp` kann jederzeit wegfallen → `homepage` als Ausweichquelle, Ausfall über Repairs melden.
- **Kein zentraler Dienst:** Jede HA-Instanz fragt selbst ab (privater Gebrauch). Kein Proxy, kein Bot, keine Weiterverteilung.
- **Quellenangabe** „Quelle: tagesschau.de“ als `attribution` an allen Entities.
- **Name:** DPMAregister-Basisrecherche am 2026-10-20 ohne Treffer für `eil?wacht` und `eil?watch` (nationale, Unions- und internationale Marken). GitHub-Organisation `eilwacht` gehört dem Projekt.
- **Marke:** Nichts, was nach Tagesschau oder ARD aussieht – kein Tagesschau-Blau, kein nachgebauter „Eilmeldung“-Balken.

## 5. Arbeitsweise

- Fixtures: `uv run tools/fetch_fixtures.py`; eine einzelne Rohdatei (z. B. aus dem Webarchiv): `uv run tools/fetch_fixtures.py --from DATEI NAME`.
- Tests: `uv run pytest`; Lint: `uv run ruff check .` und `uv run ruff format .`.
- Branches wie bei Streckenwacht: entwickelt wird auf `dev`, `main` nur für Releases.
- Release: Version in `manifest.json`, `const.py`, `pyproject.toml` anheben, `uv lock`, auf `dev` pushen, CI abwarten, `main` vorspulen, `gh release create vX --target main` (Vorab-Versionen mit `--prerelease`). Der Workflow „Release-ZIP“ hängt `eilwacht.zip` an.

### GitHub-Einstellungen (Stand 2026-10-21)

Nicht aus dem Code ablesbar, deshalb hier festgehalten:

- **Repo:** Secret Scanning mit Push-Schutz, Dependabot-Warnungen und -Sicherheitsupdates, CodeQL (Standard-Setup: Python, JavaScript, Actions), vertrauliche Meldung von Sicherheitslücken (`SECURITY.md`). Branches nach dem Mergen löschen.
- **Rulesets:** „main schützen“ (kein Löschen, kein Force-Push, Pflicht-Checks `test`, `hassfest`, `compat`, keine Ausnahmen) und „Release-Tags schützen“ (`v*`: nicht löschen, nicht verschieben).
- **Actions:** nur GitHub-eigene Actions plus `astral-sh/setup-uv`, `home-assistant/actions/*`, `hacs/action`; Workflow-Token standardmäßig nur lesend; CI-Läufe aus fremden Pull Requests brauchen immer eine Freigabe. Eine neue Action im Workflow muss dort erst erlaubt werden (*Settings → Actions → General*).
- **Bewusst aus:** „Unveränderliche Releases“ – der Workflow „Release-ZIP“ hängt die ZIP erst nach dem Veröffentlichen an.
- **Organisation:** Drittanbieter-Apps eingeschränkt, feingranulare Tokens nur mit Freigabe und Ablaufdatum.

## 6. Offene Fragen

- **Kennzeichnet `homepage` Eilmeldungen überhaupt mit `breakingNews`?** Bei der ersten echten Eilmeldung (2026-10-21, 11:25 Uhr) wurde `homepage` noch alle 10 Minuten abgefragt, ein zweites Event gab es nicht. Seit 0.1.0 dient `homepage` nur noch als Ersatz bei Ausfall von `headerapp` (Abschnitt 3), deshalb ist die Frage nur noch für diesen Fall wichtig.
- **Gibt es regionale Eilmeldungen** (`breakingNews` in `regional` bzw. `news?regions=`)? Bisher keine gesehen.
- **Wie oft gibt es Eilmeldungen?** Im Webarchiv (Juli–Oktober 2026, etwa zwei Aufnahmen pro Tag) keine; in Eilwacht die erste am 2026-10-21, rund 31 Minuten in `headerapp` sichtbar.

## 7. Erledigte Fragen

- **HA-Mindestversion:** 2026.3 (Brand-Bilder im Integrationsordner), in der CI mit dem Job `compat` geprüft.
- **Format laufender Eilmeldungen:** am 2026-10-21 an einer echten Eilmeldung verifiziert (Abschnitt 2, Fixture `headerapp_breaking.json`).
- **Bekanntmachen:** simon42 Community (Showroom, 2026-10-22); HACS-Standardliste beantragt am 2026-10-26 ([hacs/default#12711](https://github.com/hacs/default/pull/12711)). Home-Assistant-Forum (englisch) später – die Inhalte sind rein deutsch.
