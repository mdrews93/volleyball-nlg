import pickle
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from collections import defaultdict
import copy
import time
import datetime
import pprint


def main():
    start_time = time.time()
    print("Script starting at {}".format(datetime.datetime.now()))

    gamelinks = pickle.load(open("gamelinks.p", "rb"))
    base_url = "http://stats.ncaa.org/game/play_by_play/"

    raw_counts_dict = create_raw_counts_dict()
    diff_dict = create_diff_dict()

    errors = 0
    victims = []
    invalid_links = set()
    invalid_idx = set()
    for idx, link in enumerate(gamelinks):
        game_id = link.split("/")[3]
        try:
            req = Request(base_url + game_id,
                          headers={'User-Agent': 'Mozilla/5.0'})
            resp = urlopen(req).read()
            soup = BeautifulSoup(resp, "html5lib")

            # for tag in soup.find_all(name='td', class_="smtext"):
            #     print(tag)

            set_results, number_of_sets = retrieve_set_results(soup)

            sets = retrieve_sets(soup, number_of_sets)

            update_dicts(raw_counts_dict, diff_dict, sets, set_results, link, invalid_links, invalid_idx, idx)

            print("Finished processing game {} out of {} - link: {}".format(idx+1, len(gamelinks), base_url+game_id))
        except Exception as err:
            errors += 1
            print("Error processing link {}: {}".format(base_url+game_id, err))
            victims.append(idx)
    print("Saving invalid links list with {} links".format(len(invalid_links)))
    pickle.dump(invalid_links, open("invalid_gamelinks.p", "wb"))
    for i in sorted(victims.extend(invalid_idx), reverse=True):
        del gamelinks[i]

    print("Removed {} links".format(len(victims)))
    if len(victims) > 0:
        print("Saving updated links list")
        pickle.dump(gamelinks, open("gamelinks.p", "wb"))

    print("Completed processing raw counts. {} errors out of {} links".format(errors, len(gamelinks)+errors))

    percentage_score_dict = compute_score_percentages(raw_counts_dict)
    percentage_diff_dict = compute_diff_percentages(diff_dict)

    pickle.dump(raw_counts_dict, open("raw_counts_dict.p", "wb"))
    pickle.dump(percentage_score_dict, open("percentage_score_dict.p", "wb"))
    pickle.dump(percentage_diff_dict, open("percentage_diff_dict.p", "wb"))

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(percentage_score_dict)
    pp.pprint(percentage_diff_dict)

    print("Script completed at {}".format(datetime.datetime.now()))
    print("Total runtime: {} seconds".format(round(time.time() - start_time, 2)))


def retrieve_set_results(soup):
    number_of_sets = 0
    team_to_side = {}
    team_to_results = defaultdict(list)
    left_scores = []
    right_scores = []
    results_table = soup.find(name="table", class_="mytable")
    first_row = results_table.tbody.tr
    for col in first_row.find_all("td"):
        if "Set" in col.string:
            number_of_sets += 1
    # print("{} sets".format(number_of_sets))
    second_row = first_row.next_sibling.next_sibling
    for idx, col in enumerate(second_row.find_all("td")):
        if idx == 0:
            team_to_side[col.string] = "left"
        elif idx <= number_of_sets:
            left_scores.append(int(col.string))
    # print(left_scores)
    third_row = second_row.next_sibling.next_sibling
    for idx, col in enumerate(third_row.find_all("td")):
        if idx == 0:
            team_to_side[col.string] = "right"
        elif idx <= number_of_sets:
            right_scores.append(int(col.string))
    # print(right_scores)

    for (left, right) in zip(left_scores, right_scores):
        if left>right:
            team_to_results["left"].append("W")
            team_to_results["right"].append("L")
        else:
            team_to_results["left"].append("L")
            team_to_results["right"].append("W")
    return team_to_results, number_of_sets


def create_raw_counts_dict():
    dict = {}
    for i in range(46):
        dict[i] = {}
        for j in range(46):
            dict[i][j] = {"W":0, "L":0}
    return dict


def create_diff_dict():
    dict = {}
    for i in range(-30,30):
        dict[i] = {"W":0, "L":0}
    return dict


