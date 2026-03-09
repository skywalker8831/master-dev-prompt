# Project Knowledge — Master Developer Prompt Kit

> This file gives the DJ agent (and any Copilot coding agent) automatic,
> up-to-date context for every task in this repository.
> It is structured as a **tree of life**: one root, clear branches, precise leaves.

---

## 🌳 Root — What This Project Is

**Master Developer Prompt Kit** converts raw meeting transcripts into a complete,
structured engineering package in a single Claude API call.

```
transcript (plain text)
        │
        ▼
 master_dev_prompt.txt  ──►  Claude / Codex
        │
        ▼
  Structured JSON output
  ├── design_doc
  ├── pm_summary
  ├── actions
  ├── implementation_plan
  └── code_suggestions
```

Framework tags: **Whisper Flow · buildagentic · McDis Framework**

---

## 🌿 Branch 1 — Project Tree (File Map)

```
master-dev-prompt/
│
├── master_dev_prompt.txt        ← system prompt fed to the model
├── run_master_dev.sh            ← CLI entry point (single transcript)
├── batch_run_master_dev.sh      ← batch processor (whole directory)
├── validate_output.py           ← strict JSON schema validator
├── watcher.py                   ← autopilot filesystem watcher
├── app.py                       ← FastAPI HTTP server + streaming
│
├── static/
│   └── index.html               ← terminal-style web UI (SSE stream consumer)
│
├── transcripts/                 ← drop .txt transcripts here
├── outputs/                     ← generated .json (and .log) files land here
│
├── ci/
│   └── fixtures/
│       └── valid_output.json    ← minimal valid JSON fixture used by CI
│
├── tests/
│   ├── __init__.py
│   └── test_watcher.py          ← pytest suite for watcher.py helpers
│
├── docs/
│   └── plans/                   ← design docs and implementation plans
│
├── Makefile                     ← local/CI shortcuts
├── requirements.txt             ← Python dependencies
└── .github/
    ├── workflows/
    │   └── validate-master-dev-prompt.yml   ← CI validation workflow
    └── agents/
        └── dj.agent.md          ← DJ agent definition
```

---

## 🌿 Branch 2 — Tools & Commands

### 🍃 Leaf 2.1 — `run_master_dev.sh` (single transcript)

```bash
# Basic usage
./run_master_dev.sh transcript.txt

# Save to JSON
./run_master_dev.sh transcript.txt > output.json

# Mock mode (no model CLI required — emits outputs/sample.json)
./run_master_dev.sh transcript.txt --mock
MOCK_OUTPUT=1 ./run_master_dev.sh transcript.txt

# With reliability tuning
MAX_RETRIES=5 RETRY_DELAY_SECONDS=3 MASTER_DEV_TIMEOUT_SECONDS=90 \
  ./run_master_dev.sh transcript.txt > output.json
```

**Env vars:**

| Variable | Default | Purpose |
|---|---|---|
| `MAX_RETRIES` | `3` | Retry count on model error |
| `RETRY_DELAY_SECONDS` | `2` | Pause between retries |
| `MASTER_DEV_TIMEOUT_SECONDS` | `0` (off) | Hard timeout per attempt |
| `MOCK_OUTPUT` | unset | `1` → emit `outputs/sample.json` |
| `ANTHROPIC_API_KEY` | — | Required for `claude` CLI |

**Backend auto-detection:** `claude` (preferred) → `codex exec` (fallback)

---

### 🍃 Leaf 2.2 — `batch_run_master_dev.sh` (directory)

```bash
# Default: transcripts/ → outputs/
chmod +x batch_run_master_dev.sh
./batch_run_master_dev.sh

# Custom directories
./batch_run_master_dev.sh ./my_transcripts ./my_outputs

# Mock batch (CI-safe, no model required)
./batch_run_master_dev.sh ./transcripts ./outputs --mock
```

**Behavior:**
- `outputs/<name>.json` on success + valid schema
- `outputs/<name>.invalid.json` on schema failure
- `outputs/<name>.log` always (stderr from runner)
- Exit 1 if any transcript fails

---

### 🍃 Leaf 2.3 — `validate_output.py` (JSON validator)

```bash
python3 validate_output.py outputs/sample.json
# VALID: outputs/sample.json

make validate-file FILE=outputs/sample.json
make validate-outputs               # all *.json in outputs/ (ignores *.invalid.json)
```

**Validation rules:**
- Exact key match at every level (no missing, no extra)
- `actions.items` — at least one item
- `implementation_plan.milestones` — at least one item
- `implementation_plan.tech_tasks` — at least one item
- `code_suggestions.snippets` — at least one item
- Enum enforcement (see Branch 4 — Conventions)

---

### 🍃 Leaf 2.4 — `watcher.py` (autopilot)

```bash
python3 watcher.py                                        # watches transcripts/ → outputs/
python3 watcher.py --transcripts ./my-in --outputs ./my-out
```

**Core functions (also importable):**
```python
from watcher import should_process, get_output_path, process_transcript

should_process(txt_path, outputs_dir)  # True if no matching .json exists
get_output_path(txt_path, outputs_dir) # outputs_dir/<stem>.json
process_transcript(txt_path, outputs_dir, script)  # shells out to run_master_dev.sh
```

Stop with `Ctrl+C`. Already-processed files (matching `.json` in outputs) are skipped.

---

### 🍃 Leaf 2.5 — `app.py` (FastAPI server)

