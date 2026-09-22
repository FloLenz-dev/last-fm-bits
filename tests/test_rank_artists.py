from collections import defaultdict
from unittest.mock import Mock

import pytest

from rank_artists import (
    ArtistScore,
    calculate_scores,
    get_required_env,
    get_similar_artists_cached,
    load_artists_from_file,
    merge_scoreboards,
    parse_args,
    retry_with_backoff,
    update_scoreboard_if_match,
)


def test_add_score():
    scoreboard = defaultdict(ArtistScore)

    update_scoreboard_if_match(
        scoreboard,
        {"Radiohead"},
        "Radiohead",
        5.0,
        root_artist="Rainbow",
    )

    assert scoreboard["Radiohead"].total_score == 5.0
    assert scoreboard["Radiohead"].sources["Rainbow"] == 5.0

def test_score_accumulates():
    scoreboard = defaultdict(ArtistScore)

    update_scoreboard_if_match(
        scoreboard,
        {"Radiohead"},
        "Radiohead",
        5.0,
        root_artist="Rainbow",
    )

    update_scoreboard_if_match(
        scoreboard,
        {"Radiohead"},
        "Radiohead",
        2.0,
        root_artist="Rainbow",
    )

    assert scoreboard["Radiohead"].total_score == 7.0
    assert scoreboard["Radiohead"].sources["Rainbow"] == 7.0

def test_artist_not_in_target_is_ignored():
    scoreboard = defaultdict(ArtistScore)

    update_scoreboard_if_match(
        scoreboard,
        {"Radiohead"},
        "Muse",
        5.0,
        root_artist="Muse",
    )

    assert len(scoreboard) == 0

def test_non_matching_artist_does_not_modify_existing_score():
    scoreboard = defaultdict(ArtistScore)
    scoreboard["Radiohead"].total_score = 10.0

    update_scoreboard_if_match(
        scoreboard,
        {"Radiohead"},
        "Muse",
        5.0,
        root_artist="Rainbow",
    )

    assert scoreboard["Radiohead"].total_score == 10.0

def test_merge_adds_new_keys():
    a = defaultdict(
        ArtistScore,
        {
            "Radiohead": ArtistScore(
                total_score=5.0,
                sources=defaultdict(float, {"Tool": 5.0}),
            )
        },
    )

    b = defaultdict(
        ArtistScore,
        {
            "Muse": ArtistScore(
                total_score=2.0,
                sources=defaultdict(float, {"Aphex Twin": 2.0}),
            )
        },
    )

    result = merge_scoreboards(a, b)

    assert result["Radiohead"].total_score == 5.0
    assert result["Radiohead"].sources["Tool"] == 5.0
    assert result["Muse"].total_score == 2.0
    assert result["Muse"].sources["Aphex Twin"] == 2.0

def test_merge_does_not_modify_original():
    a = defaultdict(
        ArtistScore,
        {
            "Radiohead": ArtistScore(
                total_score=5.0,
                sources=defaultdict(float, {"Tool": 5.0}),
            )
        },
    )

    b = defaultdict(
        ArtistScore,
        {
            "Radiohead": ArtistScore(
                total_score=2.0,
                sources=defaultdict(float, {"Aphex Twin": 2.0}),
            )
        },
    )

    result = merge_scoreboards(a, b)

    assert a["Radiohead"].total_score == 5.0

    assert result["Radiohead"].total_score == 7.0
    assert result["Radiohead"].sources["Tool"] == 5.0
    assert result["Radiohead"].sources["Aphex Twin"] == 2.0

def test_load_artists_removes_duplicates(tmp_path):
    file = tmp_path / "artists.txt"

    file.write_text(
        "Radiohead\nMuse\nRadiohead\n",
        encoding="utf8"
    )

    artists = load_artists_from_file(file)

    assert artists == {"Radiohead", "Muse"}

def test_load_artists_ignores_empty_lines(tmp_path):
    file = tmp_path / "artists.txt"

    file.write_text(
        "\nRadiohead\n\nMuse\n",
        encoding="utf8"
    )

    artists = load_artists_from_file(file)

    assert artists == {"Radiohead", "Muse"}

def test_get_required_env_returns_value(monkeypatch):
    monkeypatch.setenv("TEST_KEY", "hello")

    assert get_required_env("TEST_KEY") == "hello"

def test_get_required_env_raises_for_missing_key():
    with pytest.raises(OSError):
        get_required_env("DOES_NOT_EXIST")

def test_retry_returns_immediately():
    result = retry_with_backoff(
        lambda: "success",
        retries=3,
    )

    assert result == "success"

def test_retry_recovers_after_failures():
    attempts = 0

    def flaky():
        nonlocal attempts

        attempts += 1

        if attempts < 3:
            raise ValueError("temporary failure")

        return "success"

    result = retry_with_backoff(
        flaky,
        retries=3,
    )

    assert result == "success"
    assert attempts == 3

def test_retry_returns_empty_list_for_permanently_invalid_artist():
    calls = 0

    def always_not_found():
        nonlocal calls
        calls += 1
        raise ValueError("Artist could not be found")

    result = retry_with_backoff(
        always_not_found,
        retries=3,
    )

    assert result == []
    assert calls == 1

