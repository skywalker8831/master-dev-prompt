<!-- CI Status -->

# Master Developer Prompt Kit
### buildagentic · McDis Framework

One prompt. One Claude call. Full engineering package from any transcript.

**Update:** Copilot coding agent now uses fewer premium requests — each session consumes just one premium request.

---

## Repository Overview

This repository is a compact Python toolkit for turning a raw developer transcript into a **strictly validated engineering package**. It exposes the same core workflow in a few forms:

- **CLI wrappers** for one-off and batch transcript processing
- **A shared Python runtime** for prompt loading and JSON/schema validation
- **A FastAPI server** with REST and streaming endpoints
- **A watcher** that processes new transcript files automatically

The center of the repo is `master_dev_runtime.py`. That module is the reusable core: it loads the master prompt, formats the transcript for the model call, parses model output as JSON, and enforces the repository's strict response schema. The CLI validator, API server, and watcher all reuse that same runtime instead of duplicating validation logic.

### Key technologies

- **Python 3.11+** for the runtime, API, validator, and watcher
- **FastAPI** + **Pydantic** for the HTTP API and request/response models
- **Anthropic Python SDK** for Claude API calls
- **pytest** for tests
- **watchdog** for filesystem watching
- **Make** for local and CI validation commands

### How the code is organized

- **Prompt and schema flow**
  - `master_dev_prompt.txt` defines the master prompt contract
  - `master_dev_runtime.py` is the canonical implementation of prompt loading and output validation
  - `validate_output.py` is a thin CLI wrapper around that shared runtime
- **Execution entry points**
  - `run_master_dev.sh` runs a single transcript through Claude/Codex
  - `batch_run_master_dev.sh` processes all transcripts in a folder
  - `watcher.py` watches `transcripts/` and writes validated results into `outputs/`
  - `app.py` exposes the same workflow over HTTP
- **User-facing assets**
  - `static/index.html` is the browser UI served by FastAPI
- **Verification and fixtures**
  - `tests/` contains pytest coverage for the runtime, watcher, and API
  - `ci/fixtures/valid_output.json` is the canonical valid output sample used in tests and validation
- **Supporting directories**
  - `transcripts/` holds input transcript samples
  - `outputs/` holds generated JSON/log artifacts
  - `.github/workflows/` contains CI automation, centered on `make ci`
  - `docs/plans/` holds project plans and roadmap notes

## Files

| File | Purpose |
|------|---------|
| `master_dev_prompt.txt` | The system prompt — defines schema + Claude's role |
| `run_master_dev.sh` | Shell script to pipe any transcript through Claude Code or Codex (supports `--mock` or `MOCK_OUTPUT=1` to emit `outputs/sample.json` when a model CLI is unavailable) |
| `validate_output.py` | JSON validator for structure + enum checks |
| `master_dev_runtime.py` | Shared Python runtime for prompt loading and strict output validation |
| `batch_run_master_dev.sh` | Batch processor for all `transcripts/*.txt` files |
| `Makefile` | Local/CI shortcuts (`validate-file`, `validate-outputs`, `ci`) |
| `.github/workflows/validate-master-dev-prompt.yml` | GitHub Actions validation workflow |
| `sample_transcript.txt` | Test transcript (Dear Saigon SMS ordering system) |
| `app.py` | FastAPI HTTP server — `POST /process` calls Claude directly via SDK, `GET /` serves the web UI |
| `static/index.html` | Terminal-style web UI — paste a transcript, get rendered artifacts |

---

## Usage

### 1. Make the script executable (first time only)
```bash
chmod +x run_master_dev.sh
```

### 2. Run with your transcript
```bash
./run_master_dev.sh your_transcript.txt
```

### 3. Save output as JSON
```bash
./run_master_dev.sh your_transcript.txt > output.json
```

### 4. Test with the sample
```bash
./run_master_dev.sh sample_transcript.txt
```

The script auto-detects:
- `claude` CLI first
- falls back to `codex exec` if `claude` is not installed

Optional reliability env vars:
- `MAX_RETRIES` (default `3`)
- `RETRY_DELAY_SECONDS` (default `2`)
- `MASTER_DEV_TIMEOUT_SECONDS` (default `0`, disabled)

Example:
```bash
MAX_RETRIES=5 RETRY_DELAY_SECONDS=3 MASTER_DEV_TIMEOUT_SECONDS=90 \
./run_master_dev.sh sample_transcript.txt > output.json
```

### 5. Validate output JSON
```bash
python3 validate_output.py output.json
```

