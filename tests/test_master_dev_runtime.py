import copy
import json
from pathlib import Path

import pytest

import master_dev_runtime as runtime_mod
from master_dev_runtime import (
    ValidationError,
    _require_dict,
    _require_enum,
    _require_exact_keys,
    _require_list,
    _require_non_empty_list,
    _require_str,
    build_user_message,
    load_system_prompt,
    parse_and_validate_output,
    validate_output_data,
    validate_output_file,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"
VALID_DATA = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ── helpers ──────────────────────────────────────────────────────────────────

def _valid():
    """Return a deep copy of the valid fixture data."""
    return copy.deepcopy(VALID_DATA)


# ── parse_and_validate_output ─────────────────────────────────────────────────

def test_parse_and_validate_output_accepts_valid_fixture():
    raw = FIXTURE_PATH.read_text(encoding="utf-8")

    result = parse_and_validate_output(raw)

    assert result["actions"]["items"][0]["priority"] == "low"
    assert result["implementation_plan"]["tech_tasks"][0]["complexity"] == "S"


def test_parse_and_validate_output_raises_for_invalid_json():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("not json at all {")


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


def test_validate_output_file_raises_for_missing_file(tmp_path):
    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(tmp_path / "nonexistent.json")


# ── load_system_prompt ────────────────────────────────────────────────────────

def test_load_system_prompt_returns_string(monkeypatch):
    monkeypatch.setattr(runtime_mod, "_system_prompt", None)
    result = load_system_prompt()
    assert isinstance(result, str)
    assert len(result) > 0


def test_load_system_prompt_caches_result(monkeypatch):
    monkeypatch.setattr(runtime_mod, "_system_prompt", None)
    first = load_system_prompt()
    second = load_system_prompt()
    assert first is second


def test_load_system_prompt_raises_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime_mod, "_system_prompt", None)
    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(tmp_path / "missing.txt")


# ── build_user_message ────────────────────────────────────────────────────────

def test_build_user_message_appends_delimiter():
    result = build_user_message("hello world")
    assert result == 'hello world\n"""'


# ── _require_dict ─────────────────────────────────────────────────────────────

def test_require_dict_passes_for_dict():
    assert _require_dict({"a": 1}, "$.x") == {"a": 1}


def test_require_dict_raises_for_non_dict():
    with pytest.raises(ValidationError, match=r"\$\.x must be an object"):
        _require_dict([1, 2], "$.x")


# ── _require_list ─────────────────────────────────────────────────────────────

def test_require_list_passes_for_list():
    assert _require_list([1, 2], "$.x") == [1, 2]


def test_require_list_raises_for_non_list():
    with pytest.raises(ValidationError, match=r"\$\.x must be an array"):
        _require_list("not a list", "$.x")


# ── _require_str ──────────────────────────────────────────────────────────────

def test_require_str_passes_for_str():
    _require_str("hello", "$.x")  # should not raise


def test_require_str_raises_for_non_str():
    with pytest.raises(ValidationError, match=r"\$\.x must be a string"):
        _require_str(42, "$.x")


# ── _require_exact_keys ───────────────────────────────────────────────────────

def test_require_exact_keys_passes_for_exact_match():
    _require_exact_keys({"a": 1, "b": 2}, ["a", "b"], "$.x")  # no raise


def test_require_exact_keys_raises_for_missing_key():
    with pytest.raises(ValidationError, match="missing="):
        _require_exact_keys({"a": 1}, ["a", "b"], "$.x")


def test_require_exact_keys_raises_for_extra_key():
    with pytest.raises(ValidationError, match="extra="):
        _require_exact_keys({"a": 1, "b": 2, "c": 3}, ["a", "b"], "$.x")


def test_require_exact_keys_raises_for_missing_and_extra():
    with pytest.raises(ValidationError, match="missing="):
        _require_exact_keys({"a": 1, "c": 3}, ["a", "b"], "$.x")


# ── _require_non_empty_list ───────────────────────────────────────────────────

def test_require_non_empty_list_passes_for_non_empty():
    assert _require_non_empty_list([1], "$.x") == [1]


def test_require_non_empty_list_raises_for_empty():
    with pytest.raises(ValidationError, match="must contain at least one item"):
        _require_non_empty_list([], "$.x")


def test_require_non_empty_list_raises_for_non_list():
    with pytest.raises(ValidationError, match="must be an array"):
        _require_non_empty_list("not a list", "$.x")


# ── _require_enum ─────────────────────────────────────────────────────────────

def test_require_enum_passes_for_valid_value():
    _require_enum("low", {"low", "medium", "high"}, "$.x")  # no raise


def test_require_enum_raises_for_invalid_value():
    with pytest.raises(ValidationError, match="must be one of"):
        _require_enum("critical", {"low", "medium", "high"}, "$.x")


