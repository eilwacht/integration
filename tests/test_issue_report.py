"""The report for a bug report: plain text, empty sections left out, no
watch names or keywords."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.eilwacht.button import endpoint_lines, watch_lines
from custom_components.eilwacht.issue_report import render, settings
from custom_components.eilwacht.keywords import KeywordFilter
from custom_components.eilwacht.watch import Watch


def test_render_sections_and_lines() -> None:
    text = render(
        "Eilwacht 0.2.2, Home Assistant 2026.11.0",
        [
            ("entry", [("watches", "0")]),
            ("sources", []),
            ("settings", settings({"b": 2, "a": 1})),
        ],
    )
    assert text == (
        "Eilwacht 0.2.2, Home Assistant 2026.11.0\n"
        "\n"
        "[entry]\n"
        "watches: 0\n"
        "\n"
        "[settings]\n"
        "a: 1\n"
        "b: 2"
    )


def test_watch_lines_count_keywords_only() -> None:
    watches = [
        Watch(
            regions=frozenset({1, 0}),
            keywords=KeywordFilter.parse("Stuttgart, S-Bahn, -Fußball"),
        ),
        Watch(regions=frozenset({16})),
    ]
    assert watch_lines(watches) == [
        ("watch 1", "national, Baden-Württemberg; keywords 2, excluded 1"),
        ("watch 2", "Thüringen; keywords 0, excluded 0"),
    ]


def coordinator(
    failures: int = 0, error: str | None = None, **rest: object
) -> SimpleNamespace:
    return SimpleNamespace(failures=failures, error=error, **rest)


def test_endpoint_lines() -> None:
    runtime = SimpleNamespace(
        breaking=coordinator(homepage_error=None, homepage_active=False), news=None
    )
    assert endpoint_lines(runtime) == [  # type: ignore[arg-type]
        ("headerapp", "ok"),
        ("homepage", "not needed"),
        ("news", "no watch"),
    ]

    runtime = SimpleNamespace(
        breaking=coordinator(
            failures=3, error="Timeout", homepage_error=None, homepage_active=True
        ),
        news=coordinator(failures=2, error="x" * 200),
    )
    lines = dict(endpoint_lines(runtime))  # type: ignore[arg-type]
    assert lines["headerapp"] == "3 failed polls in a row (Timeout)"
    assert lines["homepage"] == "standing in"
    assert lines["news"] == f"2 failed polls in a row ({'x' * 159}…)"


def test_text_and_utc() -> None:
    """Settings in plain text, not Python's spelling (same in all sister projects)."""
    from datetime import UTC, date, datetime, timedelta, timezone

    from custom_components.eilwacht.issue_report import text, utc

    assert text(True) == "yes"
    assert text(False) == "no"
    assert text(None) == "none"
    assert text([7.94, 8]) == "7.94, 8"
    assert text([]) == "none"
    assert text({"a": 1, "b": None}) == "a 1, b none"
    assert text(date(2026, 1, 1)) == "2026-01-01"
    assert text(0.5) == "0.5"
    moment = datetime(
        2026, 11, 7, 13, 39, 32, 639925, tzinfo=timezone(timedelta(hours=1))
    )
    assert text(moment) == utc(moment) == "2026-11-07 12:39 UTC"
    assert utc(datetime(2026, 11, 7, 12, 0, tzinfo=UTC)) == "2026-11-07 12:00 UTC"
    assert utc(None) == "-"
