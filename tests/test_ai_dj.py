"""
tests/test_ai_dj.py — Tests for the AI-DJ sub-project.

Covers track_library, dj_brain, playlist_builder, and dj_server without
requiring a real Anthropic API key (all network calls are mocked).
"""

import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TRACK: dict[str, Any] = {
    "title": "Strings of Life",
    "artist": "Rhythim Is Rhythim",
    "bpm": 128,
    "key": "Fm",
    "genre": "house",
    "energy": 9,
}

SAMPLE_PLAN: dict[str, Any] = {
    "playlist": [SAMPLE_TRACK],
    "transitions": [],
    "reasoning": "Great energy build.",
}


# ---------------------------------------------------------------------------
# track_library tests
# ---------------------------------------------------------------------------


class TestValidateTrack:
    def test_passes_for_valid_track(self):
        from track_library import validate_track

        validate_track(SAMPLE_TRACK)  # must not raise

    def test_raises_on_missing_key(self):
        from track_library import validate_track

        bad = {k: v for k, v in SAMPLE_TRACK.items() if k != "bpm"}
        with pytest.raises(ValueError, match="missing required keys"):
            validate_track(bad)

    def test_raises_on_bpm_too_low(self):
        from track_library import validate_track

        with pytest.raises(ValueError, match="bpm"):
            validate_track({**SAMPLE_TRACK, "bpm": 10})

    def test_raises_on_bpm_too_high(self):
        from track_library import validate_track

        with pytest.raises(ValueError, match="bpm"):
            validate_track({**SAMPLE_TRACK, "bpm": 999})

    def test_raises_on_energy_out_of_range(self):
        from track_library import validate_track

        with pytest.raises(ValueError, match="energy"):
            validate_track({**SAMPLE_TRACK, "energy": 0})

    def test_raises_on_invalid_genre(self):
        from track_library import validate_track

        with pytest.raises(ValueError, match="genre"):
            validate_track({**SAMPLE_TRACK, "genre": "reggaeton"})


class TestTrackLibrary:
    def test_empty_on_new_db(self, tmp_path):
        from track_library import TrackLibrary

        lib = TrackLibrary(tmp_path / "tracks.json")
        assert lib.all_tracks() == []

    def test_add_and_list(self, tmp_path):
        from track_library import TrackLibrary

        lib = TrackLibrary(tmp_path / "tracks.json")
        lib.add(SAMPLE_TRACK)
        tracks = lib.all_tracks()
        assert len(tracks) == 1
        assert tracks[0]["title"] == "Strings of Life"

    def test_add_persists_to_disk(self, tmp_path):
        from track_library import TrackLibrary

        db = tmp_path / "tracks.json"
        lib = TrackLibrary(db)
        lib.add(SAMPLE_TRACK)

        # Re-load from disk
        lib2 = TrackLibrary(db)
        assert len(lib2.all_tracks()) == 1

    def test_add_duplicate_raises(self, tmp_path):
        from track_library import TrackLibrary

        lib = TrackLibrary(tmp_path / "tracks.json")
        lib.add(SAMPLE_TRACK)
        with pytest.raises(ValueError, match="already exists"):
            lib.add(SAMPLE_TRACK)

    def test_remove_existing_returns_true(self, tmp_path):
        from track_library import TrackLibrary

        lib = TrackLibrary(tmp_path / "tracks.json")
        lib.add(SAMPLE_TRACK)
        assert lib.remove("Strings of Life") is True
        assert lib.all_tracks() == []

    def test_remove_missing_returns_false(self, tmp_path):
        from track_library import TrackLibrary

        lib = TrackLibrary(tmp_path / "tracks.json")
        assert lib.remove("Nonexistent Track") is False

    def test_search_by_genre(self, tmp_path):
        from track_library import TrackLibrary

        lib = TrackLibrary(tmp_path / "tracks.json")
        lib.add(SAMPLE_TRACK)
        lib.add({**SAMPLE_TRACK, "title": "Techno Track", "genre": "techno"})
        results = lib.search(genre="house")
        assert len(results) == 1
        assert results[0]["genre"] == "house"

    def test_search_by_bpm_range(self, tmp_path):
        from track_library import TrackLibrary

        lib = TrackLibrary(tmp_path / "tracks.json")
        lib.add(SAMPLE_TRACK)  # bpm=128
        lib.add({**SAMPLE_TRACK, "title": "Slow Track", "bpm": 100})
        results = lib.search(min_bpm=120, max_bpm=135)
        assert len(results) == 1
        assert results[0]["bpm"] == 128

    def test_search_by_energy(self, tmp_path):
        from track_library import TrackLibrary

        lib = TrackLibrary(tmp_path / "tracks.json")
        lib.add(SAMPLE_TRACK)  # energy=9
        lib.add({**SAMPLE_TRACK, "title": "Chill Track", "energy": 3})
        results = lib.search(min_energy=8)
        assert len(results) == 1
        assert results[0]["energy"] == 9

    def test_search_by_key(self, tmp_path):
        from track_library import TrackLibrary

        lib = TrackLibrary(tmp_path / "tracks.json")
        lib.add(SAMPLE_TRACK)  # key=Fm
        lib.add({**SAMPLE_TRACK, "title": "Am Track", "key": "Am"})
        results = lib.search(key="Fm")
        assert len(results) == 1
        assert results[0]["key"] == "Fm"

    def test_search_no_filters_returns_all(self, tmp_path):
        from track_library import TrackLibrary

        lib = TrackLibrary(tmp_path / "tracks.json")
        lib.add(SAMPLE_TRACK)
        lib.add({**SAMPLE_TRACK, "title": "Another Track"})
        assert len(lib.search()) == 2


