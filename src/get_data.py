import dotenv
import requests 
import os
dotenv.load_dotenv()

"""

# Get API Key from .env
BEARER_KEY = os.getenv("BEARER_KEY")


url = "https://test.api.amadeus.com/v1/shopping/flight-destinations"
headers = {
    "Authorization": f"Bearer {BEARER_KEY}"
}
params = {
    "origin": "TOR",
    "maxPrice": 300,
}

response = requests.get(url, headers=headers, params=params)

# Print the response (JSON format)
print(response.json())
"""
from amadeus import Client, ResponseError

amadeus = Client(
    client_id=os.getenv("API_KEY"),
    client_secret=os.getenv("API_SECRET"),
    hostname='production'
)

response = amadeus.shopping.flight_destinations.get(origin='NYC', maxPrice=200, currency='CAD')
print(response.data)


print("done")