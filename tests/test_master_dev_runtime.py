import copy
import json
from pathlib import Path

import pytest

import master_dev_runtime
from master_dev_runtime import ValidationError, parse_and_validate_output, validate_output_file


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"

# Minimal valid data used as a mutation base for schema tests.
_VALID_DATA = {
    "design_doc": {
        "context_problem": "",
        "requirements_constraints": "",
        "proposed_architecture": "",
        "alternatives": "",
        "decisions": "",
        "open_questions_risks": "",
    },
    "pm_summary": {"overview": "", "scope": "", "implications_for_timeline": ""},
    "actions": {
        "items": [{"description": "", "owner": "", "priority": "low", "type": "feature"}]
    },
    "implementation_plan": {
        "overview": "",
        "milestones": [{"name": "", "description": "", "eta_guess": "", "risks": ""}],
        "tech_tasks": [
            {"area": "backend", "description": "", "depends_on": [], "complexity": "S"}
        ],
    },
    "code_suggestions": {
        "language": "python",
        "stack_context": "",
        "snippets": [{"title": "", "purpose": "", "code": "print('ok')", "notes": ""}],
    },
}


# ── original tests ────────────────────────────────────────────────────────────

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

def test_load_system_prompt_reads_file_content(monkeypatch, tmp_path):
    p = tmp_path / "prompt.txt"
    p.write_text("hello world")
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    result = master_dev_runtime.load_system_prompt(p)
    assert result == "hello world"


def test_load_system_prompt_caches_on_second_call(monkeypatch, tmp_path):
    p = tmp_path / "prompt.txt"
    p.write_text("cached content")
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    first = master_dev_runtime.load_system_prompt(p)
    second = master_dev_runtime.load_system_prompt(p)
    assert first is second


def test_load_system_prompt_raises_for_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(master_dev_runtime, "_system_prompt", None)
    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        master_dev_runtime.load_system_prompt(tmp_path / "nonexistent.txt")


# ── build_user_message ────────────────────────────────────────────────────────

def test_build_user_message_appends_closing_triple_quote():
    from master_dev_runtime import build_user_message
    result = build_user_message("my transcript")
    assert result.startswith("my transcript")
    assert result.endswith('"""')


def test_build_user_message_preserves_transcript_content():
    from master_dev_runtime import build_user_message
    result = build_user_message("line1\nline2")
    assert "line1\nline2" in result


# ── parse_and_validate_output ─────────────────────────────────────────────────

def test_parse_and_validate_output_raises_for_invalid_json():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("{not valid json}")


def test_parse_and_validate_output_raises_for_bare_string():
    with pytest.raises(ValidationError, match="invalid JSON"):
        parse_and_validate_output("just a string without braces")


# ── validate_output_file ──────────────────────────────────────────────────────

def test_validate_output_file_raises_for_missing_file(tmp_path):
    with pytest.raises(ValidationError, match="file not found"):
        validate_output_file(tmp_path / "nonexistent.json")


def test_validate_output_file_accepts_valid_fixture():
    result = validate_output_file(FIXTURE_PATH)
    assert isinstance(result, dict)


# ── validate_output_data: root ────────────────────────────────────────────────

def test_validate_output_data_rejects_non_dict_root():
    from master_dev_runtime import validate_output_data
    with pytest.raises(ValidationError, match=r"\$ must be an object"):
        validate_output_data(["not", "a", "dict"])


