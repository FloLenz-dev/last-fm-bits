import os
import pylast
from dotenv import load_dotenv
from functools import lru_cache
from tqdm import tqdm
from time import sleep
from collections import defaultdict

# Load environment variables from .env file
load_dotenv()

# Last.fm API credentials
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_API_SECRET = os.getenv("LASTFM_API_SECRET")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME")
last_fm_password_hash = pylast.md5(os.getenv("LASTFM_PASSWORD"))

# Last.fm network instance
lastfm_network_instance = pylast.LastFMNetwork(
    api_key=LASTFM_API_KEY,
    api_secret=LASTFM_API_SECRET,
    username=LASTFM_USERNAME,
    password_hash=last_fm_password_hash,
)

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
                tqdm.write(f"Error: {e}, waiting {wait_time//60} minutes before retry...")
                sleep(wait_time)
                wait_time+=600

@lru_cache(maxsize=100000)
def get_similar_artists_cached(artist):
   """ Retrieves similar artists for a given artist, with caching for performance reasons """ 
   return artist.get_similar(limit=10)
     
def update_scoreboard_if_match(scoreboard, input_artists, artist, score):
    """Adds or updates an artist's score in the scoring list if the artist is in the input list"""

    if artist in input_artists:
        scoreboard[artist] += score
    return scoreboard

def load_artists_from_file(filepath: str = "artists.txt") -> set[str]:
    with open(filepath, "r", encoding="utf-8") as file:
        return {line.strip() for line in file if line.strip()}

def main():
    scoreboard = defaultdict(float)
    input_artists = load_artists_from_file()
    
    top_artists = retry_with_backoff(lambda: lastfm_network_instance.get_user(LASTFM_USERNAME).get_top_artists(limit=10, period=pylast.PERIOD_OVERALL)) 
    
    for top_artist in tqdm(top_artists, desc="Top Artist"):

        score = int(top_artist.weight) #How popular ist the artist with the user?
        scoreboard = update_scoreboard_if_match(scoreboard, input_artists, top_artist.item.name, score) #if top_artist is in input list, add it to scoring list

        for similar_artist in tqdm(
            retry_with_backoff(lambda: get_similar_artists_cached(top_artist.item)),
            desc=f"Similar to {top_artist.item.name}",
            leave=False
        ):
            score_similar_artist = int(top_artist.weight) * float(similar_artist.match) #How popular is the top artist with the use * how similar is the similar artist?
            scoreboard = update_scoreboard_if_match(scoreboard, input_artists, similar_artist.item.name, score_similar_artist)

            for similar_similar_artist in  get_similar_artists_cached(similar_artist.item):
                if (similar_similar_artist == top_artist): 
                    continue #Don't count it again
                score_similar_similiar_artist = score_similar_artist * float(similar_similar_artist.match)
                scoreboard =  update_scoreboard_if_match (scoreboard, input_artists, similar_similar_artist.item.get_name(), score_similar_similiar_artist)
    
    sorted_artists = dict(sorted(scoreboard.items(), key=lambda item: item[1], reverse=True))# sort descending by score
    
    for artist, score in sorted_artists.items():
        print(f"{artist}: {round(score, 2)}")
    print("Cache-Statistik:")
    print(get_similar_artists_cached.cache_info())
if __name__ == "__main__":
    main()

