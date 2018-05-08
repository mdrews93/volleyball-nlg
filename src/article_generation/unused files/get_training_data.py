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

import matplotlib
matplotlib.use('TkAgg')

import matplotlib.pyplot as plt
import matplotlib as mpl
from urllib.error import HTTPError
import pickle
import random
from nltk.corpus import words


def main():

    try:
        urls = pickle.load(open("urls.p", "rb"))
        print("Loaded {} urls.".format(len(urls)))
    except:
        print("Downloading article urls...")
        urls = get_article_urls()
        print("Downloaded {} urls.".format(len(urls)))
        print("Saved {} urls to urls.p".format(len(urls)))
        pickle.dump(urls, open("urls.p", "wb"))

    try:
        all_sentences = pickle.load(open("sentences.p", "rb"))
        articles = pickle.load(open("article_dicts.p", "rb"))
        print("Loaded {} sentences.".format(len(all_sentences)))
    except:
        print("Retrieving sentences from articles...")
        all_sentences = []
        articles = []
        num_articles = 0
        for idx, url in enumerate(urls):
            print("Article {}/{}".format(idx, len(urls)))
            # TODO: return result, num_sets
            sentence_list, result, num_sets = get_sentences("http://www.illinoistechathletics.com" + url)
            if sentence_list:
                if sentence_list[1] not in all_sentences:
                    all_sentences.extend(sentence_list)
                    # TODO: make article_sentences -> articles list of dictionaries that contain sentences, result, num_sets
                    articles.append({"sentences": sentence_list, "result": result, "num_sets": num_sets})
                    num_articles += 1
        print("Saving {} sentences to sentences.p from {} articles".format(len(all_sentences), num_articles))
        print("Saving list of each article dictionaries to article_dicts.p")
        pickle.dump(all_sentences, open("sentences.p", "wb"))
        pickle.dump(articles, open("article_dicts.p", "wb"))

    print("Extracted {} sentences.".format(len(all_sentences)))

    # tfidf_vectorizer = TfidfVectorizer(max_df=1.0, max_features=200000,
    #                                    min_df=0.01, ngram_range=(1, 3))
    #
    # single_vecotr = tfidf_vectorizer.fit_transform([all_sentences[0]])

    vec, km, clusters = cluster(all_sentences)

    print("\n")
    sequences = []
    result2seq = defaultdict(lambda: [])
    num_sets2seq = defaultdict(lambda: [])
    result_and_num_sets2seq = defaultdict(lambda: [])
    for article in articles:
        sequence = get_sentence_sequence(article["sentences"], vec, km)
        sequences.append(sequence)
        # print(article)
        # print("{} - {}".format(len(sequence), sequence))
        result2seq[article["result"]].append(sequence)
        num_sets2seq[article["num_sets"]].append(sequence)
        result_and_num_sets2seq[article["result"] + " " + str(article["num_sets"])].append(sequence)

    # for key in result_and_num_sets2seq:
        # print("Result: {} - Sequences: {}".format(key, result_and_num_sets2seq[key]))



    # Basic approach - given the result and number of sets, pick a random sequence from the possible lists
    # TODO: given a new score (W/L + num_sets), compute the most likely cluster sequence

    # TODO: get these values from a url
    match_results = "W"
    num_sets = 3

    sample_sequence = random.choice(result_and_num_sets2seq[match_results + " " + str(num_sets)])

    print("\nSample sequence: {}".format(sample_sequence))

    # Basic approach: for each cluster, retrieve a sentence from that cluster

    # TODO: given the likeliest cluster sequence, compute a sentence for each cluster
    body = ""
    for cluster_idx in sample_sequence:
        body += random.sample(clusters[cluster_idx], 1)[0] + ". "

    print("\n\n\nArticle:\n")
    print(body)




# def find_unique_words(sentences):
#     unique = []
#     corpus = set(i.lower() for i in words.words('en'))
#     for sentence in sentences:
#         for word in sentence.split():
#             if word.lower() not in corpus:
#                 unique.append(word)
#     return unique


def get_sentence_sequence(sentences, vec, km):
    sent2vec = vec.transform(sentences)
    sequence = km.predict(sent2vec)

    return sequence




