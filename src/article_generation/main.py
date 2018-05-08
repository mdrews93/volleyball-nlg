import random
from collections import defaultdict, namedtuple, Counter
import pickle
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import re
import datetime

import numpy as np

from data_retrieval import get_data, get_set_vectors

import pandas as pd

percentage_diff_dict = pickle.load(open("./data/percentage_diff_dict.p", "rb"))
percentage_score_dict = pickle.load(open("./data/percentage_score_dict.p", "rb"))


def main():
    # boxscore_url = "http://www.illinoistechathletics.com/sports/mvball/2017-18/boxscores/20180210_29pk.xml?tmpl=vbxml-monospace-template"
    # site_url = "http://www.illinoistechathletics.com/sports/mvball/2017-18/boxscores/20180210_29pk.xml?"
    # playbyplay_url = "http://www.illinoistechathletics.com/sports/mvball/2017-18/boxscores/20180210_29pk.xml?view=plays"
    schedule_url = "http://www.illinoistechathletics.com/sports/mvball/2017-18/schedule"

    boxscore_url = "http://www.illinoistechathletics.com/sports/mvball/2017-18/boxscores/20180202_0ap1.xml?tmpl=vbxml-monospace-template"
    site_url = "http://www.illinoistechathletics.com/sports/mvball/2017-18/boxscores/20180202_0ap1.xml"
    playbyplay_url = "http://www.illinoistechathletics.com/sports/mvball/2017-18/boxscores/20180202_0ap1.xml?view=plays"

    player_to_wpa = defaultdict(lambda: 0)
    player_to_max_wpa = defaultdict(lambda: {"max": 0, "play": None})
    player_to_min_wpa = defaultdict(lambda: {"min": 999, "play": None})

    points, iit_ids, iit_players = get_play_logs(playbyplay_url)

    for point in points:
        update_wpas(player_to_wpa, player_to_max_wpa, player_to_min_wpa, point, iit_ids)

    print_player_wpas(player_to_wpa, iit_players, player_to_max_wpa, player_to_min_wpa)

    info_dict, stats_dict, set_scores, team_set_attacks = get_stats(boxscore_url)
    info_dict["template_boxscore_link"] = site_url
    info_dict["template_current_date"] = datetime.datetime.today().strftime('%m-%d-%Y')

    complete_info_dict(info_dict, stats_dict, set_scores, team_set_attacks)

    home, away = get_teams(set_scores, site_url)

    opponent = ""
    if set_scores["home"]["total"] == "3" and home == "Illinois Tech":
        result = "W"
    elif set_scores["away"]["total"] == "3" and away == "Illinois Tech":
        result = "W"
    else:
        result = "L"
        print("Result: L - Home: {} ({}), Away: {} ({})".format(home, set_scores["home"]["total"], away, set_scores["away"]["total"]))

    if home == "Illinois Tech":
        opponent = info_dict["template_visitor_name"]
    else:
        opponent = info_dict["template_home_name"]


    if "mvb" in info_dict["template_boxscore_link"]:
        gender = "Men"
    else:
        gender = "Women"

    num_sets = int(set_scores["home"]["total"]) + int(set_scores["away"]["total"])

    article_dicts, all_sentences_dict, kmeans, dataframe, art_to_box, box_to_art = get_data()

    set_vectors = get_set_vectors(points)
    clusters = kmeans.predict(np.array(list(set_vectors.values())))

    print(clusters)

    corpus = get_corpus(article_dicts, result, num_sets)

    # this was the naive approach
    # template_sentences = get_template_sentences(corpus)

    with open("blank_template/template2.html", "r+") as input_file:
        txt = input_file.read()
        soup = BeautifulSoup(txt, "html5lib")

        for element in soup.find_all(lambda tag: tag.get('class') and list(filter(re.compile("template*").match, tag.get('class')))):
            filtered_class = list(filter(re.compile("template*").match, element.get('class')))[0]
            try:
                if element.name == "a":
                    element["href"] = info_dict[filtered_class]
                else:
                    element.string = str(info_dict[filtered_class])
            except Exception as err:
                element.string = filtered_class

        # pick a random image
        soup.find(name="img")["src"] = "./../data/{}.jpg?max_width=450".format(random.choice(range(1, 8)))

        title = generate_title(info_dict, result, opponent, gender, num_sets)
        soup.find(name="h1", class_="template_title").string = title
        soup.find(name="title").string = title

        # TODO: bold the location
        intro = generate_intro(info_dict, result, opponent, gender, num_sets)
        soup.find(name="p", class_="intro").string = intro

        score_summary = generate_score_summary(info_dict, set_scores, num_sets)
        score_summary_li = soup.new_tag("li")
        score_summary_li.string = score_summary
        soup.find(name="p", class_="scores").next_sibling.next_sibling.append(score_summary_li)

        summaries = generate_set_summaries(stats_dict, info_dict, dataframe, clusters,
                                           points, opponent, away, set_scores)
        for summary in summaries:
            summary_li = soup.new_tag("li")
            summary_li.string = summary
            soup.find(name="p", class_="happened").next_sibling.next_sibling.append(summary_li)

        standouts = generate_standouts(stats_dict)
        for standout in standouts:
            stat_li = soup.new_tag("li")
            stat_li.string = standout
            soup.find(name="p", class_="standouts").next_sibling.next_sibling.append(stat_li)

        stats = generate_stats(stats_dict, info_dict, opponent)
        for stat in stats:
            stat_li = soup.new_tag("li")
            stat_li.string = stat
            soup.find(name="p", class_="stats").next_sibling.next_sibling.append(stat_li)

        up_next = generate_up_next(schedule_url, boxscore_url)
        next_li = soup.new_tag("li")
        next_li.string = up_next
        soup.find(name="p", class_="next").next_sibling.next_sibling.append(next_li)

        filename = "./results/generated_article_{date:%Y-%m-%d %H:%M:%S}.html".format(date=datetime.datetime.now())
        with open(filename, "w+") as output_file:
            output_file.seek(0)
            output_file.truncate()
            # with open("output.html", "w+") as output:
            #     output.seek(0)
            #     output.truncate()
            output_file.write(str(soup))


def generate_title(info_dict, result, opponent, gender, num_sets):
    corpus = {
        # One Class for W
        "W": [
            "<GENDER>'s Volleyball <good-verb> <OPP>",
            "Scarlet Hawks <good-verb> <OPP>",
            "<GENDER>'s Volleyball <good-verb> <OPP> <SET-SCORE>",
            "Scarlet Hawks <good-verb> <OPP> <SET-SCORE>",
            "<GENDER>'s Volleyball Impresses In Win Over <OPP>",
            "<GENDER>'s Volleyball <good-verb> <OPP> in <NUM-SETS>-Set Match",
            "Scarlet Hawks <good-verb> <OPP> in <NUM-SETS>-Set Match"
        ],

        # One class for L
        "L": [
            "<bad-adj> Opponent <lose-verb> <GENDER>'s Volleyball",
            "<bad-adj> <OPP> Team <lose-verb> <GENDER>'s Volleyball",
            "<GENDER>'s Volleyball Battles <bad-adj> Opponent",
            "<OPP> <lose-verb> <GENDER>'s Volleyball",
            "<GENDER>'s Volleyball Defeated by <OPP>",
            "<GENDER>'s Volleyball Falls to <OPP>",
            "<GENDER>'s Volleyball Drops <NUM-SETS>-Set Match at <OPP>"
        ],
        "bad-adj": ["Tough", "Strong", "Solid"],
        "lose-verb": ["Beats", "Tops", "Defeats"],
        "good-verb": ["Sweeps", "Shuts Out", "Cruises Past"]
    }

    if info_dict["template_home_name"] == opponent:
        set_score = info_dict["template_visitor_sets"] + "-" + info_dict["template_home_sets"]
    else:
        set_score = info_dict["template_home_sets"] + "-" + info_dict["template_visitor_sets"]

    template = random.choice(corpus[result])
    title = re.sub("<GENDER>", gender, template)
    title = re.sub("<OPP>", opponent, title)
    title = re.sub("<good-verb>", random.choice(corpus["good-verb"]), title)
    title = re.sub("<SET-SCORE>", set_score, title)
    title = re.sub("<bad-adj>", random.choice(corpus["bad-adj"]), title)
    title = re.sub("<lose-verb>", random.choice(corpus["lose-verb"]), title)
    title = re.sub("<NUM-SETS>", str(num_sets), title)

    return title


