import requests
import json

url = 'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/401671492/competitions/401671492/competitors/3/roster/4431611/statistics/0'



response = requests.get(url)
response1 = response.json()

if response1:
     with open("bears_maybe.txt", "w") as file:
        json.dump(response1, file, indent=4)  # Saves JSON data to file with indentation

