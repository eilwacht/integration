"""Constants for Eilwacht. Pure Python, no Home Assistant imports."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "eilwacht"
VERSION: Final = "0.2.1"
USER_AGENT: Final = f"Eilwacht/{VERSION} (+https://github.com/eilwacht/integration)"
ATTRIBUTION: Final = "Quelle: tagesschau.de"

BASE_URL: Final = "https://www.tagesschau.de/"
# Undocumented endpoint of the website; "breakingNews" is only present while an
# alert is running (docs/ENTWICKLUNG.md, section 2).
HEADERAPP_URL: Final = "https://www.tagesschau.de/json/headerapp"
# Documented by bundesAPI. Without trailing slash: "/homepage/" answers 308.
HOMEPAGE_URL: Final = "https://www.tagesschau.de/api2u/homepage"
NEWS_URL: Final = "https://www.tagesschau.de/api2u/news"

REQUEST_TIMEOUT: Final = 30

# api2u allows at most 60 requests per hour for the whole instance: at most
# 30 (homepage while headerapp fails) + 8 (news, by state and national).
HEADERAPP_INTERVAL: Final = timedelta(minutes=1)
HOMEPAGE_FALLBACK_INTERVAL: Final = timedelta(minutes=2)
NEWS_INTERVAL: Final = timedelta(minutes=15)

# Failed polls in a row before a repair issue is raised (about 30 minutes).
FAILURES_BEFORE_ISSUE: Final = {"headerapp": 30, "news": 2}

SUBENTRY_WATCH: Final = "watch"
CONF_REGIONS: Final = "regions"
CONF_KEYWORDS: Final = "keywords"

EVENT_BREAKING: Final = "breaking_news"
EVENT_NEWS: Final = "news"

# api2u "regions" parameter: federal states numbered alphabetically.
REGIONS: Final[dict[int, str]] = {
    1: "Baden-Württemberg",
    2: "Bayern",
    3: "Berlin",
    4: "Brandenburg",
    5: "Bremen",
    6: "Hamburg",
    7: "Hessen",
    8: "Mecklenburg-Vorpommern",
    9: "Niedersachsen",
    10: "Nordrhein-Westfalen",
    11: "Rheinland-Pfalz",
    12: "Saarland",
    13: "Sachsen",
    14: "Sachsen-Anhalt",
    15: "Schleswig-Holstein",
    16: "Thüringen",
}
