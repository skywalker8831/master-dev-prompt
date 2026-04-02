import sys
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def test_main_returns_2_when_no_args():
    from validate_output import main

    with patch.object(sys, "argv", ["validate_output.py"]):
        assert main() == 2


def test_main_returns_2_when_too_many_args():
    from validate_output import main

    with patch.object(sys, "argv", ["validate_output.py", "a.json", "b.json"]):
        assert main() == 2


def test_main_returns_0_for_valid_file():
    from validate_output import main

    with patch.object(sys, "argv", ["validate_output.py", str(FIXTURE_PATH)]):
        assert main() == 0


def test_main_returns_1_for_invalid_file(tmp_path):
    from validate_output import main

    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    with patch.object(sys, "argv", ["validate_output.py", str(bad)]):
        assert main() == 1


def test_main_returns_1_for_missing_file(tmp_path):
    from validate_output import main

    missing = tmp_path / "ghost.json"
    with patch.object(sys, "argv", ["validate_output.py", str(missing)]):
        assert main() == 1