def test_validate_output_data_rejects_missing_root_key():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    del data["code_suggestions"]
    with pytest.raises(ValidationError, match=r"\$ keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_extra_root_key():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["unexpected"] = {}
    with pytest.raises(ValidationError, match=r"\$ keys mismatch"):
        validate_output_data(data)


# ── validate_output_data: design_doc ─────────────────────────────────────────

def test_validate_output_data_rejects_non_dict_design_doc():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["design_doc"] = "not a dict"
    with pytest.raises(ValidationError, match=r"\$\.design_doc must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_design_doc_key_mismatch():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    del data["design_doc"]["context_problem"]
    with pytest.raises(ValidationError, match=r"\$\.design_doc keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_string_design_doc_field():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["design_doc"]["context_problem"] = 42
    with pytest.raises(ValidationError, match=r"\$\.design_doc\.context_problem must be a string"):
        validate_output_data(data)


# ── validate_output_data: pm_summary ─────────────────────────────────────────

def test_validate_output_data_rejects_pm_summary_key_mismatch():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    del data["pm_summary"]["overview"]
    with pytest.raises(ValidationError, match=r"\$\.pm_summary keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_string_pm_summary_field():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["pm_summary"]["scope"] = None
    with pytest.raises(ValidationError, match=r"\$\.pm_summary\.scope must be a string"):
        validate_output_data(data)


# ── validate_output_data: actions ────────────────────────────────────────────

def test_validate_output_data_rejects_empty_actions_items():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["actions"]["items"] = []
    with pytest.raises(ValidationError, match=r"\$\.actions\.items must contain at least one item"):
        validate_output_data(data)


def test_validate_output_data_rejects_non_dict_action_item():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["actions"]["items"] = ["not a dict"]
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\] must be an object"):
        validate_output_data(data)


def test_validate_output_data_rejects_action_item_key_mismatch():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    del data["actions"]["items"][0]["priority"]
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\] keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_action_priority():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["actions"]["items"][0]["priority"] = "urgent"
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\]\.priority must be one of"):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_action_type():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["actions"]["items"][0]["type"] = "unknown"
    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\]\.type must be one of"):
        validate_output_data(data)


def test_validate_output_data_accepts_all_valid_priorities_and_types():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["actions"]["items"] = [
        {"description": "", "owner": "", "priority": p, "type": t}
        for p, t in [("high", "bug"), ("medium", "infra"), ("low", "research")]
    ]
    result = validate_output_data(data)
    assert len(result["actions"]["items"]) == 3


# ── validate_output_data: implementation_plan ────────────────────────────────

def test_validate_output_data_rejects_empty_milestones():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["implementation_plan"]["milestones"] = []
    with pytest.raises(
        ValidationError,
        match=r"\$\.implementation_plan\.milestones must contain at least one item",
    ):
        validate_output_data(data)


def test_validate_output_data_rejects_milestone_key_mismatch():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    del data["implementation_plan"]["milestones"][0]["eta_guess"]
    with pytest.raises(
        ValidationError,
        match=r"\$\.implementation_plan\.milestones\[0\] keys mismatch",
    ):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_tech_tasks():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["implementation_plan"]["tech_tasks"] = []
    with pytest.raises(
        ValidationError,
        match=r"\$\.implementation_plan\.tech_tasks must contain at least one item",
    ):
        validate_output_data(data)


def test_validate_output_data_rejects_tech_task_key_mismatch():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    del data["implementation_plan"]["tech_tasks"][0]["area"]
    with pytest.raises(
        ValidationError,
        match=r"\$\.implementation_plan\.tech_tasks\[0\] keys mismatch",
    ):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_tech_task_area():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["implementation_plan"]["tech_tasks"][0]["area"] = "unknown_area"
    with pytest.raises(
        ValidationError,
        match=r"\$\.implementation_plan\.tech_tasks\[0\]\.area must be one of",
    ):
        validate_output_data(data)


def test_validate_output_data_rejects_invalid_tech_task_complexity():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["implementation_plan"]["tech_tasks"][0]["complexity"] = "XL"
    with pytest.raises(
        ValidationError,
        match=r"\$\.implementation_plan\.tech_tasks\[0\]\.complexity must be one of",
    ):
        validate_output_data(data)


def test_validate_output_data_rejects_non_string_depends_on_item():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["implementation_plan"]["tech_tasks"][0]["depends_on"] = [123]
    with pytest.raises(
        ValidationError,
        match=r"\$\.implementation_plan\.tech_tasks\[0\]\.depends_on\[0\] must be a string",
    ):
        validate_output_data(data)


# ── validate_output_data: code_suggestions ───────────────────────────────────

def test_validate_output_data_rejects_code_suggestions_key_mismatch():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    del data["code_suggestions"]["language"]
    with pytest.raises(ValidationError, match=r"\$\.code_suggestions keys mismatch"):
        validate_output_data(data)


def test_validate_output_data_rejects_empty_snippets():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    data["code_suggestions"]["snippets"] = []
    with pytest.raises(
        ValidationError,
        match=r"\$\.code_suggestions\.snippets must contain at least one item",
    ):
        validate_output_data(data)


def test_validate_output_data_rejects_snippet_key_mismatch():
    from master_dev_runtime import validate_output_data
    data = copy.deepcopy(_VALID_DATA)
    del data["code_suggestions"]["snippets"][0]["notes"]
    with pytest.raises(
        ValidationError,
        match=r"\$\.code_suggestions\.snippets\[0\] keys mismatch",
    ):
        validate_output_data(data)
