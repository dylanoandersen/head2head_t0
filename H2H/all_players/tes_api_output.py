import requests
import json

url = 'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/401671861/competitions/4071861/competitors/11/roster/11252/statistics/0'



response = requests.get(url)
response1 = response.json()

if response1:
     with open("joooooooeeeeeeeeeeeeeeeeee.txt", "w") as file:
        json.dump(response1, file, indent=4)  # Saves JSON data to file with indentation