def test_require_enum_raises_for_non_string():
    with pytest.raises(ValidationError, match="must be a string"):
        _require_enum(1, {"low", "medium", "high"}, "$.x")


# ── validate_output_data: root-level ─────────────────────────────────────────

def test_validate_output_data_raises_when_root_not_dict():
    with pytest.raises(ValidationError, match=r"\$ must be an object"):
        validate_output_data([1, 2, 3])


def test_validate_output_data_raises_for_extra_root_key():
    data = _valid()
    data["extra_key"] = "oops"
    with pytest.raises(ValidationError, match=r"\$ keys mismatch"):
        validate_output_data(data)


# ── validate_output_data: design_doc ─────────────────────────────────────────

def test_validate_output_data_raises_when_design_doc_not_dict():
    data = _valid()
    data["design_doc"] = "not a dict"
    with pytest.raises(ValidationError, match=r"\$\.design_doc must be an object"):
        validate_output_data(data)


def test_validate_output_data_raises_when_design_doc_field_not_string():
    data = _valid()
    data["design_doc"]["context_problem"] = 42
    with pytest.raises(ValidationError, match=r"\$\.design_doc\.context_problem must be a string"):
        validate_output_data(data)


# ── validate_output_data: pm_summary ─────────────────────────────────────────

def test_validate_output_data_raises_when_pm_summary_not_dict():
    data = _valid()
    data["pm_summary"] = []
    with pytest.raises(ValidationError, match=r"\$\.pm_summary must be an object"):
        validate_output_data(data)


def test_validate_output_data_raises_when_pm_summary_field_not_string():
    data = _valid()
    data["pm_summary"]["overview"] = 99
    with pytest.raises(ValidationError, match=r"\$\.pm_summary\.overview must be a string"):
        validate_output_data(data)


# ── validate_output_data: actions ────────────────────────────────────────────

def test_validate_output_data_raises_when_actions_items_empty():
    data = _valid()
    data["actions"]["items"] = []
    with pytest.raises(ValidationError, match=r"\$\.actions\.items must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_raises_when_action_item_not_dict():
    data = _valid()
    data["actions"]["items"] = ["not a dict"]
    with pytest.raises(ValidationError, match=r"must be an object"):
        validate_output_data(data)


def test_validate_output_data_raises_when_action_priority_invalid():
    data = _valid()
    data["actions"]["items"][0]["priority"] = "critical"
    with pytest.raises(ValidationError, match=r"\.priority must be one of"):
        validate_output_data(data)


def test_validate_output_data_raises_when_action_type_invalid():
    data = _valid()
    data["actions"]["items"][0]["type"] = "unknown"
    with pytest.raises(ValidationError, match=r"\.type must be one of"):
        validate_output_data(data)


# ── validate_output_data: implementation_plan ────────────────────────────────

def test_validate_output_data_raises_when_milestones_empty():
    data = _valid()
    data["implementation_plan"]["milestones"] = []
    with pytest.raises(ValidationError, match=r"milestones must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_raises_when_milestone_field_not_string():
    data = _valid()
    data["implementation_plan"]["milestones"][0]["name"] = 123
    with pytest.raises(ValidationError, match=r"milestones\[0\]\.name must be a string"):
        validate_output_data(data)


def test_validate_output_data_raises_when_tech_tasks_empty():
    data = _valid()
    data["implementation_plan"]["tech_tasks"] = []
    with pytest.raises(ValidationError, match=r"tech_tasks must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_raises_when_tech_task_area_invalid():
    data = _valid()
    data["implementation_plan"]["tech_tasks"][0]["area"] = "marketing"
    with pytest.raises(ValidationError, match=r"\.area must be one of"):
        validate_output_data(data)


def test_validate_output_data_raises_when_tech_task_complexity_invalid():
    data = _valid()
    data["implementation_plan"]["tech_tasks"][0]["complexity"] = "XL"
    with pytest.raises(ValidationError, match=r"\.complexity must be one of"):
        validate_output_data(data)


def test_validate_output_data_raises_when_tech_task_depends_on_not_string():
    data = _valid()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [42]
    with pytest.raises(ValidationError, match=r"depends_on\[0\] must be a string"):
        validate_output_data(data)


# ── validate_output_data: code_suggestions ───────────────────────────────────

def test_validate_output_data_raises_when_snippets_empty():
    data = _valid()
    data["code_suggestions"]["snippets"] = []
    with pytest.raises(ValidationError, match=r"snippets must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_raises_when_snippet_keys_mismatch():
    data = _valid()
    data["code_suggestions"]["snippets"][0] = {"title": "", "purpose": ""}
    with pytest.raises(ValidationError, match=r"snippets\[0\] keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_raises_when_snippet_field_not_string():
    data = _valid()
    data["code_suggestions"]["snippets"][0]["code"] = 0
    with pytest.raises(ValidationError, match=r"snippets\[0\]\.code must be a string"):
        validate_output_data(data)
