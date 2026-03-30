import json
from copy import deepcopy
from pathlib import Path

import pytest

from master_dev_runtime import (
    ValidationError,
    _require_dict,
    _require_enum,
    _require_exact_keys,
    _require_list,
    _require_non_empty_list,
    _require_str,
    parse_and_validate_output,
    validate_output_data,
    validate_output_file,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "ci" / "fixtures" / "valid_output.json"
VALID_OUTPUT = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _valid_payload() -> dict:
    return deepcopy(VALID_OUTPUT)


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


@pytest.mark.parametrize("value", [None, [], "text", 1])
def test_require_dict_rejects_non_dict(value):
    with pytest.raises(ValidationError, match=r"\$\.field must be an object"):
        _require_dict(value, "$.field")


@pytest.mark.parametrize("value", [None, {}, "text", 1])
def test_require_list_rejects_non_list(value):
    with pytest.raises(ValidationError, match=r"\$\.items must be an array"):
        _require_list(value, "$.items")


@pytest.mark.parametrize("value", [None, {}, [], 1])
def test_require_str_rejects_non_string(value):
    with pytest.raises(ValidationError, match=r"\$\.name must be a string"):
        _require_str(value, "$.name")


def test_require_exact_keys_reports_missing_and_extra_keys():
    with pytest.raises(
        ValidationError,
        match=r"\$\.node keys mismatch \(missing=\['expected'\], extra=\['unexpected'\]\)",
    ):
        _require_exact_keys({"unexpected": "value"}, ["expected"], "$.node")


def test_require_non_empty_list_rejects_empty_list():
    with pytest.raises(ValidationError, match=r"\$\.items must contain at least one item"):
        _require_non_empty_list([], "$.items")


def test_require_enum_rejects_value_outside_allowed_set():
    with pytest.raises(ValidationError, match=r"\$\.priority must be one of \['high', 'low'\]"):
        _require_enum("medium", {"low", "high"}, "$.priority")


def test_parse_and_validate_output_rejects_invalid_json_syntax():
    with pytest.raises(ValidationError, match=r"invalid JSON at line 1, column 16"):
        parse_and_validate_output('{"design_doc": }')


def test_validate_output_data_rejects_invalid_action_priority():
    payload = _valid_payload()
    payload["actions"]["items"][0]["priority"] = "urgent"

    with pytest.raises(ValidationError, match=r"\$\.actions\.items\[0\]\.priority must be one of"):
        validate_output_data(payload)


def test_validate_output_data_rejects_non_string_dependency():
    payload = _valid_payload()
    payload["implementation_plan"]["tech_tasks"][0]["depends_on"] = [123]

    with pytest.raises(
        ValidationError,
        match=r"\$\.implementation_plan\.tech_tasks\[0\]\.depends_on\[0\] must be a string",
    ):
        validate_output_data(payload)


def test_validate_output_data_rejects_empty_tech_tasks():
    payload = _valid_payload()
    payload["implementation_plan"]["tech_tasks"] = []

    with pytest.raises(
        ValidationError,
        match=r"\$\.implementation_plan\.tech_tasks must contain at least one item",
    ):
        validate_output_data(payload)


def test_validate_output_data_rejects_empty_code_snippets():
    payload = _valid_payload()
    payload["code_suggestions"]["snippets"] = []

    with pytest.raises(ValidationError, match=r"\$\.code_suggestions\.snippets must contain at least one item"):
        validate_output_data(payload)