def test_retry_waits_before_retrying_after_max_attempts(monkeypatch):
    sleep_calls = []

    monkeypatch.setattr(
        "rank_artists.sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    attempts = 0

    def flaky():
        nonlocal attempts

        attempts += 1

        if attempts < 3:
            raise ValueError("temporary failure")

        return "success"

    result = retry_with_backoff(
        flaky,
        retries=2,
        wait_time=600,
    )

    assert result == "success"
    assert attempts == 3
    assert sleep_calls == [600]

def test_similar_artists_are_cached():
    get_similar_artists_cached.cache_clear()

    calls = 0

    class FakeArtist:
        def get_similar(self, limit):
            nonlocal calls
            calls += 1
            return ["Muse"]

    artist = FakeArtist()

    result1 = get_similar_artists_cached(artist, 10)
    result2 = get_similar_artists_cached(artist, 10)

    assert result1 == ["Muse"]
    assert result2 == ["Muse"]
    assert calls == 1

def test_parse_args_defaults(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["rank_artists.py"]
    )

    args = parse_args()

    assert args.depth == 3
    assert args.breadth == 10
    assert args.file == "artists.txt"

def test_parse_args_explicit_values(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["rank_artists.py", "-f", "lineup.txt", "-d", "5", "-b", "20"]
    )

    args = parse_args()

    assert args.file == "lineup.txt"
    assert args.depth == 5
    assert args.breadth == 20

class MockArtist:
    def __init__(self, name):
        self.name = name

    def get_name(self):
        return self.name

class MockSimilarItem:
    def __init__(self, artist_name, match):
        self.item = MockArtist(artist_name)
        self.match = match

class MockTopArtist:
    def __init__(self, artist_name, weight):
        self.item = MockArtist(artist_name)
        self.weight = weight

@pytest.fixture
def artists_file(tmp_path):
    file = tmp_path / "artists.txt"
    file.write_text(
        "\n".join([
            "Muse",
            "Blur",
            "Placebo",
            "Archive",
            "Poison",
            "Cinderella",
        ])
    )
    return str(file)

def test_calculate_scores(artists_file, monkeypatch):
    top_artists = [
        MockTopArtist("Radiohead", 100),
        MockTopArtist("Muse", 50),
    ]

    def fake_create_lastfm_network():
        user = Mock()

        user.get_top_artists.return_value = top_artists

        network = Mock()
        network.get_user.return_value = user

        return network, "testuser"

    def fake_get_similar_artists_cached(artist, breadth):
        mapping = {
            "Radiohead": [
                MockSimilarItem("Muse", 0.8),
                MockSimilarItem("Blur", 0.6),
                MockSimilarItem("Coldplay", 0.4),
            ],
            "Muse": [
                MockSimilarItem("Placebo", 0.5),
                MockSimilarItem("Archive", 0.25),
            ],
            "Blur": [
                MockSimilarItem("Placebo", 0.5),
                MockSimilarItem("Poison", 0.5),
            ],
            "Poison": [
                MockSimilarItem("Cinderella", 0.5),
            ]
        }

        return mapping.get(artist.name, [])

    monkeypatch.setattr(
        "rank_artists.create_lastfm_network",
        fake_create_lastfm_network,
    )

    monkeypatch.setattr(
        "rank_artists.get_similar_artists_cached",
        fake_get_similar_artists_cached,
    )

    scores = calculate_scores(
        filepath=artists_file,
        depth=3,
        breadth=10,
    )

    assert "Muse" in scores
    assert "Blur" in scores
    assert "Archive" in scores
    assert "Placebo" in scores
    assert "Poison" in scores

    assert "Radiohead" not in scores
    assert "Coldplay" not in scores
    assert "Cinderella" not in scores

    assert scores["Muse"].total_score == 130
    assert scores["Blur"].total_score == 60
    assert scores["Archive"].total_score == 32.5
    assert scores["Placebo"].total_score == 95

    assert scores["Placebo"].sources["Radiohead"] == 70

    assert scores["Placebo"].sources == {
        "Radiohead": 70,
        "Muse": 25,
    }

def _mock_top_artists_network(top_artists):
    def fake_create_lastfm_network():
        user = Mock()
        user.get_top_artists.return_value = top_artists

        network = Mock()
        network.get_user.return_value = user

        return network, "testuser"

    return fake_create_lastfm_network

def test_calculate_scores_depth_1_scores_every_top_artist(tmp_path, monkeypatch):
    """
    Regression test: at depth=1, every top artist must receive its own
    direct score. Only the traversal into *similar* artists is skipped -
    processing of subsequent top artists must not be aborted.

    (Previously, `calculate_scores` aborted the entire top-artist loop
    after the first artist at depth=1, silently dropping all following
    top artists - including their own direct score.)
    """
    artists_file = tmp_path / "artists.txt"
    artists_file.write_text("Radiohead\nMuse\nBlur")

    top_artists = [
        MockTopArtist("Radiohead", 100),
        MockTopArtist("Muse", 50),
        MockTopArtist("Blur", 30),
    ]

    monkeypatch.setattr(
        "rank_artists.create_lastfm_network",
        _mock_top_artists_network(top_artists),
    )
    monkeypatch.setattr(
        "rank_artists.get_similar_artists_cached",
        lambda artist, breadth: [],
    )

    scores = calculate_scores(
        filepath=str(artists_file),
        depth=1,
        breadth=10,
    )

    assert scores["Radiohead"].total_score == 100
    assert scores["Muse"].total_score == 50
    assert scores["Blur"].total_score == 30