from pathlib import Path

import pytest

import validate_output


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def test_main_returns_usage_error_when_argument_missing(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["validate_output.py"])

    assert validate_output.main() == 2
    assert "Usage: ./validate_output.py <output.json>" in capsys.readouterr().err


def test_main_returns_success_for_valid_output(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["validate_output.py", str(FIXTURE_PATH)])

    assert validate_output.main() == 0
    assert f"VALID: {FIXTURE_PATH}" in capsys.readouterr().out


def test_main_returns_invalid_for_missing_file(monkeypatch, capsys, tmp_path):
    missing_path = tmp_path / "missing.json"
    monkeypatch.setattr("sys.argv", ["validate_output.py", str(missing_path)])

    assert validate_output.main() == 1
    assert f"INVALID: file not found: {missing_path}" in capsys.readouterr().err


def test_main_returns_invalid_for_schema_failure(monkeypatch, capsys, tmp_path):
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["validate_output.py", str(invalid_path)])

    assert validate_output.main() == 1
    assert "INVALID: $ keys mismatch" in capsys.readouterr().err
