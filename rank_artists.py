import os
import pylast
from dotenv import load_dotenv
from functools import lru_cache
from tqdm import tqdm
from time import sleep
from collections import defaultdict
from typing import List
import argparse


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
    scoreboard: defaultdict[str, float],
    target_artists: set[str],
    artist: str,
    score: float,
) -> defaultdict[str, float]:
    """Adds or updates an artist's score in the scoring list if the artist is in the input list"""

    if artist in target_artists:
        scoreboard[artist] += score
    return scoreboard


def load_artists_from_file(filepath: str = "artists.txt") -> set[str]:
    with open(filepath, "r", encoding="utf-8") as file:
        return {line.strip() for line in file if line.strip()}


def merge_defaultdicts(
    a: defaultdict[str, float], b: dict[str, float]
) -> defaultdict[str, float]:
    result = defaultdict(float, a)  # copy of a
    for key, value in b.items():
        result[key] += value
    return result


def recursive_scoring_by_similar_artists(
    artist: pylast.SimilarItem,
    score_parent_artist: float,
    target_artists: set[str],
    breadth: int,
    current_depth: int,
    max_depth: int,
) -> defaultdict[str, float]:
    """score by artist similarity, recursivly look at neighbours of neighbours"""
    scoreboard: defaultdict[str, float] = defaultdict(float)

    if current_depth >= max_depth:
        return scoreboard  # terminate if maximum depth is reached

    # else look for neighbours of provided artists calculate their similarity scores, add them if suitable and call the function recursivly again
    for similar_artist in tqdm(
        retry_with_backoff(lambda: get_similar_artists_cached(artist.item, breadth)),
        desc=f"Similar to {artist.item.name}",
        leave=False,
    ):
        score_similar_artist = score_parent_artist * float(similar_artist.match) 
        scoreboard =  update_scoreboard_if_match (scoreboard, target_artists, similar_artist.item.get_name(), score_similar_artist)
        scoreboard =  merge_defaultdicts(scoreboard, recursive_scoring_by_similar_artists(similar_artist, score_similar_artist, target_artists, breadth, current_depth +1 , max_depth))
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


def main() -> None:
    args = parse_args()
    scoreboard: defaultdict[str, float] = defaultdict(float)
    target_artists = load_artists_from_file(args.file)
    max_depth = args.depth
    breadth = args.breadth
    current_depth = 1
    lastfm_network_instance, lastfm_username = create_lastfm_network()
    top_artists = retry_with_backoff(
        lambda: lastfm_network_instance.get_user(lastfm_username).get_top_artists(
            limit=breadth, period=pylast.PERIOD_OVERALL
        )
    )

    for top_artist in tqdm(top_artists, desc="Top Artist"):

        score = float(
            top_artist.weight
        )  # How popular ist the artist with the user? top_artist.weight is an int, but since score is an float...
        scoreboard = update_scoreboard_if_match(
            scoreboard, target_artists, top_artist.item.name, score
        )  # if top_artist is in input list, add it to scoring list
        for similar_artist in tqdm(
            retry_with_backoff(
                lambda: get_similar_artists_cached(top_artist.item, args.breadth)
            ),
            desc=f"Similar to {top_artist.item.name}",
            leave=False,
        ):
            score_similar_artist = float(top_artist.weight) * float(similar_artist.match) #How popular is the top artist with the use * how similar is the similar artist?
            scoreboard = update_scoreboard_if_match(scoreboard, target_artists, similar_artist.item.name, score_similar_artist)
            if current_depth == max_depth:
                break
            scoreboard =  merge_defaultdicts(scoreboard, recursive_scoring_by_similar_artists(similar_artist, score_similar_artist, target_artists, breadth, current_depth + 1 , max_depth))

    sorted_artists = dict(
        sorted(scoreboard.items(), key=lambda item: item[1], reverse=True)
    )  # sort descending by score

    for artist, score in sorted_artists.items():
        print(f"{artist}: {round(score, 2)}")
    print("Cache-Statistik:")
    print(get_similar_artists_cached.cache_info())


if __name__ == "__main__":
    main()
