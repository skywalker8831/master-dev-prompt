import json
from pathlib import Path

import pytest

import master_dev_runtime as _rt
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


def _valid_data() -> dict:
    """Return a deep copy of the valid fixture so each test can mutate it freely."""
    return json.loads(json.dumps(VALID_DATA))


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


# ── load_system_prompt ────────────────────────────────────────────────────────

def test_load_system_prompt_returns_non_empty_string(tmp_path, monkeypatch):
    monkeypatch.setattr(_rt, "_system_prompt", None)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("system instructions", encoding="utf-8")

    result = load_system_prompt(prompt_file)

    assert result == "system instructions"


def test_load_system_prompt_caches_on_second_call(tmp_path, monkeypatch):
    monkeypatch.setattr(_rt, "_system_prompt", None)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("cached prompt", encoding="utf-8")

    first = load_system_prompt(prompt_file)
    # Overwrite the file — the cached value should still be returned
    prompt_file.write_text("different content", encoding="utf-8")
    second = load_system_prompt(prompt_file)

    assert first == second == "cached prompt"


def test_load_system_prompt_raises_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(_rt, "_system_prompt", None)
    missing = tmp_path / "no_such_prompt.txt"

    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(missing)


# ── build_user_message ────────────────────────────────────────────────────────

def test_build_user_message_appends_triple_quote():
    result = build_user_message("transcript text")
    assert result == 'transcript text\n"""'


def test_build_user_message_preserves_transcript():
    transcript = "line one\nline two"
    result = build_user_message(transcript)
    assert result.startswith(transcript)


# ── parse_and_validate_output: invalid JSON ───────────────────────────────────

def test_parse_and_validate_output_raises_on_invalid_json():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("{not valid json")


def test_parse_and_validate_output_raises_on_empty_string():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("")


# ── validate_output_file: file not found ─────────────────────────────────────

def test_validate_output_file_raises_when_file_missing(tmp_path):
    missing = tmp_path / "ghost.json"
    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(missing)


def test_validate_output_file_accepts_valid_fixture():
    result = validate_output_file(FIXTURE_PATH)
    assert result["code_suggestions"]["language"] == "python"


# ── validate_output_data: root-level checks ───────────────────────────────────

def test_validate_output_data_raises_when_root_is_not_dict():
    with pytest.raises(ValidationError, match=r"\$ must be an object"):
        validate_output_data(["a", "list"])


def test_validate_output_data_raises_on_missing_root_key():
    data = _valid_data()
    del data["code_suggestions"]
    with pytest.raises(ValidationError, match=r"\$ keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_raises_on_extra_root_key():
    data = _valid_data()
    data["unexpected"] = "value"
    with pytest.raises(ValidationError, match=r"\$ keys mismatch"):
        validate_output_data(data)


# ── validate_output_data: design_doc ─────────────────────────────────────────

def test_validate_output_data_raises_when_design_doc_not_dict():
    data = _valid_data()
    data["design_doc"] = "a string"
    with pytest.raises(ValidationError, match=r"\$\.design_doc must be an object"):
        validate_output_data(data)


def test_validate_output_data_raises_when_design_doc_field_not_string():
    data = _valid_data()
    data["design_doc"]["context_problem"] = 42
    with pytest.raises(ValidationError, match=r"\$\.design_doc\.context_problem must be a string"):
        validate_output_data(data)


def test_validate_output_data_raises_when_design_doc_has_extra_key():
    data = _valid_data()
    data["design_doc"]["extra_field"] = "oops"
    with pytest.raises(ValidationError, match=r"\$\.design_doc keys mismatch"):
        validate_output_data(data)


# ── validate_output_data: pm_summary ─────────────────────────────────────────

def test_validate_output_data_raises_when_pm_summary_field_not_string():
    data = _valid_data()
    data["pm_summary"]["overview"] = None
    with pytest.raises(ValidationError, match=r"\$\.pm_summary\.overview must be a string"):
        validate_output_data(data)


def test_validate_output_data_raises_when_pm_summary_has_missing_key():
    data = _valid_data()
    del data["pm_summary"]["scope"]
    with pytest.raises(ValidationError, match=r"\$\.pm_summary keys mismatch"):
        validate_output_data(data)


# ── validate_output_data: actions ────────────────────────────────────────────

def test_validate_output_data_raises_when_actions_items_empty():
    data = _valid_data()
    data["actions"]["items"] = []
    with pytest.raises(ValidationError, match=r"\$\.actions\.items must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_raises_when_action_item_not_dict():
    data = _valid_data()
    data["actions"]["items"] = ["not a dict"]
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\] must be an object"):
        validate_output_data(data)


def test_validate_output_data_raises_on_invalid_priority_enum():
    data = _valid_data()
    data["actions"]["items"][0]["priority"] = "urgent"
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\]\.priority"):
        validate_output_data(data)