def retrieve_sets(soup, number_of_sets):
    sets = []
    for i in range(number_of_sets):
        sets.append([])
    tables = []
    first_table = soup.find(name="table", class_="mytable").next_sibling.next_sibling\
                                                           .next_sibling.next_sibling\
                                                           .next_sibling.next_sibling\
                                                           .next_sibling.next_sibling\
                                                           .next_sibling.next_sibling\
                                                           .next_sibling.next_sibling\
                                                           .next_sibling.next_sibling\
                                                           .next_sibling.next_sibling
    tables.append(first_table)

    second_table = first_table.next_sibling.next_sibling\
                              .next_sibling.next_sibling\
                              .next_sibling.next_sibling
    tables.append(second_table)

    third_table = second_table.next_sibling.next_sibling\
                              .next_sibling.next_sibling\
                              .next_sibling.next_sibling
    tables.append(third_table)

    if number_of_sets >=4:
        fourth_table = third_table.next_sibling.next_sibling\
                                  .next_sibling.next_sibling\
                                  .next_sibling.next_sibling
        tables.append(fourth_table)
    if number_of_sets == 5:
        fifth_table = fourth_table.next_sibling.next_sibling \
                                  .next_sibling.next_sibling \
                                  .next_sibling.next_sibling
        tables.append(fifth_table)

    for idx, table in enumerate(tables):
        for td in table.find_all(name="td", class_="smtext"):
            try:
                left_point = td.span.string
                right_point = td.span.next_sibling.next_sibling.string
                sets[idx].append((int(left_point), int(right_point)))
                # print("{} - {}".format(left_point, right_point))
                # for span in td.find_all("span"):
                #     print(span)
            except Exception as err:
                pass
    return sets

    # for tag in soup.find_all(name='td', class_="boldtext"):
    #     if not found:
    #         try:
    #             if tag["width"] == "10%":
    #                 print("here")
    #                 left_team = tag.string.split("\xa0-\xa0")[0]
    #                 right_team = tag.string.split("\xa0-\xa0")[1]
    #                 found = True
    #         except:
    #             pass
    #     else:
    #         break


def update_dicts(raw_counts_dict, diff_dict, sets, set_results, link, invalid_links, invalid_idx, idx):
    for set_num, set in enumerate(sets):
        for left_point, right_point in set:
            if left_point>25 and left_point-right_point>2 or right_point>25 and right_point-left_point>2:
                print("{} to {} at {}".format(left_point, right_point, link))
                invalid_idx.add(idx)
                invalid_links.add(link)
                return
            if left_point-right_point > 9 and set_results["left"][set_num] == "L":
                print("{} to {} and left lost at {}".format(left_point, right_point, link))
            if right_point-left_point > 9 and set_results["right"][set_num] == "L":
                print("{} to {} and right lost at {}".format(left_point, right_point, link))

            raw_counts_dict[left_point][right_point][set_results["left"][set_num]] += 1
            raw_counts_dict[right_point][left_point][set_results["right"][set_num]] += 1

            diff_dict[left_point - right_point][set_results["left"][set_num]] += 1
            diff_dict[right_point - left_point][set_results["right"][set_num]] += 1


def compute_score_percentages(raw_counts_dict):
    percentage_dict = copy.deepcopy(raw_counts_dict)
    for left_point in percentage_dict:
        for right_point in percentage_dict[left_point]:
            try:
                sum = raw_counts_dict[left_point][right_point]['W'] + raw_counts_dict[left_point][right_point]['L']

                percentage_dict[left_point][right_point]['W'] = round(raw_counts_dict[left_point][right_point]['W']/sum, 3)
                percentage_dict[left_point][right_point]['W_counts'] = raw_counts_dict[left_point][right_point]['W']

                percentage_dict[left_point][right_point]['L'] = round(raw_counts_dict[left_point][right_point]['L']/sum, 3)
                percentage_dict[left_point][right_point]['L_counts'] = raw_counts_dict[left_point][right_point]['L']
            except:
                pass
    return percentage_dict


def compute_diff_percentages(diff_dict):
    percentage_dict = copy.deepcopy(diff_dict)
    for diff in percentage_dict:
        try:
            sum = diff_dict[diff]['W'] + diff_dict[diff]['L']
            percentage_dict[diff]['W'] = round(diff_dict[diff]['W']/sum, 3)
            percentage_dict[diff]['W_counts'] = diff_dict[diff]['W']

            percentage_dict[diff]['L'] = round(diff_dict[diff]['L']/sum, 3)
            percentage_dict[diff]['L_counts'] = diff_dict[diff]['L']
        except:
            pass
    return percentage_dict


if __name__ == "__main__":
    main()