def generate_intro(info_dict, result, opponent, gender, num_sets):
    corpus = {
        "first": {
            "W": [
                "<LOCATION> - The Illinois Tech <GENDER>'s volleyball team <played-verb> <OPP>, <win-verb> in <NUM-SETS> sets.",
                "<LOCATION> - The Scarlet Hawks played <good-adj> <NUM-SETS>-set match against <OPP>.",
                "<LOCATION> - The Scarlet Hawks played <good-adj> <NUM-SETS>-set match versus <OPP>, <win-verb> <SET-SCORE>."
            ],
            "L": [
                "<LOCATION> - The Illinois Tech <GENDER>'s volleyball team <lost-verb> <OPP>, <losing-verb> in <NUM-SETS> sets."
            ]

        },
        "second": {
            "W": [
                "The <event-noun> <moved-verb> Scarlet Hawks to a <RECORD> overall record on the season. "

            ],
            "L": [
                "<despite-np> the <result> <moved-verb> Scarlet Hawks to a <RECORD> overall record."

            ]

        },
        "played-verb": ["defeated", "beat", "outplayed", "outworked"],
        "win-verb": ["overcoming them", "winning the match"],
        "lost-verb": ["lost to", "were beaten by", "were defeated by", "couldn't beat", "couldn't overcome", "fell to"],
        "losing-verb": ["losing the match", "falling short"],
        "good-adj": ["a fun", "an exciting", "a great"],
        "event-noun": ["day's match", "day's event", "match", "game"],
        "moved-verb": ["has moved the", "moved the", "brings the", "has brought the"],
        "despite-np": ["Despite a strong effort,", "Despite a good performance,", "Despite their best efforts,",
                       "While the Hawks battled hard,", "While the Hawks worked hard,"],
        "result": ["loss", "tough loss", "match", "result"]

    }

    if info_dict["template_home_name"] == opponent:
        set_score = info_dict["template_visitor_sets"] + "-" + info_dict["template_home_sets"]
        record = info_dict["template_visitor_record"]
    else:
        set_score = info_dict["template_home_sets"] + "-" + info_dict["template_visitor_sets"]
        record = info_dict["template_home_record"]

    sents = [random.choice(corpus["first"][result]), random.choice(corpus["second"][result])]
    results = ""
    for sent in sents:
        sent = re.sub("<LOCATION>", info_dict["template_location"], sent)
        sent = re.sub("<GENDER>", gender, sent)
        sent = re.sub("<played-verb>", random.choice(corpus["played-verb"]), sent)
        sent = re.sub("<OPP>", opponent, sent)
        sent = re.sub("<win-verb>", random.choice(corpus["win-verb"]), sent)
        sent = re.sub("<NUM-SETS>", str(num_sets), sent)
        sent = re.sub("<good-adj>", random.choice(corpus["good-adj"]), sent)
        sent = re.sub("<SET-SCORE>", set_score, sent)
        sent = re.sub("<lost-verb>", random.choice(corpus["lost-verb"]), sent)
        sent = re.sub("<losing-verb>", random.choice(corpus["losing-verb"]), sent)
        sent = re.sub("<event-noun>", random.choice(corpus["event-noun"]), sent)
        sent = re.sub("<moved-verb>", random.choice(corpus["moved-verb"]), sent)
        sent = re.sub("<RECORD>", record, sent)
        sent = re.sub("<despite-np>", random.choice(corpus["despite-np"]), sent)
        sent = re.sub("<result>", random.choice(corpus["result"]), sent)

        results += sent + "\n"

    return results


