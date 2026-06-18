from collections import defaultdict

import pytest

from rank_artists import update_scoreboard_if_match, load_artists_from_file, get_required_env, \
    retry_with_backoff, get_similar_artists_cached, parse_args, merge_scoreboards, ArtistScore


def test_add_score():
    scoreboard = defaultdict(ArtistScore)

    update_scoreboard_if_match(
        scoreboard,
        {"Radiohead"},
        "Radiohead",
        5.0,
        root_artist="Rainbow"
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
        'Rainbow'
    )

    update_scoreboard_if_match(
        scoreboard,
        {"Radiohead"},
        "Radiohead",
        2.0,
        'Rainbow'
    )

    assert scoreboard["Radiohead"].total_score == 7.0
    assert scoreboard["Radiohead"].sources['Rainbow'] == 7.0

def test_artist_not_in_target_is_ignored():
    scoreboard = defaultdict(ArtistScore)

    update_scoreboard_if_match(
        scoreboard,
        {"Radiohead"},
        "Muse",
        5.0,
        root_artist="Muse"
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
        'Rainbow'
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
    with pytest.raises(EnvironmentError):
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