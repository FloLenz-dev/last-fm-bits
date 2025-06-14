import os
import pylast
from dotenv import load_dotenv
from functools import lru_cache
from tqdm import tqdm

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

def get_personal_top_artists(username, network_instance):
    """ Retrieves the top artists for a given Last.fm user """

    while True: #try until success, because e.g. missing internet connection can trigger errors on many retries, still finally work
         try:
              top_artists = network_instance.get_user(username).get_top_artists(limit=10, period=pylast.PERIOD_OVERALL)
         except Exception as e:
              print(f"Error on getting top artists, {e}, retry...")
              continue
         break
    return top_artists

@lru_cache(maxsize=100000)
def get_similar_artists_cached(artist):
   """ Retrieves similar artists for a given artist, with caching for performance reasons """ 
   while True: #try until success, because e.g. missing internet connection can trigger errors on many retries, still finally work
         try:
              similar_artists = artist.get_similar(limit=10)
         except Exception as e:
              print(f"Error on getting similiar artists, {e}, retry...")
              continue
         break
   return similar_artists
     
def add_to_scoring_list_if_in_input_list(scoring_list, input_artists, artist, score):
    """Adds or updates an artist's score in the scoring list if the artist is in the input list"""

    if artist in input_artists:
        if artist in scoring_list:
            scoring_list[artist] += score
        else:
            scoring_list[artist] = score
    return scoring_list

def main():
    scoreboard = {}
    input_artists = set(["Aborted", "Acranius", "Aetherian", "After The Burial", "The Amity Affliction", "Amon Amarth", "Angstskríg", "Ankor", "Architects", "Arkona", "Armored Dawn", 
    "Asphyx", "Avralize", "The Baboon Show", "Before The Dawn", "Behemoth", "The Black Dahlia Murder", "Blasmusik Illenschwang", "Blind Channel", "Bodysnatcher", "Bokassa", "Brothers Of Metal", 
    "Brutal Sphincter", "Burning Witches", "The Butcher Sisters", "Callejon", "Carnation", "Cradle Of Filth", "Crypta", "Cult Of Fire", "Dark Tranquillity", "Dear Mother", "Defocus", "Delain", 
    "Disbelief", "Disentomb", "Dymytry", "Dynazty", "Eclipse", "Einherjer", "Embrace Your Punishment", "Emmure", "Enslaved", "Equilibrium", "Eradikated", "Erdling", "Ereb Altor", "Escuela Grind", 
    "Evil Invaders", "Exodus", "Eyes Wide Open", "Fall Of Serenity", "Fateful Finality", "Feuerschwanz", "Fixation", "Flogging Molly", "Future Palace", "Guilt Trip", "Halcyon Days", "Hand Of Juno", 
    "Heaven Shall Burn", "Hemelbestormer", "Heretoir", "Ignea", "Impalement", "Imperium Dekadenz", "Insanity Alert", "Insomnium", "J.B.O.", "Jesus Piece", "Jinjer", "Kampfar", "Korpiklaani", 
    "Kupfergold", "Leave.", "Lordi", "Lord Of The Lost", "Los Males Del Mundo", "Madball", "Mavis", "Megaherz", "Memoriam", "Mental Cruelty", "Meshuggah", "Moon Shot", "Moonspell", "Mørket", 
    "Motionless In White", "Myrkur", "Nachtblut", "Nakkeknaekker", "Neaera", "Necrophobic", "Necrotted", "Nestor", "The Night Eternal", "Nyktophobia", "Obscura", "The Ocean", "Orden Ogan", 
    "Our Promise", "Pain", "Paleface Swiss", "Palehørse", "Pest Control", "Plaguemace", "Punk Rock Factory", "Randale", "Rise Of The Northstar", "Robse", "Rotting Christ", "Samurai Pizza Cats", 
    "Shredhead", "Siamese", "Slow Fall", "Sodom", "Soulprison", "Spire Of Lazarus", "Spiritbox", "Spiritworld", "Stillbirth", "Subway To Sally", "Suotana", "Surprise Act", "Svalbard", "Sylosis", 
    "Ten56", "Tenside", "Thron", "Tilintetgjort", "Unearth", "Unprocessed", "Venues", "Viscera", "Voodoo Kiss", "Warkings", "Whitechapel", "Zerre"])
    
    top_artists = get_personal_top_artists(LASTFM_USERNAME, lastfm_network_instance)    
    
    for top_artist in tqdm(top_artists, desc="Top Artist"):

        score = int(top_artist.weight) #How popular ist the artist with the user?
        scoreboard = add_to_scoring_list_if_in_input_list(scoreboard, input_artists, top_artist.item.name, score) #if top_artist is in input list, add it to scoring list

        for similar_artist in tqdm(
            get_similar_artists_cached(top_artist.item),
            desc=f"Similar to {top_artist.item.name}",
            leave=False
        ):
            score = int(top_artist.weight) * float(similar_artist.match) #How popular is the top artist with the use * how similiar is the similiar artist?
            scoreboard = add_to_scoring_list_if_in_input_list(scoreboard, input_artists, similar_artist.item.name, score)

            for similar_similiar_artist in  get_similar_artists_cached(similar_artist.item):
                if (similar_similiar_artist == top_artist): 
                    continue #Don't count it again
                score = int(top_artist.weight) * float(similar_artist.match) * float(similar_similiar_artist.match)
                scoreboard =  add_to_scoring_list_if_in_input_list (scoreboard, input_artists, similar_similiar_artist.item.get_name(), score)
    
    sorted_artists = dict(sorted(scoreboard.items(), key=lambda item: item[1], reverse=True))# sort descending by score
    
    for artist, score in sorted_artists.items():
        print(f"{artist}: {round(score, 2)}")
    print("Cache-Statistik:")
    print(get_similar_artists_cached.cache_info())
if __name__ == "__main__":
    main()

