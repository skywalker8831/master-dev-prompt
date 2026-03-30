import json
from pathlib import Path

import pytest

from master_dev_runtime import (
    ValidationError,
    load_system_prompt,
    parse_and_validate_output,
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


def test_parse_and_validate_output_rejects_invalid_json():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("{not valid json}")


def test_validate_output_file_rejects_missing_file(tmp_path):
    missing = tmp_path / "missing.json"

    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(missing)


def test_load_system_prompt_requires_existing_file(monkeypatch, tmp_path):
    missing_prompt = tmp_path / "missing_prompt.txt"
    monkeypatch.setattr("master_dev_runtime._system_prompt", None)

    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(missing_prompt)