# TODO: investigate given current set vector, find closest one and use those sentences
def generate_set_summaries(stats_dict, info_dict, dataframe, clusters, points, opponent, away, set_scores):

    corpus = {
        "easy win": {
            "first": [
                "<IIT> <good-verb> for set <SET_NUM>. ",
                "For set <SET_NUM>, <IIT> <good-verb>. ",
                "It didn't take long for <IIT> to <lead-verb> in set <SET_NUM>. ",
                "In set <SET_NUM>, <IIT> <good-verb> over <OPP>. ",
                "<IIT> was quick to <lead-verb> in set <SET_NUM>. "
            ],
            "second": [
                "<IIT-2> scored <POINTS_TO_START> points in the first <FIRST_PART_POINTS> to bring the score to <FIRST_PART_SCORE>. ",
                "<IIT-2> went on a <BEST_RUN> run to build a <BEST_RUN_SCORE> lead. ",
                "After going on a <BEST_RUN> run, <IIT> led by <BEST_RUN_SCORE>. ",
                "<IIT-2> held the lead for <NUM_LEADING> points. ",
                "<IIT-2> held the lead for <NUM_LEADING> points on their way to <victory-path>. "
            ],
            "third": [
                "The set ended with a final score of <FINAL_SCORE>. ",
                "<IIT> <good-verb> on their way to <victory-path> <FINAL_SCORE>. ",
                "The <good-noun> by <IIT> resulted in a <FINAL_SCORE> victory. "
            ]
        },
        "win": {
            "first": [
                "<IIT> took set <SET_NUM>. ",
                "In set <SET_NUM>, <IIT> <decent-verb>. ",
                "<IIT> beat <OPP> in set <SET_NUM>. "
            ],
            "second": [
                "<IIT-2> scored <POINTS_TO_START> points in the first <FIRST_PART_POINTS> to bring the score to <FIRST_PART_SCORE>. ",
                "<IIT-2> went on a <BEST_RUN> run to build a <BEST_RUN_SCORE> lead. ",
                "After going on a <BEST_RUN> run, <IIT> led by <BEST_RUN_SCORE>. ",
                "<IIT-2> held the lead for <NUM_LEADING> points. ",
                "<IIT-2> held the lead for <NUM_LEADING> points on their way to <victory-path>. "

            ],
            "third": [
                "The set ended with a final score of <FINAL_SCORE>. ",
                "<IIT> held the lead to take the set <FINAL_SCORE>. "
            ]
        },
        "lose": {
            "first": [
                "<OPP> <opp-win-verb> in set <SET_NUM>. ",
                "<OPP> <opp-win-verb> in set <SET_NUM> to take the set over <IIT>. "


            ],
            "second": [
                "<IIT> <lose-effort>, going on a <BEST_RUN> run to bring the score to <BEST_RUN_SCORE>. ",
                "<IIT> <lose-effort>, but it wasn't enough to beat <OPP>. ",
                "<IIT> held the lead for <NUM_LEADING> points in the set. "

            ],
            "third": [
                "The set ended with a final score of <FINAL_SCORE>. ",
                "<IIT> couldn't prevail, falling to <OPP> <FINAL_SCORE>. "
            ]


        },
        "good-verb": ["dominated", "held the lead", "never looked back", "had full command", "had full control",
                      "played great", "performed great", "maintained the momentum", "never looked back",
                      "never lost control", "never lost momentum", "never lost their focus", "came out with a fight"],
        "lead-verb": ["jump ahead", "take the lead", "take control", "establish control"],
        "victory-path": ["take the set", "win the set", "victory"],
        "good-noun": ["great effor", "great performance", "dominance", "dominant effort", "dominating performance",
                      "hard work"],
        "lose-effort": ["tried hard", "fought hard", "played hard"],
        "decent-verb": ["took the win", "played hard", "fought hard", "played well"],
        "opp-win-verb": ["prevailed", "held the lead", "stood their ground", "didn't look back"],
        "IIT": ["IIT", "The Scarlet Hawks", "Illinois Tech"],
        "IIT-2": ["They", "The Hawks"]

    }


    cluster_means = []
    for cluster in range(5):
        df2 = pd.DataFrame(dataframe[dataframe["cluster"] == cluster]["vector"].values.tolist())
        cluster_means.append((cluster, df2[9].mean()))

    cluster_means = sorted(cluster_means, key=lambda tup: -tup[1])

    cluster_to_narrative = {
        cluster_means[0][0]: "easy win",
        cluster_means[1][0]: "win",
        cluster_means[2][0]: "close",
        cluster_means[3][0]: "lose",
        cluster_means[4][0]: "bad lose"
    }

    set_results = []
    for home_score, away_score in zip(set_scores["home"]["sets"], set_scores["away"]["sets"]):
        if away == opponent:
            if home_score>away_score:
                set_results.append("W")
            else:
                set_results.append("L")
        else:
            if home_score>away_score:
                set_results.append("L")
            else:
                set_results.append(("W"))

    summaries = []
    for set_num, cluster in enumerate(clusters):
        narrative = cluster_to_narrative[cluster]

        result = set_results[set_num]

        if narrative == "lose" and result == "W":
            narrative = "win"
        elif narrative == "bad lose":
            narrative = "lose"
        elif narrative == "close" and result == "L":
            narrative = "lose"
        elif narrative == "close" and result == "W":
            narrative = "win"
        elif narrative == "win" and result == "L":
            narrative = "lose"

        print(narrative)

        sentences = [
            random.choice(corpus[narrative]["first"]),
            random.choice(corpus[narrative]["second"]),
            random.choice(corpus[narrative]["third"])
        ]

        summary = ""
        for idx, sent in enumerate(sentences):
            sent = re.sub("<IIT>", random.choice(corpus["IIT"]), sent)
            sent = re.sub("<IIT-2>", random.choice(corpus["IIT-2"]), sent)
            sent = re.sub("<OPP>", opponent, sent)

            sent = re.sub("<SET_NUM>", str(set_num+1), sent)
            sent = re.sub("<good-verb>", random.choice(corpus["good-verb"]), sent)
            sent = re.sub("<lead-verb>", random.choice(corpus["lead-verb"]), sent)
            sent = re.sub("<victory-path>", random.choice(corpus["victory-path"]), sent)
            sent = re.sub("<good-noun>", random.choice(corpus["good-noun"]), sent)
            sent = re.sub("<decent-verb>", random.choice(corpus["decent-verb"]), sent)
            sent = re.sub("<opp-win-verb>", random.choice(corpus["opp-win-verb"]), sent)
            sent = re.sub("<lose-effort>", random.choice(corpus["lose-effort"]), sent)

            boundary = random.choice([9, 10, 11, 12, 13, 14])

            set_points = [p for p in points if p.set_num==(set_num+1)]
            max_diff= max([p.diff for p in set_points])
            max_diff_index = [idx for idx, p in enumerate(set_points) if p.diff == max_diff][0]
            iit_run_score = set_points[max_diff_index].iit_score - set_points[max_diff_index-10].iit_score
            opp_run_score = set_points[max_diff_index].opp_score - set_points[max_diff_index-10].opp_score


            sent = re.sub("<POINTS_TO_START>", str(points[boundary].iit_score), sent)
            sent = re.sub("<FIRST_PART_POINTS>", str(boundary+1), sent)
            sent = re.sub("<FIRST_PART_SCORE>", "{}-{}".format(points[boundary].iit_score,
                                                               points[boundary].opp_score), sent)
            sent = re.sub("<BEST_RUN>", "{}-{}".format(iit_run_score,
                                                       opp_run_score), sent)
            sent = re.sub("<BEST_RUN_SCORE>", "{}-{}".format(points[max_diff_index].iit_score,
                                                             points[max_diff_index].opp_score), sent)
            sent = re.sub("<NUM_LEADING>", str(len([p for p in points if p.diff>0 and p.set_num==(set_num+1)])), sent)

            if away == opponent:
                sent = re.sub("<FINAL_SCORE>", "{}-{}".format(set_scores["home"]["sets"][set_num],
                                                             set_scores["away"]["sets"][set_num]), sent)
            else:
                sent = re.sub("<FINAL_SCORE>", "{}-{}".format(set_scores["away"]["sets"][set_num],
                                                             set_scores["home"]["sets"][set_num]), sent)

            summary += sent

        summaries.append(summary)

    return summaries


