import sys
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def test_main_returns_0_for_valid_file(tmp_path, capsys):
    from validate_output import main

    valid = tmp_path / "valid.json"
    valid.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    with patch("sys.argv", ["validate_output.py", str(valid)]):
        result = main()

    assert result == 0
    captured = capsys.readouterr()
    assert "VALID" in captured.out


def test_main_returns_1_for_schema_invalid_json(tmp_path, capsys):
    from validate_output import main

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")

    with patch("sys.argv", ["validate_output.py", str(invalid)]):
        result = main()

    assert result == 1
    captured = capsys.readouterr()
    assert "INVALID" in captured.err


def test_main_returns_1_for_missing_file(tmp_path, capsys):
    from validate_output import main

    missing = tmp_path / "nonexistent.json"

    with patch("sys.argv", ["validate_output.py", str(missing)]):
        result = main()

    assert result == 1
    captured = capsys.readouterr()
    assert "INVALID" in captured.err


def test_main_returns_2_with_no_args(capsys):
    from validate_output import main

    with patch("sys.argv", ["validate_output.py"]):
        result = main()

    assert result == 2
    captured = capsys.readouterr()
    assert "Usage" in captured.err


def test_main_returns_2_with_too_many_args(capsys):
    from validate_output import main

    with patch("sys.argv", ["validate_output.py", "a.json", "b.json"]):
        result = main()

    assert result == 2
    captured = capsys.readouterr()
    assert "Usage" in captured.err
