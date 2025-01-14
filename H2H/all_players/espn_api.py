import requests
import json
#from .models import Player

url = "https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?limit=20000&active=true"

url1 = "https://nfl-api-data.p.rapidapi.com/nfl-ath-stats"


headers = {
	"x-rapidapi-key": "e0aeb7fd47msh823f3ee223dda3ep13cdbejsn323498bca149",
	"x-rapidapi-host": "nfl-api-data.p.rapidapi.com"
}

def fetch_espn_data():

    print("🔍 Sending request to ESPN API...")
    response = requests.get(url)
    
    print(f"🔄 Received response with status code: {response.status_code}")

    if response.status_code == 200:
        print("✅ Successfully fetched data! Parsing response...")
        return response.json()  # Return JSON data
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return None

# def get_stats():

#     player_id = 14880
#     querystring = {"id":player_id}

#     print("🔍 Sending request to ESPN API...")
#     response = requests.get(url1, headers=headers, params=querystring)
    
#     print(f"🔄 Received response with status code: {response.status_code}")

#     if response.status_code == 200:
#         print("✅ Successfully fetched data! Parsing response...")
#         return response.json()  # Return JSON data
#     else:
#         print(f"❌ Error {response.status_code}: {response.text}")
#         return None

# data = get_stats()
# if data:
#      with open("api.txt", "w") as file:
#         json.dump(data, file)  # Saves JSON data to file with indentation




