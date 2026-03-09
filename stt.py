#!/usr/bin/env python3
"""
stt.py — Command-line Speech-to-Text using SpeechRecognition + pyaudio.

Usage:
    python stt.py
    python stt.py --output transcript.txt
    python stt.py --duration 10
    python stt.py --output out.txt --duration 30

Dependencies:
    pip install SpeechRecognition pyaudio

Notes:
    - Uses your system microphone via pyaudio.
    - Transcription is performed via Google's free speech recognition service
      (requires an internet connection).
    - On Linux, install portaudio first: sudo apt-get install portaudio19-dev
    - On macOS, install portaudio first: brew install portaudio
"""

import argparse
import sys

# ─────────────────────────────────────────────
#  ARGUMENT PARSING
# ─────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record from microphone and transcribe speech to text.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Save transcript to a file
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Path to save the transcript (prints to stdout if not given).",
    )

    # Maximum listening duration in seconds
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Maximum seconds to listen (listens until silence if not set).",
    )

    # Ambient noise adjustment duration
    parser.add_argument(
        "--adjust",
        type=float,
        default=1.0,
        metavar="SECONDS",
        help="Seconds to calibrate for ambient noise (default: 1.0).",
    )

    # Language for Google recognition
    parser.add_argument(
        "--language",
        default="en-US",
        metavar="LANG",
        help="BCP-47 language tag for recognition (default: en-US).",
    )

    return parser.parse_args()


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    # Import SpeechRecognition
    try:
        import speech_recognition as sr  # type: ignore
    except ImportError:
        print(
            "Error: SpeechRecognition is not installed.\n"
            "Install it with:  pip install SpeechRecognition pyaudio",
            file=sys.stderr,
        )
        sys.exit(1)

    # Import pyaudio (needed by sr.Microphone)
    try:
        import pyaudio  # type: ignore  # noqa: F401  # Required by sr.Microphone even though not directly called
    except ImportError:
        print(
            "Error: pyaudio is not installed.\n"
            "Install it with:  pip install pyaudio\n"
            "On Linux:  sudo apt-get install portaudio19-dev && pip install pyaudio\n"
            "On macOS:  brew install portaudio && pip install pyaudio",
            file=sys.stderr,
        )
        sys.exit(1)

    recognizer = sr.Recognizer()

    # Capture audio from the default microphone
    print("Adjusting for ambient noise… (please wait)", file=sys.stderr)

    try:
        with sr.Microphone() as source:
            # Calibrate recognizer energy threshold to ambient noise level
            recognizer.adjust_for_ambient_noise(source, duration=args.adjust)

            if args.duration:
                print(
                    f"Listening for up to {args.duration} second(s)… (speak now)",
                    file=sys.stderr,
                )
                audio = recognizer.record(source, duration=args.duration)
            else:
                print(
                    "Listening… (speak now, pause to finish)",
                    file=sys.stderr,
                )
                audio = recognizer.listen(source)

    except OSError as exc:
        print(f"Error accessing microphone: {exc}", file=sys.stderr)
        sys.exit(1)

    # Transcribe audio using Google Speech Recognition (free, no API key)
    print("Transcribing…", file=sys.stderr)
    try:
        transcript = recognizer.recognize_google(audio, language=args.language)
    except sr.UnknownValueError:
        print("Error: Could not understand the audio. Please try again.", file=sys.stderr)
        sys.exit(1)
    except sr.RequestError as exc:
        print(
            f"Error: Could not reach the speech recognition service: {exc}\n"
            "Check your internet connection.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Output the transcript
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(transcript + "\n")
            print(f"Transcript saved to: {args.output}", file=sys.stderr)
        except OSError as exc:
            print(f"Error writing transcript file: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        # Print to stdout so it can be piped to other commands
        print(transcript)


if __name__ == "__main__":
    main()