```bash
export ANTHROPIC_API_KEY=sk-...
pip install fastapi uvicorn anthropic python-dotenv
uvicorn app:app --reload
```

**Endpoints:**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Serves `static/index.html` (web UI) |
| `POST` | `/process` | Returns full JSON artifact |
| `POST` | `/process/stream` | Streams response chunks as SSE |
| `GET` | `/health` | Liveness probe |

**Auth:** Set `SERVER_API_KEY` env var → all requests must send `X-Api-Key: <key>`.

**Minimal SDK call:**
```python
import anthropic, json

client = anthropic.Anthropic(api_key=YOUR_KEY)
system_prompt = open("master_dev_prompt.txt").read()

def run_master_dev(transcript: str) -> dict:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        system=system_prompt,
        messages=[{"role": "user", "content": f'{transcript}\n"""'}],
    )
    return json.loads(resp.content[0].text)
```

---

### 🍃 Leaf 2.6 — `Makefile` targets

```bash
make ci                             # test-validator + validate-outputs
make test-validator                 # validate ci/fixtures/valid_output.json
make validate-outputs               # validate all outputs/*.json
make validate-file FILE=path.json   # validate a single file
```

---

### 🍃 Leaf 2.7 — Testing

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v
```

**Test file:** `tests/test_watcher.py` — 5 tests covering:
- `should_process` returns True for new .txt
- `should_process` returns False if .json already exists
- `should_process` returns False for non-.txt files
- `get_output_path` maps .txt → .json correctly
- `process_transcript` shells out to the correct script with correct args

---

## 🌿 Branch 3 — Output JSON Schema

The model must return **only valid JSON**, no markdown, no code fences.

```json
{
  "design_doc": {
    "context_problem": "",
    "requirements_constraints": "",
    "proposed_architecture": "",
    "alternatives": "",
    "decisions": "",
    "open_questions_risks": ""
  },
  "pm_summary": {
    "overview": "",
    "scope": "",
    "implications_for_timeline": ""
  },
  "actions": {
    "items": [
      { "description": "", "owner": "", "priority": "low", "type": "feature" }
    ]
  },
  "implementation_plan": {
    "overview": "",
    "milestones": [
      { "name": "", "description": "", "eta_guess": "", "risks": "" }
    ],
    "tech_tasks": [
      { "area": "backend", "description": "", "depends_on": [], "complexity": "S" }
    ]
  },
  "code_suggestions": {
    "language": "",
    "stack_context": "",
    "snippets": [
      { "title": "", "purpose": "", "code": "", "notes": "" }
    ]
  }
}
```

---

## 🌿 Branch 4 — Conventions & Standards

### Enum values (exact strings only)

| Field | Allowed values |
|---|---|
| `priority` | `low` · `medium` · `high` |
| `type` | `feature` · `bug` · `infra` · `research` · `decision` · `follow-up` |
| `area` | `backend` · `frontend` · `infra` · `data` · `devops` · `testing` |
| `complexity` | `S` · `M` · `L` |

### Code style

- Python: follow conventions in `validate_output.py` and `watcher.py` (stdlib first, no unnecessary deps)
- Shell: `set -euo pipefail`, POSIX-compatible where possible
- All new `.py` files must be importable without side effects at module level
- `watchdog` import in `watcher.py` is wrapped in `try/except ImportError` — keep this pattern for optional deps
- Tests live in `tests/` and use `pytest`; mock subprocess calls with `unittest.mock.patch`

### Dependency management

- Add new Python packages to `requirements.txt`
- Check for vulnerabilities before adding new packages
- `watchdog` is the only third-party dep in `watcher.py` — keep it optional at import time

### CI/CD

- All PRs run `.github/workflows/validate-master-dev-prompt.yml`
- The `make ci` target must always pass before merging
- The mock batch run (`--mock`) must produce valid `outputs/sample_transcript.json`

---

## 🌿 Branch 5 — Workflows (How to Work on This Project)

### Adding a new transcript output field

1. Update `master_dev_prompt.txt` — add field to the schema comment and JSON template
2. Update `validate_output.py` — add validation logic for the new field
3. Update `ci/fixtures/valid_output.json` — add the field with a valid placeholder value
4. Update `outputs/sample.json` — add the field to the mock output
5. Run `make ci` to confirm validation passes

### Adding a new CLI mode

1. Extend `run_master_dev.sh` with a new flag/env var
2. Document in README.md under a new numbered section
3. Add batch support in `batch_run_master_dev.sh` if applicable

### Adding a new API endpoint

1. Add route to `app.py` following the existing FastAPI pattern
2. Update `static/index.html` if the endpoint has a UI surface
3. Document in README.md under the FastAPI Server section

### Fixing a test failure

1. Run `python3 -m pytest tests/ -v` to see the exact error
2. Check if `watchdog` is installed (`pip install watchdog`)
3. If `watcher.py` fails to import, the `try/except ImportError` block in `watcher.py` handles it gracefully

---

## 🌿 Branch 6 — Environment Setup

```bash
# Clone and install
pip install -r requirements.txt

# Make scripts executable (first time)
chmod +x run_master_dev.sh batch_run_master_dev.sh

# Set API key for live runs
export ANTHROPIC_API_KEY=sk-ant-...

# Verify everything works (mock, no model required)
./batch_run_master_dev.sh ./transcripts ./outputs --mock
make ci
python3 -m pytest tests/ -v
```

See `INSTALL.md` for model CLI installation instructions (`claude` or `codex`).