def cluster(sentences):
    # define vectorizer parameters
    # TODO: investigate tfidf normalization (default is L2)
    # tfidf_vectorizer = TfidfVectorizer(max_df=1.0, max_features=200000,
    #                                    min_df=0.01, ngram_range=(1, 3))
    #
    # tfidf_matrix = tfidf_vectorizer.fit_transform(sentences)
    #
    # vec = tfidf_vectorizer.fit(sentences)
    #
    # # dist = 1 - cosine_similarity(tfidf_matrix)
    #
    num_clusters = 45
    # km = KMeans(n_clusters=num_clusters)
    # km.fit(tfidf_matrix)

    vectorizer = TfidfVectorizer(min_df=0, max_df=0.5, stop_words="english", ngram_range=(1, 3))
    vec = vectorizer.fit(sentences)  # train vec using list1
    vectorized = vec.transform(sentences)  # transform list1 using vec
    km = KMeans(n_clusters=num_clusters, init='k-means++', n_init=10, max_iter=1000, tol=0.0001, precompute_distances=True,
                verbose=0, random_state=None, n_jobs=1)
    km.fit(vectorized)
    list2Vec = vec.transform([sentences[1]])  # transform list2 using vec

    print(sentences[1])
    print(km.predict(list2Vec))

    clusters = km.labels_.tolist()
    cluster_contents = []

    for idx in range(num_clusters):
        cluster_contents.append({s for i, s in enumerate(sentences) if clusters[i] == idx})
        print("Sentences in cluster {}: {}".format(idx, cluster_contents[idx]))

    return vec, km, cluster_contents


# dist = 1 - cosine_similarity(tfidf_matrix)
    #
    # linkage_matrix = ward(dist)
    #
    # fig, ax = plt.subplots(figsize=(15, 20))  # set size
    # ax = dendrogram(linkage_matrix, orientation="right", labels=all_sentences)
    #
    # plt.tick_params( \
    #     axis='x',  # changes apply to the x-axis
    #     which='both',  # both major and minor ticks are affected
    #     bottom='off',  # ticks along the bottom edge are off
    #     top='off',  # ticks along the top edge are off
    #     labelbottom='off')
    #
    # plt.savefig('word_clusters.png', dpi=400)


