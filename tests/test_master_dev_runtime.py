import json
import copy
from pathlib import Path

import pytest

import master_dev_runtime
from master_dev_runtime import (
    ValidationError,
    build_user_message,
    load_system_prompt,
    parse_and_validate_output,
    validate_output_data,
    validate_output_file,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def _valid_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ── load_system_prompt ────────────────────────────────────────────────────────

def test_load_system_prompt_raises_if_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(tmp_path / "nonexistent.txt")


def test_load_system_prompt_reads_file(tmp_path, monkeypatch):
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("my system prompt", encoding="utf-8")
    result = load_system_prompt(prompt_file)
    assert result == "my system prompt"


def test_load_system_prompt_caches_result(tmp_path, monkeypatch):
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("cached prompt", encoding="utf-8")
    first = load_system_prompt(prompt_file)
    # Remove the file — a second call must still succeed from cache
    prompt_file.unlink()
    second = load_system_prompt(prompt_file)
    assert first == second == "cached prompt"


# ── build_user_message ────────────────────────────────────────────────────────

def test_build_user_message_format():
    result = build_user_message("hello world")
    assert result == 'hello world\n"""'


def test_build_user_message_preserves_newlines():
    result = build_user_message("line1\nline2")
    assert result.startswith("line1\nline2")
    assert result.endswith('"""')


# ── validate_output_data helper paths ────────────────────────────────────────

def test_validate_output_data_rejects_non_dict_root():
    with pytest.raises(ValidationError, match=r"\$ must be an object"):
        validate_output_data("not a dict")


def test_validate_output_data_rejects_non_dict_design_doc():
    data = _valid_data()
    data["design_doc"] = "not a dict"
    with pytest.raises(ValidationError, match=r"\$\.design_doc must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_list_actions_items():
    data = _valid_data()
    data["actions"]["items"] = "not a list"
    with pytest.raises(ValidationError, match=r"\$\.actions\.items must be an array"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_string_field():
    data = _valid_data()
    data["design_doc"]["context_problem"] = 42
    with pytest.raises(ValidationError, match=r"\$\.design_doc\.context_problem must be a string"):
        validate_output_data(data)


def test_validate_output_data_rejects_extra_keys_in_design_doc():
    data = _valid_data()
    data["design_doc"]["unexpected_key"] = "surprise"
    with pytest.raises(ValidationError, match=r"\$\.design_doc keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_actions_list():
    data = _valid_data()
    data["actions"]["items"] = []
    with pytest.raises(ValidationError, match=r"\$\.actions\.items must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_milestones_list():
    data = _valid_data()
    data["implementation_plan"]["milestones"] = []
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.milestones must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_bad_enum_priority():
    data = _valid_data()
    data["actions"]["items"][0]["priority"] = "urgent"
    with pytest.raises(ValidationError, match=r"must be one of"):
        validate_output_data(data)


def test_validate_output_data_rejects_bad_enum_action_type():
    data = _valid_data()
    data["actions"]["items"][0]["type"] = "unknown"
    with pytest.raises(ValidationError, match=r"must be one of"):
        validate_output_data(data)


def test_validate_output_data_rejects_bad_enum_area():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["area"] = "marketing"
    with pytest.raises(ValidationError, match=r"must be one of"):
        validate_output_data(data)


def test_validate_output_data_rejects_bad_enum_complexity():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["complexity"] = "XL"
    with pytest.raises(ValidationError, match=r"must be one of"):
        validate_output_data(data)


def test_validate_output_data_validates_depends_on_element_type():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [123]
    with pytest.raises(ValidationError, match=r"must be a string"):
        validate_output_data(data)


def test_validate_output_data_accepts_non_empty_depends_on():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = ["task-1", "task-2"]
    result = validate_output_data(data)
    assert result["implementation_plan"]["tech_tasks"][0]["depends_on"] == ["task-1", "task-2"]


# ── parse_and_validate_output ─────────────────────────────────────────────────

def test_parse_and_validate_output_accepts_valid_fixture():
    raw = FIXTURE_PATH.read_text(encoding="utf-8")

    result = parse_and_validate_output(raw)

    assert result["actions"]["items"][0]["priority"] == "low"
    assert result["implementation_plan"]["tech_tasks"][0]["complexity"] == "S"


def test_parse_and_validate_output_rejects_malformed_json():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("{not: valid json}")


def test_parse_and_validate_output_rejects_truncated_json():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output('{"design_doc":')


# ── validate_output_file ──────────────────────────────────────────────────────

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


def test_validate_output_file_raises_if_file_missing(tmp_path):
    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(tmp_path / "missing.json")
