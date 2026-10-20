# Changelog

## Unveröffentlicht

- Projektgerüst nach dem Muster von Streckenwacht: uv, Ruff, pytest, CI, Dependabot.
- Marke: Ausrufezeichen mit Wachlicht in Signalrot, Slogan „Was wichtig ist, meldet sich.“ (`docs/BRAND.md`); Bilder für Home Assistant, GitHub und Web aus `tools/brand/build.mjs`.
- Datenquellen geprüft (`docs/ENTWICKLUNG.md` Abschnitt 2), bereinigte Fixtures für `headerapp`, `homepage`, `news` und `news?regions=1`.
- Abruf und Auswertung ohne HA-Importe: `tagesschau.py` (Client und Parser für `headerapp`, `homepage`, `news`), `model.py` (`NewsItem`), `keywords.py` (Stichwortwächter mit `*` und Ausschlüssen), `changes.py` (neue Meldungen erkennen, quellenübergreifend nach Artikelpfad).
