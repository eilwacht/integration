<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/eilwacht/integration/main/assets/github/readme-header-dark@2x.png">
  <img alt="Eilwacht – Was wichtig ist, meldet sich." src="https://raw.githubusercontent.com/eilwacht/integration/main/assets/github/readme-header-light@2x.png" width="640">
</picture>

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-9B2423.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/eilwacht/integration?color=9B2423)](https://github.com/eilwacht/integration/releases)
[![CI](https://github.com/eilwacht/integration/actions/workflows/ci.yml/badge.svg)](https://github.com/eilwacht/integration/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-F5A623.svg)](LICENSE)

> ℹ️ **Junges Projekt.** Version 0.1 ist die erste Version zum Testen. Rückmeldungen sind sehr willkommen – siehe [Fehler melden](#fehler-melden).

Eilwacht bringt Eilmeldungen und Regionalnachrichten der Tagesschau in dein Home Assistant – nicht als Nachrichtenleser, sondern als Auslöser: für eine Push-Nachricht, eine Ansage in der Küche oder ein Lichtsignal. Nachrichtenwächter melden dir neue Meldungen aus deinem Bundesland, auf Wunsch nur die mit bestimmten Stichworten wie „Warnstreik“ oder „S-Bahn“.

*English:* Home Assistant integration for breaking news and regional news from Germany's public broadcaster Tagesschau, as triggers for automations. German-language content only.

## Was Eilwacht kann

- **Eilmeldungen** der Tagesschau als Event, als Binärsensor „Eilmeldung aktiv“ und als Sensor „Letzte Eilmeldung“ – ohne Einrichtung, sofort nach dem Hinzufügen.
- **Nachrichtenwächter** für ein oder mehrere Bundesländer, auf Wunsch auch bundesweit: Event bei jeder neuen Meldung, letzte Meldung, Zahl der Meldungen der letzten 24 Stunden.
- **Stichwortwächter:** nur Meldungen mit bestimmten Wörtern, mit Platzhaltern und Ausschlüssen.
- **Fertige Blueprints** für Push-Nachricht und Ansage, mit Ruhezeiten.
- Fällt eine Quelle aus, erscheint nach einer Weile ein Hinweis unter *Reparaturen*.

<img src="https://raw.githubusercontent.com/eilwacht/integration/main/assets/screenshots/integration.png" alt="Eilwacht in Home Assistant: das Gerät Eilwacht und ein Nachrichtenwächter Stuttgart" width="720">

## Datenquelle

Alle Daten kommen von [tagesschau.de](https://www.tagesschau.de):

| Was | Woher | Wie oft |
| --- | --- | --- |
| Eilmeldungen | die Kopfzeile der Website (`json/headerapp`) | jede Minute |
| Eilmeldungen, Ersatzquelle | Startseite der Tagesschau-API (`api2u/homepage`, Feld `breakingNews`) | nur solange die erste Quelle ausfällt, dann alle 2 Minuten |
| Regionalnachrichten | Tagesschau-API (`api2u/news`), alle Bundesländer aller Wächter in einer Abfrage | alle 15 Minuten |

Die Nutzungsbedingungen der Tagesschau erlauben die Nutzung für den **privaten, nicht-kommerziellen Gebrauch** und höchstens 60 Abrufe pro Stunde. Eilwacht bleibt mit höchstens 8 Abrufen pro Stunde (38, solange die Kopfzeile ausfällt) darunter. Jede Home-Assistant-Instanz ruft die Daten selbst ab; es gibt keinen zentralen Server.

**Eilwacht ist kein Angebot der ARD oder der Tagesschau** und steht mit ihnen in keiner Verbindung.

## Was Eilwacht nicht kann

- **Nur die Tagesschau.** Andere Sender (ZDF, Deutschlandfunk, SWR, n-tv) kennzeichnen Eilmeldungen nicht maschinenlesbar. Für beliebige RSS-Feeds gibt es in Home Assistant die Integration [Feedreader](https://www.home-assistant.io/integrations/feedreader/).
- **Keine Volltexte und Bilder** – Schlagzeile, Dachzeile, erster Satz und der Link zum Artikel.
- **Keine amtlichen Warnungen.** Dafür gibt es [NINA](https://www.home-assistant.io/integrations/nina/) und die [DWD-Wetterwarnungen](https://www.home-assistant.io/integrations/dwd_weather_warnings/).
- **Nichts nachträglich:** Was während eines Neustarts von Home Assistant erscheint, wird nicht nachgemeldet – dafür auch nichts doppelt.
- **Eilmeldungen sind selten.** Die Tagesschau verschickt sie nur bei wirklich wichtigen Ereignissen. Im Alltag melden sich die Nachrichtenwächter deutlich öfter.

## Datenschutz

Eilwacht ruft nur tagesschau.de ab. Deine Bundesländer und Stichworte bleiben in Home Assistant; die Abfrage enthält nur die Nummern der Bundesländer.

## Installation (HACS, benutzerdefiniertes Repository)

Voraussetzung: Home Assistant **2026.3** oder neuer und [HACS](https://hacs.xyz/).

**Mit einem Klick:** [![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=eilwacht&repository=integration&category=integration) → herunterladen, Home Assistant neu starten → [![Integration hinzufügen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=eilwacht)

Oder von Hand:

1. HACS öffnen → Menü (⋮) → **Benutzerdefinierte Repositories**.
2. URL `https://github.com/eilwacht/integration` eintragen, Typ **Integration**, hinzufügen.
3. **Eilwacht** in HACS öffnen → **Herunterladen**.
4. Home Assistant neu starten.
5. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Eilwacht**.

## Einrichtung

### Eilmeldungen

Nichts zu tun: Nach dem Hinzufügen gibt es das Gerät **Eilwacht** mit den Eilmeldungs-Entitäten.

### Nachrichtenwächter

*Geräte & Dienste → Eilwacht → Nachrichtenwächter hinzufügen*:

<img src="https://raw.githubusercontent.com/eilwacht/integration/main/assets/screenshots/waechter_hinzufuegen.png" alt="Dialog Nachrichtenwächter hinzufügen: Name, Bundesländer, Stichworte" width="400">


| Feld | Bedeutung |
| --- | --- |
| **Name** | z. B. „Stuttgart“ oder „Streik“; erscheint in den Namen der Entitäten |
| **Bundesländer** | Regionalnachrichten dieser Länder. **Bundesweit** ergänzt überregionale Nachrichten ohne Bundesland. |
| **Stichworte** | optional, durch Kommas getrennt; leer heißt: jede Meldung |

Stichworte durchsuchen Dachzeile, Schlagzeile, ersten Satz und Schlagwörter der Meldung, ohne Rücksicht auf Groß- und Kleinschreibung. Ein Stichwort findet alle Wörter, die damit **beginnen** – so klappt es auch mit Mehrzahl, Beugung und zusammengesetzten Wörtern:

| Eingabe | findet | findet nicht |
| --- | --- | --- |
| `Stuttgart` | „Stuttgart“, „Stuttgarter Gänsheide“ | |
| `Streik` | „Streik“, „Streiks“, „Streikende“ | „Warnstreik“ |
| `*streik` | „Warnstreik“, „Bahnstreiks“, „Streik“ | |
| `Bahn` | „Bahn“, „Bahnhof“ | „Autobahn“, „S-Bahn“ |
| `S-Bahn Stuttgart` | „S-Bahn Stuttgart“, „S-Bahn Stuttgarts“ | „S-Bahn in Stuttgart“ |
| `-Fußball` | schließt Meldungen mit „Fußball“ oder „Fußballer“ aus | |

Wächter lassen sich jederzeit über ⋮ → **Neu konfigurieren** ändern.

## Entitäten

Entitäts-IDs bei deutscher Oberfläche, Wächter mit dem Namen „Stuttgart“:

| Entität | Beispiel-ID | Inhalt |
| --- | --- | --- |
| **Eilmeldung** (Event) | `event.eilwacht_eilmeldung` | löst bei jeder neuen Eilmeldung aus, Ereignistyp `breaking_news` |
| **Eilmeldung aktiv** | `binary_sensor.eilwacht_eilmeldung_aktiv` | an, solange tagesschau.de eine Eilmeldung zeigt; Attribute `titles`, `urls` |
| **Letzte Eilmeldung** | `sensor.eilwacht_letzte_eilmeldung` | Schlagzeile der letzten Eilmeldung; bleibt nach ihrem Ende und über Neustarts erhalten |
| **Neue Meldung** (Event) | `event.eilwacht_stuttgart_neue_meldung` | löst bei jeder neuen Meldung des Wächters aus, Ereignistyp `news` |
| **Letzte Meldung** | `sensor.eilwacht_stuttgart_letzte_meldung` | Schlagzeile der neuesten Meldung des Wächters |
| **Meldungen (24 h)** | `sensor.eilwacht_stuttgart_meldungen_24_h` | Zahl der Meldungen des Wächters aus den letzten 24 Stunden |

Events und die Sensoren mit Schlagzeile tragen dieselben Attribute: `title`, `topline` (Dachzeile), `summary` (erster Satz), `url`, `published`, `regions`, `ressort` und bei Wächtern mit Stichworten `keywords` (die gefundenen Stichworte).

<table>
  <tr>
    <td valign="top"><img src="https://raw.githubusercontent.com/eilwacht/integration/main/assets/screenshots/geraet_eilwacht.png" alt="Gerät Eilwacht: Eilmeldung aktiv, Letzte Eilmeldung, Event Eilmeldung" width="360"></td>
    <td valign="top"><img src="https://raw.githubusercontent.com/eilwacht/integration/main/assets/screenshots/geraet_waechter.png" alt="Gerät eines Nachrichtenwächters: Letzte Meldung, Meldungen (24 h), Event Neue Meldung" width="360"></td>
  </tr>
</table>

<sub>Screenshots mit Beispieltexten statt echter Schlagzeilen.</sub>

## Was du damit bauen kannst

### Fertige Blueprints

Ohne YAML: Blueprint importieren, Entität und Handy auswählen, fertig.

| Blueprint | Was sie tut | |
| --- | --- | --- |
| **Eilmeldung aufs Handy** | Push-Nachricht bei jeder neuen Eilmeldung; ein Tippen öffnet den Artikel. Ruhezeit (Standard 22–7 Uhr) | [![Blueprint importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Feilwacht%2Fintegration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Feilwacht%2Feilmeldung_push.yaml) |
| **Eilmeldung ansagen** | liest die Schlagzeile über Lautsprecher vor, auf Wunsch nur wenn jemand zu Hause ist. Ruhezeit (Standard 21:30–7:30 Uhr) | [![Blueprint importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Feilwacht%2Fintegration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Feilwacht%2Feilmeldung_ansage.yaml) |
| **Neue Meldung eines Nachrichtenwächters aufs Handy** | Push-Nachricht bei jeder neuen Meldung eines Wächters, mit Dachzeile oder gefundenem Stichwort als Titel. Ruhezeit (Standard 22–7 Uhr) | [![Blueprint importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Feilwacht%2Fintegration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Feilwacht%2Fneue_meldung_push.yaml) |

Die Push-Nachrichten gehen an ein Handy mit der offiziellen Home-Assistant-App.

### Licht kurz rot färben bei einer Eilmeldung

```yaml
alias: Eilmeldung – Licht
triggers:
  - trigger: state
    entity_id: event.eilwacht_eilmeldung
conditions:
  # Nach einem Neustart zeigt die Event-Entität ihr letztes Ereignis erneut an.
  - condition: template
    value_template: >-
      {{ trigger.from_state is not none
         and trigger.from_state.state != 'unavailable'
         and trigger.to_state.state not in ['unavailable', 'unknown'] }}
actions:
  - action: light.turn_on
    target:
      entity_id: light.wohnzimmer
    data:
      color_name: red
      flash: short
```

### Letzte Eilmeldung im Dashboard

```yaml
type: markdown
title: Eilmeldung
content: >-
  {% set s = states.sensor.eilwacht_letzte_eilmeldung %}
  {% if s and s.state not in ['unknown', 'unavailable'] %}
  **[{{ s.state }}]({{ s.attributes.url }})**

  {{ s.attributes.summary or '' }}

  <small>{{ as_timestamp(s.attributes.published) | timestamp_custom('%d.%m. %H:%M') if s.attributes.published else '' }} · Quelle: tagesschau.de</small>
  {% else %}
  Keine Eilmeldung.
  {% endif %}
```

## Fehlerbehebung

- **Reparaturen:** Ist die Eilmeldungs-Quelle 30 Minuten lang nicht erreichbar oder schlagen die Nachrichten zweimal in Folge fehl, erscheint unter *Einstellungen → System → Reparaturen* ein Hinweis. Er verschwindet von selbst, sobald der Abruf wieder klappt.
- **Diagnose:** *Geräte & Dienste → Eilwacht → ⋮ → Diagnose herunterladen*. Sie enthält deine Wächter samt Stichworten und die zuletzt aufgezeichnete Eilmeldung im Rohformat.
- **Ausführliches Protokoll:**

  ```yaml
  logger:
    logs:
      custom_components.eilwacht: debug
  ```

## Fehler melden

Fehler und Ideen bitte als [GitHub-Issue](https://github.com/eilwacht/integration/issues), möglichst mit Diagnose-Datei und Home-Assistant-Version.

## Schwesterprojekt

[Streckenwacht](https://github.com/streckenwacht/integration) – Baustellen, Sperrungen und Staus auf deiner Strecke.

## Lizenz

MIT, siehe [LICENSE](LICENSE). Die Inhalte der Meldungen gehören der Tagesschau (ARD-aktuell) und dürfen nur privat genutzt werden.
