from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import pickle
import time
import datetime

years = ["2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018"]
months = ["01", "02", "03", "04"]
days = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
        "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
        "21", "22", "23", "24", "25", "26", "27", "28", "29", "30",
        "31"]
divisions = ["1", "3"]
gamelinks = []
request_count = 0

start_time = time.time()
print("Script starting at {}".format(datetime.datetime.now()))

for division in divisions:
    for year in years:
        for month in months:
            for day in days:
                printed = False
                try:
                    req = Request("http://stats.ncaa.org/team/schedule_list?academic_year=" + year
                                  + "&division=" + division
                                  + "&id=12825&sport_code=MVB&schedule_date=" + month
                                  +"%2F" + day
                                  +"%2F" + year,
                                         headers={'User-Agent': 'Mozilla/5.0'})
                    resp = urlopen(req).read()
                    soup = BeautifulSoup(resp, "html5lib")
                    request_count += 1
                    gamecount = 0
                    for link in soup.find_all('a', href=True):
                        if "/game/index" in link['href']:
                            gamecount += 1
                            url = link['href'].split("?")[0]
                            gamelinks.append(url)
                    print("{} games: division {} on {}/{}/{}".format(gamecount, division, month, day, year))
                    print("Total games retrieved: {}".format(len(gamelinks)))
                    printed = True
                except Exception as err:
                    print("Error occurred with settings M:{} D:{} Y:{} d:{}: {}".format(month, day, year, division, err))
                if not printed:
                    print("Error occurred with settings {}/{}/{} d{}".format(month, day, year, division))
        pickle.dump(gamelinks, open("gamelinks.p", "wb"))


print("{} total requests".format(request_count))
pickle.dump(gamelinks, open("gamelinks.p", "wb"))

print("Script completed at {}".format(datetime.datetime.now()))
print("Total runtime: {} seconds".format(round(time.time()-start_time, 2)))