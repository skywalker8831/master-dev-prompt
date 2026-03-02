# Autopilot File Watcher Design

**Date:** 2026-03-01
**Project:** Master Developer Prompt Kit

---

## Problem

The existing pipeline requires manual invocation (`./run_master_dev.sh transcript.txt`) for every transcript. There is no way to "drop and forget" — users must remember to run the script after placing a transcript.

## Goal

Add an autopilot layer: watch the `transcripts/` folder and automatically process any new `.txt` file, writing output to `outputs/` without any manual intervention.

---

## Architecture

```
transcripts/<name>.txt  →  watcher.py  →  run_master_dev.sh  →  outputs/<name>.json
                                                               →  outputs/<name>.log
```

**Component:** `watcher.py`
- Uses Python `watchdog` library for OS-native filesystem events (FSEvents on macOS, inotify on Linux)
- Monitors `transcripts/` directory for file creation events
- Filters to `.txt` files only
- Skips files already processed (checks for existing `outputs/<name>.json`)
- Calls `run_master_dev.sh` as a subprocess
- Logs activity to stdout and per-file `.log` in `outputs/`

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Trigger mechanism | File watcher (watchdog) | OS-native events, zero CPU idle cost, fits existing folder structure |
| Deduplication | Check for existing `.json` | Simple, stateless, no database needed |
| Process execution | Subprocess call to `run_master_dev.sh` | Reuses existing retry/timeout/backend logic |
| Run mode | Foreground process | Simple to start/stop, no daemon complexity |

---

## Alternatives Considered

- **Cron job** — periodic polling, less immediate, would require tracking "already processed" state
- **Webhook/API trigger** — requires external integration (Slack, Zoom), more setup

---

## Open Questions / Risks

- What should happen if `run_master_dev.sh` fails after all retries? (Currently: log the error, skip the file)
- Should already-failed files be retried on next watcher start? (Currently: no, requires manual re-drop)

---

## Files Affected

| File | Change |
|------|--------|
| `watcher.py` | New file — the autopilot watcher |
| `requirements.txt` | Add `watchdog` dependency |
| `README.md` | Add watcher usage section |