def generate_standouts(stats_dict):
    corpus = {"verb": ["tallied", "recorded", "earned", "had", "got", "picked up", "accumulated", "totalled",
                       "ended the match with", "ended up with"],
              "good-np": ["an impressive outing", "a great outing", "a great game", "an impressive game",
                          "a notable performance", "a great performance", "an impressive performance", "a notable game",
                          "a noteworthy outing", "a noteworthy game", "a noteworthy performance",
                          "an exciting performance", "an exciting outing", "an exciting game", "an exciting match",
                          "an impressive match", "an exciting match"],
              "solo-leader": ["<PLAYER> led the team with <STAT> <STAT-NOUN>.",
                              "<PLAYER> led the team in <STAT-NOUN> with <STAT>.",
                              "<PLAYER> led the <IIT_MASCOT> in <STAT-NOUN> with <STAT>.",
                              "<PLAYER> led the <IIT_MASCOT> with <STAT> <STAT-NOUN>.",
                              "With <STAT> <STAT-NOUN>, <PLAYER> led the <IIT_MASCOT>.",
                              "<PLAYER> <VERB> <STAT> <STAT-NOUN> to lead the <IIT_MASCOT>.",
                              "<PLAYER> <VERB> <STAT> <STAT-NOUN> to lead the team in <STAT-NOUN>.",
                              "<PLAYER> <VERB> more <STAT-NOUN> than anyone else on the <IIT_MASCOT> with <STAT> <STAT-NOUN>.",
                              "<PLAYER> <VERB> <STAT> <STAT-NOUN> to lead the <IIT_MASCOT>.",
                              "<PLAYER> (<STAT>) led the team in <STAT-NOUN>.",
                              "<PLAYER> (<STAT>) led the <IIT_MASCOT> in <STAT-NOUN>."],
              "high-solo-count": ["<PLAYER> dominated with <STAT> <STAT-NOUN>.",
                                  "<PLAYER> <VERB> <STAT> <STAT-NOUN>.",
                                  "<PLAYER> had <GOOD-NP> with <STAT> <STAT-NOUN>."],
              "two-stat-leaders": ["<PLAYER> and <PLAYER> both led the team with <STAT> <STAT-NOUN>.",
                                    "<PLAYER> and <PLAYER> both led the <IIT_MASCOT> with <STAT> <STAT-NOUN>.",
                                    "With <STAT> <STAT-NOUN>, both <PLAYER> and <PLAYER> led the <IIT_MASCOT> in <STAT-NOUN>.",
                                    "<PLAYER> and <PLAYER> shared the lead in <STAT-NOUN> with <STAT> <STAT-NOUN>.",
                                    "<PLAYER> and <PLAYER> each had <STAT> <STAT-NOUN> to lead the <IIT_MASCOT> in <STAT-NOUN>.",
                                    "<PLAYER> and <PLAYER> topped the leaderboard in <STAT-NOUN> with <STAT> <STAT-NOUN> each.",
                                    "<PLAYER> and <PLAYER> each had <STAT> <STAT-NOUN> to lead the <IIT_MASCOT>.",
                                    "ith <STAT> <STAT-NOUN> each, <PLAYER> and <PLAYER> led the <IIT_MASCOT> in <STAT-NOUN>.",
                                    "<PLAYER> and <PLAYER> both <VERB> <STAT> <STAT-NOUN> to lead the <IIT_MASCOT>."],
              "two-high-count": ["<PLAYER> (<STAT>) and <PLAYER> (<STAT>) both <VERB> double digit <STAT-NOUN>.",
                                "<PLAYER>, along with <PLAYER>, <VERB> <STAT> <STAT-NOUN>.",
                                "<PLAYER> and <PLAYER> each <VERB> <STAT> <STAT-NOUN>."],
              "player-led-two-stats": ["<PLAYER> led the team in <STAT> <STAT-NOUN> and <STAT> <STAT-NOUN>.",
                                        "With <STAT> <STAT-NOUN> and <STAT> <STAT-NOUN>, <PLAYER> led the team in both categories.",
                                        "<PLAYER> led the <IIT_MASCOT> in <STAT-NOUN> (<STAT>) and <STAT-NOUN> (<STAT>).",
                                        "<PLAYER> had <GOOD-NP>, leading in both <STAT> <STAT-NOUN> and <STAT> <STAT-NOUN>.",
                                        "<PLAYER> <VERB> <STAT> <STAT-NOUN> and <STAT> <STAT-NOUN> to lead the <IIT_MASCOT>"],
              "player-led-in-three-stats": ["<PLAYER> led the <IIT_MASCOT> with <STAT> <STAT-NOUN>, <STAT> <STAT-NOUN>, and <STAT> <STAT-NOUN>.",
                                            "<PLAYER> led the <IIT_MASCOT> in <STAT-NOUN> (<STAT>), <STAT-NOUN> (<STAT>) and <STAT-NOUN> (<STAT>).",
                                            "<PLAYER> had <GOOD-NP>, leading the <IIT_MASCOT> with <STAT> <STAT-NOUN>, <STAT> <STAT-NOUN>, and <STAT> <STAT-NOUN>.",
                                            "<PLAYER> had <GOOD-NP>, leading in <STAT-NOUN> (<STAT>), <STAT-NOUN> (<STAT>) and <STAT-NOUN> (<STAT>).",
                                            "<PLAYER> had <GOOD-NP> as <GENDER> <VERB> <STAT> <STAT-NOUN>, <STAT> <STAT-NOUN>, and <STAT> <STAT-NOUN> to lead the <IIT_MASCOT>"],
              "K": ["kills"],
              "DIGS": ["digs"],
              "A": ["assists"],
              "B": ["blocks"]}
    # TODO: compute block leader

    def get_leaders(home_stats_dict, stat):
        stat_leaderboard = sorted(home_stats_dict.items(), key=lambda x: -x[1][stat])
        stat_leader = stat_leaderboard[0][0]
        value = stat_leaderboard[0][1][stat]
        second_stat_leader = None
        if stat_leaderboard[1][1][stat] == value:
            second_stat_leader = stat_leaderboard[1][0]

        return value, stat_leader, second_stat_leader

    home_stats_dict = {k.split("_")[1]:v for (k,v) in stats_dict.items() if "home" in k and "totals" not in k}
    kills, kill_leader, second_kill_leader = get_leaders(home_stats_dict, "K")
    digs, digs_leader, second_digs_leader = get_leaders(home_stats_dict, "DIGS")
    assists, assists_leader, second_assists_leader = get_leaders(home_stats_dict, "A")

    # maps player name to the stats they led in
    stat_lookup = defaultdict(lambda: [])
    stat_lookup[kill_leader].append(("K", kills))
    stat_lookup[second_kill_leader].append(("K", kills))
    stat_lookup[digs_leader].append(("DIGS", digs))

    stat_lookup[second_digs_leader].append(("DIGS", digs))
    stat_lookup[assists_leader].append(("A", assists))
    stat_lookup[second_assists_leader].append(("A", assists))

    # maps player name to how many stats they led in
    leader_counts = Counter()
    leader_counts.update([kill_leader, second_kill_leader, digs_leader, second_digs_leader, assists_leader, second_assists_leader])

    # maps stat-noun to list of players who led in the category
    leader_dict = defaultdict(lambda: [])
    leader_dict["K"].append((kill_leader, kills))
    leader_dict["DIGS"].append((digs_leader, digs))
    leader_dict["A"].append((assists_leader, assists))
    if second_kill_leader:
        leader_dict["K"].append((second_kill_leader, kills))
    if second_digs_leader:
        leader_dict["DIGS"].append((second_digs_leader, digs))
    if second_assists_leader:
        leader_dict["A"].append((second_assists_leader, assists))

    results = []

    for stat, leaders in leader_dict.items():
        sentence = ""
        if len(leaders) == 1:
            if leaders[0][1] >= 10 and stat != "A":
                template = random.choice(corpus["high-solo-count"])
            else:
                template = random.choice(corpus["solo-leader"])
            sentence = re.sub("<STAT>", str(leaders[0][1]), template)
            sentence = re.sub("<STAT-NOUN>", corpus[stat][0], sentence)
            sentence = re.sub("<PLAYER>", leaders[0][0], sentence, count=1)

        elif len(leaders) == 2:
            if leaders[0][1] >= 10:
                template = random.choice(corpus["two-high-count"])
            else:
                template = random.choice(corpus["two-stat-leaders"])
            sentence = re.sub("<STAT-NOUN>", corpus[stat][0], template)

            sentence = re.sub("<STAT>", str(leaders[0][1]), sentence)
            sentence = re.sub("<PLAYER>", leaders[0][0], sentence, count=1)
            sentence = re.sub("<PLAYER>", leaders[1][0], sentence, count=1)

        sentence = re.sub("<IIT_MASCOT>", "Scarlet Hawks", sentence)
        sentence = re.sub("<VERB>", corpus["verb"][0], sentence)
        sentence = re.sub("<GOOD-NP>", corpus["good-np"][0], sentence)

        results.append(sentence)

    for name, count in leader_counts.items():
        if name and count==2:
            template = random.choice(corpus["player-led-two-stats"])

        elif name and count == 3:
            template = random.choice(corpus["player-led-in-three-stats"])

        if name and count>=2:
            sentence = re.sub("<PLAYER>", name, template)

            for (name, value) in stat_lookup[name]:
                sentence = re.sub("<STAT>", value, sentence, count=1)
                sentence = re.sub("<STAT-NOUN>", name, sentence, count=1)

            sentence = re.sub("<VERB>", corpus["verb"], sentence)
            sentence = re.sub("<GOOD-NP>", corpus["good-np"], sentence)

            results.append(sentence)
    return results


