import json
from pathlib import Path

import pytest

from master_dev_runtime import (
    ValidationError,
    load_system_prompt,
    parse_and_validate_output,
    validate_output_data,
    validate_output_file,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


@pytest.fixture()
def valid_output_dict():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


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


def test_parse_and_validate_output_reports_json_error():
    with pytest.raises(ValidationError, match=r"invalid JSON at line 1, column 2"):
        parse_and_validate_output("{")


def test_validate_output_file_requires_existing_path(tmp_path):
    missing = tmp_path / "missing.json"

    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(missing)


def test_validate_output_data_requires_non_empty_items(valid_output_dict):
    invalid = json.loads(json.dumps(valid_output_dict))
    invalid["actions"]["items"] = []

    with pytest.raises(ValidationError, match=r"\$\.actions\.items must contain at least one item"):
        validate_output_data(invalid)


def test_validate_output_data_rejects_invalid_enum(valid_output_dict):
    invalid = json.loads(json.dumps(valid_output_dict))
    invalid["implementation_plan"]["tech_tasks"][0]["area"] = "mobile"

    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.area must be one of"):
        validate_output_data(invalid)


def test_load_system_prompt_raises_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("master_dev_runtime._system_prompt", None)

    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(tmp_path / "missing.txt")


def test_load_system_prompt_caches_content(monkeypatch, tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("first")
    monkeypatch.setattr("master_dev_runtime._system_prompt", None)

    first = load_system_prompt(prompt_file)
    prompt_file.write_text("second")
    second = load_system_prompt(prompt_file)

    assert first == "first"
    assert second == "first"
