import json
import sys
from pathlib import Path

import pytest

import validate_output as cli


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = PROJECT_ROOT / "ci" / "fixtures" / "valid_output.json"


def test_main_requires_argument(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["validate_output.py"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Usage:" in captured.err


def test_main_accepts_valid_file(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(FIXTURE_PATH)])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "VALID" in captured.out
    assert str(FIXTURE_PATH) in captured.out


def test_main_rejects_invalid_file(tmp_path, capsys, monkeypatch):
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"design_doc": {}}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["validate_output.py", str(invalid)])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "INVALID" in captured.err
    assert "$ keys mismatch" in captured.err
