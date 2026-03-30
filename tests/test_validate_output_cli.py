import sys
from pathlib import Path

import pytest

from validate_output import main


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def test_main_shows_usage_when_missing_argument(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["validate_output.py"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Usage" in captured.err


def test_main_returns_error_for_invalid_json(tmp_path, capsys, monkeypatch):
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(invalid_path)])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "INVALID:" in captured.err
    assert "$ keys mismatch" in captured.err


def test_main_accepts_valid_file(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(FIXTURE_PATH)])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"VALID: {FIXTURE_PATH}" in captured.out
