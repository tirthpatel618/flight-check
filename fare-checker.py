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


amadeus = Client(
    client_id=os.getenv("API_KEY"),
    client_secret=os.getenv("API_SECRET"),
    hostname='production'
)

def search_flights(max_price):
    departure_date = date.today() + timedelta(days=1)
    return_date = departure_date + timedelta(days=4)
    origin = 'YYZ'
    try: 
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode="ZRH",
            departureDate=departure_date,
            returnDate=return_date,
            adults=1,
            currencyCode='CAD'
        )
    except ResponseError as error:
        print(f"An error occurred: {error}")
        return None
    
    flights = []
    for offer in response.data:
        if 'price' in offer and 'total' in offer['price']:
            price = float(offer['price']['total'])
            if price <= max_price:
                flight_info = parse_flight_offer(offer, "ZRH", departure_date, return_date)
                flights.append(flight_info)
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

