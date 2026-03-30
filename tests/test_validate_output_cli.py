import sys
from pathlib import Path

from validate_output import main


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def test_main_shows_usage_when_missing_argument(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_output.py"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Usage:" in captured.err


def test_main_reports_valid_output(monkeypatch, tmp_path, capsys):
    valid_json = tmp_path / "valid.json"
    valid_json.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(valid_json)])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"VALID: {valid_json}" in captured.out


def test_main_reports_invalid_output(monkeypatch, tmp_path, capsys):
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(invalid_json)])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "INVALID: $ keys mismatch" in captured.err
