import requests
import json

url1 = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/3917849"


totalProj = 'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2024/types/2/athletes/3139477/statistics'
playerNews = 'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2021/athletes/3117251/notes'
playerNews1 = 'https://site.api.espn.com/apis/fantasy/v2/games/ffl/news/players?limit=100&playerId=3053760'
headshot = 'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/athletes/3117251'
teamInjuries = 'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/teams/12/injuries'
teamsOnBye = 'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2024/types/2/weeks/8'

liveBox = 'https://cdn.espn.com/core/nfl/boxscore?xhr=1&gameId=401671489'

test = 'http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2024/teams/12?lang=en&region=us'
own = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2024/players?view=kona_player_info"
rr = 'https://api.sportsdata.io/v3/nfl/projections/json/PlayerGameProjectionStatsByWeek/2024REG/17?key=85266f5b9d954fbebb82673d6d417982'
headers = {
    "X-Fantasy-Filter": '{"players":{"limit":3000}}'
}

response = requests.get(rr, headers=headers)
response1 = response.json()

if response1:
     with open("testzzzz.txt", "w") as file:
        json.dump(response1, file, indent=4)  # Saves JSON data to file with indentation
