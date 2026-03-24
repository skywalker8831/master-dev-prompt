from pathlib import Path

import validate_output


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def test_main_requires_exactly_one_argument(monkeypatch, capsys):
    monkeypatch.setattr(validate_output.sys, "argv", ["validate_output.py"])

    result = validate_output.main()

    captured = capsys.readouterr()
    assert result == 2
    assert "Usage: ./validate_output.py <output.json>" in captured.err


def test_main_reports_invalid_output(monkeypatch, tmp_path, capsys):
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(validate_output.sys, "argv", ["validate_output.py", str(invalid_path)])

    result = validate_output.main()

    captured = capsys.readouterr()
    assert result == 1
    assert "INVALID: $ keys mismatch" in captured.err


def test_main_reports_valid_output(monkeypatch, capsys):
    monkeypatch.setattr(validate_output.sys, "argv", ["validate_output.py", str(FIXTURE_PATH)])

    result = validate_output.main()

    captured = capsys.readouterr()
    assert result == 0
    assert f"VALID: {FIXTURE_PATH}" in captured.out
