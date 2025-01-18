import requests
import json

url = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=1000&dates=2024'



response = requests.get(url)
response1 = response.json()

if response1:
     with open("api.txt", "w") as file:
        json.dump(response1, file, indent=4)  # Saves JSON data to file with indentation