def test_validate_output_data_raises_on_invalid_type_enum():
    data = _valid_data()
    data["actions"]["items"][0]["type"] = "unknown-type"
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\]\.type"):
        validate_output_data(data)


def test_validate_output_data_raises_when_action_description_not_string():
    data = _valid_data()
    data["actions"]["items"][0]["description"] = 99
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\]\.description must be a string"):
        validate_output_data(data)


def test_validate_output_data_accepts_all_valid_priorities():
    for priority in ("low", "medium", "high"):
        data = _valid_data()
        data["actions"]["items"][0]["priority"] = priority
        result = validate_output_data(data)
        assert result["actions"]["items"][0]["priority"] == priority


def test_validate_output_data_accepts_all_valid_action_types():
    for action_type in ("feature", "bug", "infra", "research", "decision", "follow-up"):
        data = _valid_data()
        data["actions"]["items"][0]["type"] = action_type
        result = validate_output_data(data)
        assert result["actions"]["items"][0]["type"] == action_type


# ── validate_output_data: implementation_plan ────────────────────────────────

def test_validate_output_data_raises_when_milestones_empty():
    data = _valid_data()
    data["implementation_plan"]["milestones"] = []
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.milestones must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_raises_when_milestone_missing_key():
    data = _valid_data()
    del data["implementation_plan"]["milestones"][0]["risks"]
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.milestones\[0\] keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_raises_when_milestone_field_not_string():
    data = _valid_data()
    data["implementation_plan"]["milestones"][0]["eta_guess"] = 123
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.milestones\[0\]\.eta_guess must be a string"):
        validate_output_data(data)


def test_validate_output_data_raises_when_tech_tasks_empty():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"] = []
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_raises_on_invalid_area_enum():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["area"] = "mobile"
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.area"):
        validate_output_data(data)


def test_validate_output_data_raises_on_invalid_complexity_enum():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["complexity"] = "XL"
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.complexity"):
        validate_output_data(data)


def test_validate_output_data_raises_when_tech_task_missing_key():
    data = _valid_data()
    del data["implementation_plan"]["tech_tasks"][0]["depends_on"]
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\] keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_raises_when_depends_on_not_list():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = "some-task"
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.depends_on must be an array"):
        validate_output_data(data)


def test_validate_output_data_raises_when_depends_on_item_not_string():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [42]
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.depends_on\[0\] must be a string"):
        validate_output_data(data)


def test_validate_output_data_accepts_all_valid_areas():
    for area in ("backend", "frontend", "infra", "data", "devops", "testing"):
        data = _valid_data()
        data["implementation_plan"]["tech_tasks"][0]["area"] = area
        result = validate_output_data(data)
        assert result["implementation_plan"]["tech_tasks"][0]["area"] == area


def test_validate_output_data_accepts_all_valid_complexities():
    for complexity in ("S", "M", "L"):
        data = _valid_data()
        data["implementation_plan"]["tech_tasks"][0]["complexity"] = complexity
        result = validate_output_data(data)
        assert result["implementation_plan"]["tech_tasks"][0]["complexity"] == complexity


def test_validate_output_data_accepts_multiple_depends_on_strings():
    data = _valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = ["task-a", "task-b"]
    result = validate_output_data(data)
    assert result["implementation_plan"]["tech_tasks"][0]["depends_on"] == ["task-a", "task-b"]


# ── validate_output_data: code_suggestions ───────────────────────────────────

def test_validate_output_data_raises_when_snippets_empty():
    data = _valid_data()
    data["code_suggestions"]["snippets"] = []
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_raises_when_snippet_missing_key():
    data = _valid_data()
    del data["code_suggestions"]["snippets"][0]["notes"]
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets\[0\] keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_raises_when_snippet_field_not_string():
    data = _valid_data()
    data["code_suggestions"]["snippets"][0]["code"] = []
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets\[0\]\.code must be a string"):
        validate_output_data(data)


def test_validate_output_data_raises_when_language_not_string():
    data = _valid_data()
    data["code_suggestions"]["language"] = True
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.language must be a string"):
        validate_output_data(data)
