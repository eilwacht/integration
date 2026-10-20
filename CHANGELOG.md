# Changelog

## 0.1.0b1 – 2026-10-20

Erste Vorab-Version zum Testen.

- **Eilmeldungen** der Tagesschau: Event „Eilmeldung“, Binärsensor „Eilmeldung aktiv“, Sensor „Letzte Eilmeldung“. Abruf jede Minute, die Startseite der Tagesschau-API dient als zweite Quelle, falls die erste ausfällt.
- **Nachrichtenwächter** für ein oder mehrere Bundesländer oder bundesweit, auf Wunsch mit Stichworten (`Warnstreik`, `Streik*`, `*streik`, `-Fußball`): Event „Neue Meldung“, Sensor „Letzte Meldung“, Sensor „Meldungen (24 h)“.
- **Blueprints:** Eilmeldung aufs Handy, Eilmeldung ansagen, neue Meldung eines Nachrichtenwächters aufs Handy – mit Ruhezeiten, ohne erneutes Senden nach Neustart oder Ausfall.
- Hinweis unter *Reparaturen*, wenn eine Quelle längere Zeit nicht erreichbar ist.
- Der Diagnose-Download enthält die zuletzt aufgezeichnete Eilmeldung im Rohformat. Das Format laufender Eilmeldungen ist noch nicht an einer echten Meldung überprüft – wer eine erlebt, hilft mit der Diagnose-Datei sehr.
- Getestet mit Home Assistant 2026.3 und 2026.10.