def generate_stats(stats_dict, info_dict, opponent):
    # TODO: biggest difference
    corpus = {
        "categories": ["hit_percent", "kills", "blocks", "digs", "aces"],
        "hit_percent": [
            "<OPP> <finished-verb> a team <OPP_HIT> attack percentage to <IIT>'s <IIT_HIT>.",
            "<OPP> hit <OPP_HIT> compared to <IIT>'s <IIT_HIT>.",
            "<IIT> <finished-verb> a team <IIT_HIT> attack percentage to <OPP>'s <OPP_HIT>.",
            "<IIT> hit <IIT_HIT> compared to <IIT>'s <OPP_HIT>.",
            "<HIGHER_HITTER> <outhit-verb> <LOWER_HITTER> (<HIGH_HIT> to <LOW_HIT>).",
            "<HIGHER_HITTER> <outhit-verb> <LOWER_HITTER> with <HIGH_HIT> while <LOWER_HITTER> hit <LOW_HIT>."
        ],
        "kills": [
            "<OPP> <finished-verb> <OPP_KILLS> kills to <IIT>'s <IIT_KILLS>.",
            "<HIGHER_KILLER> had more kills than <LOWER_KILLER> with <HIGH_KILLS> kills compared to <LOWER_KILLER>'s <LOW_KILLS>.",
            "<HIGHER_KILLER> had more kills than <LOWER_KILLER> with <HIGH_KILLS> kills while <LOWER_KILLER> <finished-verb> <LOW_KILLS>.",
            "<OPP> <finished-verb> <OPP_KILLS> kills while <IIT> <finished-verb> <IIT_KILLS>.",
            "<IIT> <finished-verb> <IIT_KILLS> kills while <OPP> <finished-verb> <OPP_KILLS>.",
            "<IIT> <finished-verb> <IIT_KILLS> kills to <OPP>'s <OPP_KILLS>."
        ],
        "blocks": [
            "<OPP> <finished-verb> <OPP_BLOCKS> blocks to <IIT>'s <IIT_BLOCKS>.",
            "<HIGHER_BLOCKER> had more blocks than <LOWER_BLOCKER> with <HIGH_BLOCKS> blocks compared to <LOWER_BLOCKER>'s <LOW_BLOCKS>.",
            "<HIGHER_BLOCKER> had more blocks than <LOWER_BLOCKER> with <HIGH_BLOCKS> blocks while <LOWER_BLOCKER> <finished-verb> <LOW_BLOCKS>.",
            "<OPP> <finished-verb> <OPP_BLOCKS> blocks while <IIT> <finished-verb> <IIT_BLOCKS>.",
            "<IIT> <finished-verb> <IIT_BLOCKS> blocks while <OPP> <finished-verb> <OPP_BLOCKS>.",
            "<IIT> <finished-verb> <IIT_BLOCKS> blocks to <OPP>'s <OPP_BLOCKS>."
        ],
        "digs": [
            "<OPP> <finished-verb> <OPP_DIGS> digs to <IIT>'s <IIT_DIGS>.",
            "<HIGHER_DIGGER> had more digs than <LOWER_DIGGER> with <HIGH_DIGS> digs compared to <LOWER_DIGGER>'s <LOW_DIGS>.",
            "<HIGHER_DIGGER> had more digs than <LOWER_DIGGER> with <HIGH_DIGS> digs while <LOWER_DIGGER> <finished-verb> <LOW_DIGS>.",
            "<OPP> <finished-verb> <OPP_DIGS> digs while <IIT> <finished-verb> <IIT_DIGS>.",
            "<IIT> <finished-verb> <IIT_DIGS> digs while <OPP> <finished-verb> <OPP_DIGS>.",
            "<IIT> <finished-verb> <IIT_DIGS> digs to <OPP>'s <OPP_DIGS>."
        ],
        "aces": [
            "<OPP> <finished-verb> <OPP_ACES> aces to <IIT>'s <IIT_ACES>.",
            "<HIGHER_ACER> had more aces than <LOWER_ACER> with <HIGH_ACES> aces compared to <LOWER_ACER>'s <LOW_ACES>.",
            "<HIGHER_ACER> had more aces than <LOWER_ACER> with <HIGH_ACES> aces while <LOWER_ACER> <finished-verb> <LOW_ACES>.",
            "<OPP> <finished-verb> <OPP_ACES> aces while <IIT> <finished-verb> <IIT_ACES>.",
            "<IIT> <finished-verb> <IIT_ACES> aces while <OPP> <finished-verb> <OPP_ACES>.",
            "<IIT> <finished-verb> <IIT_ACES> aces to <OPP>'s <OPP_ACES>."
        ],
        "finished-verb": ["finished with", "ended the match with", "ended up with", "earned", "accumulated", "had", "racked up"],
        "outhit-verb": ["outhit", "had the advantage in hit percentage over", "hit better than"],
        "IIT": ["IIT", "The Scarlet Hawks", "The Hawks", "Illinois Tech"]
    }

    if opponent == info_dict["template_visitor_name"]:
        opp_key = "away_totals"
        iit_key =  "home_totals"
    else:
        opp_key = "home_totals"
        iit_key = "away_totals"

    # TODO: check for equality

    opp_hit = stats_dict[opp_key]["K%"]
    iit_hit = stats_dict[iit_key]["K%"]
    if opp_hit > iit_hit:
        higher_hitter = "<OPP>"
        high_hit = opp_hit
        lower_hitter = "<IIT>"
        low_hit = iit_hit
    else:
        higher_hitter = "<IIT>"
        high_hit = iit_hit
        lower_hitter = "<OPP>"
        low_hit = opp_hit

    opp_kills = stats_dict[opp_key]["K"]
    iit_kills = stats_dict[iit_key]["K"]
    if opp_kills > iit_kills:
        higher_killer = "<OPP>"
        high_kills = opp_kills
        lower_killer = "<IIT>"
        low_kills = iit_kills

    else:
        higher_killer = "<IIT>"
        high_kills = iit_kills
        lower_killer = "<OPP>"
        low_kills = opp_kills

    opp_blocks = stats_dict[opp_key]["BS"]+stats_dict[opp_key]["BA"]/2
    iit_blocks = stats_dict[iit_key]["BS"]+stats_dict[iit_key]["BA"]/2
    if opp_blocks > iit_blocks:
        higher_blocker ="<OPP>"
        high_blocks = opp_blocks
        lower_blocker ="<IIT>"
        low_blocks = iit_blocks
    else:
        higher_blocker ="<IIT>"
        high_blocks = iit_blocks
        lower_blocker ="<OPP>"
        low_blocks = opp_blocks

    opp_digs = stats_dict[opp_key]["DIGS"]
    iit_digs = stats_dict[iit_key]["DIGS"]
    if opp_digs > iit_digs:
        higher_digger ="<OPP>"
        high_digs = opp_digs
        lower_digger ="<IIT>"
        low_digs = iit_digs
    else:
        higher_digger ="<IIT>"
        high_digs = iit_digs
        lower_digger ="<OPP>"
        low_digs = opp_digs

    opp_aces = stats_dict[opp_key]["SA"]
    iit_aces = stats_dict[iit_key]["SA"]
    if opp_aces > iit_aces:
        higher_acer ="<OPP>"
        high_aces = opp_aces
        lower_acer ="<IIT>"
        low_aces = iit_aces
    else:
        higher_acer ="<IIT>"
        high_aces = iit_aces
        lower_acer ="<OPP>"
        low_aces = opp_aces

    stats = []
    categories = random.sample(corpus["categories"], 3)

    templates = []
    for cat in categories:
        templates.append(random.choice(corpus[cat]))

    for template in templates:

        sent = re.sub("<OPP_HIT>", str(opp_hit), template)
        sent = re.sub("<IIT_HIT>", str(iit_hit), sent)
        sent = re.sub("<HIGHER_HITTER>", higher_hitter, sent)
        sent = re.sub("<LOWER_HITTER>", lower_hitter, sent)
        sent = re.sub("<LOW_HIT>", str(low_hit), sent)
        sent = re.sub("<HIGH_HIT>", str(high_hit), sent)

        sent = re.sub("<OPP_KILLS>", str(opp_kills), sent)
        sent = re.sub("<IIT_KILLS>", str(iit_kills), sent)
        sent = re.sub("<HIGHER_KILLER>", higher_killer, sent)
        sent = re.sub("<LOWER_KILLER>", lower_killer, sent)
        sent = re.sub("<LOW_KILLS>", str(low_kills), sent)
        sent = re.sub("<HIGH_KILLS>", str(high_kills), sent)

        sent = re.sub("<OPP_BLOCKS>", str(opp_blocks), sent)
        sent = re.sub("<IIT_BLOCKS>", str(iit_blocks), sent)
        sent = re.sub("<HIGHER_BLOCKER>", higher_blocker, sent)
        sent = re.sub("<LOWER_BLOCKER>", lower_blocker, sent)
        sent = re.sub("<LOW_BLOCKS>", str(low_blocks), sent)
        sent = re.sub("<HIGH_BLOCKS>", str(high_blocks), sent)

        sent = re.sub("<OPP_DIGS>", str(opp_digs), sent)
        sent = re.sub("<IIT_DIGS>", str(iit_digs), sent)
        sent = re.sub("<HIGHER_DIGGER>", higher_digger, sent)
        sent = re.sub("<LOWER_DIGGER>", lower_digger, sent)
        sent = re.sub("<LOW_DIGS>", str(low_digs), sent)
        sent = re.sub("<HIGH_DIGS>", str(high_digs), sent)

        sent = re.sub("<OPP_ACES>", str(opp_aces), sent)
        sent = re.sub("<IIT_ACES>", str(iit_aces), sent)
        sent = re.sub("<HIGHER_ACER>", higher_acer, sent)
        sent = re.sub("<LOWER_ACER>", lower_acer, sent)
        sent = re.sub("<LOW_ACES>", str(low_aces), sent)
        sent = re.sub("<HIGH_ACES>", str(high_aces), sent)

        sent = re.sub("<outhit-verb>", random.choice(corpus["outhit-verb"]), sent)
        sent = re.sub("<finished-verb>", random.choice(corpus["finished-verb"]), sent, count=1)
        sent = re.sub("<finished-verb>", random.choice(corpus["finished-verb"]), sent, count=1)

        sent = re.sub("<OPP>", opponent, sent)
        sent = re.sub("<IIT>", random.choice(corpus["IIT"]), sent)

        stats.append(sent)

    return stats


