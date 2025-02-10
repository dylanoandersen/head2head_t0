import requests
import json

url1 = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/401671617/competitions/401671617/competitors/22/roster/4240631/statistics/0"

# point projections
url = 'https://api.sportsdata.io/v3/nfl/projections/json/PlayerGameProjectionStatsByWeek/2024POST/1?key=85266f5b9d954fbebb82673d6d417982'
url2 = 'https://api.sportsdata.io/v3/nfl/projections/json/PlayerGameProjectionStatsByWeek/2024POST/4?key=85266f5b9d954fbebb82673d6d417982'

# new player stats live update?
url3 = 'https://api.sportsdata.io/v3/nfl/odds/json/BettingPlayerPropsByScoreID/18436?key=85266f5b9d954fbebb82673d6d417982'

# game details
url4 = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=401671696'

response = requests.get(url4)
response1 = response.json()

if response1:
     with open("gamz.txt", "w") as file:
        json.dump(response1, file, indent=4)  # Saves JSON data to file with indentation