Validation is strict:
- required object keys must match exactly
- `actions.items`, `implementation_plan.milestones`, `implementation_plan.tech_tasks`, and `code_suggestions.snippets` must each contain at least one item
- enum fields must use the exact allowed values

Or with Make:
```bash
make validate-file FILE=output.json
```

### 6. Batch run all transcripts
Put `.txt` transcripts in `transcripts/`, then run:
```bash
chmod +x batch_run_master_dev.sh
./batch_run_master_dev.sh
```

Custom folders:
```bash
./batch_run_master_dev.sh ./my_transcripts ./my_outputs
```

Validate all generated outputs:
```bash
make validate-outputs
```

Batch behavior:
- successful runs write `outputs/<name>.json`
- schema failures write `outputs/<name>.invalid.json`
- run logs go to `outputs/<name>.log`
- `make validate-outputs` validates only `*.json` and ignores `*.invalid.json`

### 7. CI checks
Local CI-equivalent check:
```bash
make ci
```

GitHub Actions runs the same checks on push and pull request.

Python test suite:
```bash
python3 -m pytest -q
```

---

## Manual (no script)

```bash
{
  cat master_dev_prompt.txt
  cat your_transcript.txt
  echo ""
  echo '"""'
} | claude
```

Codex alternative:

```bash
{
  cat master_dev_prompt.txt
  cat your_transcript.txt
  echo ""
  echo '"""'
} | codex exec --skip-git-repo-check -
```

---

## Output Modes

| Mode | What you get |
|------|-------------|
| `design_doc` | context, requirements, architecture, alternatives, decisions, open questions |
| `pm_summary` | plain-language overview, scope, timeline implications |
| `actions` | tasks with owner, priority (low/medium/high), type |
| `implementation_plan` | milestones with ETA + risks, tech tasks with complexity (S/M/L) |
| `code_suggestions` | real runnable snippets in detected language, stack context |

---

## FastAPI Server

Run the included server for HTTP access and a browser UI:

```bash
export ANTHROPIC_API_KEY=sk-...
pip install fastapi uvicorn anthropic python-dotenv
uvicorn app:app --reload
```

- `GET /` — opens the web UI (paste transcript, get rendered artifacts)
- `POST /process` — returns schema-validated structured JSON from any transcript
- `POST /process/stream` — streams partial text and emits a final schema-validated result or validation error event
- `GET /health` — liveness check

Optional: set `SERVER_API_KEY` to require an `X-Api-Key` header on all requests.

### Minimal SDK snippet

```python
import anthropic, json

client = anthropic.Anthropic(api_key=YOUR_KEY)

with open("master_dev_prompt.txt") as f:
    system_prompt = f.read()

def run_master_dev(transcript: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        system=system_prompt,
        messages=[{"role": "user", "content": f'{transcript}\n"""'}]
    )
    return json.loads(response.content[0].text)
```

---

## Autopilot Watcher

Run the watcher to automatically process any transcript dropped into `transcripts/`:

```bash
python3 watcher.py
```

Then drop any `.txt` file into `transcripts/` — validated JSON output appears in `outputs/` automatically.

Custom directories:

```bash
python3 watcher.py --transcripts ./my-transcripts --outputs ./my-outputs
```

Stop with `Ctrl+C`. Files already processed (with a matching `.json` in `outputs/`) are skipped automatically.
Schema failures are written to `outputs/<name>.invalid.json`, and validator details are appended to `outputs/<name>.log`.

---

## GitHub Actions Workflows

Three workflows run automatically on the `main` branch:

| Workflow | File | Trigger | Purpose |
|---|---|---|---|
| **Validate Master Dev Prompt** | `validate-master-dev-prompt.yml` | Push / PR to `main` | Installs Python deps, runs `make ci` (schema validation + pytest suite) |
| **Copilot Auto-Fix** | `copilot-autofix.yml` | Push / PR | GitHub Copilot automated code fix suggestions |
| **Cleanup Old Workflow Runs** | `cleanup-workflow-runs.yml` | Weekly (Sun 3am UTC) + manual | Deletes workflow run history older than 30 days via GitHub API |

### Running CI locally

```bash
make ci
```

### Triggering the cleanup workflow manually

1. Go to **Actions** → **Cleanup Old Workflow Runs**
2. Click **Run workflow** → select branch `main` → **Run workflow**

### Branch conventions

- Default branch: `main`
- Copilot feature branches are ephemeral — they are deleted after their PR is merged or closed
- Do not force-push to `main`
