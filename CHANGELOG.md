# Changelog

## Unveröffentlicht

- **Bericht für Fehlermeldung lesbarer:** Einstellungen ohne Python-Schreibweise – `yes`/`no` statt `True`/`False`, `none` statt `None`, Listen ohne Klammern, Zeitpunkte als `2026-11-07 12:39 UTC`.

## 0.3.1 – 2026-11-06

- **Behoben:** Die Beispielkarte für die Meldungsliste blieb nach dem Update leer, wenn die Liste mit der zuletzt gezeigten Eilmeldung aus 0.2.x begann: Diesem Eintrag fehlten die Angaben zum Vorschaubild, und die Markdown-Karte von Home Assistant bricht bei einem fehlenden Schlüssel die ganze Karte ab. Jetzt hat jeder Eintrag von `recent` immer alle Schlüssel (`title`, `url`, `published`, `image`, `image_copyright`, `image_alt`, bei Wächtern `keywords`), unbekannte Werte sind leer. Bestehende Listen werden beim nächsten Start ergänzt.
- Die Beispielkarte in der README liest die Einträge jetzt mit `e.get('…')` und funktioniert so auch, falls einmal ein Schlüssel fehlt. Wer die Karte aus 0.3.0 übernommen hat: Nach dem Update geht sie wieder, die neue Fassung ist trotzdem robuster.
- Wächter ohne Stichworte haben in `recent` jetzt `keywords: []` statt gar keinen Eintrag.

## 0.3.0 – 2026-11-06

- **Neu: die letzten 5 Meldungen als Liste** im Attribut `recent` der Sensoren „Letzte Eilmeldung“ und „Letzte Meldung“ (je Wächter), die neueste zuerst, jede mit Schlagzeile, Link, Zeit und Vorschaubild (`title`, `url`, `published`, `image`, `image_copyright`, `image_alt`, bei Wächtern mit Stichworten auch `keywords`). Gedacht fürs Dashboard, die README hat eine fertige Markdown-Karte („Die letzten Meldungen als Liste“). Eine Meldung steht nur einmal darin; die Liste eines Wächters behält auch ältere Meldungen, die tagesschau.de nicht mehr ausliefert, und beginnt nach dem Ändern des Wächters neu. Sie übersteht Neustarts, landet aber nicht in der Datenbank. Nach dem Update beginnt die Eilmeldungsliste mit der zuletzt gezeigten Eilmeldung.
- **Neu: Vorschaubild** in den Attributen `image` (Adresse eines kleinen Bildes, meist 144 × 144 Pixel), `image_copyright` (Bildnachweis) und `image_alt` an Events, Sensoren mit Schlagzeile und in `recent`. Eilwacht lädt kein Bild herunter und setzt kein Entitätsbild; erst der Browser lädt es von tagesschau.de, wenn eine Karte es zeigt – dann bitte mit Bildnachweis. Eilmeldungen haben meist kein Bild.
- „Letzte Eilmeldung“ zeigt jetzt auch eine Eilmeldung, die während eines Neustarts erschien, wenn schon eine ältere angezeigt wurde (bisher blieb dann die ältere stehen; das Event und die Blueprints meldeten sie schon richtig).
- **Neu: Schaltfläche „Bericht für Fehlermeldung“** am Gerät „Eilwacht“ (unter *Diagnose*). Sie zeigt einen kurzen Bericht als Benachrichtigung zum Kopieren in ein Issue: Versionen, Zustand der Abrufe bei tagesschau.de mit Fehlermeldung, Zahl der Wächter, laufenden Eilmeldungen und Meldungen, je Wächter die Bundesländer und die Zahl der Stichworte, Entitäten ohne Wert und offene Reparaturhinweise – ohne Entity-IDs, Namen der Wächter, Stichworte und Schlagzeilen. Viele wollen die Diagnose-Datei nicht öffentlich teilen, weil Home Assistant ihr unter anderem die Liste aller installierten Integrationen voranstellt. Die README erklärt jetzt unter „Fehler melden“, was in der Diagnose-Datei steht und welche Teile man vor dem Teilen löschen oder ersetzen darf. Die Issue-Vorlage fragt nach dem Bericht statt nach der Diagnose-Datei.

## 0.2.2 – 2026-11-05

