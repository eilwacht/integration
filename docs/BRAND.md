# Eilwacht – Marke & Bilddateien

## Idee

Ein Ausrufezeichen, dessen Punkt das leuchtende Wachlicht mit Halo ist: was wichtig ist, meldet sich. Der Balken ist die Fahrbahn aus dem Streckenwacht-Icon, auf den Kopf gestellt – so bleiben beide Integrationen als Geschwister erkennbar (gleiche Kachel, gleiche Schutzzone, gleiches Amber-Wachlicht, gleiche Schrift). Die Kachelfarbe ist **RAL 3001 Signalrot**.

**Slogan:** „Was wichtig ist, meldet sich.“

Bewusst nichts, was nach Tagesschau oder ARD aussieht: kein Tagesschau-Blau, kein nachgebauter „Eilmeldung“-Balken, kein Globus oder Sprecherpult.

## Farben

| Rolle | Hex | Hinweis |
| --- | --- | --- |
| Kachel, Wortmarke | `#9B2423` | RAL 3001 Signalrot |
| Wachlicht | `#F5A623` | Amber, wie bei Streckenwacht |
| Ausrufezeichen | `#FBF7EE` | warmes Off-White |
| Heller Hintergrund | `#FAF7F2` | README-Kopf, Social Preview |
| Dunkler Hintergrund | `#14181D` | README-Kopf (Dark Mode) |
| Tagline hell / dunkel | `#6B6357` / `#B9B2A6` | |

Halo: Amber mit 35 % Deckkraft.

## Schrift

**Space Grotesk** (Google Fonts, SIL Open Font License), Bold 700 für die Wortmarke, Medium 500 für Tagline und Zusatzzeilen. In allen SVGs ist der Text in Pfade umgewandelt.

## Dateien

| Ort | Inhalt |
| --- | --- |
| `custom_components/eilwacht/brand/` | `icon(@2x)`, `dark_icon(@2x)`, `logo(@2x)`, `dark_logo(@2x)` – lädt Home Assistant ab 2026.3 aus der Integration |
| `assets/github/` | README-Kopf hell/dunkel (960×220, @2x), Social Preview 1280×640, Profilbild der Organisation 500/1024 |
| `assets/brand/svg/` | Vektor-Master: Icon, Mini-Icon, vollflächiges Icon, Motiv, Logo, README-Kopf, Social Preview |
| `assets/brand/png/` | Icon 16–2048 px, Motiv ohne Kachel, Logo hell/dunkel |
| `assets/brand/favicon/` | `favicon.ico` (16/32/48), `favicon.svg`, PNG, Apple-Touch- und Android-Icons |

Profilbild der Organisation und Social Preview lassen sich nicht per API setzen: von Hand hochladen (Organisation → Settings → Profile; Repo → Settings → General → Social preview).

## Regeln

- **≤ 32 px immer die Mini-Variante**: breiterer Balken, größerer Punkt, kein Halo.
- Motiv ohne Kachel: auf hellem Grund Balken in Signalrot (`mark-on-light`), auf dunklem in Off-White (`mark-on-dark`).
- Farben nicht verändern, Motiv nicht verzerren, keine Schatten oder Verläufe.
- Um Logo und Icon mindestens ¼ der Kachelbreite frei lassen.

## Neu erzeugen

```bash
cd tools/brand
npm install
node build.mjs
```

Das Skript schreibt direkt an die Plätze oben (vorher werden diese Ordner geleert). Farben, Name, Slogan und Unterzeile stehen als Konstanten oben in `build.mjs`. Anders als bei Streckenwacht entfällt das Umkopieren, und `favicon.ico` entsteht ohne ImageMagick.

Technische Notiz (von Streckenwacht übernommen): `font.getPath()` und `Path.toPathData()` von opentype.js 2.0.0 erzeugen bei Space Grotesk für manche Koordinaten `NaN`; das Skript setzt die Buchstaben deshalb selbst und serialisiert die Pfade selbst.

## Entstehung

Drei Motive im Design-Canvas verglichen (für Eingeladene: `https://claude.ai/artifact/81fEQziNF8E5dNVSi4BYK8`): Meldung (Nachrichtenkarte mit Hinweispunkt), Sender (Mast mit Wellen), Ausruf. Gewählt am 2026-10-20: Ausruf in Signalrot – am klarsten bei 16 px und durch die gespiegelte Fahrbahn am engsten mit Streckenwacht verwandt. Verworfene Kachelfarbe: Wasserblau RAL 5021.
