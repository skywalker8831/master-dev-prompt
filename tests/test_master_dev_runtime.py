import json
from pathlib import Path

import pytest

import master_dev_runtime
from master_dev_runtime import ValidationError, load_system_prompt, parse_and_validate_output, validate_output_file


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


def test_parse_and_validate_output_reports_json_location():
    with pytest.raises(ValidationError, match=r"invalid JSON at line 1, column 1"):
        parse_and_validate_output("not json")


def test_parse_and_validate_output_requires_object_root():
    with pytest.raises(ValidationError, match=r"^\$ must be an object$"):
        parse_and_validate_output("[]")


def test_parse_and_validate_output_requires_non_empty_lists():
    payload = {
        "design_doc": {
            "context_problem": "",
            "requirements_constraints": "",
            "proposed_architecture": "",
            "alternatives": "",
            "decisions": "",
            "open_questions_risks": "",
        },
        "pm_summary": {
            "overview": "",
            "scope": "",
            "implications_for_timeline": "",
        },
        "actions": {"items": []},
        "implementation_plan": {
            "overview": "",
            "milestones": [
                {"name": "", "description": "", "eta_guess": "", "risks": ""},
            ],
            "tech_tasks": [
                {"area": "backend", "description": "", "depends_on": [], "complexity": "S"},
            ],
        },
        "code_suggestions": {"language": "", "stack_context": "", "snippets": []},
    }

    with pytest.raises(ValidationError, match=r"\$\.actions\.items must contain at least one item"):
        parse_and_validate_output(json.dumps(payload))


def test_validate_output_file_rejects_missing_path(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(ValidationError, match=r"file not found"):
        validate_output_file(missing)


def test_load_system_prompt_raises_when_file_missing(monkeypatch, tmp_path):
    fake_path = tmp_path / "nope.txt"
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)

    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(fake_path)
