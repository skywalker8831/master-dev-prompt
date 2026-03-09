import sys
from pathlib import Path

# Allow tests to import ai_dj modules directly (e.g. `from track_library import ...`)
# matching the same pattern used for root-level modules like watcher.py.
sys.path.insert(0, str(Path(__file__).parent.parent / "ai_dj"))
