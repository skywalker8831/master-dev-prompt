import json
import sys
from pathlib import Path

import pytest


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


# ── main() argument-count guard ───────────────────────────────────────────────

def test_main_returns_2_with_no_arguments(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["validate_output.py"])

    from validate_output import main

    assert main() == 2


def test_main_returns_2_with_too_many_arguments(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["validate_output.py", "a.json", "extra"])

    from validate_output import main

    assert main() == 2


# ── main() happy path ─────────────────────────────────────────────────────────

def test_main_returns_0_and_prints_valid_for_valid_file(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(FIXTURE_PATH)])

    from validate_output import main

    result = main()

    assert result == 0
    assert "VALID" in capsys.readouterr().out


# ── main() error paths ────────────────────────────────────────────────────────

def test_main_returns_1_and_prints_invalid_for_bad_schema(monkeypatch, tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(bad)])

    from validate_output import main

    result = main()

    assert result == 1
    assert "INVALID" in capsys.readouterr().err


def test_main_returns_1_and_prints_invalid_for_missing_file(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_output.py", "/nonexistent/path.json"])

    from validate_output import main

    result = main()

    assert result == 1
    assert "INVALID" in capsys.readouterr().err


def test_main_returns_1_for_malformed_json(monkeypatch, tmp_path, capsys):
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not valid json}")
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(malformed)])

    from validate_output import main

    result = main()

    assert result == 1
    assert "INVALID" in capsys.readouterr().err
