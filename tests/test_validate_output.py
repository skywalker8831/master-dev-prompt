import importlib
from pathlib import Path

import pytest
import validate_output


SCRIPT_NAME = "validate_output.py"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


@pytest.fixture(autouse=True)
def reload_validate_output_module():
    importlib.reload(validate_output)


def test_main_requires_exactly_one_argument(monkeypatch, capsys):
    monkeypatch.setattr(validate_output.sys, "argv", [SCRIPT_NAME])

    result = validate_output.main()

    captured = capsys.readouterr()
    assert result == 2
    assert "Usage: ./validate_output.py <output.json>" in captured.err


def test_main_reports_invalid_output(monkeypatch, tmp_path, capsys):
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(validate_output.sys, "argv", [SCRIPT_NAME, str(invalid_path)])

    result = validate_output.main()

    captured = capsys.readouterr()
    assert result == 1
    assert "INVALID: $ keys mismatch" in captured.err


def test_main_reports_valid_output(monkeypatch, capsys):
    monkeypatch.setattr(validate_output.sys, "argv", [SCRIPT_NAME, str(FIXTURE_PATH)])

    result = validate_output.main()

    captured = capsys.readouterr()
    assert result == 0
    assert f"VALID: {FIXTURE_PATH}" in captured.out