# TODO: nltk sentence splitter
def process(string, opponents, players):
    #TODO: improve <SCORE> (don't include records or stat comparisons) (one keyword: "outdug", "outblocked", "led"
    #TODO: "blocks (three solo)"


    results = string.lower()

    if "how it happened" in results:
        return ["how it happened"]
    if "stats to know" in results:
        return ["stats to know"]


    results = re.sub("\.[ ]*–[ ]*", " – ", results)
    results = re.sub("\.[ ]*-[ ]*", " - ", results)
    results = re.sub("p\.m\.", "pm", results)
    results = re.sub("a\.m\.", "am", results)
    results = re.sub("st\.", "st", results)

    results = re.sub("(^| )illinois tech($| |,|')", r"\1<IIT>\2", results)
    results = re.sub("(^| )illinois institute of technology($| |,|')", r"\1<IIT>\2", results)
    results = re.sub("(^| )tech($| |,|')", r"\1<IIT>\2", results)
    results = re.sub("(^| )scarlet hawks($| |'|,)", r"\1<IIT_MASCOT>\2", results)
    results = re.sub("(^| )scarlet hawk($| |'|,)", r"\1<IIT_MASCOT>\2", results)
    results = re.sub("(^| )hawks($| |'|,)", r"\1<IIT_MASCOT>\2", results)

    if "<IIT_MASCOT> standouts" in results:
        return ["<IIT_MASCOT> standouts"]

    for player in players:
        results = re.sub("(^| |,)" + player + "($| |,|')", r"\1<IIT_PLAYER>\2", results)
        results = re.sub("(^| |,)" + player.split(" ", 1)[1] + "($| |,|')", r"\1<IIT_PLAYER>\2", results)

    for opponent in opponents:
        results = re.sub("(^| )" + opponent + "($| )", r"\1<OPP>\2", results)

    results = re.sub("<OPP> [0-9], <IIT> [0-9]", "<OPP> <OPP_SETS>, <IIT> <IIT_SETS>", results)
    results = re.sub("<IIT> [0-9], <OPP> [0-9]", "<IIT> <IIT_SETS>, <OPP> <OPP_SETS>", results)

    if re.search("<OPP> [0-9], <OPP> [0-9]:", results):
        print(string)
        print(opponents)

    results = re.sub("[-]?\.[0-9]{3}%?", "<HIT_PERCENTAGE>", results)

    if re.search("digs", results):
        results = re.sub("(one|two|three|four|five|six|seven|eight|nine|[0-9]{1,2}) digs", "<DIGS>", results)
        results = re.sub("digs \((one|two|three|four|five|six|seven|eight|nine|[0-9]{1,2})\)", "<DIGS>", results)

    if re.search("kills", results):
        results = re.sub("(one|two|three|four|five|six|seven|eight|nine|[0-9]{1,2}) (total )?kills", "<KILLS>", results)
        results = re.sub("kills \((one|two|three|four|five|six|seven|eight|nine|[0-9]{1,2})\)", "<KILLS>", results)

    if re.search("block assist(s)?", results):
        results = re.sub("(one|two|three|four|five|six|seven|eight|nine|[0-9]{1,2}) block assist[s]?", "<BLOCK_ASSISTS>", results)
        results = re.sub("block assist[s]? \((one|two|three|four|five|six|seven|eight|nine|[0-9]{1,2})\)",
                         "<BLOCK_ASSISTS>", results)

    if re.search("assists", results):
        results = re.sub("(one|two|three|four|five|six|seven|eight|nine|[0-9]{1,2}) assists", "<ASSISTS>", results)
        results = re.sub("assists \((one|two|three|four|five|six|seven|eight|nine|[0-9]{1,2})\)", "<ASSISTS>", results)

    if re.search("(service)? aces", results):
        results = re.sub("(one|two|three|four|five|six|seven|eight|nine|[0-9]{1,2}) (service )? ace(s)?", "<ACES>", results)
        results = re.sub("(service)?[ ]? ace(s)? \((one|two|three|four|five|six|seven|eight|nine|[0-9]{1,2})\)", " <ACES>",
                         results)


    results = re.sub("([0-9]{1,2}[ ]*-[ ]*[0-9]{1,2})", "<SCORE>", results)
    results = re.sub("<SCORE>\.[^$]", "<SCORE>, ", results)
    results = re.sub("[-]?\.[0-9]{3} hit percentage", "<HIT_PERCENTAGE>", results)

    results = re.sub("[a-z]{3} [0-3][0-9], <YEAR>", "<GAME_DATE>", results)


    results = re.sub(u"\xa0", " ", results)

    results = re.sub("–", "-", results)
    results = re.sub("[ ]*-[ ]+", " - ", results)

    results = re.sub("set (one|two|three|four|five)", "<SET_NUM>", results)
    results = re.sub("(first|second|third|fourth|fifth) set", "<SET_NUM>", results)
    results = re.sub("<SET_NUM>. <IIT> [0-9]{1,2}, <OPP> [0-9]{1,2}", "<SET_NUM>: <IIT> <IIT_SET_SCORE>, <OPP> <OPP_SET_SCORE>", results)

    # results = re.sub(
    #     "([0-9]{1,2} *- *[0-9]{1,2})[ ]*,[ ]*([0-9]{1,2} *- *[0-9]{1,2})[ ]*\.[ ]*([0-9]{1,2} *- *[0-9]{1,2})",
    #     "\1, \2, \3", results)
    # results = re.sub(
    #     "([0-9]{1,2}[ ]*-[ ]*[0-9]{1,2})[ ]*\.[ ]*([0-9]{1,2}[ ]*-[ ]*[0-9]{1,2})[ ]*,[ ]*([0-9]{1,2}[ ]*-[ ]*[0-9]{1,2})",
    #     "\1, \2, \3", results)
    # results = re.sub(
    #     "([0-9]{1,2}[ ]*-[ ]*[0-9]{1,2})[ ]*\.[ ]*([0-9]{1,2}[ ]*-[ ]*[0-9]{1,2})[ ]*\.[ ]*([0-9]{1,2}[ ]*-[ ]*[0-9]{1,2})",
    #     "\1, \2, \3", results)
    if "<OPP> 3: <IIT> 25" in string:
        print(string)

    return results.split(".")



