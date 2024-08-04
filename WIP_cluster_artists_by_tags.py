import pylast
import pickle
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import numpy as np



# You have to have your own unique two values for API_KEY and API_SECRET
# Obtain yours from https://www.last.fm/api/account/create for Last.fm
API_KEY = "dummy"  # this is a sample key
API_SECRET = "dummy"

# In order to perform a write operation you need to authenticate yourself
username = "dummy"
password_hash = pylast.md5("dummy")

network_instance = pylast.LastFMNetwork(
    api_key=API_KEY,
    api_secret=API_SECRET,
    username=username,
    password_hash=password_hash,
)

library_instance = pylast.Library(
    user = username,
    network = network_instance
)

top_artists = library_instance.get_artists(
    #user = "dummy",
    limit = 1000,
    #page = 1,
    #api_key = API_KEY
)

#vectorize
artist2tag2weight = dict()
global_tag_list = []
for top_artist in top_artists:
    artist2tag2weight[top_artist.item.name] = dict()
    top_tags = pylast.Artist.get_top_tags(
    self = top_artist.item,
    limit = 1000
    )
    for tag in top_tags:
        if not tag.item.name in global_tag_list:
            global_tag_list.append(tag.item.name)
        artist2tag2weight[top_artist.item.name][tag.item.name] = int(tag.weight)

artist_names = []
artists_tags_matrix = []
for top_artist in top_artists:
    artist_names.append(top_artist.item.name)
    tags_vector = []
    for tag in global_tag_list:
        if tag in artist2tag2weight[top_artist.item.name].keys():
            tags_vector.append(artist2tag2weight[top_artist.item.name][tag])
        else:
            tags_vector.append(0)
    artists_tags_matrix.append(tags_vector)
X = np.array(artists_tags_matrix)
best_score = -2
best_cluster_count = 1
for n in range(2,3):
    kmeans = KMeans(n_clusters=n, random_state=0, n_init="auto").fit(X)
    if silhouette_score(X, kmeans.fit_predict(X)) > best_score:
        best_cluster_count = n
        best_score = silhouette_score(X, kmeans.fit_predict(X))
        print(best_cluster_count)
        print(best_score)
                        # best is 223 for 1000 artists
kmeans = KMeans(n_clusters=2, random_state=0, n_init="auto").fit(X)
center2artist = {}
for counter in range(len(kmeans.labels_)):
    if kmeans.labels_[counter] in center2artist.keys():
        center2artist[kmeans.labels_[counter]].append(artist_names[counter])
    else:
        center2artist[kmeans.labels_[counter]] = [artist_names[counter]]

print (center2artist)


counter1 = 0
counter2 = 0
for cluster_center1 in kmeans.cluster_centers_:
    definining_tags = set()
    for cluster_center2 in kmeans.cluster_centers_:
        counter2 += 1
        if counter1 == (counter2-1): continue
        max_diff = 0
        max_diff_n = -1
        for n in range(len(global_tag_list)):
            if (cluster_center1[n] - cluster_center2[n]) > max_diff:
                max_diff = cluster_center1[n] - cluster_center2[n]
                max_diff_n = n
        #print(str(counter1) + " " + str(global_tag_list[max_diff_n]) + " " + str(counter2-1))
        definining_tags.add(global_tag_list[max_diff_n])
    print(counter1)
    print(definining_tags)
    counter2 = 0
    counter1 += 1


#print(global_tag_list)
#print(kmeans.cluster_centers_)