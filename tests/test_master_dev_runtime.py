import copy
import json
from pathlib import Path

import pytest

import master_dev_runtime as runtime_module
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
    """Return a deep copy of the valid fixture data for safe mutation in tests."""
    return copy.deepcopy(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


# ── Existing tests ────────────────────────────────────────────────────────────

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


# ── build_user_message ────────────────────────────────────────────────────────

def test_build_user_message_appends_delimiter():
    result = build_user_message("my transcript")
    assert result == 'my transcript\n"""'


# ── load_system_prompt ────────────────────────────────────────────────────────

def test_load_system_prompt_loads_file_and_caches_result(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_module, "_system_prompt", None)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("hello world prompt")

    first = load_system_prompt(prompt_file)
    second = load_system_prompt(prompt_file)  # second call should use cache

    assert first == second == "hello world prompt"
    assert runtime_module._system_prompt == "hello world prompt"


def test_load_system_prompt_raises_if_file_missing(monkeypatch):
    monkeypatch.setattr(runtime_module, "_system_prompt", None)

    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(Path("/nonexistent/prompt.txt"))


# ── parse_and_validate_output ─────────────────────────────────────────────────

def test_parse_and_validate_output_raises_on_invalid_json():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("{not valid json}")


# ── validate_output_file ──────────────────────────────────────────────────────

def test_validate_output_file_raises_if_file_not_found():
    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(Path("/nonexistent/missing.json"))


# ── validate_output_data — root-level checks ──────────────────────────────────

def test_validate_output_data_raises_on_non_dict_root():
    with pytest.raises(ValidationError, match=r"\$ must be an object"):
        validate_output_data("not a dict")


def test_validate_output_data_raises_on_extra_root_key():
    data = _valid_data()
    data["unexpected_key"] = "value"

    with pytest.raises(ValidationError, match=r"extra=\['unexpected_key'\]"):
        validate_output_data(data)


def test_validate_output_data_raises_on_non_string_design_doc_field():
    data = _valid_data()
    data["design_doc"]["context_problem"] = 42

    with pytest.raises(ValidationError, match=r"must be a string"):
        validate_output_data(data)


# ── validate_output_data — actions checks ────────────────────────────────────

def test_validate_output_data_raises_on_non_list_action_items():
    data = _valid_data()
    data["actions"]["items"] = "not a list"

    with pytest.raises(ValidationError, match=r"must be an array"):
        validate_output_data(data)


def test_validate_output_data_raises_on_empty_action_items():
    data = _valid_data()
    data["actions"]["items"] = []

    with pytest.raises(ValidationError, match=r"must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_raises_on_invalid_priority():
    data = _valid_data()
    data["actions"]["items"][0]["priority"] = "critical"

    with pytest.raises(ValidationError, match=r"must be one of"):
        validate_output_data(data)


def test_validate_output_data_raises_on_invalid_action_type():
    data = _valid_data()
    data["actions"]["items"][0]["type"] = "unknown_type"

    with pytest.raises(ValidationError, match=r"must be one of"):
        validate_output_data(data)


# ── validate_output_data — implementation_plan checks ────────────────────────

def test_validate_output_data_raises_on_invalid_area():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["area"] = "mobile"

    with pytest.raises(ValidationError, match=r"must be one of"):
        validate_output_data(data)


def test_validate_output_data_raises_on_invalid_complexity():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["complexity"] = "XL"

    with pytest.raises(ValidationError, match=r"must be one of"):
        validate_output_data(data)


def test_validate_output_data_raises_on_non_string_depends_on_item():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [123]

    with pytest.raises(ValidationError, match=r"must be a string"):
        validate_output_data(data)
