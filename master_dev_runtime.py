"""Shared runtime helpers for prompt loading and strict output validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROMPT_PATH = Path(__file__).parent / "master_dev_prompt.txt"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8096

PRIORITY = {"low", "medium", "high"}
ACTION_TYPE = {"feature", "bug", "infra", "research", "decision", "follow-up"}
AREA = {"backend", "frontend", "infra", "data", "devops", "testing"}
COMPLEXITY = {"S", "M", "L"}

_system_prompt: str | None = None


class ValidationError(ValueError):
    """Raised when model output does not match the required schema."""


def load_system_prompt(prompt_path: Path = PROMPT_PATH) -> str:
    global _system_prompt
    if _system_prompt is None:
        if not prompt_path.exists():
            raise RuntimeError("master_dev_prompt.txt not found")
        _system_prompt = prompt_path.read_text(encoding="utf-8")
    return _system_prompt


def build_user_message(transcript: str) -> str:
    return f'{transcript}\n"""'


def _require_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must be an object")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{path} must be an array")
    return value


def _require_str(value: Any, path: str) -> None:
    if not isinstance(value, str):
        raise ValidationError(f"{path} must be a string")


def _require_exact_keys(obj: dict[str, Any], keys: list[str], path: str) -> None:
    expected = set(keys)
    actual = set(obj.keys())
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"extra={extra}")
        raise ValidationError(f"{path} keys mismatch ({', '.join(details)})")


def _require_non_empty_list(value: Any, path: str) -> list[Any]:
    items = _require_list(value, path)
    if len(items) == 0:
        raise ValidationError(f"{path} must contain at least one item")
    return items


def _require_enum(value: Any, allowed: set[str], path: str) -> None:
    _require_str(value, path)
    if value not in allowed:
        raise ValidationError(f"{path} must be one of {sorted(allowed)}")


def validate_output_data(data: Any) -> dict[str, Any]:
    root = _require_dict(data, "$")
    root_keys = ["design_doc", "pm_summary", "actions", "implementation_plan", "code_suggestions"]
    _require_exact_keys(root, root_keys, "$")

    design_doc = _require_dict(root["design_doc"], "$.design_doc")
    design_doc_keys = [
        "context_problem",
        "requirements_constraints",
        "proposed_architecture",
        "alternatives",
        "decisions",
        "open_questions_risks",
    ]
    _require_exact_keys(design_doc, design_doc_keys, "$.design_doc")
    for key in design_doc_keys:
        _require_str(design_doc[key], f"$.design_doc.{key}")

    pm_summary = _require_dict(root["pm_summary"], "$.pm_summary")
    pm_summary_keys = ["overview", "scope", "implications_for_timeline"]
    _require_exact_keys(pm_summary, pm_summary_keys, "$.pm_summary")
    for key in pm_summary_keys:
        _require_str(pm_summary[key], f"$.pm_summary.{key}")

    actions = _require_dict(root["actions"], "$.actions")
    _require_exact_keys(actions, ["items"], "$.actions")
    action_items = _require_non_empty_list(actions["items"], "$.actions.items")
    for idx, item in enumerate(action_items):
        item_path = f"$.actions.items[{idx}]"
        entry = _require_dict(item, item_path)
        action_item_keys = ["description", "owner", "priority", "type"]
        _require_exact_keys(entry, action_item_keys, item_path)
        _require_str(entry["description"], f"{item_path}.description")
        _require_str(entry["owner"], f"{item_path}.owner")
        _require_enum(entry["priority"], PRIORITY, f"{item_path}.priority")
        _require_enum(entry["type"], ACTION_TYPE, f"{item_path}.type")

    implementation = _require_dict(root["implementation_plan"], "$.implementation_plan")
    _require_exact_keys(implementation, ["overview", "milestones", "tech_tasks"], "$.implementation_plan")
    _require_str(implementation["overview"], "$.implementation_plan.overview")

    milestones = _require_non_empty_list(implementation["milestones"], "$.implementation_plan.milestones")
    for idx, milestone in enumerate(milestones):
        milestone_path = f"$.implementation_plan.milestones[{idx}]"
        entry = _require_dict(milestone, milestone_path)
        milestone_keys = ["name", "description", "eta_guess", "risks"]
        _require_exact_keys(entry, milestone_keys, milestone_path)
        _require_str(entry["name"], f"{milestone_path}.name")
        _require_str(entry["description"], f"{milestone_path}.description")
        _require_str(entry["eta_guess"], f"{milestone_path}.eta_guess")
        _require_str(entry["risks"], f"{milestone_path}.risks")

    tech_tasks = _require_non_empty_list(implementation["tech_tasks"], "$.implementation_plan.tech_tasks")
    for idx, task in enumerate(tech_tasks):
        task_path = f"$.implementation_plan.tech_tasks[{idx}]"
        entry = _require_dict(task, task_path)
        tech_task_keys = ["area", "description", "depends_on", "complexity"]
        _require_exact_keys(entry, tech_task_keys, task_path)
        _require_enum(entry["area"], AREA, f"{task_path}.area")
        _require_str(entry["description"], f"{task_path}.description")
        depends_on = _require_list(entry["depends_on"], f"{task_path}.depends_on")
        for dep_idx, dep in enumerate(depends_on):
            _require_str(dep, f"{task_path}.depends_on[{dep_idx}]")
        _require_enum(entry["complexity"], COMPLEXITY, f"{task_path}.complexity")

    code_suggestions = _require_dict(root["code_suggestions"], "$.code_suggestions")
    _require_exact_keys(code_suggestions, ["language", "stack_context", "snippets"], "$.code_suggestions")
    _require_str(code_suggestions["language"], "$.code_suggestions.language")
    _require_str(code_suggestions["stack_context"], "$.code_suggestions.stack_context")

    snippets = _require_non_empty_list(code_suggestions["snippets"], "$.code_suggestions.snippets")
    for idx, snippet in enumerate(snippets):
        snippet_path = f"$.code_suggestions.snippets[{idx}]"
        entry = _require_dict(snippet, snippet_path)
        snippet_keys = ["title", "purpose", "code", "notes"]
        _require_exact_keys(entry, snippet_keys, snippet_path)
        _require_str(entry["title"], f"{snippet_path}.title")
        _require_str(entry["purpose"], f"{snippet_path}.purpose")
        _require_str(entry["code"], f"{snippet_path}.code")
        _require_str(entry["notes"], f"{snippet_path}.notes")

    return root


def parse_and_validate_output(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    return validate_output_data(data)


def validate_output_file(json_path: Path) -> dict[str, Any]:
    if not json_path.is_file():
        raise ValidationError(f"file not found: {json_path}")
    return parse_and_validate_output(json_path.read_text(encoding="utf-8"))
