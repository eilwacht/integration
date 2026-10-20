"""Keyword filter for news items. Pure Python, no Home Assistant imports.

Syntax (comma-separated, case-insensitive):
  Warnstreik     whole word: matches "Warnstreik", not "Warnstreiks"
  Streik*        word starting with "Streik": "Streiks", "Streikende"
  *streik        word ending with "streik": "Warnstreik", "Bahnstreik"
  S-Bahn Stuttgart  phrases work the same way
  -Fußball       exclude: items mentioning it never match
An empty filter matches every item.
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
    return re.compile(rf"(?<!{_WORD}){body}(?!{_WORD})", re.IGNORECASE)


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
