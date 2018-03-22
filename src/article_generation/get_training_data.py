from collections import defaultdict, namedtuple
import pickle
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import re
import datetime
from dateutil.parser import parse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from scipy.cluster.hierarchy import ward, dendrogram
import matplotlib.pyplot as plt
import matplotlib as mpl
from urllib.error import HTTPError


def main():

    urls = get_article_urls()
    print("Downloaded {} urls.".format(len(urls)))

    all_sentences = []
    article_sentences = []
    for url in urls:
        sentence_list = get_sentences("http://www.illinoistechathletics.com" + url)
        all_sentences.extend(sentence_list)
        article_sentences.append(sentence_list)

    print("Extracted {} sentences.".format(len(all_sentences)))
    # define vectorizer parameters
    # TODO: investigate tfidf normalization (default is L2)
    tfidf_vectorizer = TfidfVectorizer(max_df=1.0, max_features=200000,
                                       min_df=0.01, ngram_range=(1, 3))

    tfidf_matrix = tfidf_vectorizer.fit_transform(all_sentences)

    # dist = 1 - cosine_similarity(tfidf_matrix)

    num_clusters = 30
    km = KMeans(n_clusters=num_clusters)
    km.fit(tfidf_matrix)
    clusters = km.labels_.tolist()

    print(clusters)

    print("Sentences in cluster 0: {}".format({s for idx, s in enumerate(all_sentences) if clusters[idx] == 0}))
    print("\nSentences in cluster 1: {}".format({s for idx, s in enumerate(all_sentences) if clusters[idx] == 1}))
    print("\nSentences in cluster 2: {}".format({s for idx, s in enumerate(all_sentences) if clusters[idx] == 2}))
    print("\nSentences in cluster 3: {}".format({s for idx, s in enumerate(all_sentences) if clusters[idx] == 3}))
    print("\nSentences in cluster 4: {}".format({s for idx, s in enumerate(all_sentences) if clusters[idx] == 4}))
    print("\nSentences in cluster 5: {}".format({s for idx, s in enumerate(all_sentences) if clusters[idx] == 5}))
    print("\nSentences in cluster 0: {}".format({s for idx, s in enumerate(all_sentences) if clusters[idx] == 6}))

    dist = 1 - cosine_similarity(tfidf_matrix)

    linkage_matrix = ward(dist)

    fig, ax = plt.subplots(figsize=(15, 20))  # set size
    ax = dendrogram(linkage_matrix, orientation="right", labels=all_sentences)

    plt.tick_params( \
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom='off',  # ticks along the bottom edge are off
        top='off',  # ticks along the top edge are off
        labelbottom='off')

    plt.savefig('ward_clusters.png', dpi=400)

# TODO: nltk sentence splitter
def process(string):
    results =  re.sub("\. –", " –", string)
    results = re.sub("p\.m\.", "pm", results)
    results = re.sub("a\.m\.", "am", results)
    results = re.sub("St\.", "St", results)
    return results.lower().split(". ")


def get_sentences(url):
    req = Request(url,
                  headers={'User-Agent': 'Mozilla/5.0'})

    resp = urlopen(req).read()
    soup = BeautifulSoup(resp, "html5lib")

    article_soup = soup.find(name="div", class_="article-text")

    sentences = []

    for candidate in article_soup.text.split("\n"):
        if candidate.lstrip():
            sentences.append(candidate.lstrip())

    results = []

    for sentence in sentences:
        results.extend(process(sentence))

    results = [x.rstrip(".").lstrip(chr(8211) + " ") for x in results]

    return results


def get_article_urls():
    years = ["2017-18", "2016-17", "2015-16", "2014-15"]
    genders = ["m", "w"]
    urls = []
    base_url = "http://www.illinoistechathletics.com/sports/"

    for gender in genders:
        for year in years:
            try:
                url = base_url + gender + "vball/" + year + "/schedule"
                req = Request(url,
                              headers={'User-Agent': 'Mozilla/5.0'})
                resp = urlopen(req).read()
                soup = BeautifulSoup(resp, "html5lib")
                for link in soup.find(name="div", class_="schedule-content").find_all('a', href=True):
                    if "Recap" in link.text:
                        urls.append(link["href"])
            except HTTPError as err:
                print("{} for {}".format(err, url))


    return urls

if __name__ == "__main__":
    main()
