import json
from pathlib import Path

import pytest

from master_dev_runtime import (
    ACTION_TYPE,
    AREA,
    COMPLEXITY,
    PRIORITY,
    ValidationError,
    parse_and_validate_output,
    validate_output_data,
    validate_output_file,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


def _load_valid() -> dict:
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


# ── Missing / extra top-level keys ───────────────────────────────────────────

def test_rejects_missing_top_level_key():
    data = _load_valid()
    del data["design_doc"]
    with pytest.raises(ValidationError, match="design_doc"):
        validate_output_data(data)


def test_rejects_extra_top_level_key():
    data = _load_valid()
    data["unexpected_key"] = "value"
    with pytest.raises(ValidationError, match="keys mismatch"):
        validate_output_data(data)


# ── Empty list rejections ─────────────────────────────────────────────────────

def test_rejects_empty_actions_items():
    data = _load_valid()
    data["actions"]["items"] = []
    with pytest.raises(ValidationError, match=r"actions\.items"):
        validate_output_data(data)


def test_rejects_empty_milestones():
    data = _load_valid()
    data["implementation_plan"]["milestones"] = []
    with pytest.raises(ValidationError, match="milestones"):
        validate_output_data(data)


def test_rejects_empty_tech_tasks():
    data = _load_valid()
    data["implementation_plan"]["tech_tasks"] = []
    with pytest.raises(ValidationError, match="tech_tasks"):
        validate_output_data(data)


def test_rejects_empty_snippets():
    data = _load_valid()
    data["code_suggestions"]["snippets"] = []
    with pytest.raises(ValidationError, match="snippets"):
        validate_output_data(data)


# ── Enum validation ───────────────────────────────────────────────────────────

def test_rejects_invalid_priority():
    data = _load_valid()
    data["actions"]["items"][0]["priority"] = "urgent"
    with pytest.raises(ValidationError, match="priority"):
        validate_output_data(data)


def test_rejects_invalid_action_type():
    data = _load_valid()
    data["actions"]["items"][0]["type"] = "unknown"
    with pytest.raises(ValidationError, match="type"):
        validate_output_data(data)


def test_rejects_invalid_area():
    data = _load_valid()
    data["implementation_plan"]["tech_tasks"][0]["area"] = "mobile"
    with pytest.raises(ValidationError, match="area"):
        validate_output_data(data)


def test_rejects_invalid_complexity():
    data = _load_valid()
    data["implementation_plan"]["tech_tasks"][0]["complexity"] = "XL"
    with pytest.raises(ValidationError, match="complexity"):
        validate_output_data(data)


@pytest.mark.parametrize("priority", sorted(PRIORITY))
def test_all_valid_priorities_accepted(priority):
    data = _load_valid()
    data["actions"]["items"][0]["priority"] = priority
    validate_output_data(data)  # should not raise


@pytest.mark.parametrize("action_type", sorted(ACTION_TYPE))
def test_all_valid_action_types_accepted(action_type):
    data = _load_valid()
    data["actions"]["items"][0]["type"] = action_type
    validate_output_data(data)  # should not raise


@pytest.mark.parametrize("area", sorted(AREA))
def test_all_valid_areas_accepted(area):
    data = _load_valid()
    data["implementation_plan"]["tech_tasks"][0]["area"] = area
    validate_output_data(data)  # should not raise


@pytest.mark.parametrize("complexity", sorted(COMPLEXITY))
def test_all_valid_complexities_accepted(complexity):
    data = _load_valid()
    data["implementation_plan"]["tech_tasks"][0]["complexity"] = complexity
    validate_output_data(data)  # should not raise


# ── Type validation ───────────────────────────────────────────────────────────

def test_rejects_non_string_design_doc_field():
    data = _load_valid()
    data["design_doc"]["context_problem"] = 42
    with pytest.raises(ValidationError, match="context_problem"):
        validate_output_data(data)


def test_rejects_non_dict_root():
    with pytest.raises(ValidationError, match=r"\$"):
        validate_output_data(["not", "a", "dict"])


# ── File handling ─────────────────────────────────────────────────────────────

def test_validate_output_file_missing_file(tmp_path):
    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(tmp_path / "nonexistent.json")


def test_validate_output_file_invalid_json(tmp_path):
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("not valid json", encoding="utf-8")
    with pytest.raises(ValidationError, match="invalid JSON"):
        validate_output_file(bad_path)


# ── depends_on list items ─────────────────────────────────────────────────────

def test_rejects_non_string_in_depends_on():
    data = _load_valid()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [123]
    with pytest.raises(ValidationError, match="depends_on"):
        validate_output_data(data)
