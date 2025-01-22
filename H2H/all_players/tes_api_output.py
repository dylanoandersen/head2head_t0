import requests
import json

url = 'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/401671814/competitions/401671814/competitors/9/roster/4248528/statistics/0'



response = requests.get(url)
response1 = response.json()

if response1:
     with open("api3.txt", "w") as file:
        json.dump(response1, file, indent=4)  # Saves JSON data to file with indentation

