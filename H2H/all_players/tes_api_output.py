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

response = requests.get(test)
response1 = response.json()

if response1:
     with open("test.txt", "w") as file:
        json.dump(response1, file, indent=4)  # Saves JSON data to file with indentation
