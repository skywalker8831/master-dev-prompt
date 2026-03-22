#!/usr/bin/env python3
"""Validate Master Dev Prompt JSON output structure and enum values."""

import sys
from pathlib import Path

from master_dev_runtime import ValidationError, validate_output_file


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: ./validate_output.py <output.json>", file=sys.stderr)
        return 2

    json_path = Path(sys.argv[1])
    try:
        validate_output_file(json_path)
    except ValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1

    print(f"VALID: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