def generate_up_next(schedule_url, boxscore_url):
    # TODO: what to do if game isn't found?

    req = Request(schedule_url,
                  headers={'User-Agent': 'Mozilla/5.0'})
    resp = urlopen(req).read()
    soup = BeautifulSoup(resp, "html5lib")

    found = False
    for game in soup.findAll(name="div", class_="event-row"):
        if game["data-boxscore"] in boxscore_url:
            found = True
            continue
        if found:
            next_opponent = game.find(name="span", class_="team-name").string
            next_location = game.find(name="div", class_="notes").text.lstrip().rstrip()
            next_date = game.find(name="div", class_="date")["title"]
            break

    corpus = {
        "template": [
            "<IIT> will <face-verb> <OPP> at <LOC> on <DATE>.",
            "<IIT> will <face-verb> <OPP> on <DATE> at <LOC>.",
            "The next match for <IIT> will be on <DATE> at <LOC> against <OPP>.",
            "<IIT> continues its season on <DATE>, <facing-verb> <OPP> at <LOC>."
        ],
        "IIT": ["IIT", "The Scarlet Hawks", "The Hawks", "Illinois Tech"],
        "face-verb": ["face", "take on", "oppose", "challenge", "go up against", "square off with"],
        "facing-verb": ["facing", "taking on", "opposing", "challenging", "going up against", "squaring off with"]
    }

    up_next = random.choice(corpus["template"])
    up_next = re.sub("<IIT>", random.choice(corpus["IIT"]), up_next)
    up_next = re.sub("<face-verb>", random.choice(corpus["face-verb"]), up_next)
    up_next = re.sub("<OPP>", next_opponent, up_next)
    up_next = re.sub("<LOC>", next_location, up_next)
    up_next = re.sub("<DATE>", next_date, up_next)
    up_next = re.sub("<facing-verb>", random.choice(corpus["facing-verb"]), up_next)

    return up_next


def generate_score_summary(info_dict, set_scores, num_sets):
    results = ""
    results += info_dict["template_home_name"] + " " + set_scores["home"]["total"] + ", "
    results += info_dict["template_visitor_name"] + " " + set_scores["away"]["total"] + " ("

    for idx, _ in enumerate(range(num_sets)):
        results += str(set_scores["home"]["sets"][idx]) + "-" + str(set_scores["away"]["sets"][idx])
        if idx+1 == num_sets:
            results += ") "
        else:
            results += ", "

    return results



def get_template_sentences(corpus):
    results = {}
    results["title"] = random.choice(corpus["title"])
    results["intro"] = None
    while not results["intro"]:
        temp = random.choice(corpus["intro"])
        if "<LOCATION>" in temp:
            results["intro"] = temp
    results["how it happened"] = random.sample(corpus["how it happened"], 4)
    results["standouts"] = random.sample(corpus["scarlet hawk standouts"], 4)
    results["stats"] = random.sample(corpus["stats to know"], 4)
    results["next"] = random.choice(corpus["up next"])

    return results


def get_teams(set_scores, site_url):
    req = Request(site_url,
                  headers={'User-Agent': 'Mozilla/5.0'})
    resp = urlopen(req).read()
    soup = BeautifulSoup(resp, "html5lib")

    home = ""
    away = ""

    for idx, stats_header in enumerate(soup.findAll(name="span", class_="stats-header")):
        name = stats_header.text[:len(stats_header.text)-1].lstrip().rstrip()
        sets = stats_header.text[-1]
        for key, dictionary in set_scores.items():
            if dictionary["total"] == sets:
                if key == "home":
                    home = name
                else:
                    away = name

    return home, away


def get_corpus(article_dicts, result, num_sets):
    results = defaultdict(lambda: [])
    for url, article in article_dicts.items():
        if article["result"] == result and article["num_sets"] == num_sets:
            for key, list in article["sentence_dict"].items():
                results[key].extend(list)

    return results


def update_wpas(player_to_wpa, player_to_max_wpa, player_to_min_wpa, point, iit_ids):
    previous_point = namedtuple('previous_point', 'iit_score opp_score')
    if point.iit_score + point.opp_score == 1:
        previous_score = previous_point(iit_score=0, opp_score=0)
    elif point.winner in iit_ids:
        previous_score = previous_point(iit_score=point.iit_score-1, opp_score=point.opp_score)
    else:
        previous_score = previous_point(iit_score=point.iit_score, opp_score=point.opp_score-1)

    wpa = get_wpa((previous_score.iit_score, previous_score.opp_score), (point.iit_score, point.opp_score))

    player = None

    if "Service error" in point.summary:
        player = point.server
    elif "Service ace" in point.summary:
        player = point.server
    # elif "block error" in point.summary:
    elif "Kill by" in point.summary:
        if point.winner not in iit_ids and "error by" in point.summary:
            player = point.summary.split("error by ")[1].split(". ")[0]
        elif point.winner in iit_ids:
            if "(from" in point.summary:
                hitter = point.summary.split("Kill by ")[1].split(" (")[0]
                setter = point.summary.split("(from ")[1].split(")")[0]
                player_to_wpa[hitter] += wpa*(4/5)
                player_to_wpa[setter] += wpa*(1/5)

                if wpa * (4 / 5) > player_to_max_wpa[hitter]["max"]:
                    player_to_max_wpa[hitter]["max"] = wpa
                    player_to_max_wpa[hitter]["play"] = point
                if wpa * (1 / 5) > player_to_max_wpa[setter]["max"]:
                    player_to_max_wpa[setter]["max"] = wpa
                    player_to_max_wpa[setter]["play"] = point

                if wpa * (4 / 5) < player_to_min_wpa[hitter]["min"]:
                    player_to_min_wpa[hitter]["min"] = wpa
                    player_to_min_wpa[hitter]["play"] = point
                if wpa * (1 / 5) < player_to_min_wpa[setter]["min"]:
                    player_to_min_wpa[setter]["min"] = wpa
                    player_to_min_wpa[setter]["play"] = point
                return
            else:
                player = point.summary.split("Kill by ")[1].split(". ")[0]
    elif "Attack error" in point.summary:
        if point.winner not in iit_ids:
            if "). " not in point.summary:
                player = point.summary.split("Attack error by ")[1].split(". ")[0]
            else:
                player = point.summary.split("Attack error by ")[1].split(" (")[0]
        elif "(block by" in point.summary and point.winner in iit_ids:
            players = point.summary.split("(block by ")[1].split("). ")[0].split(";")
            for player in players:
                player_to_wpa[player.lstrip()] += wpa/len(players)
            return
    elif "Bad set" in point.summary and point.winner not in iit_ids:
        player = point.summary.split(" by ")[1].split(". ")[0]

    if player:
        player_to_wpa[player.lstrip()] += wpa

        if wpa > player_to_max_wpa[player.lstrip()]["max"]:
            player_to_max_wpa[player.lstrip()]["max"] = wpa
            player_to_max_wpa[player.lstrip()]["play"] = point

        if wpa < player_to_min_wpa[player.lstrip()]["min"]:
            player_to_min_wpa[player.lstrip()]["min"] = wpa
            player_to_min_wpa[player.lstrip()]["play"] = point


