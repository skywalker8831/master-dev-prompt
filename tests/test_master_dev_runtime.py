import json
from pathlib import Path

import pytest

import master_dev_runtime
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


def _make_valid_data() -> dict:
    """Return a minimal but fully valid output data structure."""
    return {
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
        "actions": {
            "items": [
                {"description": "", "owner": "", "priority": "low", "type": "feature"}
            ]
        },
        "implementation_plan": {
            "overview": "",
            "milestones": [
                {"name": "", "description": "", "eta_guess": "", "risks": ""}
            ],
            "tech_tasks": [
                {
                    "area": "backend",
                    "description": "",
                    "depends_on": [],
                    "complexity": "S",
                }
            ],
        },
        "code_suggestions": {
            "language": "python",
            "stack_context": "",
            "snippets": [
                {"title": "", "purpose": "", "code": "print('ok')", "notes": ""}
            ],
        },
    }


# ── load_system_prompt ────────────────────────────────────────────────────────

def test_load_system_prompt_raises_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    missing = tmp_path / "no_such_prompt.txt"

    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(prompt_path=missing)


def test_load_system_prompt_returns_file_contents(tmp_path, monkeypatch):
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("system prompt text", encoding="utf-8")

    result = load_system_prompt(prompt_path=prompt_file)

    assert result == "system prompt text"


def test_load_system_prompt_caches_result(tmp_path, monkeypatch):
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("cached text", encoding="utf-8")

    first = load_system_prompt(prompt_path=prompt_file)
    # Delete the file – the second call must still succeed because the result is cached.
    prompt_file.unlink()
    second = load_system_prompt(prompt_path=prompt_file)

    assert first == second == "cached text"


# ── build_user_message ────────────────────────────────────────────────────────

def test_build_user_message_appends_closing_marker():
    result = build_user_message("hello transcript")

    assert result == 'hello transcript\n"""'


# ── _require_dict ─────────────────────────────────────────────────────────────

def test_require_dict_raises_for_non_dict():
    with pytest.raises(ValidationError, match=r"\$\.foo must be an object"):
        _require_dict("not a dict", "$.foo")


def test_require_dict_passes_for_dict():
    d = {"key": "value"}
    assert _require_dict(d, "$.foo") is d


# ── _require_list ─────────────────────────────────────────────────────────────

def test_require_list_raises_for_non_list():
    with pytest.raises(ValidationError, match=r"\$\.bar must be an array"):
        _require_list("not a list", "$.bar")


def test_require_list_passes_for_list():
    lst = [1, 2, 3]
    assert _require_list(lst, "$.bar") is lst


# ── _require_str ──────────────────────────────────────────────────────────────

def test_require_str_raises_for_non_str():
    with pytest.raises(ValidationError, match=r"\$\.baz must be a string"):
        _require_str(42, "$.baz")


def test_require_str_passes_for_str():
    _require_str("hello", "$.baz")  # no exception


# ── _require_exact_keys ───────────────────────────────────────────────────────

def test_require_exact_keys_raises_for_extra_keys():
    obj = {"a": 1, "b": 2, "c": 3}
    with pytest.raises(ValidationError, match=r"extra=\['c'\]"):
        _require_exact_keys(obj, ["a", "b"], "$.obj")


def test_require_exact_keys_raises_showing_both_missing_and_extra():
    obj = {"a": 1, "c": 3}
    with pytest.raises(ValidationError, match=r"missing=\['b'\].*extra=\['c'\]"):
        _require_exact_keys(obj, ["a", "b"], "$.obj")


# ── _require_non_empty_list ───────────────────────────────────────────────────

def test_require_non_empty_list_raises_for_empty_list():
    with pytest.raises(ValidationError, match=r"\$\.items must contain at least one item"):
        _require_non_empty_list([], "$.items")


# ── _require_enum ─────────────────────────────────────────────────────────────

def test_require_enum_raises_for_invalid_value():
    with pytest.raises(ValidationError, match=r"\$\.priority must be one of"):
        _require_enum("urgent", {"low", "medium", "high"}, "$.priority")


def test_require_enum_passes_for_valid_value():
    _require_enum("low", {"low", "medium", "high"}, "$.priority")  # no exception


# ── validate_output_data – depends_on items ──────────────────────────────────

def test_validate_output_data_accepts_non_empty_depends_on():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = ["task-1", "task-2"]

    result = validate_output_data(data)

    assert result["implementation_plan"]["tech_tasks"][0]["depends_on"] == ["task-1", "task-2"]


def test_validate_output_data_rejects_non_string_in_depends_on():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [123]

    with pytest.raises(ValidationError, match=r"depends_on\[0\] must be a string"):
        validate_output_data(data)


# ── parse_and_validate_output ─────────────────────────────────────────────────

def test_parse_and_validate_output_accepts_valid_fixture():
    raw = FIXTURE_PATH.read_text(encoding="utf-8")

    result = parse_and_validate_output(raw)

    assert result["actions"]["items"][0]["priority"] == "low"
    assert result["implementation_plan"]["tech_tasks"][0]["complexity"] == "S"


def test_parse_and_validate_output_raises_for_malformed_json():
    with pytest.raises(ValidationError, match=r"invalid JSON"):
        parse_and_validate_output("{not valid json")


def test_parse_and_validate_output_includes_location_in_error():
    with pytest.raises(ValidationError, match=r"line \d+"):
        parse_and_validate_output("{not valid json")


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
    missing = tmp_path / "no_such_file.json"

    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(missing)
