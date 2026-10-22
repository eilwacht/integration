"""Keyword filter for news items. Pure Python, no Home Assistant imports.

Syntax (comma-separated, case-insensitive):
  Stuttgart      words starting with it: "Stuttgart", "Stuttgarter"
  Streik         "Streik", "Streiks", "Streikende", not "Warnstreik"
  *streik        words containing it: "Warnstreik", "Bahnstreiks"
  Bahn           "Bahnhof", not "Autobahn", not "S-Bahn"
  S-Bahn Stuttgart  phrases: the last word may continue ("Stuttgarter")
  -Fußball       exclude: items with words starting with it never match
An empty filter matches every item. German inflects and compounds a lot,
so matching the start of words finds what users mean ("Stuttgarter",
"Streiks") without a trailing "*" (still accepted).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .model import NewsItem

# Letters, digits and hyphens belong to a word ("S-Bahn", "A8").
_WORD = r"[\w-]"


def _compile(term: str) -> re.Pattern[str]:
    words = (
        f"{_WORD}*".join(re.escape(part) for part in word.split("*"))
        for word in term.split()
    )
    body = r"\s+".join(words)
    # Anchored at the start of a word only: the word may continue.
    return re.compile(rf"(?<!{_WORD}){body}", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class KeywordFilter:
    """Parsed keyword list."""

    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()

    @classmethod
    def parse(cls, text: str | None) -> KeywordFilter:
        """Parse the comma-separated user input; blank terms are ignored."""
        include: list[str] = []
        exclude: list[str] = []
        for raw in (text or "").split(","):
            term = " ".join(raw.split())
            if term.startswith("-"):
                term = term[1:].strip()
                target = exclude
            else:
                target = include
            if term.strip("*"):
                target.append(term)
        return cls(tuple(include), tuple(exclude))

    def __bool__(self) -> bool:
        return bool(self.include or self.exclude)

    def matches(self, item: NewsItem) -> tuple[str, ...] | None:
        """Matching include terms, or None if the item does not pass.

        Returns an empty tuple for a pass without include terms.
        """
        text = item.text
        if any(_compile(term).search(text) for term in self.exclude):
            return None
        if not self.include:
            return ()
        found = tuple(term for term in self.include if _compile(term).search(text))
        return found or None
