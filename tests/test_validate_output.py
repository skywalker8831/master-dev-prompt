import json
import sys
from pathlib import Path

import validate_output


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def test_main_requires_argument(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_output.py"])

    result = validate_output.main()

    captured = capsys.readouterr()
    assert result == 2
    assert "Usage: ./validate_output.py <output.json>" in captured.err


def test_main_accepts_valid_file(monkeypatch, capsys, tmp_path):
    copy = tmp_path / "output.json"
    copy.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(copy)])

    result = validate_output.main()

    captured = capsys.readouterr()
    assert result == 0
    assert f"VALID: {copy}" in captured.out


def test_main_rejects_invalid_file(monkeypatch, capsys, tmp_path):
    invalid = tmp_path / "bad.json"
    invalid.write_text(json.dumps({"design_doc": {}}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(invalid)])

    result = validate_output.main()

    captured = capsys.readouterr()
    assert result == 1
    assert "INVALID: $" in captured.err
