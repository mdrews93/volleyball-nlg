from collections import defaultdict, namedtuple
import pickle
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import re
import datetime

percentage_diff_dict = pickle.load(open("./data/percentage_diff_dict.p", "rb"))
percentage_score_dict = pickle.load(open("./data/percentage_score_dict.p", "rb"))


def main():
    boxscore_url = "http://www.illinoistechathletics.com/sports/mvball/2017-18/boxscores/20180112_1ei7.xml?tmpl=vbxml-monospace-template"
    site_url = "http://www.illinoistechathletics.com/sports/mvball/2017-18/boxscores/20180112_1ei7.xml"
    playbyplay_url = "http://www.illinoistechathletics.com/sports/mvball/2017-18/boxscores/20180210_29pk.xml?view=plays"

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

    with open("template.html", "r+") as file:
        txt = file.read()
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

        file.seek(0)
        file.truncate()

        file.write(str(soup))






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
    Point = namedtuple('Point', 'iit_score opp_score server summary winner')
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

    for point in soup.find_all(name="tr"):
        try:
            if point["class"][0] in ["even", "odd"]:
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
                                        server=server,
                                        summary=summary,
                                        winner=winner)
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
    # info_dict["template_home_set_four_score"] = set_scores["home"]["sets"][3]
    # info_dict["template_home_set_five_score"] = set_scores["home"]["sets"][4]

    info_dict["template_visitor_set_one_score"] = set_scores["away"]["sets"][0]
    info_dict["template_visitor_set_two_score"] = set_scores["away"]["sets"][1]
    info_dict["template_visitor_set_three_score"] = set_scores["away"]["sets"][2]
    # info_dict["template_visitor_set_four_score"] = set_scores["away"]["sets"][3]
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
                info_dict["template_home_ace_leader"] = "A: " + name.split("_")[1] + " - " + str(aces)

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