def get_wpa(before_score, after_score):
    before_wp = percentage_score_dict[before_score[0]][before_score[1]]['W']
    after_wp = percentage_score_dict[after_score[0]][after_score[1]]['W']
    return round((after_wp-before_wp)*100, 3)


def get_play_logs(url):
    Point = namedtuple('Point', 'iit_score opp_score diff server summary winner set_num')
    points = []
    iit_players = set()
    iit_ids = set()

    req = Request(url,
                  headers={'User-Agent': 'Mozilla/5.0'})
    resp = urlopen(req).read()
    soup = BeautifulSoup(resp, "html5lib")

    left_id = soup.find(name="th", id="set1").previous_sibling.previous_sibling.string
    right_id = soup.find(name="th", id="set1").next_sibling.next_sibling.string

    if left_id == "IITMVB" or left_id == "IIT":
        iit_id = left_id
        opp_id = right_id
    else:
        iit_id = right_id
        opp_id = left_id

    iit_ids.add(iit_id)

    set_num = 0
    for point in soup.find_all(name="tr"):
        try:
            if "--" in point.text:
                set_num += 1
            elif point["class"][0] in ["even", "odd"]:
                summary = point.td.next_sibling.next_sibling.string.lstrip()
                if all(x not in summary for x in ["starters:", "Timeout", "subs"]):
                    score = point.td.string
                    if not score:
                        score = point.td.next_sibling.next_sibling\
                                        .next_sibling.next_sibling.string
                    scores = score.split("-")
                    if left_id == iit_id:
                        iit_score = int(scores[0])
                        opp_score = int(scores[1])
                    else:
                        iit_score = int(scores[1])
                        opp_score = int(scores[0])

                    server = summary.split("] ")[0].replace("[", "")
                    winner = summary.split("Point ")[1]
                    summary = summary.split("] ")[1].split("Point ")[0]

                    point = Point(iit_score=iit_score,
                                    opp_score=opp_score,
                                    diff=iit_score-opp_score,
                                    server=server,
                                    summary=summary,
                                    winner=winner,
                                    set_num=set_num)
                    points.append(point)

                elif iit_id + " starters:" in summary:
                    for player in summary.split("starters: ")[1].split("; "):
                        iit_players.add(player.rstrip().replace(".",""))
                elif iit_id + " subs:" in summary:
                    for player in summary.split("subs: ")[1].split("; "):
                        iit_players.add(player.rstrip().replace(".",""))
        except Exception as err:
            # print(err)
            pass

    return points, iit_ids, iit_players


def get_stats(boxscore_url):

    stats = {"SP": 0, "K": 0, "E": 0, "TA": 0, "K%": 0,
             "A": 0, "SA": 0, "SE": 0, "RE": 0, "DIGS": 0,
             "BS": 0, "BA": 0, "BE": 0, "BHE": 0, "PTS": 0}
    stats_dict = defaultdict(lambda: stats.copy())

    info_dict = {}
    set_attacks = {"K":0, "E":0, "TA":0, "PCT":0}
    team_set_attacks = {"home": [], "away": []}

    set_scores = {"home": {"total": 0, "sets": []}, "away": {"total": 0, "sets": []}}

    req = Request(boxscore_url,
                  headers={'User-Agent': 'Mozilla/5.0'})
    resp = urlopen(req).read()
    soup = BeautifulSoup(resp, "html5lib")

    info_dict["template_location"] = soup.body.div.div.text.split("\n")[3].split("@")[1]

    away_name_string = soup.find("table").tbody.tr.find("th", class_="align-left").string

    info_dict["template_visitor_name"] = away_name_string.split(" (")[0]
    info_dict["template_visitor_record"] = "(" + away_name_string.split(" (")[1]

    row = ""
    tables = soup.find_all("table")
    for row in tables[0].tbody.find_all(lambda tag: tag.name == 'tr' and
                                                 tag.get('class') == ["odd"] or
                                                 tag.get('class') == ["even"]):
        name = ""
        for idx, col in enumerate(row.find_all("td")):
            if idx==1:
                name = "away_"+col.string.lstrip().split(".")[0]
            elif idx == 2:
                stats_dict[name]["SP"] = int(col.string)
            elif idx == 3:
                stats_dict[name]["K"] = int(col.string)
            elif idx == 4:
                stats_dict[name]["E"] = int(col.string)
            elif idx == 5:
                stats_dict[name]["TA"] = int(col.string)
            elif idx == 6:
                stats_dict[name]["K%"] = float(col.string)
            elif idx == 7:
                stats_dict[name]["A"] = int(col.string)
            elif idx == 8:
                stats_dict[name]["SA"] = int(col.string)
            elif idx == 9:
                stats_dict[name]["SE"] = int(col.string)
            elif idx == 10:
                stats_dict[name]["RE"] = int(col.string)
            elif idx == 11:
                stats_dict[name]["DIGS"] = int(col.string)
            elif idx == 12:
                stats_dict[name]["BS"] = int(col.string)
            elif idx == 13:
                stats_dict[name]["BA"] = int(col.string)
            elif idx == 14:
                stats_dict[name]["BE"] = int(col.string)
            elif idx == 15:
                stats_dict[name]["BHE"] = int(col.string)
            elif idx == 16:
                stats_dict[name]["PTS"] = float(col.string)

    name = "away_totals"
    for idx, col in enumerate(row.next_sibling.next_sibling.next_sibling.next_sibling.find_all("td")):
        if idx == 2:
            stats_dict[name]["SP"] = int(col.string)
        elif idx == 2:
            stats_dict[name]["K"] = int(col.string)
        elif idx == 3:
            stats_dict[name]["E"] = int(col.string)
        elif idx == 4:
            stats_dict[name]["TA"] = int(col.string)
        elif idx == 5:
            stats_dict[name]["K%"] = float(col.string)
        elif idx == 6:
            stats_dict[name]["A"] = int(col.string)
        elif idx == 7:
            stats_dict[name]["SA"] = int(col.string)
        elif idx == 8:
            stats_dict[name]["SE"] = int(col.string)
        elif idx == 9:
            stats_dict[name]["RE"] = int(col.string)
        elif idx == 10:
            stats_dict[name]["DIGS"] = int(col.string)
        elif idx == 11:
            stats_dict[name]["BS"] = int(col.string)
        elif idx == 12:
            stats_dict[name]["BA"] = int(col.string)
        elif idx == 13:
            stats_dict[name]["BE"] = int(col.string)
        elif idx == 14:
            stats_dict[name]["BHE"] = int(col.string)
        elif idx == 15:
            stats_dict[name]["PTS"] = float(col.string)


    for idx, row in enumerate(tables[2].tbody.find_all("tr")):
        dict = set_attacks.copy()
        for c_idx, col in enumerate(row.find_all("td")):
            if idx>= 2:
                if c_idx == 1:
                    dict["K"] = int(col.string)
                if c_idx == 2:
                    dict["E"] = int(col.string)
                if c_idx == 3:
                    dict["TA"] = int(col.string)
                if c_idx == 4:
                    dict["PCT"] = float(col.string)
        if idx>=2:
            team_set_attacks["away"].append(dict)

    for idx, row in enumerate(tables[3].tbody.find_all("tr")):
        if idx == 1:
            name = "away"
        elif idx == 2:
            name = "home"
        for c_idx, col in enumerate(row.find_all("td")):
            if c_idx == 1:
                s = col.string
                set_scores[name]["total"] = s[s.find("(")+1:s.find(")")]
            if c_idx >= 2 and "-" not in col.string:
                set_scores[name]["sets"].append(int(col.string))

            # print(col)

    home_name_string = tables[4].tbody.tr.find("th", class_="align-left").string

    info_dict["template_home_name"] = home_name_string.split(" (")[0]
    info_dict["template_home_record"] = "(" + home_name_string.split(" (")[1]

    for row in tables[4].tbody.find_all(lambda tag: tag.name == 'tr' and
                                tag.get('class') == ["odd"] or
                                tag.get('class') == ["even"]):
        name = ""
        for idx, col in enumerate(row.find_all("td")):
            if idx == 1:
                name = "home_" + col.string.lstrip().split(".")[0]
            elif idx == 2:
                stats_dict[name]["SP"] = int(col.string)
            elif idx == 3:
                stats_dict[name]["K"] = int(col.string)
            elif idx == 4:
                stats_dict[name]["E"] = int(col.string)
            elif idx == 5:
                stats_dict[name]["TA"] = int(col.string)
            elif idx == 6:
                stats_dict[name]["K%"] = float(col.string)
            elif idx == 7:
                stats_dict[name]["A"] = int(col.string)
            elif idx == 8:
                stats_dict[name]["SA"] = int(col.string)
            elif idx == 9:
                stats_dict[name]["SE"] = int(col.string)
            elif idx == 10:
                stats_dict[name]["RE"] = int(col.string)
            elif idx == 11:
                stats_dict[name]["DIGS"] = int(col.string)
            elif idx == 12:
                stats_dict[name]["BS"] = int(col.string)
            elif idx == 13:
                stats_dict[name]["BA"] = int(col.string)
            elif idx == 14:
                stats_dict[name]["BE"] = int(col.string)
            elif idx == 15:
                stats_dict[name]["BHE"] = int(col.string)
            elif idx == 16:
                stats_dict[name]["PTS"] = float(col.string)


    name = "home_totals"
    for idx, col in enumerate(row.next_sibling.next_sibling.next_sibling.next_sibling.find_all("td")):
        if idx == 2:
            stats_dict[name]["SP"] = int(col.string)
        elif idx == 2:
            stats_dict[name]["K"] = int(col.string)
        elif idx == 3:
            stats_dict[name]["E"] = int(col.string)
        elif idx == 4:
            stats_dict[name]["TA"] = int(col.string)
        elif idx == 5:
            stats_dict[name]["K%"] = float(col.string)
        elif idx == 6:
            stats_dict[name]["A"] = int(col.string)
        elif idx == 7:
            stats_dict[name]["SA"] = int(col.string)
        elif idx == 8:
            stats_dict[name]["SE"] = int(col.string)
        elif idx == 9:
            stats_dict[name]["RE"] = int(col.string)
        elif idx == 10:
            stats_dict[name]["DIGS"] = int(col.string)
        elif idx == 11:
            stats_dict[name]["BS"] = int(col.string)
        elif idx == 12:
            stats_dict[name]["BA"] = int(col.string)
        elif idx == 13:
            stats_dict[name]["BE"] = int(col.string)
        elif idx == 14:
            stats_dict[name]["BHE"] = int(col.string)
        elif idx == 15:
            stats_dict[name]["PTS"] = float(col.string)

    for idx, row in enumerate(tables[6].tbody.find_all("tr")):
        dict = set_attacks.copy()
        for c_idx, col in enumerate(row.find_all("td")):
            if idx >= 2:
                if c_idx == 1:
                    dict["K"] = int(col.string)
                if c_idx == 2:
                    dict["E"] = int(col.string)
                if c_idx == 3:
                    dict["TA"] = int(col.string)
                if c_idx == 4:
                    dict["PCT"] = float(col.string)
        if idx >= 2:
            team_set_attacks["home"].append(dict)

    return info_dict, stats_dict, set_scores, team_set_attacks

