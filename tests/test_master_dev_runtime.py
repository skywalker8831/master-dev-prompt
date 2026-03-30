import json
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
    _require_dict,
    _require_list,
    _require_str,
    _require_exact_keys,
    _require_non_empty_list,
    _require_enum,
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

def test_load_system_prompt_raises_runtime_error_for_missing_file(tmp_path):
    missing = tmp_path / "nonexistent.txt"
    original = master_dev_runtime._system_prompt
    master_dev_runtime._system_prompt = None
    try:
        with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
            load_system_prompt(prompt_path=missing)
    finally:
        master_dev_runtime._system_prompt = original


def test_load_system_prompt_reads_and_caches_file(tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Hello prompt", encoding="utf-8")
    original = master_dev_runtime._system_prompt
    master_dev_runtime._system_prompt = None
    try:
        result = load_system_prompt(prompt_path=prompt_file)
        assert result == "Hello prompt"
        # Second call returns cached value (file can be deleted)
        prompt_file.unlink()
        result2 = load_system_prompt(prompt_path=prompt_file)
        assert result2 == "Hello prompt"
    finally:
        master_dev_runtime._system_prompt = original


# ── build_user_message ────────────────────────────────────────────────────────

def test_build_user_message_appends_closing_delimiter():
    result = build_user_message("My transcript")
    assert result == 'My transcript\n"""'


def test_build_user_message_empty_transcript():
    result = build_user_message("")
    assert result == '\n"""'


# ── _require_dict ─────────────────────────────────────────────────────────────

def test_require_dict_raises_for_non_dict():
    with pytest.raises(ValidationError, match=r"\$\.foo must be an object"):
        _require_dict("not a dict", "$.foo")


def test_require_dict_returns_dict():
    d = {"key": "value"}
    assert _require_dict(d, "$.foo") is d


# ── _require_list ─────────────────────────────────────────────────────────────

def test_require_list_raises_for_non_list():
    with pytest.raises(ValidationError, match=r"\$\.bar must be an array"):
        _require_list("not a list", "$.bar")


def test_require_list_returns_list():
    lst = [1, 2, 3]
    assert _require_list(lst, "$.bar") is lst


# ── _require_str ──────────────────────────────────────────────────────────────

def test_require_str_raises_for_non_string():
    with pytest.raises(ValidationError, match=r"\$\.baz must be a string"):
        _require_str(42, "$.baz")


def test_require_str_accepts_string():
    # Should not raise
    _require_str("hello", "$.baz")


# ── _require_exact_keys ───────────────────────────────────────────────────────

def test_require_exact_keys_raises_for_missing_keys():
    with pytest.raises(ValidationError, match=r"missing=\['b'\]"):
        _require_exact_keys({"a": 1}, ["a", "b"], "$.obj")


def test_require_exact_keys_raises_for_extra_keys():
    with pytest.raises(ValidationError, match=r"extra=\['c'\]"):
        _require_exact_keys({"a": 1, "b": 2, "c": 3}, ["a", "b"], "$.obj")


def test_require_exact_keys_raises_for_both_missing_and_extra():
    with pytest.raises(ValidationError) as exc_info:
        _require_exact_keys({"a": 1, "c": 3}, ["a", "b"], "$.obj")
    msg = str(exc_info.value)
    assert "missing=['b']" in msg
    assert "extra=['c']" in msg


def test_require_exact_keys_passes_for_exact_match():
    # Should not raise
    _require_exact_keys({"a": 1, "b": 2}, ["a", "b"], "$.obj")


# ── _require_non_empty_list ───────────────────────────────────────────────────

def test_require_non_empty_list_raises_for_empty_list():
    with pytest.raises(ValidationError, match=r"\$\.items must contain at least one item"):
        _require_non_empty_list([], "$.items")


def test_require_non_empty_list_raises_for_non_list():
    with pytest.raises(ValidationError, match=r"\$\.items must be an array"):
        _require_non_empty_list("not a list", "$.items")


def test_require_non_empty_list_returns_non_empty_list():
    lst = [1, 2]
    assert _require_non_empty_list(lst, "$.items") is lst


# ── _require_enum ─────────────────────────────────────────────────────────────

def test_require_enum_raises_for_invalid_value():
    with pytest.raises(ValidationError, match=r"must be one of"):
        _require_enum("ultra", {"low", "medium", "high"}, "$.priority")


def test_require_enum_raises_for_non_string():
    with pytest.raises(ValidationError, match=r"must be a string"):
        _require_enum(99, {"low", "medium", "high"}, "$.priority")


def test_require_enum_accepts_valid_value():
    # Should not raise
    _require_enum("high", {"low", "medium", "high"}, "$.priority")


# ── parse_and_validate_output ─────────────────────────────────────────────────

def test_parse_and_validate_output_rejects_invalid_json():
    with pytest.raises(ValidationError, match=r"invalid JSON"):
        parse_and_validate_output("not valid json {{{")


def test_parse_and_validate_output_rejects_non_object_json():
    with pytest.raises(ValidationError, match=r"\$ must be an object"):
        parse_and_validate_output("[1, 2, 3]")


# ── validate_output_file ──────────────────────────────────────────────────────

def test_validate_output_file_raises_for_missing_file(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(ValidationError, match=r"file not found"):
        validate_output_file(missing)


def test_validate_output_file_accepts_valid_fixture():
    result = validate_output_file(FIXTURE_PATH)
    assert "design_doc" in result


# ── validate_output_data: depends_on element validation ───────────────────────

def _make_valid_data():
    """Return a copy of the valid fixture data as a Python dict."""
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_validate_output_data_rejects_non_string_depends_on_element():
    data = _make_valid_data()
    # Inject a non-string element into the first tech_task's depends_on list
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [42]
    with pytest.raises(ValidationError, match=r"depends_on\[0\] must be a string"):
        validate_output_data(data)


def test_validate_output_data_accepts_empty_depends_on():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = []
    result = validate_output_data(data)
    assert result["implementation_plan"]["tech_tasks"][0]["depends_on"] == []


def test_validate_output_data_rejects_invalid_action_priority():
    data = _make_valid_data()
    data["actions"]["items"][0]["priority"] = "critical"
    with pytest.raises(ValidationError, match=r"priority must be one of"):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_action_type():
    data = _make_valid_data()
    data["actions"]["items"][0]["type"] = "unknown"
    with pytest.raises(ValidationError, match=r"type must be one of"):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_tech_task_area():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"][0]["area"] = "mobile"
    with pytest.raises(ValidationError, match=r"area must be one of"):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_tech_task_complexity():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"][0]["complexity"] = "XL"
    with pytest.raises(ValidationError, match=r"complexity must be one of"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_actions_items():
    data = _make_valid_data()
    data["actions"]["items"] = []
    with pytest.raises(ValidationError, match=r"actions.items must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_milestones():
    data = _make_valid_data()
    data["implementation_plan"]["milestones"] = []
    with pytest.raises(ValidationError, match=r"milestones must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_tech_tasks():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"] = []
    with pytest.raises(ValidationError, match=r"tech_tasks must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_snippets():
    data = _make_valid_data()
    data["code_suggestions"]["snippets"] = []
    with pytest.raises(ValidationError, match=r"snippets must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_extra_root_key():
    data = _make_valid_data()
    data["extra_field"] = "oops"
    with pytest.raises(ValidationError, match=r"\$ keys mismatch"):
        validate_output_data(data)
