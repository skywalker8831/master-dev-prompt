# AI-DJ

An AI-powered DJ assistant that uses [Claude](https://www.anthropic.com/claude) to build
intelligent, mood-aware playlists from your local track library and expose them over a REST API.

---

## Project layout

```
ai_dj/
├── track_library.py    # JSON-backed track catalogue — add, remove, search
├── dj_brain.py         # Claude-powered DJ decision engine
├── playlist_builder.py # Combines library + brain to build and export playlists
├── dj_server.py        # FastAPI HTTP server exposing all functionality
└── README.md           # This file
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11 + |
| anthropic | latest |
| fastapi | latest |
| uvicorn | latest |

Install all dependencies from the root of the repository:

```bash
pip install -r requirements.txt
```

> **Tip:** the root `requirements.txt` already includes `fastapi`, `uvicorn`, and `anthropic`.

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Script reference

### `track_library.py` — Track catalogue manager

Manages a JSON file (`tracks.json` by default) that stores your local track metadata.

**Track fields**

| Field | Type | Description |
|---|---|---|
| `title` | string | Track title |
| `artist` | string | Artist name |
| `bpm` | number | Beats per minute (40–300) |
| `key` | string | Musical key (e.g. `Am`, `C`, `F#m`) |
| `genre` | string | One of the supported genres (see below) |
| `energy` | number | Energy level 1–10 |

**Supported genres:** `house`, `techno`, `trance`, `drum_and_bass`, `ambient`,
`hip_hop`, `pop`, `rock`, `jazz`, `classical`, `other`

**CLI examples**

```bash
# List all tracks
python3 track_library.py --list

# Add a track
python3 track_library.py --add \
  '{"title":"Strings of Life","artist":"Rhythim Is Rhythim","bpm":128,"key":"Fm","genre":"house","energy":9}'

# Search by genre and BPM range
python3 track_library.py --search genre=house,min_bpm=120,max_bpm=135

# Remove a track
python3 track_library.py --remove "Strings of Life"

# Use a custom database file
python3 track_library.py --db my_library.json --list
```

---

### `dj_brain.py` — AI DJ decision engine

Sends your track list and desired mood to Claude and receives back an ordered playlist
with suggested transitions and a short explanation.

**Output schema**

```json
{
  "playlist": [
    {"title": "...", "artist": "...", "bpm": 128, "key": "Am", "energy": 8}
  ],
  "transitions": [
    {"from_track": "...", "to_track": "...", "type": "beatmatch fade", "notes": "..."}
  ],
  "reasoning": "..."
}
```

**CLI examples**

```bash
# Generate a 60-minute house set
python3 dj_brain.py --tracks tracks.json --mood "euphoric festival peak" --duration 60

# Save output to a file
python3 dj_brain.py --mood "warm sunset chill" --duration 45 --output plan.json

# Use a specific Claude model
python3 dj_brain.py --model claude-3-5-haiku-20241022 --mood "underground grooves"
```

---

### `playlist_builder.py` — Playlist builder & exporter

Wraps `TrackLibrary` and `DJBrain` to filter tracks and produce a complete set plan,
then export it to **JSON** and/or **M3U** formats.

**CLI examples**

```bash
# Build a 60-minute house set, print JSON to stdout
python3 playlist_builder.py --mood "late-night underground" --genre house --duration 60

# Save as both JSON and M3U
python3 playlist_builder.py \
  --mood "peak-time energy" \
  --min-bpm 125 --max-bpm 135 \
  --duration 90 \
  --output-json set.json \
  --output-m3u  set.m3u

# Filter by energy level
python3 playlist_builder.py \
  --mood "chill warm-up" \
  --genre ambient \
  --min-energy 3 --max-energy 6 \
  --duration 30
```

---

### `dj_server.py` — HTTP API server

A FastAPI server that exposes the full AI-DJ system over HTTP.

**Start the server**

```bash
cd ai_dj
uvicorn dj_server:app --reload --port 8001
```

Interactive API docs are available at <http://localhost:8001/docs>.

**Endpoints**

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/tracks` | List all tracks |
| `POST` | `/tracks` | Add a track |
| `DELETE` | `/tracks/{title}` | Remove a track |
| `GET` | `/tracks/search` | Filter tracks |
| `POST` | `/playlist` | Generate an AI playlist |

**Example requests**

```bash
# Add a track
curl -s -X POST http://localhost:8001/tracks \
  -H "Content-Type: application/json" \
  -d '{"title":"Blue Monday","artist":"New Order","bpm":130,"key":"Dm","genre":"other","energy":8}'

# Generate a playlist
curl -s -X POST http://localhost:8001/playlist \
  -H "Content-Type: application/json" \
  -d '{"mood":"euphoric club peak","duration_minutes":60,"genre":"house"}'

# Search tracks
curl -s "http://localhost:8001/tracks/search?genre=house&min_bpm=125&max_bpm=132"
```

**Optional API key protection**

Set `DJ_API_KEY` to restrict access:

```bash
export DJ_API_KEY="my-secret-token"
```

Then include the header `Authorization: Bearer my-secret-token` in every request.

**Custom track database path**

```bash
export DJ_TRACKS_DB="/data/my_library.json"
```

---

## End-to-end quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Go into the ai_dj directory
cd ai_dj

# 4. Seed the library with a few tracks
python3 track_library.py --add \
  '{"title":"Strings of Life","artist":"Rhythim Is Rhythim","bpm":128,"key":"Fm","genre":"house","energy":9}'
python3 track_library.py --add \
  '{"title":"Your Love","artist":"Frankie Knuckles","bpm":122,"key":"Cm","genre":"house","energy":7}'
python3 track_library.py --add \
  '{"title":"Can You Feel It","artist":"Larry Heard","bpm":118,"key":"Am","genre":"house","energy":6}'

# 5. Build a playlist
python3 playlist_builder.py \
  --mood "deep soulful late night" \
  --genre house \
  --duration 30 \
  --output-json set.json \
  --output-m3u  set.m3u

# 6. Inspect the result
cat set.json
```

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-3-5-sonnet-20241022` | Claude model override |
| `DJ_TRACKS_DB` | No | `tracks.json` | Path to the track library file |
| `DJ_API_KEY` | No | — | Bearer token to protect the HTTP API |
| `DJ_PORT` | No | `8001` | Port for `dj_server.py` |