# ---------------------------------------------------------------------------
# dj_brain tests (Anthropic API mocked)
# ---------------------------------------------------------------------------


def _make_mock_response(content: str) -> MagicMock:
    """Build a mock Anthropic messages.create() response."""
    msg = MagicMock()
    msg.content = [MagicMock(text=content)]
    return msg


class TestDJBrain:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from dj_brain import DJBrain

        with pytest.raises(RuntimeError, match="API key"):
            DJBrain()

    def test_generate_plan_returns_parsed_json(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from dj_brain import DJBrain

        plan_json = json.dumps(SAMPLE_PLAN)
        with patch("anthropic.Anthropic") as MockAnth:
            mock_client = MockAnth.return_value
            mock_client.messages.create.return_value = _make_mock_response(plan_json)

            brain = DJBrain(api_key="test-key")
            result = brain.generate_plan(tracks=[SAMPLE_TRACK], mood="peak time")

        assert result["playlist"] == [SAMPLE_TRACK]
        assert result["reasoning"] == "Great energy build."

    def test_generate_plan_raises_on_empty_tracks(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from dj_brain import DJBrain

        with patch("anthropic.Anthropic"):
            brain = DJBrain(api_key="test-key")
            with pytest.raises(ValueError, match="empty"):
                brain.generate_plan(tracks=[], mood="any")

    def test_generate_plan_raises_on_bad_json(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from dj_brain import DJBrain

        with patch("anthropic.Anthropic") as MockAnth:
            mock_client = MockAnth.return_value
            mock_client.messages.create.return_value = _make_mock_response(
                "Sorry, I cannot do that."
            )
            brain = DJBrain(api_key="test-key")
            with pytest.raises(ValueError, match="non-JSON"):
                brain.generate_plan(tracks=[SAMPLE_TRACK], mood="peak time")

    def test_suggest_next_track_returns_selection(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from dj_brain import DJBrain

        selection = {"selected_track": SAMPLE_TRACK, "transition": {"type": "beatmatch fade", "notes": "smooth"}}
        with patch("anthropic.Anthropic") as MockAnth:
            mock_client = MockAnth.return_value
            mock_client.messages.create.return_value = _make_mock_response(
                json.dumps(selection)
            )
            brain = DJBrain(api_key="test-key")
            result = brain.suggest_next_track(
                current_track=SAMPLE_TRACK,
                candidates=[SAMPLE_TRACK],
                mood="chill",
            )
        assert result["selected_track"] == SAMPLE_TRACK
        assert result["transition"]["type"] == "beatmatch fade"


# ---------------------------------------------------------------------------
# playlist_builder tests
# ---------------------------------------------------------------------------


class TestPlaylistBuilder:
    def _make_builder(self, tmp_path, monkeypatch):
        """Return a PlaylistBuilder with a pre-loaded library and mocked brain."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from playlist_builder import PlaylistBuilder

        # Write a small library
        db = tmp_path / "tracks.json"
        db.write_text(json.dumps([SAMPLE_TRACK]))

        with patch("dj_brain.anthropic.Anthropic"):
            builder = PlaylistBuilder(db_path=db)
        return builder

    def test_export_json(self, tmp_path, monkeypatch):
        builder = self._make_builder(tmp_path, monkeypatch)
        out = tmp_path / "set.json"
        from playlist_builder import PlaylistBuilder

        PlaylistBuilder.export_json(SAMPLE_PLAN, out)
        data = json.loads(out.read_text())
        assert data["reasoning"] == "Great energy build."

    def test_export_m3u(self, tmp_path, monkeypatch):
        builder = self._make_builder(tmp_path, monkeypatch)
        out = tmp_path / "set.m3u"
        plan = {**SAMPLE_PLAN, "filters": {"mood": "peak"}}
        from playlist_builder import PlaylistBuilder

        PlaylistBuilder.export_m3u(plan, out)
        content = out.read_text()
        assert "#EXTM3U" in content
        assert "Strings of Life" in content
        assert "#EXTINF" in content

    def test_build_raises_when_no_candidates(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from playlist_builder import PlaylistBuilder

        # Empty library
        db = tmp_path / "tracks.json"
        db.write_text("[]")

        with patch("dj_brain.anthropic.Anthropic"):
            builder = PlaylistBuilder(db_path=db)
            with pytest.raises(ValueError, match="No tracks matched"):
                builder.build(mood="peak time")

    def test_build_adds_filters_to_plan(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from playlist_builder import PlaylistBuilder

        db = tmp_path / "tracks.json"
        db.write_text(json.dumps([SAMPLE_TRACK]))

        with patch("dj_brain.anthropic.Anthropic") as MockAnth:
            mock_client = MockAnth.return_value
            mock_client.messages.create.return_value = _make_mock_response(
                json.dumps(SAMPLE_PLAN)
            )
            builder = PlaylistBuilder(db_path=db)
            plan = builder.build(mood="deep groove", genre="house", duration_minutes=30)

        assert plan["filters"]["mood"] == "deep groove"
        assert plan["filters"]["genre"] == "house"
        assert plan["filters"]["duration_minutes"] == 30


# ---------------------------------------------------------------------------
# dj_server tests (FastAPI TestClient)
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_client(tmp_path, monkeypatch):
    """Provide a FastAPI TestClient with a temporary track DB."""
    monkeypatch.setenv("DJ_TRACKS_DB", str(tmp_path / "tracks.json"))
    monkeypatch.delenv("DJ_API_KEY", raising=False)
    # Ensure server module is reloaded so env vars take effect
    import importlib

    import dj_server

    importlib.reload(dj_server)

    from fastapi.testclient import TestClient

    return TestClient(dj_server.app)


class TestDJServer:
    def test_health_returns_ok(self, test_client):
        resp = test_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_list_tracks_empty(self, test_client):
        resp = test_client.get("/tracks")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_add_track_success(self, test_client):
        resp = test_client.post("/tracks", json=SAMPLE_TRACK)
        assert resp.status_code == 201
        assert "added" in resp.json()["message"].lower()

    def test_add_track_invalid_genre(self, test_client):
        bad = {**SAMPLE_TRACK, "genre": "reggaeton"}
        resp = test_client.post("/tracks", json=bad)
        assert resp.status_code == 422

    def test_add_track_invalid_bpm(self, test_client):
        bad = {**SAMPLE_TRACK, "bpm": 5}
        resp = test_client.post("/tracks", json=bad)
        assert resp.status_code == 422

    def test_list_tracks_after_add(self, test_client):
        test_client.post("/tracks", json=SAMPLE_TRACK)
        resp = test_client.get("/tracks")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_remove_track_success(self, test_client):
        test_client.post("/tracks", json=SAMPLE_TRACK)
        resp = test_client.delete(f"/tracks/{SAMPLE_TRACK['title']}")
        assert resp.status_code == 200
        assert resp.json()["message"] != ""

    def test_remove_track_not_found(self, test_client):
        resp = test_client.delete("/tracks/Nonexistent")
        assert resp.status_code == 404

    def test_search_tracks_by_genre(self, test_client):
        test_client.post("/tracks", json=SAMPLE_TRACK)
        resp = test_client.get("/tracks/search?genre=house")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_tracks_no_match(self, test_client):
        test_client.post("/tracks", json=SAMPLE_TRACK)
        resp = test_client.get("/tracks/search?genre=techno")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_generate_playlist_no_api_key(self, test_client, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        test_client.post("/tracks", json=SAMPLE_TRACK)
        resp = test_client.post("/playlist", json={"mood": "peak time"})
        assert resp.status_code == 500
        assert "ANTHROPIC_API_KEY" in resp.json()["detail"]

    def test_generate_playlist_no_candidates(self, test_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        # Library is empty → no candidates
        resp = test_client.post("/playlist", json={"mood": "peak time"})
        assert resp.status_code == 422
        assert "No tracks" in resp.json()["detail"]

    def test_generate_playlist_success(self, test_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        test_client.post("/tracks", json=SAMPLE_TRACK)

        with patch("dj_brain.anthropic.Anthropic") as MockAnth:
            mock_client = MockAnth.return_value
            mock_client.messages.create.return_value = _make_mock_response(
                json.dumps(SAMPLE_PLAN)
            )
            resp = test_client.post("/playlist", json={"mood": "peak time"})

        assert resp.status_code == 200
        data = resp.json()
        assert "playlist" in data
        assert data["reasoning"] == "Great energy build."
