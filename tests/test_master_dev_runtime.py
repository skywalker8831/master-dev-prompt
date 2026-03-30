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
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def _valid_data() -> dict:
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


# ── load_system_prompt ────────────────────────────────────────────────────────

def test_load_system_prompt_raises_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    missing = tmp_path / "nonexistent.txt"

    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(missing)


def test_load_system_prompt_reads_from_custom_path(tmp_path, monkeypatch):
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("my custom prompt", encoding="utf-8")

    result = load_system_prompt(prompt_file)

    assert result == "my custom prompt"


# ── build_user_message ────────────────────────────────────────────────────────

def test_build_user_message_appends_delimiter():
    result = build_user_message("transcript text")

    assert result == 'transcript text\n"""'


# ── primitive validators ──────────────────────────────────────────────────────

def test_validate_output_data_rejects_non_dict_design_doc():
    data = _valid_data()
    data["design_doc"] = "not a dict"

    with pytest.raises(ValidationError, match=r"\$\.design_doc must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_list_action_items():
    data = _valid_data()
    data["actions"]["items"] = "not a list"

    with pytest.raises(ValidationError, match=r"\$\.actions\.items must be an array"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_string_design_doc_field():
    data = _valid_data()
    data["design_doc"]["context_problem"] = 42

    with pytest.raises(ValidationError, match=r"\$\.design_doc\.context_problem must be a string"):
        validate_output_data(data)


def test_validate_output_data_reports_extra_keys_in_mismatch():
    data = _valid_data()
    data["design_doc"]["extra_key"] = "oops"

    with pytest.raises(ValidationError, match=r"extra=\['extra_key'\]"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_action_items():
    data = _valid_data()
    data["actions"]["items"] = []

    with pytest.raises(ValidationError, match=r"\$\.actions\.items must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_priority_enum():
    data = _valid_data()
    data["actions"]["items"][0]["priority"] = "urgent"

    with pytest.raises(ValidationError, match=r"must be one of"):
        validate_output_data(data)


# ── parse_and_validate_output ─────────────────────────────────────────────────

def test_parse_and_validate_output_rejects_malformed_json():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("{ not valid json }")


# ── validate_output_file ──────────────────────────────────────────────────────

def test_validate_output_file_raises_for_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.json"

    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(missing)


# ── tech_tasks depends_on element validation ──────────────────────────────────

def test_validate_output_data_rejects_non_string_depends_on_entry():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [123]

    with pytest.raises(ValidationError, match=r"depends_on\[0\] must be a string"):
        validate_output_data(data)
