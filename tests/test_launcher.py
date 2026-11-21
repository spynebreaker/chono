import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
pytest.importorskip("tkinter")
from chono import launcher  # noqa: E402


def test_when_says_how_long_ago_in_plain_words():
    now = time.mktime((2026, 11, 21, 15, 0, 0, 0, 0, -1))
    assert launcher.when(now - 60, now) == "Hace un momento"
    assert launcher.when(now - 5 * 3600, now) == "Hoy"
    assert launcher.when(now - 26 * 3600, now) == "Ayer"
    assert launcher.when(now - 4 * 86400, now) == "Hace 4 días"
    assert launcher.when(now - 40 * 86400, now) == time.strftime("%d/%m/%Y", time.localtime(now - 40 * 86400))


def test_greeting_follows_the_hour():
    assert launcher.greeting(8) == "Buenos días"
    assert launcher.greeting(15) == "Buenas tardes"
    assert launcher.greeting(21) == "Buenas noches"


def test_recent_documents_newest_first_without_repeats_or_missing_files(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "CONFIG", tmp_path / "config.json")
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    a.write_bytes(b"%PDF")
    b.write_bytes(b"%PDF")
    launcher.note_recent(str(a))
    launcher.note_recent(str(b))
    launcher.note_recent(str(a))
    assert [p.name for p, _ in launcher.recent_files()] == ["a.pdf", "b.pdf"]
    b.unlink()
    assert [p.name for p, _ in launcher.recent_files()] == ["a.pdf"]