#TODO: ties (like three players with 1 SA)
def complete_info_dict(info_dict, stats_dict, set_scores, team_set_attacks):

    info_dict["template_home_set_one_score"] = set_scores["home"]["sets"][0]
    info_dict["template_home_set_two_score"] = set_scores["home"]["sets"][1]
    info_dict["template_home_set_three_score"] = set_scores["home"]["sets"][2]
    info_dict["template_home_set_four_score"] = set_scores["home"]["sets"][3]
    # info_dict["template_home_set_five_score"] = set_scores["home"]["sets"][4]

    info_dict["template_visitor_set_one_score"] = set_scores["away"]["sets"][0]
    info_dict["template_visitor_set_two_score"] = set_scores["away"]["sets"][1]
    info_dict["template_visitor_set_three_score"] = set_scores["away"]["sets"][2]
    info_dict["template_visitor_set_four_score"] = set_scores["away"]["sets"][3]
    # info_dict["template_visitor_set_five_score"] = set_scores["away"]["sets"][4]

    info_dict["template_home_sets"] = set_scores["home"]["total"]
    info_dict["template_visitor_sets"] = set_scores["away"]["total"]

    info_dict["template_home_team_aces"] = stats_dict["home_totals"]["SA"]
    info_dict["template_visitor_team_aces"] = stats_dict["away_totals"]["SA"]
    info_dict["template_home_team_digs"] = stats_dict["home_totals"]["DIGS"]
    info_dict["template_visitor_team_digs"] = stats_dict["away_totals"]["DIGS"]
    info_dict["template_home_team_blocks"] = stats_dict["home_totals"]["BS"]+stats_dict["home_totals"]["BA"]/2
    info_dict["template_visitor_team_blocks"] = stats_dict["away_totals"]["BS"]+stats_dict["away_totals"]["BA"]/2
    info_dict["template_home_team_hitting_percentage"] = stats_dict["home_totals"]["K%"]
    info_dict["template_visitor_team_hitting_percentage"] = stats_dict["away_totals"]["K%"]

    kills = 0
    digs = 0
    blocks = 0
    aces = 0
    for (name, stats) in [(key,val) for key, val in stats_dict.items() if "home" in key]:
        if "totals" not in name:
            if stats["K"] > kills:
                kills = stats["K"]
                info_dict["template_home_kill_leader"] = "K: " + name.split("_")[1] + " - " + str(kills)
            if stats["DIGS"] > digs:
                digs = stats["DIGS"]
                info_dict["template_home_dig_leader"] = "D: " + name.split("_")[1] + " - " + str(digs)
            if stats["BS"]+stats["BA"] > blocks:
                blocks = stats["BS"]+stats["BA"]
                info_dict["template_home_block_leader"] = "B: " + name.split("_")[1] + " - " + str(blocks)
            if stats["SA"] > aces:
                aces = stats["SA"]
                info_dict["template_home_ace_leader"] = "SA: " + name.split("_")[1] + " - " + str(aces)

    kills = 0
    digs = 0
    blocks = 0
    aces = 0
    for (name, stats) in [(key,val) for key, val in stats_dict.items() if "away" in key]:
        if "totals" not in name:
            if stats["K"] > kills:
                kills = stats["K"]
                info_dict["template_visitor_kill_leader"] = "K: " + name.split("_")[1] + " - " + str(kills)
            if stats["DIGS"] > digs:
                digs = stats["DIGS"]
                info_dict["template_visitor_dig_leader"] = "D: "+ name.split("_")[1] + " - " + str(digs)
            if stats["BS"]+stats["BA"] > blocks:
                blocks = stats["BS"]+stats["BA"]
                info_dict["template_visitor_block_leader"] = "B: " + name.split("_")[1] + " - " + str(blocks)
            if stats["SA"] > aces:
                aces = stats["SA"]
                info_dict["template_visitor_ace_leader"] = "SA: " + name.split("_")[1] + " - " + str(aces)


def print_player_wpas(player_to_wpa, iit_players, player_to_max_wpa, player_to_min_wpa):
    for name in player_to_wpa:
        if name in iit_players:
            print("{}: {} total\n\t\t{} for min for point {}\n\t\t{} max for point {}".format(name,
                                                                                              round(player_to_wpa[name],
                                                                                                    4),
                                                                                              round(player_to_min_wpa[
                                                                                                        name]["min"],
                                                                                                    4),
                                                                                              player_to_min_wpa[name][
                                                                                                  "play"],
                                                                                              round(player_to_max_wpa[
                                                                                                        name]["max"],
                                                                                                    4),
                                                                                              player_to_max_wpa[name][
                                                                                                  "play"]))


if __name__ == "__main__":
    main()

