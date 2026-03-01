#!/usr/bin/env python3
"""Validate Master Dev Prompt JSON output structure and enum values."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


PRIORITY = {"low", "medium", "high"}
ACTION_TYPE = {"feature", "bug", "infra", "research", "decision", "follow-up"}
AREA = {"backend", "frontend", "infra", "data", "devops", "testing"}
COMPLEXITY = {"S", "M", "L"}


def fail(msg: str) -> None:
    print(f"INVALID: {msg}", file=sys.stderr)
    sys.exit(1)


def require_dict(value: Any, path: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{path} must be an object")
    return value


def require_list(value: Any, path: str) -> List[Any]:
    if not isinstance(value, list):
        fail(f"{path} must be an array")
    return value


def require_str(value: Any, path: str) -> None:
    if not isinstance(value, str):
        fail(f"{path} must be a string")


def require_keys(obj: Dict[str, Any], keys: List[str], path: str) -> None:
    for key in keys:
        if key not in obj:
            fail(f"{path}.{key} is missing")


def require_exact_keys(obj: Dict[str, Any], keys: List[str], path: str) -> None:
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
        fail(f"{path} keys mismatch ({', '.join(details)})")


def require_non_empty_list(value: Any, path: str) -> List[Any]:
    items = require_list(value, path)
    if len(items) == 0:
        fail(f"{path} must contain at least one item")
    return items


def require_enum(value: Any, allowed: set, path: str) -> None:
    require_str(value, path)
    if value not in allowed:
        fail(f"{path} must be one of {sorted(allowed)}")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: ./validate_output.py <output.json>", file=sys.stderr)
        return 2

    json_path = Path(sys.argv[1])
    if not json_path.is_file():
        fail(f"file not found: {json_path}")

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")

    root = require_dict(data, "$")
    root_keys = ["design_doc", "pm_summary", "actions", "implementation_plan", "code_suggestions"]
    require_keys(
        root,
        root_keys,
        "$",
    )
    require_exact_keys(root, root_keys, "$")

    design_doc = require_dict(root["design_doc"], "$.design_doc")
    design_doc_keys = [
        "context_problem",
        "requirements_constraints",
        "proposed_architecture",
        "alternatives",
        "decisions",
        "open_questions_risks",
    ]
    require_keys(
        design_doc,
        design_doc_keys,
        "$.design_doc",
    )
    require_exact_keys(design_doc, design_doc_keys, "$.design_doc")
    for key in design_doc_keys:
        require_str(design_doc[key], f"$.design_doc.{key}")

    pm_summary = require_dict(root["pm_summary"], "$.pm_summary")
    pm_summary_keys = ["overview", "scope", "implications_for_timeline"]
    require_keys(pm_summary, pm_summary_keys, "$.pm_summary")
    require_exact_keys(pm_summary, pm_summary_keys, "$.pm_summary")
    for key in pm_summary_keys:
        require_str(pm_summary[key], f"$.pm_summary.{key}")

    actions = require_dict(root["actions"], "$.actions")
    actions_keys = ["items"]
    require_keys(actions, actions_keys, "$.actions")
    require_exact_keys(actions, actions_keys, "$.actions")
    action_items = require_non_empty_list(actions["items"], "$.actions.items")
    for idx, item in enumerate(action_items):
        item_path = f"$.actions.items[{idx}]"
        entry = require_dict(item, item_path)
        action_item_keys = ["description", "owner", "priority", "type"]
        require_keys(entry, action_item_keys, item_path)
        require_exact_keys(entry, action_item_keys, item_path)
        require_str(entry["description"], f"{item_path}.description")
        require_str(entry["owner"], f"{item_path}.owner")
        require_enum(entry["priority"], PRIORITY, f"{item_path}.priority")
        require_enum(entry["type"], ACTION_TYPE, f"{item_path}.type")

    implementation = require_dict(root["implementation_plan"], "$.implementation_plan")
    implementation_keys = ["overview", "milestones", "tech_tasks"]
    require_keys(implementation, implementation_keys, "$.implementation_plan")
    require_exact_keys(implementation, implementation_keys, "$.implementation_plan")
    require_str(implementation["overview"], "$.implementation_plan.overview")

    milestones = require_non_empty_list(implementation["milestones"], "$.implementation_plan.milestones")
    for idx, milestone in enumerate(milestones):
        milestone_path = f"$.implementation_plan.milestones[{idx}]"
        entry = require_dict(milestone, milestone_path)
        milestone_keys = ["name", "description", "eta_guess", "risks"]
        require_keys(entry, milestone_keys, milestone_path)
        require_exact_keys(entry, milestone_keys, milestone_path)
        require_str(entry["name"], f"{milestone_path}.name")
        require_str(entry["description"], f"{milestone_path}.description")
        require_str(entry["eta_guess"], f"{milestone_path}.eta_guess")
        require_str(entry["risks"], f"{milestone_path}.risks")

    tech_tasks = require_non_empty_list(implementation["tech_tasks"], "$.implementation_plan.tech_tasks")
    for idx, task in enumerate(tech_tasks):
        task_path = f"$.implementation_plan.tech_tasks[{idx}]"
        entry = require_dict(task, task_path)
        tech_task_keys = ["area", "description", "depends_on", "complexity"]
        require_keys(entry, tech_task_keys, task_path)
        require_exact_keys(entry, tech_task_keys, task_path)
        require_enum(entry["area"], AREA, f"{task_path}.area")
        require_str(entry["description"], f"{task_path}.description")
        depends_on = require_list(entry["depends_on"], f"{task_path}.depends_on")
        for dep_idx, dep in enumerate(depends_on):
            require_str(dep, f"{task_path}.depends_on[{dep_idx}]")
        require_enum(entry["complexity"], COMPLEXITY, f"{task_path}.complexity")

    code_suggestions = require_dict(root["code_suggestions"], "$.code_suggestions")
    code_suggestion_keys = ["language", "stack_context", "snippets"]
    require_keys(code_suggestions, code_suggestion_keys, "$.code_suggestions")
    require_exact_keys(code_suggestions, code_suggestion_keys, "$.code_suggestions")
    require_str(code_suggestions["language"], "$.code_suggestions.language")
    require_str(code_suggestions["stack_context"], "$.code_suggestions.stack_context")

    snippets = require_non_empty_list(code_suggestions["snippets"], "$.code_suggestions.snippets")
    for idx, snippet in enumerate(snippets):
        snippet_path = f"$.code_suggestions.snippets[{idx}]"
        entry = require_dict(snippet, snippet_path)
        snippet_keys = ["title", "purpose", "code", "notes"]
        require_keys(entry, snippet_keys, snippet_path)
        require_exact_keys(entry, snippet_keys, snippet_path)
        require_str(entry["title"], f"{snippet_path}.title")
        require_str(entry["purpose"], f"{snippet_path}.purpose")
        require_str(entry["code"], f"{snippet_path}.code")
        require_str(entry["notes"], f"{snippet_path}.notes")

    print(f"VALID: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
