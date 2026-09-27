import pytest

from gui.results_table import (
    TABLE_COLUMNS,
    TAG_COLORS,
    TAGS_CELL_TEMPLATE,
    build_row,
)
from rank_artists import ArtistScore


@pytest.fixture(autouse=True)
def fake_tags(monkeypatch):
    calls = []

    def fake_get_artist_tags(artist):
        calls.append(artist)
        return ["rock", "indie"]

    monkeypatch.setattr("gui.results_table.get_artist_tags", fake_get_artist_tags)
    return calls


def make_score(total, sources=None):
    score = ArtistScore(total_score=total)
    for artist, value in (sources or {}).items():
        score.sources[artist] = value
    return score


@pytest.mark.parametrize(
    "rank, expected",
    [(1, "🥇"), (2, "🥈"), (3, "🥉"), (4, 4), (17, 17)],
)
def test_rank_uses_medals_for_top_three(rank, expected):
    row = build_row(rank, "Radiohead", make_score(10.0), max_score=10.0)

    assert row["rank"] == expected


def test_bar_is_percentage_of_max_score():
    row = build_row(5, "Radiohead", make_score(2.5), max_score=10.0)

    assert row["bar"] == 25


def test_best_artist_gets_full_bar():
    row = build_row(1, "Radiohead", make_score(7.3), max_score=7.3)

    assert row["bar"] == 100


def test_score_is_rounded():
    row = build_row(1, "Radiohead", make_score(12.6), max_score=12.6)

    assert row["score"] == 13


def test_top_contributors_are_joined():
    score = make_score(10.0, {"Muse": 6.0, "Blur": 4.0})

    row = build_row(1, "Radiohead", score, max_score=10.0)

    assert row["top_contributors"] == "Muse (60%), Blur (40%)"


def test_no_contributors_gives_empty_string():
    row = build_row(1, "Radiohead", make_score(0.0), max_score=1)

    assert row["top_contributors"] == ""


def test_tags_are_fetched_for_artist(fake_tags):
    row = build_row(1, "Radiohead", make_score(10.0), max_score=10.0)

    assert row["tags"] == ["rock", "indie"]
    assert fake_tags == ["Radiohead"]


def test_row_has_a_value_for_every_column():
    row = build_row(1, "Radiohead", make_score(10.0), max_score=10.0)

    assert {column["field"] for column in TABLE_COLUMNS} == set(row)


def test_tags_template_contains_all_colors():
    assert "COLORS" not in TAGS_CELL_TEMPLATE
    assert f"% {len(TAG_COLORS)}]" in TAGS_CELL_TEMPLATE
    for color in TAG_COLORS:
        assert f"'{color}'" in TAGS_CELL_TEMPLATE
