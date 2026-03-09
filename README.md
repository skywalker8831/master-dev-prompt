# Master Developer Prompt Kit
### Whisper Flow · buildagentic · McDis Framework

One prompt. One Claude call. Full engineering package from any transcript.

---

## Get the project

**GitHub:** <https://github.com/skywalker8831/master-dev-prompt>

```bash
git clone https://github.com/skywalker8831/master-dev-prompt.git
cd master-dev-prompt
pip install -r requirements.txt   # installs fastapi, uvicorn, anthropic, watchdog, pytest, httpx
```

Or download a ZIP directly from GitHub:
<https://github.com/skywalker8831/master-dev-prompt/archive/refs/heads/main.zip>

---

## Files

| File | Purpose |
|------|---------|
| `master_dev_prompt.txt` | The system prompt — defines schema + Claude's role |
| `run_master_dev.sh` | Shell script to pipe any transcript through Claude Code or Codex (supports `--mock` or `MOCK_OUTPUT=1` to emit `outputs/sample.json` when a model CLI is unavailable) |
| `validate_output.py` | JSON validator for structure + enum checks |
| `batch_run_master_dev.sh` | Batch processor for all `transcripts/*.txt` files |
| `Makefile` | Local/CI shortcuts (`validate-file`, `validate-outputs`, `test`, `ci`) |
| `.github/workflows/validate-master-dev-prompt.yml` | GitHub Actions validation workflow |
| `sample_transcript.txt` | Test transcript (Dear Saigon SMS ordering system) |
| `app.py` | FastAPI HTTP server — `POST /process` calls Claude directly via SDK, `GET /` serves the web UI |
| `static/index.html` | Terminal-style web UI — paste a transcript, get rendered artifacts |
| `ai_dj/` | **AI-DJ sub-project** — four-script system that builds Claude-powered DJ playlists from a local track library (see [`ai_dj/README.md`](ai_dj/README.md)) |

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
- `POST /process` — returns structured JSON from any transcript
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

Then drop any `.txt` file into `transcripts/` — the JSON output appears in `outputs/` automatically.

Custom directories:

```bash
python3 watcher.py --transcripts ./my-transcripts --outputs ./my-outputs
```

Stop with `Ctrl+C`. Files already processed (with a matching `.json` in `outputs/`) are skipped automatically.

---

## Final Products & Quality Assurance

### Where are the final products?

Every run writes its output to the **`outputs/`** folder in the repository root:

| File | Meaning |
|------|---------|
| `outputs/<name>.json` | ✅ Valid structured JSON — the finished product |
| `outputs/<name>.invalid.json` | ❌ Run completed but the JSON failed schema validation |
| `outputs/<name>.log` | 📋 Full run log for debugging |

`<name>` matches the transcript filename without the `.txt` extension.  
Example: `transcripts/my_feature.txt` → `outputs/my_feature.json`

### Do we double-check until you're done?

Yes. Every output goes through a three-layer quality pipeline before it is considered finished:

**Layer 1 — Schema validation (after every run)**

`validate_output.py` checks the JSON immediately after generation:
- All required top-level keys must be present (`design_doc`, `pm_summary`, `actions`, `implementation_plan`, `code_suggestions`)
- Every list field (`actions.items`, milestones, tech_tasks, snippets) must contain at least one item
- Enum fields (`priority`, `type`, `area`, `complexity`) must use exact allowed values
- If any check fails, the file is saved as `*.invalid.json` and the run exits non-zero

```bash
python3 validate_output.py outputs/my_feature.json   # manual check
make validate-file FILE=outputs/my_feature.json      # via Make
```

**Layer 2 — Batch re-validation (all outputs at once)**

Run this to re-validate every file in `outputs/` in one pass:

```bash
make validate-outputs
```

Failed files (`*.invalid.json`) are ignored by this target so they don't block the rest.

**Layer 3 — Continuous Integration (automatic, every push/PR)**

GitHub Actions runs the full CI suite automatically on every push and pull request:

```bash
make ci   # same checks, locally
```

`make ci` runs `test-validator` (fixture check) then `validate-outputs` (all outputs). The workflow fails the build if any output is invalid — nothing merges until everything passes.

> **Summary:** output → immediate schema check → batch re-check → CI gate on every push. The pipeline will not let an invalid file slip through unnoticed.
