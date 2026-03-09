#!/usr/bin/env python3
"""
track_library.py — Local track metadata library for the AI-DJ system.

Manages a JSON-backed catalogue of audio tracks.  Each track entry stores
the metadata that the DJ brain uses when building playlists (title, artist,
BPM, musical key, genre, and energy level).

Usage (CLI):
    python3 track_library.py --list
    python3 track_library.py --add '{"title":"Song A","artist":"Artist X","bpm":128,"key":"Am","genre":"house","energy":7}'
    python3 track_library.py --search genre=house
    python3 track_library.py --remove "Song A"

Usage (library):
    from track_library import TrackLibrary
    lib = TrackLibrary("tracks.json")
    lib.add({"title": "Song A", "artist": "Artist X", "bpm": 128,
             "key": "Am", "genre": "house", "energy": 7})
    results = lib.search(genre="house", min_bpm=120, max_bpm=135)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_KEYS = {"title", "artist", "bpm", "key", "genre", "energy"}

VALID_GENRES = {
    "house", "techno", "trance", "drum_and_bass", "ambient",
    "hip_hop", "pop", "rock", "jazz", "classical", "other",
}


def _validate_track(track: dict[str, Any]) -> None:
    """Raise ValueError if *track* is missing required fields or has bad values."""
    missing = REQUIRED_KEYS - track.keys()
    if missing:
        raise ValueError(f"Track is missing required keys: {missing}")
    if not isinstance(track["bpm"], (int, float)) or not (40 <= track["bpm"] <= 300):
        raise ValueError(f"bpm must be a number between 40 and 300, got {track['bpm']!r}")
    if not isinstance(track["energy"], (int, float)) or not (1 <= track["energy"] <= 10):
        raise ValueError(f"energy must be between 1 and 10, got {track['energy']!r}")
    if track.get("genre") not in VALID_GENRES:
        raise ValueError(
            f"genre must be one of {sorted(VALID_GENRES)}, got {track['genre']!r}"
        )


class TrackLibrary:
    """JSON-backed catalogue of audio tracks."""

    def __init__(self, db_path: str | Path = "tracks.json") -> None:
        self.db_path = Path(db_path)
        self._tracks: list[dict[str, Any]] = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> list[dict[str, Any]]:
        if self.db_path.exists():
            with self.db_path.open() as fh:
                return json.load(fh)
        return []

    def save(self) -> None:
        """Persist the current catalogue to disk."""
        with self.db_path.open("w") as fh:
            json.dump(self._tracks, fh, indent=2)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, track: dict[str, Any]) -> None:
        """Add *track* to the library after validation."""
        _validate_track(track)
        if any(t["title"] == track["title"] and t["artist"] == track["artist"]
               for t in self._tracks):
            raise ValueError(
                f"Track '{track['title']}' by '{track['artist']}' already exists."
            )
        self._tracks.append(track)
        self.save()

    def remove(self, title: str) -> bool:
        """Remove the first track whose title matches *title*.  Returns True on success."""
        before = len(self._tracks)
        self._tracks = [t for t in self._tracks if t["title"] != title]
        if len(self._tracks) < before:
            self.save()
            return True
        return False

    def all_tracks(self) -> list[dict[str, Any]]:
        """Return a copy of all tracks."""
        return list(self._tracks)

    # ------------------------------------------------------------------
    # Search / filter
    # ------------------------------------------------------------------

    def search(
        self,
        *,
        genre: str | None = None,
        min_bpm: float | None = None,
        max_bpm: float | None = None,
        min_energy: float | None = None,
        max_energy: float | None = None,
        key: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return tracks matching all supplied filters."""
        results = self._tracks
        if genre is not None:
            results = [t for t in results if t.get("genre") == genre]
        if min_bpm is not None:
            results = [t for t in results if t.get("bpm", 0) >= min_bpm]
        if max_bpm is not None:
            results = [t for t in results if t.get("bpm", 0) <= max_bpm]
        if min_energy is not None:
            results = [t for t in results if t.get("energy", 0) >= min_energy]
        if max_energy is not None:
            results = [t for t in results if t.get("energy", 0) <= max_energy]
        if key is not None:
            results = [t for t in results if t.get("key") == key]
        return results


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def _parse_kv_filter(arg: str) -> dict[str, str]:
    """Parse a ``key=value`` filter string into a dict."""
    filters: dict[str, str] = {}
    for pair in arg.split(","):
        if "=" not in pair:
            raise argparse.ArgumentTypeError(f"Expected key=value, got {pair!r}")
        k, v = pair.split("=", 1)
        filters[k.strip()] = v.strip()
    return filters


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the AI-DJ track library")
    parser.add_argument("--db", default="tracks.json", help="Path to the track database")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all tracks")
    group.add_argument("--add", metavar="JSON", help="Add a track (JSON string)")
    group.add_argument("--remove", metavar="TITLE", help="Remove a track by title")
    group.add_argument(
        "--search",
        metavar="FILTERS",
        help="Filter tracks, e.g. genre=house,min_bpm=120",
    )
    args = parser.parse_args()

    lib = TrackLibrary(args.db)

    if args.list:
        tracks = lib.all_tracks()
        if not tracks:
            print("Library is empty.")
        else:
            print(json.dumps(tracks, indent=2))

    elif args.add:
        try:
            track = json.loads(args.add)
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON: {exc}", file=sys.stderr)
            return 1
        try:
            lib.add(track)
            print(f"Added: {track['title']} by {track['artist']}")
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    elif args.remove:
        if lib.remove(args.remove):
            print(f"Removed: {args.remove}")
        else:
            print(f"Not found: {args.remove}", file=sys.stderr)
            return 1

    elif args.search:
        try:
            raw = _parse_kv_filter(args.search)
        except argparse.ArgumentTypeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        kwargs: dict[str, Any] = {}
        for k, v in raw.items():
            if k in ("min_bpm", "max_bpm", "min_energy", "max_energy"):
                kwargs[k] = float(v)
            else:
                kwargs[k] = v

        results = lib.search(**kwargs)
        if not results:
            print("No tracks matched the filter.")
        else:
            print(json.dumps(results, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
