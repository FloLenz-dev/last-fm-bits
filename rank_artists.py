import os
from copy import deepcopy
from dataclasses import dataclass, field

import pylast
from dotenv import load_dotenv
from functools import lru_cache
from tqdm import tqdm
from time import sleep
from collections import defaultdict
from typing import List, Any
import argparse


@dataclass
class ArtistScore:
    total_score: float = 0.0
    sources: defaultdict[str, float] = field(
        default_factory=lambda: defaultdict(float)
    )

def parse_args():
    parser = argparse.ArgumentParser(
        description="Score input artists based on similarity to a user's Last.fm top artists."
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default="artists.txt",
        help="Path to the input file containing artist names (default: 'artists.txt').",
    )
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=3,
        help="Maximum recursion depth when traversing similar artists (default: 3).",
    )
    parser.add_argument(
        "-b",
        "--breadth",
        type=int,
        default=10,
        help="Number of top artists to fetch from the user profile (default: 10).",
    )
    return parser.parse_args()


def get_required_env(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise EnvironmentError(f"Environment variable {key} is required")
    return value


def retry_with_backoff(func, *args, retries=10, wait_time=600, **kwargs):
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            attempt += 1
            if attempt < retries:
                tqdm.write(f"Error: {e}, retrying...")
            else:
                tqdm.write(
                    f"Error: {e}, waiting {wait_time//60} minutes before retry..."
                )
                sleep(wait_time)
                wait_time += 600


@lru_cache(maxsize=100000)
def get_similar_artists_cached(
    artist: pylast.Artist, breadth=10
) -> List[pylast.SimilarItem]:
    """Retrieves similar artists for a given artist, with caching for performance reasons"""
    return artist.get_similar(limit=breadth)


def update_scoreboard_if_match(
    scoreboard: defaultdict[str, ArtistScore],
    target_artists: set[str],
    artist: str,
    score: float,
    root_artist: str,
) -> defaultdict[str, ArtistScore]:
    """Adds or updates an artist's score in the scoring list if the artist is in the input list"""

    if artist in target_artists:
        scoreboard[artist].total_score += score
        scoreboard[artist].sources[root_artist] += score
    return scoreboard


def load_artists_from_file(filepath: str = "artists.txt") -> set[str]:
    with open(filepath, "r", encoding="utf-8") as file:
        return {line.strip() for line in file if line.strip()}


def merge_scoreboards(
    scoreboard1: defaultdict[str, ArtistScore],
    scoreboard2: defaultdict[str, ArtistScore],
) -> defaultdict[str, ArtistScore]:

    result = deepcopy(scoreboard1)
    for artist, score_data in scoreboard2.items():
        result[artist].total_score += score_data.total_score

        for source, contribution in score_data.sources.items():
            result[artist].sources[source] += contribution

    return result


def recursive_scoring_by_similar_artists(
    artist: pylast.SimilarItem,
    root_artist: str,
    score_parent_artist: float,
    target_artists: set[str],
    breadth: int,
    current_depth: int,
    max_depth: int,
) -> defaultdict[str, ArtistScore]:
    """score by artist similarity, recursively look at neighbors of neighbors"""
    scoreboard: defaultdict[str, ArtistScore] = defaultdict(ArtistScore)

    if current_depth >= max_depth:
        return scoreboard  # terminate if maximum depth is reached

    # else look for neighbors of provided artists calculate their similarity scores, add them if suitable and call the function recursively again
    for similar_artist in tqdm(
        retry_with_backoff(lambda: get_similar_artists_cached(artist.item, breadth)),
        desc=f"Similar to {artist.item.name}",
        leave=False,
    ):
        score_similar_artist = score_parent_artist * float(similar_artist.match) 
        scoreboard =  update_scoreboard_if_match (
            scoreboard, target_artists, similar_artist.item.get_name(), score_similar_artist, root_artist
        )
        scoreboard =  merge_scoreboards(
            scoreboard,
            recursive_scoring_by_similar_artists(
                similar_artist, root_artist, score_similar_artist, target_artists, breadth, current_depth +1 , max_depth
            )
        )
    return scoreboard


# Load environment variables from .env file
def create_lastfm_network():
    load_dotenv()

    api_key = get_required_env("LASTFM_API_KEY")
    api_secret = get_required_env("LASTFM_API_SECRET")
    username = get_required_env("LASTFM_USERNAME")
    password = get_required_env("LASTFM_PASSWORD")

    network = pylast.LastFMNetwork(
        api_key=api_key,
        api_secret=api_secret,
        username=username,
        password_hash=pylast.md5(password),
    )

    return network, username

@lru_cache(maxsize=1000)
def get_artist_tags(artist_name: str) -> list[Any | None]:

    network, _ = create_lastfm_network()

    artist = network.get_artist(artist_name)

    tags = artist.get_top_tags()

    return [
        tag.item.name
        for tag in tags[:3]
    ]

def calculate_scores(
    filepath: str,
    depth: int,
    breadth: int,
    progress_callback=None,
    status_callback=None,
) -> dict[str, ArtistScore]:

    if progress_callback is None:
        progress_callback = lambda current, total: None

    if status_callback is None:
        status_callback = lambda message: None

    scoreboard: defaultdict[str, ArtistScore] = defaultdict(ArtistScore)


    target_artists = load_artists_from_file(filepath)
    max_depth = depth
    current_depth = 1

    status_callback("Connecting to Last.fm...")
    lastfm_network_instance, lastfm_username = create_lastfm_network()

    status_callback("Fetching top artists...")
    top_artists = retry_with_backoff(
        lambda: lastfm_network_instance.get_user(lastfm_username).get_top_artists(
            limit=breadth,
            period=pylast.PERIOD_OVERALL,
        )
    )

    status_callback("Calculating scores...")

    total_artists = len(top_artists)

    for index, top_artist in enumerate(
    tqdm(top_artists, desc="Top Artist"),
        start=1
    ):
        progress_callback(index, total_artists)

        score = float(top_artist.weight)

        scoreboard = update_scoreboard_if_match(
            scoreboard,
            target_artists,
            top_artist.item.name,
            score,
            top_artist.item.name,
        )

        for similar_artist in tqdm(
            retry_with_backoff(
                lambda: get_similar_artists_cached(
                    top_artist.item,
                    breadth,
                )
            ),
            desc=f"Similar to {top_artist.item.name}",
            leave=False,
        ):

            score_similar_artist = (
                float(top_artist.weight)
                * float(similar_artist.match)
            )

            scoreboard = update_scoreboard_if_match(
                scoreboard,
                target_artists,
                similar_artist.item.name,
                score_similar_artist,
                top_artist.item.name
            )

            if current_depth == max_depth:
                break

            scoreboard = merge_scoreboards(
                scoreboard,
                recursive_scoring_by_similar_artists(
                    similar_artist,
                    top_artist.item.name,
                    score_similar_artist,
                    target_artists,
                    breadth,
                    current_depth + 1,
                    max_depth,
                ),
            )

    return dict(
        sorted(
            scoreboard.items(),
            key=lambda item: item[1].total_score,
            reverse=True,
        )
    )


def main() -> None:
    args = parse_args()

    sorted_artists = calculate_scores(
        filepath=args.file,
        depth=args.depth,
        breadth=args.breadth,
    )

    for artist, score_data in sorted_artists.items():
        print(f"{artist}: {score_data.total_score:.2f}")

    print("Cache-Statistic:")
    print(get_similar_artists_cached.cache_info())

if __name__ == "__main__":
    main()
