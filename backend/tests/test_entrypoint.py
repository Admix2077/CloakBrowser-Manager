"""Tests for Docker entrypoint startup cleanup."""

from __future__ import annotations

from pathlib import Path


def test_entrypoint_cleans_scoped_invisible_playwright_firefox():
    entrypoint = Path(__file__).parents[2] / "entrypoint.sh"
    text = entrypoint.read_text()

    assert r"\.cache/invisible-playwright/.*/firefox" in text
    assert "pkill -f 'firefox'" not in text
    assert "pkill -f firefox" not in text

