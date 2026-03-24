import importlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

import master_dev_runtime


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"
VALID_RESULT = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _valid_result():
    return deepcopy(VALID_RESULT)


def test_parse_and_validate_output_accepts_valid_fixture():
    raw = FIXTURE_PATH.read_text(encoding="utf-8")

    result = master_dev_runtime.parse_and_validate_output(raw)

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

    with pytest.raises(master_dev_runtime.ValidationError, match=r"\$\.design_doc keys mismatch"):
        master_dev_runtime.validate_output_file(invalid_path)


def test_load_system_prompt_reads_file_once(tmp_path):
    importlib.reload(master_dev_runtime)
    prompt_path = tmp_path / "master_dev_prompt.txt"
    prompt_path.write_text("first prompt", encoding="utf-8")

    first = master_dev_runtime.load_system_prompt(prompt_path)
    prompt_path.write_text("second prompt", encoding="utf-8")
    second = master_dev_runtime.load_system_prompt(prompt_path)

    assert first == "first prompt"
    assert second == "first prompt"


def test_load_system_prompt_raises_when_prompt_missing(tmp_path):
    importlib.reload(master_dev_runtime)
    missing_path = tmp_path / "missing.txt"

    with pytest.raises(RuntimeError, match="master_dev_prompt.txt not found"):
        master_dev_runtime.load_system_prompt(missing_path)


def test_build_user_message_appends_transcript_terminator():
    assert master_dev_runtime.build_user_message("meeting notes") == 'meeting notes\n"""'


def test_parse_and_validate_output_rejects_invalid_json():
    with pytest.raises(master_dev_runtime.ValidationError, match=r"invalid JSON at line 1, column 2"):
        master_dev_runtime.parse_and_validate_output("{")


@pytest.mark.parametrize(
    ("field_path", "invalid_value", "expected_error"),
    [
        (("actions", "items", 0, "priority"), "urgent", r"\$\.actions\.items\[0\]\.priority must be one of"),
        (("actions", "items", 0, "type"), "task", r"\$\.actions\.items\[0\]\.type must be one of"),
        (("implementation_plan", "tech_tasks", 0, "area"), "mobile", r"\$\.implementation_plan\.tech_tasks\[0\]\.area must be one of"),
        (("implementation_plan", "tech_tasks", 0, "complexity"), "XL", r"\$\.implementation_plan\.tech_tasks\[0\]\.complexity must be one of"),
    ],
)
def test_parse_and_validate_output_rejects_invalid_enum_values(field_path, invalid_value, expected_error):
    payload = _valid_result()
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = invalid_value

    with pytest.raises(master_dev_runtime.ValidationError, match=expected_error):
        master_dev_runtime.parse_and_validate_output(json.dumps(payload))


@pytest.mark.parametrize(
    ("field_path", "invalid_value", "expected_error"),
    [
        (("design_doc", "context_problem"), 123, r"\$\.design_doc\.context_problem must be a string"),
        (("actions", "items"), "not-a-list", r"\$\.actions\.items must be an array"),
        (
            ("implementation_plan", "tech_tasks", 0, "depends_on"),
            "setup",
            r"\$\.implementation_plan\.tech_tasks\[0\]\.depends_on must be an array",
        ),
        (
            ("implementation_plan", "tech_tasks", 0, "depends_on"),
            [1],
            r"\$\.implementation_plan\.tech_tasks\[0\]\.depends_on\[0\] must be a string",
        ),
    ],
)
def test_parse_and_validate_output_rejects_invalid_types(field_path, invalid_value, expected_error):
    payload = _valid_result()
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = invalid_value

    with pytest.raises(master_dev_runtime.ValidationError, match=expected_error):
        master_dev_runtime.parse_and_validate_output(json.dumps(payload))
