import json
from pathlib import Path

import pytest

import master_dev_runtime as runtime
from master_dev_runtime import (
    ValidationError,
    build_user_message,
    load_system_prompt,
    parse_and_validate_output,
    validate_output_data,
    validate_output_file,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"
VALID_DATA = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ── parse_and_validate_output / validate_output_file ─────────────────────────

def test_parse_and_validate_output_accepts_valid_fixture():
    raw = FIXTURE_PATH.read_text(encoding="utf-8")

    result = parse_and_validate_output(raw)

    assert result["actions"]["items"][0]["priority"] == "low"
    assert result["implementation_plan"]["tech_tasks"][0]["complexity"] == "S"


def test_parse_and_validate_output_rejects_invalid_json():
    with pytest.raises(ValidationError, match=r"invalid JSON"):
        parse_and_validate_output("{not valid json")


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


def test_validate_output_file_rejects_missing_file(tmp_path):
    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(tmp_path / "nonexistent.json")


# ── load_system_prompt ────────────────────────────────────────────────────────

def test_load_system_prompt_returns_string(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "_system_prompt", None)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("system prompt content", encoding="utf-8")

    result = load_system_prompt(prompt_file)

    assert result == "system prompt content"


def test_load_system_prompt_caches_after_first_call(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "_system_prompt", None)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("cached prompt", encoding="utf-8")

    first = load_system_prompt(prompt_file)
    # Remove file to confirm second call returns cached value
    prompt_file.unlink()
    second = load_system_prompt(prompt_file)

    assert first == second == "cached prompt"


def test_load_system_prompt_raises_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "_system_prompt", None)

    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(tmp_path / "missing.txt")


# ── build_user_message ────────────────────────────────────────────────────────

def test_build_user_message_appends_delimiter():
    result = build_user_message("hello transcript")
    assert result == 'hello transcript\n"""'


# ── _require_dict / _require_list / _require_str raises ──────────────────────

def test_validate_output_data_raises_when_root_not_dict():
    with pytest.raises(ValidationError, match=r"\$ must be an object"):
        validate_output_data(["not", "a", "dict"])


def test_validate_output_data_raises_when_design_doc_not_dict():
    data = {**VALID_DATA, "design_doc": "oops"}
    with pytest.raises(ValidationError, match=r"\$\.design_doc must be an object"):
        validate_output_data(data)


def test_validate_output_data_raises_when_actions_items_not_list():
    import copy
    data = copy.deepcopy(VALID_DATA)
    data["actions"]["items"] = "not-a-list"
    with pytest.raises(ValidationError, match=r"\$\.actions\.items must be an array"):
        validate_output_data(data)


def test_validate_output_data_raises_when_design_doc_field_not_string():
    import copy
    data = copy.deepcopy(VALID_DATA)
    data["design_doc"]["context_problem"] = 123
    with pytest.raises(ValidationError, match=r"\$\.design_doc\.context_problem must be a string"):
        validate_output_data(data)


# ── _require_exact_keys extra-keys branch ────────────────────────────────────

def test_validate_output_data_raises_for_extra_root_keys():
    import copy
    data = copy.deepcopy(VALID_DATA)
    data["unexpected_key"] = "extra"
    with pytest.raises(ValidationError, match=r"extra=\['unexpected_key'\]"):
        validate_output_data(data)


# ── _require_non_empty_list ───────────────────────────────────────────────────

def test_validate_output_data_raises_when_actions_items_empty():
    import copy
    data = copy.deepcopy(VALID_DATA)
    data["actions"]["items"] = []
    with pytest.raises(ValidationError, match=r"\$\.actions\.items must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_raises_when_milestones_empty():
    import copy
    data = copy.deepcopy(VALID_DATA)
    data["implementation_plan"]["milestones"] = []
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.milestones must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_raises_when_snippets_empty():
    import copy
    data = copy.deepcopy(VALID_DATA)
    data["code_suggestions"]["snippets"] = []
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets must contain at least one item"):
        validate_output_data(data)


# ── _require_enum ─────────────────────────────────────────────────────────────

def test_validate_output_data_raises_for_invalid_action_priority():
    import copy
    data = copy.deepcopy(VALID_DATA)
    data["actions"]["items"][0]["priority"] = "critical"
    with pytest.raises(ValidationError, match=r"priority.*must be one of"):
        validate_output_data(data)


def test_validate_output_data_raises_for_invalid_action_type():
    import copy
    data = copy.deepcopy(VALID_DATA)
    data["actions"]["items"][0]["type"] = "unknown"
    with pytest.raises(ValidationError, match=r"type.*must be one of"):
        validate_output_data(data)


def test_validate_output_data_raises_for_invalid_tech_task_area():
    import copy
    data = copy.deepcopy(VALID_DATA)
    data["implementation_plan"]["tech_tasks"][0]["area"] = "marketing"
    with pytest.raises(ValidationError, match=r"area.*must be one of"):
        validate_output_data(data)


def test_validate_output_data_raises_for_invalid_tech_task_complexity():
    import copy
    data = copy.deepcopy(VALID_DATA)
    data["implementation_plan"]["tech_tasks"][0]["complexity"] = "XL"
    with pytest.raises(ValidationError, match=r"complexity.*must be one of"):
        validate_output_data(data)


# ── depends_on list item validation ──────────────────────────────────────────

def test_validate_output_data_raises_for_non_string_depends_on_item():
    import copy
    data = copy.deepcopy(VALID_DATA)
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [42]
    with pytest.raises(ValidationError, match=r"depends_on\[0\] must be a string"):
        validate_output_data(data)
