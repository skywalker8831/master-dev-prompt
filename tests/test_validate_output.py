import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from validate_output import main


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def test_main_valid_file_returns_0(capsys):
    with patch.object(sys, "argv", ["validate_output.py", str(FIXTURE_PATH)]):
        result = main()
    assert result == 0
    assert "VALID" in capsys.readouterr().out


def test_main_schema_invalid_file_returns_1(tmp_path, capsys):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{}")
    with patch.object(sys, "argv", ["validate_output.py", str(bad_file)]):
        result = main()
    assert result == 1
    assert "INVALID" in capsys.readouterr().err


def test_main_missing_file_returns_1(tmp_path, capsys):
    with patch.object(sys, "argv", ["validate_output.py", str(tmp_path / "nonexistent.json")]):
        result = main()
    assert result == 1
    assert "INVALID" in capsys.readouterr().err


def test_main_no_args_returns_2(capsys):
    with patch.object(sys, "argv", ["validate_output.py"]):
        result = main()
    assert result == 2
    assert "Usage" in capsys.readouterr().err


def test_main_too_many_args_returns_2(capsys):
    with patch.object(sys, "argv", ["validate_output.py", "a.json", "b.json"]):
        result = main()
    assert result == 2
    assert "Usage" in capsys.readouterr().err
