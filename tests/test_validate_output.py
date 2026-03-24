import json
import sys
from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"
VALID_JSON = FIXTURE_PATH.read_text(encoding="utf-8")


# ── validate_output.main() ────────────────────────────────────────────────────

def test_main_returns_0_for_valid_output(tmp_path, monkeypatch, capsys):
    from validate_output import main

    valid_file = tmp_path / "output.json"
    valid_file.write_text(VALID_JSON, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(valid_file)])

    exit_code = main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "VALID" in captured.out


def test_main_returns_1_for_invalid_output(tmp_path, monkeypatch, capsys):
    from validate_output import main

    invalid_file = tmp_path / "output.json"
    invalid_file.write_text(json.dumps({"design_doc": {}}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(invalid_file)])

    exit_code = main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "INVALID" in captured.err


def test_main_returns_1_for_missing_file(tmp_path, monkeypatch, capsys):
    from validate_output import main

    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(tmp_path / "nonexistent.json")])

    exit_code = main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "INVALID" in captured.err


def test_main_returns_2_for_wrong_arg_count(monkeypatch, capsys):
    from validate_output import main

    monkeypatch.setattr(sys, "argv", ["validate_output.py"])

    exit_code = main()

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "Usage" in captured.err
