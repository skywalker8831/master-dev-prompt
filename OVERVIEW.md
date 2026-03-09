# Project Overview — Master Developer Prompt Kit

## What Is This?

The **Master Developer Prompt Kit** turns any meeting transcript into a complete engineering package in a single AI call. You feed it a raw conversation — a planning meeting, a design review, a standup — and it outputs a structured JSON document containing a design doc, PM summary, action items, implementation plan, and runnable code suggestions.

It is built on a single, carefully engineered system prompt (`master_dev_prompt.txt`) that instructs a language model to produce a fixed, validated JSON schema every time.

---

## Why It Exists

Engineering teams lose time translating meeting notes into tickets, design docs, and sprint plans. This kit automates that translation step so that the artifacts are ready immediately after the call ends, in a consistent machine-readable format that downstream tools can consume.

---

## Key Components

| Component | Role |
|-----------|------|
| `master_dev_prompt.txt` | The system prompt. Defines the output schema and instructs the model to produce only valid JSON with no prose. |
| `run_master_dev.sh` | CLI entry point. Pipes a transcript through `claude` or `codex`. Supports mock mode (`--mock`) for offline testing. |
| `batch_run_master_dev.sh` | Processes every `.txt` file in `transcripts/` in one shot. Writes JSON, invalid-JSON, and log files to `outputs/`. |
| `watcher.py` | Autopilot daemon. Watches `transcripts/` and processes new files automatically as they are dropped in. |
| `app.py` | FastAPI HTTP server. Accepts transcripts via `POST /process` and serves a browser UI at `GET /`. |
| `static/index.html` | Terminal-style web UI. Paste a transcript, see the rendered artifacts. |
| `validate_output.py` | Strict JSON schema validator. Checks required keys, enum values, and non-empty arrays. |
| `Makefile` | Shortcuts for local and CI validation (`make ci`, `make validate-file`, `make validate-outputs`). |
| `INSTALL.md` | Step-by-step guide to installing and authenticating the `claude` or `codex` CLI on macOS. |

---

## Data Flow

```
transcript (.txt)
        │
        ▼
  run_master_dev.sh          ← CLI path
  app.py /process            ← HTTP path
  watcher.py                 ← autopilot path
        │
        │  (system prompt + transcript)
        ▼
  claude / codex / Anthropic SDK
        │
        │  (raw JSON text)
        ▼
  validate_output.py         ← optional validation step
        │
        ▼
  output.json
  ┌──────────────────────────────────┐
  │ design_doc                       │
  │ pm_summary                       │
  │ actions                          │
  │ implementation_plan              │
  │ code_suggestions                 │
  └──────────────────────────────────┘
```

---

## Output Schema at a Glance

| Section | Contents |
|---------|----------|
| `design_doc` | context/problem, requirements, proposed architecture, alternatives, decisions, open questions |
| `pm_summary` | plain-language overview, scope, timeline implications |
| `actions` | task list — each item has description, owner, priority (`low`/`medium`/`high`), type |
| `implementation_plan` | milestones with ETA and risks; tech tasks with area and complexity (`S`/`M`/`L`) |
| `code_suggestions` | runnable code snippets with language, description, and stack context |

---

## Choosing the Right Entry Point

| Situation | Use |
|-----------|-----|
| Quick one-off on the command line | `run_master_dev.sh` |
| No model CLI installed | `run_master_dev.sh --mock` or `MOCK_OUTPUT=1` |
| Process a batch of transcripts | `batch_run_master_dev.sh` |
| Always-on, drop-in processing | `watcher.py` |
| Team / web access | `app.py` (FastAPI server + web UI) |
| Integrate into your own code | Anthropic SDK snippet in `README.md` |

---

## Repository Layout

```
master-dev-prompt/
├── master_dev_prompt.txt       # system prompt (schema definition)
├── run_master_dev.sh           # single-transcript CLI runner
├── batch_run_master_dev.sh     # batch CLI runner
├── watcher.py                  # autopilot file watcher
├── app.py                      # FastAPI server
├── validate_output.py          # JSON schema validator
├── Makefile                    # CI/local shortcuts
├── sample_transcript.txt       # example input
├── transcripts/                # drop .txt files here
├── outputs/                    # generated .json files land here
├── static/
│   └── index.html              # web UI
├── docs/
│   └── plans/                  # implementation plan notes
├── README.md                   # usage guide
├── INSTALL.md                  # CLI installation guide
└── OVERVIEW.md                 # this file
```
