#!/usr/bin/env python3
"""
playlist_builder.py — Builds and exports DJ playlists for the AI-DJ system.

Combines the TrackLibrary and DJBrain to produce a complete, exportable
playlist from a filtered subset of the local track catalogue.

Supported export formats:
  • JSON  — machine-readable playlist with full metadata and transitions
  • M3U   — standard playlist format recognised by most media players

Usage (CLI):
    # Generate a 60-minute house set and save as JSON + M3U
    python3 playlist_builder.py \
        --mood "underground late-night groove" \
        --genre house \
        --duration 60 \
        --output-json set.json \
        --output-m3u  set.m3u

    # Only use tracks between 125–132 BPM
    python3 playlist_builder.py \
        --mood "peak-time energy" \
        --min-bpm 125 --max-bpm 132 \
        --duration 30

Usage (library):
    from playlist_builder import PlaylistBuilder
    builder = PlaylistBuilder(db_path="tracks.json")
    result = builder.build(mood="chill sunset", genre="ambient", duration_minutes=45)
    builder.export_json(result, "set.json")
    builder.export_m3u(result, "set.m3u")
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from dj_brain import DJBrain
from track_library import TrackLibrary


class PlaylistBuilder:
    """Orchestrates TrackLibrary + DJBrain to build and export playlists."""

    def __init__(
        self,
        db_path: str | Path = "tracks.json",
        model: str | None = None,
    ) -> None:
        self._library = TrackLibrary(db_path)
        self._brain = DJBrain(**({"model": model} if model else {}))

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(
        self,
        mood: str,
        duration_minutes: int = 60,
        genre: str | None = None,
        min_bpm: float | None = None,
        max_bpm: float | None = None,
        min_energy: float | None = None,
        max_energy: float | None = None,
        key: str | None = None,
    ) -> dict[str, Any]:
        """Filter the track library and generate an AI-ordered DJ plan.

        Returns the raw plan dict from DJBrain (keys: playlist, transitions,
        reasoning) augmented with a ``filters`` summary.
        """
        candidates = self._library.search(
            genre=genre,
            min_bpm=min_bpm,
            max_bpm=max_bpm,
            min_energy=min_energy,
            max_energy=max_energy,
            key=key,
        )

        if not candidates:
            raise ValueError(
                "No tracks matched the supplied filters. "
                "Relax your filter criteria or add more tracks."
            )

        plan = self._brain.generate_plan(
            tracks=candidates,
            mood=mood,
            duration_minutes=duration_minutes,
        )

        plan["filters"] = {
            "genre": genre,
            "min_bpm": min_bpm,
            "max_bpm": max_bpm,
            "min_energy": min_energy,
            "max_energy": max_energy,
            "key": key,
            "duration_minutes": duration_minutes,
            "mood": mood,
        }

        return plan

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    @staticmethod
    def export_json(plan: dict[str, Any], path: str | Path) -> None:
        """Write *plan* as a pretty-printed JSON file."""
        Path(path).write_text(json.dumps(plan, indent=2))

    @staticmethod
    def export_m3u(plan: dict[str, Any], path: str | Path) -> None:
        """Write *plan*'s playlist as an M3U file.

        Each entry uses ``# <artist> – <title> (BPM: <bpm>, Key: <key>)``
        as an extended-info comment, with a placeholder file path
        ``<artist>/<title>.mp3`` that users can replace with real paths.
        """
        lines = ["#EXTM3U", f"# Mood: {plan.get('filters', {}).get('mood', '')}"]
        for track in plan.get("playlist", []):
            title = track.get("title", "Unknown")
            artist = track.get("artist", "Unknown")
            bpm = track.get("bpm", "?")
            key = track.get("key", "?")
            lines.append(
                f"#EXTINF:-1,{artist} – {title} (BPM: {bpm}, Key: {key})"
            )
            # Placeholder path — users substitute the real file location
            safe_artist = artist.replace("/", "_")
            safe_title = title.replace("/", "_")
            lines.append(f"{safe_artist}/{safe_title}.mp3")
        Path(path).write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and export an AI-generated DJ playlist"
    )
    # Library / AI options
    parser.add_argument("--db", default="tracks.json", help="Track library JSON file")
    parser.add_argument("--mood", required=True, help="Desired vibe or energy arc")
    parser.add_argument(
        "--duration", type=int, default=60, metavar="MINUTES",
        help="Target set length in minutes (default: 60)",
    )
    parser.add_argument("--model", default=None, help="Override the Claude model")

    # Track filters
    parser.add_argument("--genre", default=None, help="Filter by genre")
    parser.add_argument("--min-bpm", type=float, default=None)
    parser.add_argument("--max-bpm", type=float, default=None)
    parser.add_argument("--min-energy", type=float, default=None)
    parser.add_argument("--max-energy", type=float, default=None)
    parser.add_argument("--key", default=None, help="Filter by musical key (e.g. Am)")

    # Export options
    parser.add_argument(
        "--output-json", metavar="FILE",
        help="Write the full plan as JSON to FILE",
    )
    parser.add_argument(
        "--output-m3u", metavar="FILE",
        help="Write the playlist as an M3U file to FILE",
    )
    args = parser.parse_args()

    try:
        builder = PlaylistBuilder(db_path=args.db, model=args.model)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Building playlist: mood='{args.mood}', duration={args.duration} min …",
        file=sys.stderr,
    )

    try:
        plan = builder.build(
            mood=args.mood,
            duration_minutes=args.duration,
            genre=args.genre,
            min_bpm=args.min_bpm,
            max_bpm=args.max_bpm,
            min_energy=args.min_energy,
            max_energy=args.max_energy,
            key=args.key,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output_json:
        PlaylistBuilder.export_json(plan, args.output_json)
        print(f"JSON written to {args.output_json}", file=sys.stderr)

    if args.output_m3u:
        PlaylistBuilder.export_m3u(plan, args.output_m3u)
        print(f"M3U written to {args.output_m3u}", file=sys.stderr)

    if not args.output_json and not args.output_m3u:
        print(json.dumps(plan, indent=2))

    track_count = len(plan.get("playlist", []))
    print(f"Done — {track_count} tracks in playlist.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