- Kategorien im Manifest für die neue Integrationsübersicht von Home Assistant 2026.11 (Nachrichten & soziale Medien).
- README und Demo: Installation über den Marketplace von Home Assistant 2026.11, für ältere Versionen weiter HACS.
- **Demo zum Ausprobieren ohne Installation:** [eilwacht.github.io/integration](https://eilwacht.github.io/integration/) mit Stichwort-Tester (Stichworte eintippen, Bundesländer wählen und sehen, welche Meldungen ein Nachrichtenwächter melden würde und warum), Geräten, Dashboard-Karte, Verlauf, Push-Nachrichten und Ansage – an einem ruhigen Nachmittag und bei laufender Eilmeldung. Alle Meldungen sind erfunden und so gekennzeichnet; verarbeitet werden sie vom Code der Integration.
- Intern: `tools/make_demo.py` erzeugt die Daten der Demo, der Workflow „Demo“ veröffentlicht sie über GitHub Pages.
- Intern: wöchentlicher Quellen-Check (`tools/source_check.py`, Workflow „Quellen-Check“, montags): ruft headerapp, homepage und news mit dem echten Client ab und prüft, ob Format, Zeitangaben und Bundesländer noch erkannt werden (nur Zahlen im Bericht, keine Inhalte). Bei Problemen öffnet er ein Issue mit Label `quellen-check` und schließt es wieder, sobald alles geht.
- Intern: Entwicklungs- und Testumgebung auf Home Assistant 2026.10.4 angehoben (Testbibliothek 0.13.375), wie bei Streckenwacht.
- Intern: `astral-sh/setup-uv` 10.3.2; Dependabot schlägt Aktualisierungen jetzt für `dev` vor statt für `main`.

## 0.2.1 – 2026-10-26

- **Schonender für SD-Karten:** Das Gedächtnis für Neustarts wird nur noch kurz nach neuen Meldungen geschrieben, sonst höchstens alle 3 Stunden und beim Herunterfahren (bisher bis zu alle 10 Minuten). „Meldungen (24 h)“ legt keine Langzeitstatistik mehr an, die Home Assistant alle 5 Minuten fortschrieb; der normale Verlauf bleibt. Falls Home Assistant danach unter *Reparaturen* meldet, dass der Sensor keine Statistik mehr hat: die alten Statistikdaten löschen.

## 0.2.0 – 2026-10-22

- **Nichts verpassen beim Neustart:** Eilmeldungen und Wächter-Meldungen, die erscheinen, während Home Assistant neu startet, werden danach gemeldet – auch über die Blueprints aufs Handy. Bisher lernte Eilwacht nach jedem Start still, was schon da war. Nach mehr als 6 Stunden Pause oder nach dem Ändern eines Wächters wird weiterhin still gelernt.

## 0.1.1 – 2026-10-22

- „Meldungen (24 h)“ zeigt wieder „Meldungen“ als Einheit. Die Entfernung in 0.1.0 war ein Irrtum: Die Oberfläche übersetzt die Einheit, nur die Rohdaten speichern sie englisch. Wer 0.1.0 installiert hatte, sieht unter *Reparaturen* eventuell erneut einen Hinweis zur Einheit – einfach bestätigen.
- README mit Screenshots.

## 0.1.0 – 2026-10-22

Erste reguläre Version, nach dem Test auf einer echten Home-Assistant-Instanz.

- **Stichworte finden jetzt alle Wörter, die mit ihnen beginnen:** `Stuttgart` findet auch „Stuttgarter“, `Streik` auch „Streiks“ (aber weiterhin nicht „Warnstreik“, dafür `*streik`). Bisher zählte nur das ganze Wort. Bestehende Wächter finden dadurch eher mehr Meldungen.
- Die Startseite der Tagesschau-API wird nur noch abgefragt, solange die Kopfzeile ausfällt. Eine Eilmeldung verweist auf eine eigene Seite, die Startseite auf den Artikel – beide zusammen hätten dieselbe Eilmeldung zweimal melden können. Nebenbei sinkt der Datenverkehr auf etwa 7 MB am Tag.
- „Meldungen (24 h)“ ohne Einheit (in 0.1.1 zurückgenommen).
- Das Format laufender Eilmeldungen ist jetzt an einer echten Eilmeldung (21.10.2026) bestätigt und getestet.

## 0.1.0b1 – 2026-10-20

Erste Vorab-Version zum Testen.

- **Eilmeldungen** der Tagesschau: Event „Eilmeldung“, Binärsensor „Eilmeldung aktiv“, Sensor „Letzte Eilmeldung“. Abruf jede Minute, die Startseite der Tagesschau-API dient als zweite Quelle, falls die erste ausfällt.
- **Nachrichtenwächter** für ein oder mehrere Bundesländer oder bundesweit, auf Wunsch mit Stichworten (`Warnstreik`, `Streik`, `*streik`, `-Fußball`): Event „Neue Meldung“, Sensor „Letzte Meldung“, Sensor „Meldungen (24 h)“.
- **Blueprints:** Eilmeldung aufs Handy, Eilmeldung ansagen, neue Meldung eines Nachrichtenwächters aufs Handy – mit Ruhezeiten, ohne erneutes Senden nach Neustart oder Ausfall.
- Hinweis unter *Reparaturen*, wenn eine Quelle längere Zeit nicht erreichbar ist.
- Der Diagnose-Download enthält die zuletzt aufgezeichnete Eilmeldung im Rohformat. Das Format laufender Eilmeldungen ist noch nicht an einer echten Meldung überprüft – wer eine erlebt, hilft mit der Diagnose-Datei sehr.
- Getestet mit Home Assistant 2026.3 und 2026.10.
