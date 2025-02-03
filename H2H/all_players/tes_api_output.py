import requests
import json

url1 = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/401671617/competitions/401671617/competitors/22/roster/4240631/statistics/0"
url = 'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/401671617/competitions/401671617/competitors/22/statistics'


response = requests.get(url)
response1 = response.json()

if response1:
     with open("cardprteam_defmaygbe.txt", "w") as file:
        json.dump(response1, file, indent=4)  # Saves JSON data to file with indentation
