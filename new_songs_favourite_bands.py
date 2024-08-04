import os
import pylast
import pickle
import spotipy
import spotipy.util as util

# Spotify login data (get yours at https://developer.spotify.com/ and replace the dummy values)
os.environ["SPOTIPY_CLIENT_ID"] = "dummy"
os.environ["SPOTIPY_CLIENT_SECRET"] = "dummy"
os.environ["SPOTIPY_REDIRECT_URI"] = "http://localhost:8888/callback"
scope = 'playlist-modify-public'
token = util.prompt_for_user_token("dummy", scope)

# Last.fm API credentials (get yours at https://www.last.fm/api/account/create and replace the dummy values)
API_KEY = "dummy"
API_SECRET = "dummy"
username = "dummy"
password_hash = pylast.md5("dummy")

#Spotify playlist ID (see e.g. https://clients.caster.fm/knowledgebase/110/How-to-find-Spotify-playlist-ID.html and replace the dummy value)
playlist_id = "dummy"

# Spotify instance
spotifyObject = spotipy.Spotify(auth=token)

# Last.fm network instance
network_instance = pylast.LastFMNetwork(
    api_key=API_KEY,
    api_secret=API_SECRET,
    username=username,
    password_hash=password_hash,
)

# get user's library instance
library_instance = pylast.Library(
    user=username,
    network=network_instance
)

def get_recent_tracks(filename):
    if os.path.exists(filename):
        #get from pickle file
        with open(filename, 'r+b') as file:
            return pickle.load(file)
    else:
        #download from last.fm and pickle to file
        user_instace = network_instance.get_user(username)
        recent_tracks = user_instace.get_recent_tracks(limit=None)
        with open(filename, 'wb') as file:
            pickle.dump(recent_tracks, file)
            return recent_tracks

def get_top_artists(library, limit=100): #default: get the top 100 artists of a user
    return library.get_artists(limit=limit)

def get_global_top_tracks(artist, network, limit=2): #default: get the top 2 tracks of a artist
    artist_instance = pylast.Artist(artist, network)
    return artist_instance.get_top_tracks(limit=limit)

def is_track_in_users_tracks(track, artist_name, recent_tracks):
    return any(recent_track.track.get_name().lower() == track.get_title().lower() and
               recent_track.track.get_artist().get_name().lower() == artist_name.lower() 
               for recent_track in recent_tracks)

def search_spotify_track(spotify, artist_name, track_title):
    search_results = spotify.search(q=f"artist:{artist_name} track:{track_title}", type="track")
    if search_results['tracks']['items']:
        return search_results['tracks']['items'][0]['uri']
    return None

def calculate_penalty_score(artist_count, song_count):
    return song_count * (artist_count + 0.1) # higher penalty score for less frequent songs or artist, +0.1 as tie breaker

def main():
    recent_tracks_file = "recent_tracks2.p"
    recent_tracks = get_recent_tracks(recent_tracks_file)
    top_artists = get_top_artists(library_instance)

    song_uri_to_song_penalty_scores = {}
    artist_count = 1

    for top_artist in top_artists:
        global_top_tracks_of_artist = get_global_top_tracks(top_artist.item, network_instance) #find global top tracks of user's top artist
        song_count = 1
        for global_top_track_of_artist in global_top_tracks_of_artist:
            artist_name = top_artist.item.get_name()
            track_title = global_top_track_of_artist.item.get_title()
            if not is_track_in_users_tracks(global_top_track_of_artist.item, artist_name, recent_tracks): # check if user played the global top track already
                uri = search_spotify_track(spotifyObject, artist_name, track_title) #get spotify instance of that track
                if uri:
                    song_uri_to_song_penalty_scores[uri] = calculate_penalty_score(artist_count, song_count) #save spotify instance and penalty score
                    song_count += 1
        artist_count += 1

    sorted_songs = dict(sorted(song_uri_to_song_penalty_scores.items(), key=lambda item: item[1]))# sort by penalty score
    
    for uri, score in sorted_songs.items():
        spotifyObject.playlist_add_items(playlist_id, [uri], position=0) #add song to spotify playlist

if __name__ == "__main__":
    main()