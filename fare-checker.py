import os
import sys
import json
import smtplib
from email.message import EmailMessage
from datetime import date, timedelta
import requests
import dotenv
from amadeus import Client, ResponseError

dotenv.load_dotenv()

class Config:
    AMADEUS_CLIENT_ID = os.getenv("API_KEY")
    AMADEUS_CLIENT_SECRET = os.getenv("API_SECRET")

    ORIGIN = 'YYZ'
    DESTINATIONS = ["PRG", "AMS", "FRA", "BCN", "MAD", "FCO", "VIE", "ZRH", "ARN", "OSL", "BUD"]
    PRICE_THRESHOLD = 4000

class FlightMoniter:
    def __init__(self):
        self.amadeus = Client(
            client_id=Config.AMADEUS_CLIENT_ID,
            client_secret=Config.AMADEUS_CLIENT_SECRET,
            hostname='production'
        )
        self.deals_found = []
    
    def get_dates(self):
        weekends = []
        today = date.today()

        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7

        next_friday = today + timedelta(days=days_until_friday)
        for week in range(4):
            friday = next_friday + timedelta(weeks=week)
            monday = friday + timedelta(days=3)
            weekends.append((friday, monday))
        return weekends


    def search_flights(self, destination, departure_date, return_date):
        try: 
            response = self.amadeus.shopping.flight_offers_search.get(
                originLocationCode=Config.ORIGIN,
                destinationLocationCode=destination,
                departureDate=departure_date,
                returnDate=return_date,
                adults=1,
                currencyCode='CAD'
            )
            flights = []
            for offer in response.data:
                if 'price' in offer and 'total' in offer['price']:
                    price = float(offer['price']['total'])
                    if price <= Config.max_price:
                        flight_info = self.parse_flight_offer(offer, destination, departure_date, return_date)
                        flights.append(flight_info)

        except ResponseError as error:
            print(f"An error occurred: {error}")
            return None        
        return flights
                
    def parse_flight_offer(offer, destination, departure_date, return_date):
        outbound = offer['itineraries'][0]
        inbound = offer['itineraries'][1] if len(offer['itineraries']) > 1 else None
        
        def parse_segment(segment):
            return {
                'from': segment['departure']['iataCode'],
                'to': segment['arrival']['iataCode'],
                'departure': segment['departure']['at'],
                'arrival': segment['arrival']['at'],
                'carrier': segment['carrierCode'],
                'flight_number': segment['number']
            }
        
        flight_info = {
            'destination': destination,
            'departure_date': departure_date,
            'return_date': return_date,
            'price': float(offer['price']['total']),
            'currency': offer['price']['currency'],
            'outbound_segments': [parse_segment(seg) for seg in outbound['segments']],
            'inbound_segments': [parse_segment(seg) for seg in inbound['segments']] if inbound else [],
            'booking_class': offer['travelerPricings'][0]['fareDetailsBySegment'][0]['cabin'] if 'fareDetailsBySegment' in offer['travelerPricings'][0] else 'ECONOMY'
        }
        
        return flight_info
    


print(search_flights(4000))

