"""Tests for the validate_output.py CLI wrapper."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

CLI_PATH = Path(__file__).resolve().parents[1] / "validate_output.py"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def test_validate_output_cli_returns_zero_for_valid_file():
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), str(FIXTURE_PATH)],
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 0
    assert "VALID:" in result.stdout


def test_validate_output_cli_returns_one_for_invalid_file(tmp_path):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{}", encoding="utf-8")
    
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), str(invalid_file)],
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 1
    assert "INVALID:" in result.stderr


def test_validate_output_cli_returns_two_for_missing_argument():
    result = subprocess.run(
        [sys.executable, str(CLI_PATH)],
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 2
    assert "Usage:" in result.stderr


def test_validate_output_cli_returns_one_for_missing_file(tmp_path):
    missing_file = tmp_path / "nonexistent.json"
    
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), str(missing_file)],
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 1
    assert "INVALID:" in result.stderr
    assert "file not found" in result.stderr


def test_validate_output_cli_returns_one_for_invalid_json_syntax(tmp_path):
    malformed_file = tmp_path / "malformed.json"
    malformed_file.write_text("{ invalid json }", encoding="utf-8")
    
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), str(malformed_file)],
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 1
    assert "INVALID:" in result.stderr
    assert "invalid JSON" in result.stderr


def test_validate_output_cli_shows_specific_validation_error(tmp_path):
    # File with valid JSON but invalid schema (missing required keys)
    incomplete_file = tmp_path / "incomplete.json"
    incomplete_file.write_text(
        json.dumps({
            "design_doc": {"context_problem": "test"},  # Missing other required keys
            "pm_summary": {},
            "actions": {"items": []},
            "implementation_plan": {},
            "code_suggestions": {},
        }),
        encoding="utf-8",
    )
    
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), str(incomplete_file)],
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 1
    assert "INVALID:" in result.stderr
    assert "keys mismatch" in result.stderr
