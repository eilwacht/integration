# Changelog

## 0.1.0 – 2026-10-22

Erste reguläre Version, nach dem Test auf einer echten Home-Assistant-Instanz.

- **Stichworte finden jetzt alle Wörter, die mit ihnen beginnen:** `Stuttgart` findet auch „Stuttgarter“, `Streik` auch „Streiks“ (aber weiterhin nicht „Warnstreik“, dafür `*streik`). Bisher zählte nur das ganze Wort. Bestehende Wächter finden dadurch eher mehr Meldungen.
- Die Startseite der Tagesschau-API wird nur noch abgefragt, solange die Kopfzeile ausfällt. Eine Eilmeldung verweist auf eine eigene Seite, die Startseite auf den Artikel – beide zusammen hätten dieselbe Eilmeldung zweimal melden können. Nebenbei sinkt der Datenverkehr auf etwa 7 MB am Tag.
- „Meldungen (24 h)“ ohne Einheit: Home Assistant speichert Einheiten immer auf Englisch („items“).
- Das Format laufender Eilmeldungen ist jetzt an einer echten Eilmeldung (21.10.2026) bestätigt und getestet.

## 0.1.0b1 – 2026-10-20

Erste Vorab-Version zum Testen.

- **Eilmeldungen** der Tagesschau: Event „Eilmeldung“, Binärsensor „Eilmeldung aktiv“, Sensor „Letzte Eilmeldung“. Abruf jede Minute, die Startseite der Tagesschau-API dient als zweite Quelle, falls die erste ausfällt.
- **Nachrichtenwächter** für ein oder mehrere Bundesländer oder bundesweit, auf Wunsch mit Stichworten (`Warnstreik`, `Streik`, `*streik`, `-Fußball`): Event „Neue Meldung“, Sensor „Letzte Meldung“, Sensor „Meldungen (24 h)“.
- **Blueprints:** Eilmeldung aufs Handy, Eilmeldung ansagen, neue Meldung eines Nachrichtenwächters aufs Handy – mit Ruhezeiten, ohne erneutes Senden nach Neustart oder Ausfall.
- Hinweis unter *Reparaturen*, wenn eine Quelle längere Zeit nicht erreichbar ist.
- Der Diagnose-Download enthält die zuletzt aufgezeichnete Eilmeldung im Rohformat. Das Format laufender Eilmeldungen ist noch nicht an einer echten Meldung überprüft – wer eine erlebt, hilft mit der Diagnose-Datei sehr.
- Getestet mit Home Assistant 2026.3 und 2026.10.
