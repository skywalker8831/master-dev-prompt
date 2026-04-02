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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _valid_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ── load_system_prompt ────────────────────────────────────────────────────────

def test_load_system_prompt_raises_when_file_missing(tmp_path):
    missing = tmp_path / "no_such_prompt.txt"
    original = runtime._system_prompt
    runtime._system_prompt = None
    try:
        with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
            load_system_prompt(prompt_path=missing)
    finally:
        runtime._system_prompt = original


def test_load_system_prompt_returns_cached_value(tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("hello prompt", encoding="utf-8")

    # Reset cache so we can test a fresh load then caching.
    original = runtime._system_prompt
    runtime._system_prompt = None
    try:
        first = load_system_prompt(prompt_path=prompt_file)
        assert first == "hello prompt"
        # Overwrite the file; cached value should still be returned.
        prompt_file.write_text("changed", encoding="utf-8")
        second = load_system_prompt(prompt_path=prompt_file)
        assert second == "hello prompt"
    finally:
        runtime._system_prompt = original


# ── build_user_message ────────────────────────────────────────────────────────

def test_build_user_message_appends_triple_quote():
    msg = build_user_message("my transcript")
    assert msg == 'my transcript\n"""'


# ── parse_and_validate_output ─────────────────────────────────────────────────

def test_parse_and_validate_output_accepts_valid_fixture():
    raw = FIXTURE_PATH.read_text(encoding="utf-8")

    result = parse_and_validate_output(raw)

    assert result["actions"]["items"][0]["priority"] == "low"
    assert result["implementation_plan"]["tech_tasks"][0]["complexity"] == "S"


def test_parse_and_validate_output_raises_for_invalid_json():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("not json at all {{{")


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


def test_validate_output_file_raises_when_file_not_found(tmp_path):
    missing = tmp_path / "ghost.json"
    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(missing)


# ── validate_output_data — root-level checks ──────────────────────────────────

def test_validate_output_data_raises_when_root_not_dict():
    with pytest.raises(ValidationError, match=r"\$ must be an object"):
        validate_output_data(["not", "a", "dict"])


def test_validate_output_data_raises_when_root_has_extra_key():
    payload = _valid_payload()
    payload["unexpected"] = "value"
    with pytest.raises(ValidationError, match=r"\$ keys mismatch"):
        validate_output_data(payload)


def test_validate_output_data_raises_when_root_missing_key():
    payload = _valid_payload()
    del payload["code_suggestions"]
    with pytest.raises(ValidationError, match=r"\$ keys mismatch"):
        validate_output_data(payload)


# ── validate_output_data — design_doc ────────────────────────────────────────

def test_validate_output_data_raises_when_design_doc_field_not_string():
    payload = _valid_payload()
    payload["design_doc"]["context_problem"] = 42
    with pytest.raises(ValidationError, match=r"\$\.design_doc\.context_problem must be a string"):
        validate_output_data(payload)


# ── validate_output_data — pm_summary ────────────────────────────────────────

def test_validate_output_data_raises_when_pm_summary_field_not_string():
    payload = _valid_payload()
    payload["pm_summary"]["overview"] = None
    with pytest.raises(ValidationError, match=r"\$\.pm_summary\.overview must be a string"):
        validate_output_data(payload)


# ── validate_output_data — actions ───────────────────────────────────────────

def test_validate_output_data_raises_when_actions_items_empty():
    payload = _valid_payload()
    payload["actions"]["items"] = []
    with pytest.raises(ValidationError, match=r"\$\.actions\.items must contain at least one item"):
        validate_output_data(payload)


def test_validate_output_data_raises_when_action_item_priority_invalid():
    payload = _valid_payload()
    payload["actions"]["items"][0]["priority"] = "urgent"
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\]\.priority must be one of"):
        validate_output_data(payload)


def test_validate_output_data_raises_when_action_item_type_invalid():
    payload = _valid_payload()
    payload["actions"]["items"][0]["type"] = "unknown"
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\]\.type must be one of"):
        validate_output_data(payload)


# ── validate_output_data — implementation_plan ───────────────────────────────

def test_validate_output_data_raises_when_milestones_empty():
    payload = _valid_payload()
    payload["implementation_plan"]["milestones"] = []
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.milestones must contain at least one item"):
        validate_output_data(payload)


def test_validate_output_data_raises_when_tech_tasks_empty():
    payload = _valid_payload()
    payload["implementation_plan"]["tech_tasks"] = []
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks must contain at least one item"):
        validate_output_data(payload)


def test_validate_output_data_raises_when_tech_task_area_invalid():
    payload = _valid_payload()
    payload["implementation_plan"]["tech_tasks"][0]["area"] = "marketing"
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.area must be one of"):
        validate_output_data(payload)


def test_validate_output_data_raises_when_tech_task_complexity_invalid():
    payload = _valid_payload()
    payload["implementation_plan"]["tech_tasks"][0]["complexity"] = "XL"
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.complexity must be one of"):
        validate_output_data(payload)


def test_validate_output_data_raises_when_tech_task_depends_on_item_not_string():
    payload = _valid_payload()
    payload["implementation_plan"]["tech_tasks"][0]["depends_on"] = [123]
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.depends_on\[0\] must be a string"):
        validate_output_data(payload)


def test_validate_output_data_raises_when_tech_task_depends_on_not_a_list():
    payload = _valid_payload()
    payload["implementation_plan"]["tech_tasks"][0]["depends_on"] = "not-a-list"
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.depends_on must be an array"):
        validate_output_data(payload)


# ── validate_output_data — code_suggestions ──────────────────────────────────

def test_validate_output_data_raises_when_snippets_empty():
    payload = _valid_payload()
    payload["code_suggestions"]["snippets"] = []
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets must contain at least one item"):
        validate_output_data(payload)


def test_validate_output_data_raises_when_snippet_field_not_string():
    payload = _valid_payload()
    payload["code_suggestions"]["snippets"][0]["title"] = 99
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets\[0\]\.title must be a string"):
        validate_output_data(payload)


# ── _require_exact_keys — extra-only path ────────────────────────────────────

def test_validate_output_data_raises_with_extra_only_key_in_design_doc():
    payload = _valid_payload()
    payload["design_doc"]["bonus_field"] = "surprise"
    with pytest.raises(ValidationError, match=r"extra=\['bonus_field'\]"):
        validate_output_data(payload)
