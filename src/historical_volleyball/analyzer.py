import pickle
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
from collections import namedtuple, defaultdict
import pprint

percentage_diff_dict = pickle.load(open("percentage_diff_dict.p", "rb"))
percentage_score_dict = pickle.load(open("percentage_score_dict.p", "rb"))


def main():
    player_to_wpa = defaultdict(lambda: 0)

    schedule_url = "http://www.illinoistechathletics.com/sports/mvball/2017-18/schedule/"
    base_url = "http://www.illinoistechathletics.com"
    game_links = get_gamelinks(schedule_url)

    points, iit_ids, iit_players = get_play_logs(game_links, base_url)

    for point in points:
        update_wpas(player_to_wpa, point, iit_ids)

    for name in player_to_wpa:
        if name in iit_players:
            print("{}: {}".format(name, round(player_to_wpa[name], 4)))


def update_wpas(player_to_wpa, point, iit_ids):
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
    elif "block error" in point.summary:
        if point.winner not in iit_ids:
            player = point.summary.split("error by ")[1].split(". ")[0]
    elif "Kill by" in point.summary and point.winner in iit_ids:
        if "(from" in point.summary:
            hitter = point.summary.split("Kill by ")[1].split(" (")[0]
            setter = point.summary.split("(from ")[1].split(")")[0]
            player_to_wpa[hitter] += wpa*(4/5)
            player_to_wpa[setter] += wpa*(1/5)
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




def get_wpa(before_score, after_score):
    before_wp = percentage_score_dict[before_score[0]][before_score[1]]['W']
    after_wp = percentage_score_dict[after_score[0]][after_score[1]]['W']
    return round((after_wp-before_wp)*100, 3)


def get_gamelinks(schedule_url):
    game_links = []
    req = Request(schedule_url,
                  headers={'User-Agent': 'Mozilla/5.0'})
    resp = urlopen(req).read()
    soup = BeautifulSoup(resp, "html5lib")

    for link in soup.find_all(name='a', class_="link", href=True):
        if "Box Score" in link['aria-label']:
            game_links.append(link["href"])

    return game_links


def get_play_logs(game_links, base_url):
    Point = namedtuple('Point', 'iit_score opp_score server summary winner')
    points = []
    iit_players = set()
    iit_ids = set()
    for game_link in game_links:
        req = Request(base_url + game_link + "?view=plays",
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
                pass

    return points, iit_ids, iit_players




if __name__ == "__main__":
    main()