import requests
import json

url = "https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?limit=20000&active=true"



response = requests.get(url)
response1 = response.json()

if response1:
     with open("hi.txt", "w") as file:
        json.dump(response1, file, indent=4)  # Saves JSON data to file with indentation