def get_sentences(url):
    req = Request(url,
                  headers={'User-Agent': 'Mozilla/5.0'})

    resp = urlopen(req).read()
    soup = BeautifulSoup(resp, "html5lib")

    article_soup = soup.find(name="div", class_="article-text")

    opponents = [elt.string.lower() for elt in soup.findAll(name="div", class_="name")]

    try:
        opp_results = soup.find(name="div", class_="scorebox vis").text.split("\n")
        opponents.append(opp_results[1].lstrip(" ").lower())

        opp_set = int(opp_results[2].lstrip(" "))

        iit_set = int(soup.find(name="div", class_="scorebox home").text.split("\n")[2].lstrip(" "))

        match_results = "W" if iit_set > opp_set else "L"
        num_sets = opp_set + iit_set
    except Exception as err:
        print("Exception {} for URL: {}".format(err, url))
        match_results = "O"
        num_sets = 0

    try:
        ul = article_soup.find(name="ul")
        for li in ul.findAll(name="li"):
            li = li.string
            opponents.append(re.split(" [0-9]", li)[0].lower().lstrip())
            opponents.append(li.split(", ")[1].split(" ")[0].lower().lstrip())
    except:
        pass

    if "tech" in opponents:
        opponents.remove("tech")
    if "illinois tech" in opponents:
        opponents.remove("illinois tech")

    for idx, opp in enumerate(opponents):
        opponents[idx] = re.sub("^#[0-9]{1,2} ", "", opp)

    opponents = set(opponents)

    candidate_sentences = []

    for candidate in article_soup.text.split("\n"):
        if candidate.lstrip():
            candidate_sentences.append(candidate.lstrip())

    sentences = []

    players = ["mihailo djuric", "ben peschl", "easton kays", "derek bostick", "lukasz kupiec", "cinjun coe",
               "eric adam", "daniel throop", "hani salameh", "steven komendanchik", "evan robeck", "andriy bench",
               "Courtney Curcio", "Courtney Darling", "Reya Green", "Claire Pantell", "Kayla Frazier", "Taylor Burton",
               "Justine Bracco", "Lydia Goebel", "Jelena Vujicic", "Sinjin Acuna", "Katherine McCutcheon",
               "Natalie Freund", "Leah van der Sanden", "Caitlyn Kenneally", "Alyssa Miner", "Sara Hassell",
               "Cassie Hansen", "Irena Grauzinis", "Chelsea Badiola", "Claire Fraeyman", "Julie Kipta-Skutnik",
               "Adriane Walther", "Elizabeth Woltman", "Taylor Duman", "Shea Manley", "Alex Babusci","Ryan Barnes",
               "Kyle Bumpass", "Michael Drews", "Victor Garcia", "Allan Huang", "Irshad Hussain", "Filip Letkiewicz",
               "Sahil Rana", "Julian Salas", "Paulo Sassmannschausen", "Kevin Schroeder", "Andrew Woltman",
               "David Allen", "Arvin Bahrami", "Yuriy Shepta"]

    players = set([player.lower() for player in players])

    for sentence in candidate_sentences:
        sentences.extend(process(sentence, opponents, players))

    sentences = [x.rstrip(".").lstrip(chr(8211) + " ") for x in sentences]

    return sentences, match_results, num_sets


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


# def find_unique_team_names(urls):
#     teams = {}
#     for url in urls:
#         req = Request("http://www.illinoistechathletics.com"+url,
#                       headers={'User-Agent': 'Mozilla/5.0'})
#
#         resp = urlopen(req).read()
#         soup = BeautifulSoup(resp, "html5lib")
#
#         article_soup = soup.find(name="div", class_="article-text")
#
#         try:
#             teams[article_soup.find(name="ul").text.split("(")[0]] = [elt.string for elt in soup.findAll(name="div", class_="name")]
#         except Exception as err:
#             print(err)
#             print(article_soup.find(name="ul"))
#             print(url)
#
#     return teams


if __name__ == "__main__":
    main()