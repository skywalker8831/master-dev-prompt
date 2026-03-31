"""Tests for the validate_output.py CLI entry point."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import validate_output


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"
VALID_JSON = FIXTURE_PATH.read_text(encoding="utf-8")


def test_main_returns_2_when_no_args(capsys):
    with patch.object(sys, "argv", ["validate_output.py"]):
        exit_code = validate_output.main()
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "Usage" in captured.err


def test_main_returns_2_when_too_many_args(capsys):
    with patch.object(sys, "argv", ["validate_output.py", "a.json", "b.json"]):
        exit_code = validate_output.main()
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "Usage" in captured.err


def test_main_returns_0_for_valid_file(tmp_path, capsys):
    valid_path = tmp_path / "output.json"
    valid_path.write_text(VALID_JSON, encoding="utf-8")

    with patch.object(sys, "argv", ["validate_output.py", str(valid_path)]):
        exit_code = validate_output.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "VALID" in captured.out


def test_main_returns_1_for_invalid_file(tmp_path, capsys):
    invalid_path = tmp_path / "bad.json"
    invalid_path.write_text(json.dumps({"design_doc": {}}), encoding="utf-8")

    with patch.object(sys, "argv", ["validate_output.py", str(invalid_path)]):
        exit_code = validate_output.main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "INVALID" in captured.err


def test_main_returns_1_for_missing_file(tmp_path, capsys):
    missing = tmp_path / "ghost.json"

    with patch.object(sys, "argv", ["validate_output.py", str(missing)]):
        exit_code = validate_output.main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "INVALID" in captured.err


def test_main_returns_1_for_malformed_json(tmp_path, capsys):
    bad_path = tmp_path / "malformed.json"
    bad_path.write_text("{not valid json", encoding="utf-8")

    with patch.object(sys, "argv", ["validate_output.py", str(bad_path)]):
        exit_code = validate_output.main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "INVALID" in captured.err
