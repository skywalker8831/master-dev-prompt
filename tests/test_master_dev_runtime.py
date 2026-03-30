import json
from pathlib import Path

import pytest

import master_dev_runtime
from master_dev_runtime import (
    ACTION_TYPE,
    AREA,
    COMPLEXITY,
    PRIORITY,
    ValidationError,
    build_user_message,
    load_system_prompt,
    parse_and_validate_output,
    validate_output_data,
    validate_output_file,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"


@pytest.fixture(autouse=True)
def reset_system_prompt_cache():
    """Reset the cached system prompt before and after each test."""
    original = master_dev_runtime._system_prompt
    yield
    master_dev_runtime._system_prompt = original


# ── Test fixtures and valid output ────────────────────────────────────────────

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


# ── Test load_system_prompt ───────────────────────────────────────────────────

def test_load_system_prompt_returns_string():
    # Reset the cached prompt to ensure fresh load
    master_dev_runtime._system_prompt = None
    
    prompt = load_system_prompt()
    
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_load_system_prompt_caches_result():
    # Reset the cached prompt
    master_dev_runtime._system_prompt = None
    
    prompt1 = load_system_prompt()
    prompt2 = load_system_prompt()
    
    assert prompt1 is prompt2


def test_load_system_prompt_raises_for_missing_file(tmp_path):
    # Reset cache to ensure it checks the file path
    master_dev_runtime._system_prompt = None
    missing_path = tmp_path / "nonexistent.txt"
    
    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        load_system_prompt(prompt_path=missing_path)


def test_load_system_prompt_loads_custom_path(tmp_path):
    custom_prompt = tmp_path / "custom_prompt.txt"
    custom_prompt.write_text("Custom prompt content")
    # Reset the cache before testing custom path
    master_dev_runtime._system_prompt = None
    
    # Note: load_system_prompt uses global cache, so custom path loading 
    # won't use the cache in this test context
    result = load_system_prompt(prompt_path=custom_prompt)
    
    assert result == "Custom prompt content"


# ── Test build_user_message ───────────────────────────────────────────────────

def test_build_user_message_formats_transcript():
    transcript = "Sample meeting transcript"
    
    result = build_user_message(transcript)
    
    assert result == 'Sample meeting transcript\n"""'


def test_build_user_message_handles_empty_transcript():
    result = build_user_message("")
    
    assert result == '\n"""'


def test_build_user_message_handles_multiline_transcript():
    transcript = "Line 1\nLine 2\nLine 3"
    
    result = build_user_message(transcript)
    
    assert result == 'Line 1\nLine 2\nLine 3\n"""'


# ── Test validate_output_file ─────────────────────────────────────────────────

def test_validate_output_file_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "nonexistent.json"
    
    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(missing_path)


def test_validate_output_file_accepts_valid_file(tmp_path):
    valid_data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    valid_path = tmp_path / "valid.json"
    valid_path.write_text(json.dumps(valid_data), encoding="utf-8")
    
    result = validate_output_file(valid_path)
    
    assert result["design_doc"]["context_problem"] == ""


# ── Test parse_and_validate_output ────────────────────────────────────────────

def test_parse_and_validate_output_rejects_invalid_json():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("{ invalid json }")


def test_parse_and_validate_output_reports_json_error_location():
    with pytest.raises(ValidationError, match=r"line \d+, column \d+"):
        parse_and_validate_output('{"key": }')


# ── Test root-level schema validation ─────────────────────────────────────────

def test_validate_output_data_rejects_non_dict_root():
    with pytest.raises(ValidationError, match=r"\$ must be an object"):
        validate_output_data([])


def test_validate_output_data_rejects_missing_root_keys():
    with pytest.raises(ValidationError, match=r"\$ keys mismatch"):
        validate_output_data({"design_doc": {}})


def test_validate_output_data_rejects_extra_root_keys():
    valid_data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    valid_data["extra_key"] = "value"
    
    with pytest.raises(ValidationError, match=r"\$ keys mismatch.*extra="):
        validate_output_data(valid_data)


# ── Test design_doc validation ────────────────────────────────────────────────

def test_validate_output_data_rejects_non_dict_design_doc():
    data = _make_valid_data()
    data["design_doc"] = "not a dict"
    
    with pytest.raises(ValidationError, match=r"\$\.design_doc must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_missing_design_doc_keys():
    data = _make_valid_data()
    data["design_doc"] = {"context_problem": ""}
    
    with pytest.raises(ValidationError, match=r"\$\.design_doc keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_string_design_doc_field():
    data = _make_valid_data()
    data["design_doc"]["context_problem"] = 123
    
    with pytest.raises(ValidationError, match=r"\$\.design_doc\.context_problem must be a string"):
        validate_output_data(data)


# ── Test pm_summary validation ────────────────────────────────────────────────

def test_validate_output_data_rejects_non_dict_pm_summary():
    data = _make_valid_data()
    data["pm_summary"] = []
    
    with pytest.raises(ValidationError, match=r"\$\.pm_summary must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_missing_pm_summary_keys():
    data = _make_valid_data()
    data["pm_summary"] = {"overview": ""}
    
    with pytest.raises(ValidationError, match=r"\$\.pm_summary keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_string_pm_summary_field():
    data = _make_valid_data()
    data["pm_summary"]["scope"] = None
    
    with pytest.raises(ValidationError, match=r"\$\.pm_summary\.scope must be a string"):
        validate_output_data(data)


# ── Test actions validation ───────────────────────────────────────────────────

def test_validate_output_data_rejects_non_dict_actions():
    data = _make_valid_data()
    data["actions"] = "not a dict"
    
    with pytest.raises(ValidationError, match=r"\$\.actions must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_actions_items():
    data = _make_valid_data()
    data["actions"]["items"] = []
    
    with pytest.raises(ValidationError, match=r"\$\.actions\.items must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_list_actions_items():
    data = _make_valid_data()
    data["actions"]["items"] = {"item": 1}
    
    with pytest.raises(ValidationError, match=r"\$\.actions\.items must be an array"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_dict_action_item():
    data = _make_valid_data()
    data["actions"]["items"] = ["not a dict"]
    
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\] must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_missing_action_item_keys():
    data = _make_valid_data()
    data["actions"]["items"] = [{"description": "test"}]
    
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\] keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_priority():
    data = _make_valid_data()
    data["actions"]["items"][0]["priority"] = "critical"  # Not in allowed values
    
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\]\.priority must be one of"):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_action_type():
    data = _make_valid_data()
    data["actions"]["items"][0]["type"] = "invalid_type"
    
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\]\.type must be one of"):
        validate_output_data(data)


def test_validate_output_data_accepts_all_valid_priorities():
    for priority in PRIORITY:
        data = _make_valid_data()
        data["actions"]["items"][0]["priority"] = priority
        result = validate_output_data(data)
        assert result["actions"]["items"][0]["priority"] == priority


def test_validate_output_data_accepts_all_valid_action_types():
    for action_type in ACTION_TYPE:
        data = _make_valid_data()
        data["actions"]["items"][0]["type"] = action_type
        result = validate_output_data(data)
        assert result["actions"]["items"][0]["type"] == action_type


# ── Test implementation_plan validation ───────────────────────────────────────

def test_validate_output_data_rejects_non_dict_implementation_plan():
    data = _make_valid_data()
    data["implementation_plan"] = "not a dict"
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_missing_implementation_plan_keys():
    data = _make_valid_data()
    data["implementation_plan"] = {"overview": ""}
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_milestones():
    data = _make_valid_data()
    data["implementation_plan"]["milestones"] = []
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.milestones must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_dict_milestone():
    data = _make_valid_data()
    data["implementation_plan"]["milestones"] = ["not a dict"]
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.milestones\[0\] must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_missing_milestone_keys():
    data = _make_valid_data()
    data["implementation_plan"]["milestones"] = [{"name": "test"}]
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.milestones\[0\] keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_tech_tasks():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"] = []
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_dict_tech_task():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"] = [42]
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\] must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_area():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"][0]["area"] = "invalid_area"
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.area must be one of"):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_complexity():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"][0]["complexity"] = "XL"
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.complexity must be one of"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_list_depends_on():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = "not a list"
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.depends_on must be an array"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_string_in_depends_on():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [123]
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[0\]\.depends_on\[0\] must be a string"):
        validate_output_data(data)


def test_validate_output_data_accepts_all_valid_areas():
    for area in AREA:
        data = _make_valid_data()
        data["implementation_plan"]["tech_tasks"][0]["area"] = area
        result = validate_output_data(data)
        assert result["implementation_plan"]["tech_tasks"][0]["area"] == area


def test_validate_output_data_accepts_all_valid_complexities():
    for complexity in COMPLEXITY:
        data = _make_valid_data()
        data["implementation_plan"]["tech_tasks"][0]["complexity"] = complexity
        result = validate_output_data(data)
        assert result["implementation_plan"]["tech_tasks"][0]["complexity"] == complexity


# ── Test code_suggestions validation ──────────────────────────────────────────

def test_validate_output_data_rejects_non_dict_code_suggestions():
    data = _make_valid_data()
    data["code_suggestions"] = "not a dict"
    
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_missing_code_suggestions_keys():
    data = _make_valid_data()
    data["code_suggestions"] = {"language": "python"}
    
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_snippets():
    data = _make_valid_data()
    data["code_suggestions"]["snippets"] = []
    
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_dict_snippet():
    data = _make_valid_data()
    data["code_suggestions"]["snippets"] = ["not a dict"]
    
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets\[0\] must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_missing_snippet_keys():
    data = _make_valid_data()
    data["code_suggestions"]["snippets"] = [{"title": "test"}]
    
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets\[0\] keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_string_snippet_field():
    data = _make_valid_data()
    data["code_suggestions"]["snippets"][0]["code"] = 123
    
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets\[0\]\.code must be a string"):
        validate_output_data(data)


# ── Test multiple items in arrays ─────────────────────────────────────────────

def test_validate_output_data_validates_all_action_items():
    data = _make_valid_data()
    data["actions"]["items"].append({
        "description": "Second item",
        "owner": "dev2",
        "priority": "invalid",  # Invalid at index 1
        "type": "bug"
    })
    
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[1\]\.priority must be one of"):
        validate_output_data(data)


def test_validate_output_data_validates_all_milestones():
    data = _make_valid_data()
    data["implementation_plan"]["milestones"].append({
        "name": "Milestone 2",
        "description": 123,  # Invalid at index 1
        "eta_guess": "2 weeks",
        "risks": "None"
    })
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.milestones\[1\]\.description must be a string"):
        validate_output_data(data)


def test_validate_output_data_validates_all_tech_tasks():
    data = _make_valid_data()
    data["implementation_plan"]["tech_tasks"].append({
        "area": "backend",
        "description": "Task 2",
        "depends_on": [42],  # Invalid - non-string dependency
        "complexity": "M"
    })
    
    with pytest.raises(ValidationError, match=r"\$\.implementation_plan\.tech_tasks\[1\]\.depends_on\[0\] must be a string"):
        validate_output_data(data)


def test_validate_output_data_validates_all_snippets():
    data = _make_valid_data()
    data["code_suggestions"]["snippets"].append({
        "title": "Snippet 2",
        "purpose": None,  # Invalid at index 1
        "code": "print('hi')",
        "notes": ""
    })
    
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets\[1\]\.purpose must be a string"):
        validate_output_data(data)


# ── Helper functions ──────────────────────────────────────────────────────────

def _make_valid_data():
    """Create a minimal valid output data structure for testing."""
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
