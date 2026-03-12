# Copilot Instructions

## Project Overview

**Master Developer Prompt Kit** — a prompt engineering and AI workflow tool that transforms any transcript into a full engineering package (design docs, PM summaries, action items, implementation plans, code suggestions) via a single Claude API call.

Framework: Whisper Flow · buildagentic · McDis Framework

---

## Key Files

| File | Purpose |
|------|---------|
| `master_dev_prompt.txt` | Core system prompt — defines the JSON output schema and Claude's role |
| `run_master_dev.sh` | CLI entry point — pipes a transcript through Claude or Codex (supports `--mock` / `MOCK_OUTPUT=1`) |
| `batch_run_master_dev.sh` | Batch processor for all `transcripts/*.txt` files |
| `validate_output.py` | Strict JSON schema validator (structure + enum checks) |
| `app.py` | FastAPI server — `POST /process`, `GET /` (web UI), `GET /health` |
| `watcher.py` | File watcher — auto-processes any `.txt` dropped into `transcripts/` |
| `Makefile` | CI shortcuts: `validate-file`, `validate-outputs`, `ci` |
| `static/index.html` | Terminal-style browser UI |

---

## Build, Test & CI

```bash
# Run all CI checks (validator fixture + all outputs)
make ci

# Validate a single output file
make validate-file FILE=outputs/sample.json

# Validate all outputs in the outputs/ directory
make validate-outputs

# Run the test suite
python3 -m pytest tests/
```

GitHub Actions runs `make ci` on every push to `main`/`master` and on pull requests.

---

## Output JSON Schema

All outputs must conform to the following top-level structure:

```json
{
  "design_doc": { ... },
  "pm_summary": { ... },
  "actions": { "items": [ ... ] },
  "implementation_plan": { "overview": "", "milestones": [ ... ], "tech_tasks": [ ... ] },
  "code_suggestions": { "language": "", "stack_context": "", "snippets": [ ... ] }
}
```

**Enum constraints** (enforced by `validate_output.py`):
- `actions.items[].priority`: `low` | `medium` | `high`
- `actions.items[].type`: `feature` | `bug` | `infra` | `research` | `decision` | `follow-up`
- `implementation_plan.tech_tasks[].area`: `backend` | `frontend` | `infra` | `data` | `devops` | `testing`
- `implementation_plan.tech_tasks[].complexity`: `S` | `M` | `L`

Lists that must be non-empty: `actions.items`, `implementation_plan.milestones`, `implementation_plan.tech_tasks`, `code_suggestions.snippets`.

---

## Development Conventions

- **Python version**: 3.11 (see CI workflow). Use standard library where possible.
- **Shell scripts**: Bash with `set -euo pipefail`. Make scripts executable with `chmod +x`.
- **Mock mode**: Use `--mock` flag or `MOCK_OUTPUT=1` env var when running without a live API key. Mock outputs are written to `outputs/sample.json`.
- **Outputs directory**: Generated JSON goes into `outputs/`. Invalid outputs are written as `*.invalid.json` and skipped by `make validate-outputs`.
- **Transcripts directory**: Input `.txt` transcripts live in `transcripts/`.
- **No extra keys**: The validator enforces exact key sets — do not add or remove top-level or nested keys from the schema.

---

## FastAPI Server

```bash
export ANTHROPIC_API_KEY=sk-...
pip install fastapi uvicorn anthropic python-dotenv
uvicorn app:app --reload
```

Endpoints:
- `GET /` — browser UI
- `POST /process` — accepts `{ "transcript": "..." }`, returns structured JSON
- `GET /health` — liveness check

Set `SERVER_API_KEY` env var to require `X-Api-Key` header authentication.

---

## Autopilot Watcher

```bash
python3 watcher.py [--transcripts ./transcripts] [--outputs ./outputs]
```

Watches for new `.txt` files and automatically processes them; already-processed files (matching `.json` exists) are skipped.
