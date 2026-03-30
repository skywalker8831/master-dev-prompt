import json
from pathlib import Path

import pytest

import master_dev_runtime as _runtime_module
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


# ── load_system_prompt ────────────────────────────────────────────────────────

def test_load_system_prompt_raises_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(_runtime_module, "_system_prompt", None)
    missing = tmp_path / "nonexistent_prompt.txt"

    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(prompt_path=missing)


def test_load_system_prompt_returns_cached_value_on_second_call(tmp_path, monkeypatch):
    monkeypatch.setattr(_runtime_module, "_system_prompt", None)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("my system prompt", encoding="utf-8")

    first = load_system_prompt(prompt_path=prompt_file)
    # Overwrite file — second call should still return cached value
    prompt_file.write_text("changed content", encoding="utf-8")
    second = load_system_prompt(prompt_path=prompt_file)

    assert first == "my system prompt"
    assert second == "my system prompt"


# ── build_user_message ────────────────────────────────────────────────────────

def test_build_user_message_appends_triple_quote():
    result = build_user_message("hello transcript")

    assert result == 'hello transcript\n"""'


# ── _require_dict ─────────────────────────────────────────────────────────────

def test_require_dict_raises_on_non_dict():
    with pytest.raises(ValidationError, match=r"\$\.foo must be an object"):
        _require_dict("not a dict", "$.foo")


def test_require_dict_returns_dict_unchanged():
    d = {"key": "value"}
    assert _require_dict(d, "$.foo") is d


# ── _require_list ─────────────────────────────────────────────────────────────

def test_require_list_raises_on_non_list():
    with pytest.raises(ValidationError, match=r"\$\.bar must be an array"):
        _require_list("not a list", "$.bar")


def test_require_list_returns_list_unchanged():
    lst = [1, 2, 3]
    assert _require_list(lst, "$.bar") is lst


# ── _require_str ──────────────────────────────────────────────────────────────

def test_require_str_raises_on_non_string():
    with pytest.raises(ValidationError, match=r"\$\.baz must be a string"):
        _require_str(42, "$.baz")


def test_require_str_accepts_empty_string():
    _require_str("", "$.baz")  # should not raise


# ── _require_exact_keys ───────────────────────────────────────────────────────

def test_require_exact_keys_raises_for_extra_keys_only():
    with pytest.raises(ValidationError, match=r"extra=\['extra'\]"):
        _require_exact_keys({"a": 1, "extra": 2}, ["a"], "$.obj")


def test_require_exact_keys_raises_for_missing_and_extra_keys():
    with pytest.raises(ValidationError, match=r"missing=\['b'\].*extra=\['x'\]"):
        _require_exact_keys({"a": 1, "x": 2}, ["a", "b"], "$.obj")


def test_require_exact_keys_passes_for_exact_match():
    _require_exact_keys({"a": 1, "b": 2}, ["a", "b"], "$.obj")  # should not raise


# ── _require_non_empty_list ───────────────────────────────────────────────────

def test_require_non_empty_list_raises_on_empty():
    with pytest.raises(ValidationError, match="must contain at least one item"):
        _require_non_empty_list([], "$.items")


def test_require_non_empty_list_raises_on_non_list():
    with pytest.raises(ValidationError, match="must be an array"):
        _require_non_empty_list("not a list", "$.items")


def test_require_non_empty_list_returns_items():
    result = _require_non_empty_list([1, 2], "$.items")
    assert result == [1, 2]


# ── _require_enum ─────────────────────────────────────────────────────────────

def test_require_enum_raises_on_invalid_value():
    with pytest.raises(ValidationError, match="must be one of"):
        _require_enum("invalid", {"low", "medium", "high"}, "$.priority")


def test_require_enum_raises_on_non_string():
    with pytest.raises(ValidationError, match="must be a string"):
        _require_enum(42, {"low", "medium"}, "$.priority")


def test_require_enum_passes_for_valid_value():
    _require_enum("low", {"low", "medium", "high"}, "$.priority")  # should not raise


# ── parse_and_validate_output ─────────────────────────────────────────────────

def test_parse_and_validate_output_raises_on_invalid_json():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("{ not valid json }")


def test_parse_and_validate_output_raises_on_non_object_root():
    with pytest.raises(ValidationError, match=r"\$ must be an object"):
        parse_and_validate_output(json.dumps([1, 2, 3]))


# ── validate_output_file ──────────────────────────────────────────────────────

def test_validate_output_file_raises_when_file_missing(tmp_path):
    missing = tmp_path / "does_not_exist.json"

    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(missing)


# ── validate_output_data — depends_on entries ─────────────────────────────────

def test_validate_output_data_rejects_non_string_depends_on_entry():
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [42]

    with pytest.raises(ValidationError, match=r"depends_on\[0\] must be a string"):
        validate_output_data(data)


def test_validate_output_data_accepts_depends_on_with_string_entries():
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = ["task-1", "task-2"]

    result = validate_output_data(data)

    assert result["implementation_plan"]["tech_tasks"][0]["depends_on"] == ["task-1", "task-2"]
