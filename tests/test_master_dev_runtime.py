import json
from pathlib import Path

import pytest

from master_dev_runtime import (
    ValidationError,
    parse_and_validate_output,
    validate_output_data,
    validate_output_file,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def test_parse_and_validate_output_accepts_valid_fixture():
    raw = FIXTURE_PATH.read_text(encoding="utf-8")

    result = parse_and_validate_output(raw)

    assert result["actions"]["items"][0]["priority"] == "low"
    assert result["implementation_plan"]["tech_tasks"][0]["complexity"] == "S"


def test_validate_output_file_rejects_schema_invalid_json(tmp_path):
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text(
        json.dumps(
            {
                "design_doc": {},
                "pm_summary": {},
                "actions": {"items": []},
                "implementation_plan": {"overview": "", "milestones": [], "tech_tasks": []},
                "code_suggestions": {"language": "", "stack_context": "", "snippets": []},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match=r"\$\.design_doc keys mismatch"):
        validate_output_file(invalid_path)


def test_validate_output_file_missing_file(tmp_path):
    missing = tmp_path / "definitely-missing.json"

    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(missing)


def test_parse_and_validate_output_rejects_invalid_json():
    with pytest.raises(ValidationError, match=r"invalid JSON at line 1, column 2"):
        parse_and_validate_output("{")


def test_validate_output_data_requires_non_empty_lists():
    minimal = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    minimal["actions"]["items"] = []

    with pytest.raises(ValidationError, match=r"\$\.actions\.items must contain at least one item"):
        validate_output_data(minimal)


def test_validate_output_data_rejects_invalid_enum_values():
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data["actions"]["items"][0]["priority"] = "urgent"

    with pytest.raises(ValidationError, match=r"\.priority must be one of \['high', 'low', 'medium'\]"):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_complexity():
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data["implementation_plan"]["tech_tasks"][0]["complexity"] = "XL"

    with pytest.raises(ValidationError, match=r"\.complexity must be one of \['L', 'M', 'S'\]"):
        validate_output_data(data)
