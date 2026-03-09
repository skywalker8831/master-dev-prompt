#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# mock_runner.sh
#
# A deterministic mock runner for dry-run / confidence testing.
# It never calls any LLM backend; it always outputs a known-good
# JSON fixture so that CI and local checks can reach 100% confidence
# without depending on external services.
#
# Usage:
#   ./mock_runner.sh <transcript.txt>
#   ./mock_runner.sh <transcript.txt> --fixture path/to/fixture.json
#   MOCK_FIXTURE=path/to/fixture.json ./mock_runner.sh <transcript.txt>
#
# Exit codes:
#   0  – success (fixture JSON written to stdout)
#   1  – missing/unreadable transcript file
#   2  – missing/unreadable fixture file
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_FIXTURE="$SCRIPT_DIR/outputs/sample.json"

TRANSCRIPT_FILE="${1:-}"
shift || true

# Parse optional --fixture flag from remaining args
FIXTURE_FILE="${MOCK_FIXTURE:-$DEFAULT_FIXTURE}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fixture)
      FIXTURE_FILE="${2:-}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

# Validate transcript argument
if [[ -z "$TRANSCRIPT_FILE" ]]; then
  echo "Usage: ./mock_runner.sh <transcript.txt> [--fixture path/to/fixture.json]" >&2
  exit 1
fi

if [[ ! -f "$TRANSCRIPT_FILE" ]]; then
  echo "Error: transcript file not found: $TRANSCRIPT_FILE" >&2
  exit 1
fi

# Validate fixture file
if [[ -z "$FIXTURE_FILE" ]]; then
  echo "Error: fixture path is empty" >&2
  exit 2
fi

if [[ ! -f "$FIXTURE_FILE" ]]; then
  echo "Error: fixture file not found: $FIXTURE_FILE" >&2
  exit 2
fi

# Emit the fixture (deterministic output)
cat "$FIXTURE_FILE"
