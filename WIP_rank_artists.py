import os
import pylast
import pickle
import spotipy
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Last.fm API credentials
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_API_SECRET = os.getenv("LASTFM_API_SECRET")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME")
last_fm_password_hash = pylast.md5(os.getenv("LASTFM_PASSWORD"))

print (LASTFM_API_KEY)

# Last.fm network instance
network_instance = pylast.LastFMNetwork(
    api_key=LASTFM_API_KEY,
    api_secret=LASTFM_API_SECRET,
    username=LASTFM_USERNAME,
    password_hash=last_fm_password_hash,
)

def get_personal_top_artists(username, network_instance):
    return network_instance.get_user(username).get_top_artists(limit=100, period=pylast.PERIOD_OVERALL)
    
def get_artist_instance(artist_name, network_instance):
    return network_instance.get_artist(artist_name)

def get_similiar_artists(artist):
    return artist.get_similar(limit=100)

def add_to_scoring_list_if_in_input_list(scoring_list, input_artists, artist, score):
    if artist in input_artists:
        print("\t" + artist)
        if artist in scoring_list:
            scoring_list[artist] += score
        else:
            scoring_list[artist] = score
    return scoring_list


def main():
    artists_to_scores = {}
    input_artists = ["Aborted", "Acranius", "Aetherian", "After The Burial", "The Amity Affliction", "Amon Amarth", "Angstskríg", "Ankor", "Architects", "Arkona", "Armored Dawn", 
    "Asphyx", "Avralize", "The Baboon Show", "Before The Dawn", "Behemoth", "The Black Dahlia Murder", "Blasmusik Illenschwang", "Blind Channel", "Bodysnatcher", "Bokassa", "Brothers Of Metal", 
    "Brutal Sphincter", "Burning Witches", "The Butcher Sisters", "Callejon", "Carnation", "Cradle Of Filth", "Crypta", "Cult Of Fire", "Dark Tranquillity", "Dear Mother", "Defocus", "Delain", 
    "Disbelief", "Disentomb", "Dymytry", "Dynazty", "Eclipse", "Einherjer", "Embrace Your Punishment", "Emmure", "Enslaved", "Equilibrium", "Eradikated", "Erdling", "Ereb Altor", "Escuela Grind", 
    "Evil Invaders", "Exodus", "Eyes Wide Open", "Fall Of Serenity", "Fateful Finality", "Feuerschwanz", "Fixation", "Flogging Molly", "Future Palace", "Guilt Trip", "Halcyon Days", "Hand Of Juno", 
    "Heaven Shall Burn", "Hemelbestormer", "Heretoir", "Ignea", "Impalement", "Imperium Dekadenz", "Insanity Alert", "Insomnium", "J.B.O.", "Jesus Piece", "Jinjer", "Kampfar", "Korpiklaani", 
    "Kupfergold", "Leave.", "Lordi", "Lord Of The Lost", "Los Males Del Mundo", "Madball", "Mavis", "Megaherz", "Memoriam", "Mental Cruelty", "Meshuggah", "Moon Shot", "Moonspell", "Mørket", 
    "Motionless In White", "Myrkur", "Nachtblut", "Nakkeknaekker", "Neaera", "Necrophobic", "Necrotted", "Nestor", "The Night Eternal", "Nyktophobia", "Obscura", "The Ocean", "Orden Ogan", 
    "Our Promise", "Pain", "Paleface Swiss", "Palehørse", "Pest Control", "Plaguemace", "Punk Rock Factory", "Randale", "Rise Of The Northstar", "Robse", "Rotting Christ", "Samurai Pizza Cats", 
    "Shredhead", "Siamese", "Slow Fall", "Sodom", "Soulprison", "Spire Of Lazarus", "Spiritbox", "Spiritworld", "Stillbirth", "Subway To Sally", "Suotana", "Surprise Act", "Svalbard", "Sylosis", 
    "Ten56", "Tenside", "Thron", "Tilintetgjort", "Unearth", "Unprocessed", "Venues", "Viscera", "Voodoo Kiss", "Warkings", "Whitechapel", "Zerre"]
    top_artists = get_personal_top_artists(LASTFM_USERNAME, network_instance)    
    
    for top_artist in top_artists:
        print (top_artist.item.name)
        score = int(top_artist.weight)
        artists_to_scores = add_to_scoring_list_if_in_input_list(artists_to_scores, input_artists, top_artist.item.name, score)
        neighbours_of_top_artist = get_similiar_artists(top_artist.item)
        
        for neighbour_of_top_artist in neighbours_of_top_artist:
            score = int(top_artist.weight) * float(neighbour_of_top_artist.match)
            artists_to_scores = add_to_scoring_list_if_in_input_list(artists_to_scores, input_artists, neighbour_of_top_artist.item.name, score)
            neighbours_of_neighbour_of_top_artist = get_similiar_artists(get_artist_instance(neighbour_of_top_artist.item.get_name(), network_instance))
            
            for neighbour_of_neighbour_of_top_artist in neighbours_of_neighbour_of_top_artist:
                if (neighbour_of_neighbour_of_top_artist == top_artist):
                    continue
                score = int(top_artist.weight) * float(neighbour_of_top_artist.match) * float(neighbour_of_neighbour_of_top_artist.match)
                artists_to_scores =  add_to_scoring_list_if_in_input_list(artists_to_scores, input_artists, neighbour_of_neighbour_of_top_artist.item.get_name(), score)
    
    sorted_artists = dict(sorted(artists_to_scores.items(), key=lambda item: item[1]))# sort descendin by score
    
    for artist, score in sorted_artists.items():
        print(f"{artist}: {score}")

if __name__ == "__main__":
    main()