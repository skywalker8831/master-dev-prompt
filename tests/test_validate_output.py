"""Tests for the validate_output.py CLI entry point."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def _run_main(args):
    """Call validate_output.main() with the given sys.argv args (excluding script name)."""
    from validate_output import main

    with patch("sys.argv", ["validate_output.py"] + args):
        return main()


# ── argument validation ───────────────────────────────────────────────────────

def test_main_returns_2_without_arguments(capsys):
    result = _run_main([])
    assert result == 2
    captured = capsys.readouterr()
    assert "Usage:" in captured.err


def test_main_returns_2_with_too_many_arguments(capsys, tmp_path):
    result = _run_main(["file1.json", "file2.json"])
    assert result == 2
    captured = capsys.readouterr()
    assert "Usage:" in captured.err


# ── valid file ────────────────────────────────────────────────────────────────

def test_main_returns_0_for_valid_file(capsys):
    result = _run_main([str(FIXTURE_PATH)])
    assert result == 0
    captured = capsys.readouterr()
    assert "VALID:" in captured.out


# ── invalid / missing file ────────────────────────────────────────────────────

def test_main_returns_1_for_missing_file(capsys, tmp_path):
    missing = tmp_path / "nonexistent.json"
    result = _run_main([str(missing)])
    assert result == 1
    captured = capsys.readouterr()
    assert "INVALID:" in captured.err


def test_main_returns_1_for_schema_invalid_json(capsys, tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps({"design_doc": {}}), encoding="utf-8")
    result = _run_main([str(bad_file)])
    assert result == 1
    captured = capsys.readouterr()
    assert "INVALID:" in captured.err


def test_main_returns_1_for_malformed_json(capsys, tmp_path):
    bad_file = tmp_path / "malformed.json"
    bad_file.write_text("{ not valid json", encoding="utf-8")
    result = _run_main([str(bad_file)])
    assert result == 1
    captured = capsys.readouterr()
    assert "INVALID:" in captured.err


# ── __main__ guard ────────────────────────────────────────────────────────────

def test_main_can_be_called_as_system_exit(tmp_path):
    missing = tmp_path / "no.json"
    with patch("sys.argv", ["validate_output.py", str(missing)]):
        with pytest.raises(SystemExit) as exc_info:
            import validate_output
            raise SystemExit(validate_output.main())
    assert exc_info.value.code == 1
