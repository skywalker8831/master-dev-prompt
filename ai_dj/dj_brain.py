#!/usr/bin/env python3
"""
dj_brain.py — AI-powered DJ decision engine for the AI-DJ system.

Uses Claude (via the Anthropic API) to recommend track orderings, suggest
transitions, and adapt the playlist to a desired mood and energy arc.

Usage (CLI):
    python3 dj_brain.py \
        --tracks tracks.json \
        --mood "euphoric festival peak" \
        --duration 60

Usage (library):
    from dj_brain import DJBrain
    brain = DJBrain(api_key="sk-ant-...")
    plan = brain.generate_plan(
        tracks=[{"title": "Song A", "bpm": 128, ...}, ...],
        mood="warm sunset",
        duration_minutes=45,
    )
    print(plan["playlist"])
    print(plan["transitions"])

Environment variables:
    ANTHROPIC_API_KEY  — Anthropic API key (required if not passed explicitly)
    ANTHROPIC_MODEL    — Claude model to use (default: claude-3-5-sonnet-20241022)
"""

import argparse
import json
import os
import sys
from typing import Any

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore[assignment]


_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

_SYSTEM_PROMPT = """\
You are an expert AI DJ with deep knowledge of music theory, harmonic mixing,
energy management, and crowd psychology.

When given a list of tracks and a desired mood/energy arc you will:
1. Select and order tracks to create a coherent journey for the audience.
2. Suggest a transition type for each consecutive pair of tracks
   (e.g. "beatmatch fade", "cut", "filter sweep", "echo out").
3. Briefly explain your reasoning for the ordering.

Always respond with a single, valid JSON object matching this schema:
{
  "playlist": [
    {"title": "<string>", "artist": "<string>", "bpm": <number>,
     "key": "<string>", "energy": <number>}
  ],
  "transitions": [
    {"from_track": "<title>", "to_track": "<title>",
     "type": "<transition type>", "notes": "<brief note>"}
  ],
  "reasoning": "<paragraph explaining the overall arc>"
}

Do not include any text outside the JSON object.
"""


class DJBrain:
    """Wraps the Anthropic API to produce AI-generated DJ set plans."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        if anthropic is None:
            raise RuntimeError(
                "The 'anthropic' package is not installed. "
                "Run: pip install anthropic"
            )
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "Anthropic API key not found. "
                "Set ANTHROPIC_API_KEY or pass api_key= to DJBrain()."
            )
        self._client = anthropic.Anthropic(api_key=resolved_key)
        self._model = model

    def generate_plan(
        self,
        tracks: list[dict[str, Any]],
        mood: str,
        duration_minutes: int = 60,
    ) -> dict[str, Any]:
        """Ask Claude to produce a DJ set plan for *tracks*.

        Args:
            tracks: List of track dicts (from TrackLibrary.all_tracks()).
            mood: Free-text description of the desired vibe or energy arc.
            duration_minutes: Approximate target set length in minutes.

        Returns:
            Parsed JSON dict with ``playlist``, ``transitions``, and
            ``reasoning`` keys.
        """
        if not tracks:
            raise ValueError("tracks list must not be empty")

        user_message = (
            f"Target mood/energy: {mood}\n"
            f"Target set duration: approximately {duration_minutes} minutes\n\n"
            f"Available tracks:\n{json.dumps(tracks, indent=2)}"
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Claude returned non-JSON output: {exc}\n\nRaw output:\n{raw}"
            ) from exc

    def suggest_next_track(
        self,
        current_track: dict[str, Any],
        candidates: list[dict[str, Any]],
        mood: str,
    ) -> dict[str, Any]:
        """Pick the best next track from *candidates* given the current track and mood.

        Returns:
            Dict with ``selected_track`` and ``transition`` keys.
        """
        user_message = (
            f"Currently playing: {json.dumps(current_track)}\n"
            f"Target mood: {mood}\n\n"
            f"Choose the best next track from these candidates and suggest "
            f"a transition type:\n{json.dumps(candidates, indent=2)}\n\n"
            "Respond with JSON: "
            '{"selected_track": {<full track object>}, '
            '"transition": {"type": "<type>", "notes": "<notes>"}}'
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Claude returned non-JSON output: {exc}\n\nRaw output:\n{raw}"
            ) from exc


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an AI-powered DJ set plan")
    parser.add_argument(
        "--tracks",
        default="tracks.json",
        help="Path to the track library JSON file",
    )
    parser.add_argument(
        "--mood",
        default="energetic crowd peak",
        help='Desired mood / energy arc (e.g. "warm sunset chill")',
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        metavar="MINUTES",
        help="Target set duration in minutes (default: 60)",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("ANTHROPIC_MODEL", _DEFAULT_MODEL),
        help="Claude model to use",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Write the plan JSON to FILE instead of stdout",
    )
    args = parser.parse_args()

    from pathlib import Path

    tracks_path = Path(args.tracks)
    if not tracks_path.exists():
        print(f"Error: track library not found: {tracks_path}", file=sys.stderr)
        return 1

    with tracks_path.open() as fh:
        tracks = json.load(fh)

    if not tracks:
        print("Error: track library is empty — add tracks first.", file=sys.stderr)
        return 1

    try:
        brain = DJBrain(model=args.model)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Generating DJ plan for {len(tracks)} tracks, "
        f"mood='{args.mood}', duration={args.duration} min …",
        file=sys.stderr,
    )

    try:
        plan = brain.generate_plan(
            tracks=tracks,
            mood=args.mood,
            duration_minutes=args.duration,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_text = json.dumps(plan, indent=2)

    if args.output:
        Path(args.output).write_text(output_text)
        print(f"Plan written to {args.output}", file=sys.stderr)
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
