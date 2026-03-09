#!/usr/bin/env python3
"""
tts.py — Command-line Text-to-Speech using pyttsx3 (offline, no API key required).

Usage:
    python tts.py "Hello world"
    python tts.py --file conversation-log.md
    python tts.py --file conversation-log.md --rate 150 --volume 0.8

Dependencies:
    pip install pyttsx3

Notes:
    - Works on Windows (SAPI5), macOS (NSSpeech), and Linux (espeak).
    - On Linux, install espeak first: sudo apt-get install espeak
"""

import argparse
import sys

# ─────────────────────────────────────────────
#  ARGUMENT PARSING
# ─────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Text-to-speech from a string or file (uses pyttsx3, offline).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Positional: text to speak (optional when --file is given)
    parser.add_argument(
        "text",
        nargs="?",
        default=None,
        help="Text string to speak aloud.",
    )

    # Read from a file instead of a positional argument
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="Path to a text/markdown file to read aloud.",
    )

    # Speech rate (words per minute); pyttsx3 default is ~200
    parser.add_argument(
        "--rate",
        type=int,
        default=175,
        metavar="WPM",
        help="Speech rate in words per minute (default: 175).",
    )

    # Volume (0.0 – 1.0)
    parser.add_argument(
        "--volume",
        type=float,
        default=1.0,
        metavar="LEVEL",
        help="Volume level from 0.0 (silent) to 1.0 (full, default: 1.0).",
    )

    # Optionally list available voices and exit
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="Print available voices and exit.",
    )

    # Voice index to use
    parser.add_argument(
        "--voice",
        type=int,
        default=0,
        metavar="INDEX",
        help="Index of the voice to use (see --list-voices, default: 0).",
    )

    return parser.parse_args()


# ─────────────────────────────────────────────
#  HELPER: load pyttsx3
# ─────────────────────────────────────────────

def _get_engine(rate: int, volume: float, voice_index: int):
    """Initialise and configure a pyttsx3 TTS engine."""
    try:
        import pyttsx3  # type: ignore
    except ImportError:
        print(
            "Error: pyttsx3 is not installed.\n"
            "Install it with:  pip install pyttsx3",
            file=sys.stderr,
        )
        sys.exit(1)

    engine = pyttsx3.init()

    # Set speech rate (words per minute)
    engine.setProperty("rate", rate)

    # Set volume (0.0 – 1.0)
    volume = max(0.0, min(1.0, volume))
    engine.setProperty("volume", volume)

    # Set voice by index if available
    voices = engine.getProperty("voices")
    if voices and 0 <= voice_index < len(voices):
        engine.setProperty("voice", voices[voice_index].id)
    elif voices:
        print(
            f"Warning: voice index {voice_index} out of range "
            f"(0–{len(voices) - 1}). Using default voice.",
            file=sys.stderr,
        )

    return engine


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    # Validate volume range
    if not (0.0 <= args.volume <= 1.0):
        print("Error: --volume must be between 0.0 and 1.0.", file=sys.stderr)
        sys.exit(1)

    engine = _get_engine(args.rate, args.volume, args.voice)

    # --list-voices: print available voices and exit
    if args.list_voices:
        voices = engine.getProperty("voices")
        if not voices:
            print("No voices found on this system.")
        else:
            print(f"{'Index':<6} {'ID':<60} Name")
            print("-" * 90)
            for i, v in enumerate(voices):
                print(f"{i:<6} {v.id:<60} {v.name}")
        sys.exit(0)

    # Determine the text to speak
    if args.file:
        # Read from file
        try:
            with open(args.file, encoding="utf-8") as fh:
                content = fh.read().strip()
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except OSError as exc:
            print(f"Error reading file: {exc}", file=sys.stderr)
            sys.exit(1)
        if not content:
            print("Error: The file is empty.", file=sys.stderr)
            sys.exit(1)
        text = content
    elif args.text:
        text = args.text.strip()
        if not text:
            print("Error: Provided text is empty.", file=sys.stderr)
            sys.exit(1)
    else:
        print(
            "Error: Provide a text argument or use --file.\n"
            "Run  python tts.py --help  for usage.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Speak the text
    print(f"Speaking (rate={args.rate} wpm, volume={args.volume:.1f})…")
    engine.say(text)
    engine.runAndWait()
    print("Done.")


if __name__ == "__main__":
    main()
