# last-fm-bits
Tools using the last.fm API

This project is meant to utilize the last.fm API for various insideful or fun uses.

# Features
## new_songs_favourite_bands.py
- Retrieve the top tracks of your favorite artists from Last.fm.
- Selects the ones you haven't listen to yet
- Add the selected to one of your spotify playlists

## WIP_cluster_artists_by_tags.py
- Select your favorite artists from Last.fm
- clusters them by k-means-clustering based on their tags
- TO-DO: more sophisticated clustering with better results, code-cleanup

## rank_artists.py
- Ranks a list of artists (e.g. a festival lineup) based on their similarity to your Last.fm listening history.
- uses the similar Artist Option of last.fm
- TO-DO: do reverse search


# Setup

**install python packages**

pip install -r requirements.txt

**Obtain API Keys:**

   - **Spotify:**
     - Register your application on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications).
     - Note your `Client ID`, `Client Secret`, and set a `Redirect URI`.

   - **Last.fm:**
     - Sign up or log in to [Last.fm](https://www.last.fm/api) and create an application to get your `API Key` and `API Secret`.
  
  Copy .env.example to .env and fill in your credentials.
  
**for new_songs_favourite_bands bit: Get a Spotify Premium account**
The use of the Spotify API requires an account with active premium subscription

# Example
## Call
python rank_artists.py --file artists.txt --depth 3 --breadth 10

## Result
Radiohead: 5321.2
Muse: 4820.1
The National: 4510.3

# License
This project is licensed under the MIT License.
