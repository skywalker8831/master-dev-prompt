import json
from pathlib import Path

import pytest

import master_dev_runtime


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def test_parse_and_validate_output_accepts_valid_fixture():
    raw = FIXTURE_PATH.read_text(encoding="utf-8")

    result = master_dev_runtime.parse_and_validate_output(raw)

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

    with pytest.raises(master_dev_runtime.ValidationError, match=r"\$\.design_doc keys mismatch"):
        master_dev_runtime.validate_output_file(invalid_path)


def test_load_system_prompt_requires_file(monkeypatch, tmp_path):
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    missing = tmp_path / "missing_prompt.txt"

    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        master_dev_runtime.load_system_prompt(prompt_path=missing)

    assert master_dev_runtime._system_prompt is None


def test_load_system_prompt_is_cached(monkeypatch, tmp_path):
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("first", encoding="utf-8")

    first = master_dev_runtime.load_system_prompt(prompt_path=prompt_path)
    prompt_path.write_text("second", encoding="utf-8")
    second = master_dev_runtime.load_system_prompt(prompt_path=prompt_path)

    assert first == "first"
    assert second == "first"


def test_parse_and_validate_output_reports_json_location():
    with pytest.raises(master_dev_runtime.ValidationError, match=r"invalid JSON at line 1, column \d+"):
        master_dev_runtime.parse_and_validate_output("{bad json")


def test_validate_output_file_requires_existing_file(tmp_path):
    missing = tmp_path / "nope.json"

    with pytest.raises(master_dev_runtime.ValidationError, match="file not found"):
        master_dev_runtime.validate_output_file(missing)


def test_validate_output_data_rejects_non_object_root():
    with pytest.raises(master_dev_runtime.ValidationError, match=r"\$ must be an object"):
        master_dev_runtime.validate_output_data("not an object")


def test_validate_output_data_rejects_empty_actions_items():
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data["actions"]["items"] = []

    with pytest.raises(master_dev_runtime.ValidationError, match=r"\$\.actions.items must contain at least one item"):
        master_dev_runtime.validate_output_data(data)


def test_validate_output_data_rejects_invalid_priority():
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data["actions"]["items"][0]["priority"] = "urgent"

    with pytest.raises(master_dev_runtime.ValidationError, match=r"\$\.actions.items\[0\].priority must be one of"):
        master_dev_runtime.validate_output_data(data)


def test_validate_output_data_rejects_empty_tech_tasks():
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data["implementation_plan"]["tech_tasks"] = []

    with pytest.raises(master_dev_runtime.ValidationError, match=r"\$\.implementation_plan.tech_tasks must contain at least one item"):
        master_dev_runtime.validate_output_data(data)


def test_validate_output_data_rejects_invalid_area():
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data["implementation_plan"]["tech_tasks"][0]["area"] = "mobile"

    with pytest.raises(master_dev_runtime.ValidationError, match=r"\$\.implementation_plan.tech_tasks\[0\].area must be one of"):
        master_dev_runtime.validate_output_data(data)
