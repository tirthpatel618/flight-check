import os
import sys
import json
import smtplib
from email.message import EmailMessage
from datetime import date, timedelta, datetime
import dotenv
from amadeus import Client, ResponseError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

dotenv.load_dotenv()

class Config:
    AMADEUS_CLIENT_ID = os.getenv("API_KEY")
    AMADEUS_CLIENT_SECRET = os.getenv("API_SECRET")

    ORIGIN = 'YYZ'
    #change according to where you want to go?
    DESTINATIONS = ["PRG", "AMS", "FRA", "BCN", "MAD", "FCO", "VIE", "ZRH", "ARN", "OSL", "BUD"]
    WEEKS=4
    PRICE_THRESHOLD = int(os.getenv("PRICE_THRESHOLD", 400))  # Default to 400 if not set

    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
    RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")


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
        for week in range(Config.WEEKS):
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
                    if price <= Config.PRICE_THRESHOLD:
                        flight_info = self.parse_flight_offer(offer, destination, departure_date, return_date)
                        flights.append(flight_info)

        except ResponseError as error:
            print(f"An error occurred: {error}")
            return None        
        return flights
                
    def parse_flight_offer(self, offer, destination, departure_date, return_date):
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
    
    def format_flight_for_email(self, flight):
        """Format flight information for email"""
        html = f"""
        <div style="border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h3 style="color: #2c3e50;">✈️ {Config.ORIGIN} → {flight['destination']} → {Config.ORIGIN}</h3>
            <p style="font-size: 24px; color: #27ae60; font-weight: bold;">
                ${flight['price']:.2f} {flight['currency']}
            </p>
            
            <h4>Outbound: {flight['departure_date']}</h4>
            <ul>
        """
        
        for seg in flight['outbound_segments']:
            dep_time = datetime.fromisoformat(seg['departure'].replace('T', ' ')).strftime('%H:%M')
            arr_time = datetime.fromisoformat(seg['arrival'].replace('T', ' ')).strftime('%H:%M')
            html += f"""
                <li>{seg['from']} → {seg['to']} | {seg['carrier']}{seg['flight_number']} | {dep_time} - {arr_time}</li>
            """
        
        html += f"""
            </ul>
            
            <h4>Return: {flight['return_date']}</h4>
            <ul>
        """
        
        for seg in flight['inbound_segments']:
            dep_time = datetime.fromisoformat(seg['departure'].replace('T', ' ')).strftime('%H:%M')
            arr_time = datetime.fromisoformat(seg['arrival'].replace('T', ' ')).strftime('%H:%M')
            html += f"""
                <li>{seg['from']} → {seg['to']} | {seg['carrier']}{seg['flight_number']} | {dep_time} - {arr_time}</li>
            """
        
        html += f"""
            </ul>
            <p><strong>Class:</strong> {flight['booking_class']}</p>
        </div>
        """
        
        return html
    def send_email(self):
        """Send email with found deals"""
        if not self.deals_found:
            print("No deals found below threshold")
            return
        
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"✈️ Flight Deals Alert: {len(self.deals_found)} flights under ${Config.PRICE_THRESHOLD}"
        msg['From'] = Config.SENDER_EMAIL
        msg['To'] = Config.RECIPIENT_EMAIL
        
        # Create HTML content
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #2c3e50;">🎉 Flight Deals Found!</h2>
            <p>Found {len(self.deals_found)} flights from Toronto under ${Config.PRICE_THRESHOLD} CAD</p>
            <hr>
        """
        
        # Add each flight
        for flight in self.deals_found:
            html_content += self.format_flight_for_email(flight)
        
        html_content += """
            <hr>
            <p style="color: #7f8c8d; font-size: 12px;">
                This is an automated alert from your flight price monitor.<br>
                Prices may change quickly - book soon if interested!
            </p>
        </body>
        </html>
        """
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        try:
            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(Config.SENDER_EMAIL, Config.SENDER_PASSWORD)
                server.send_message(msg)
                print(f"Email sent successfully with {len(self.deals_found)} deals!")
        except Exception as e:
            print(f"Failed to send email: {e}")
    def run(self):

        weekends = self.get_dates()
        for destination in Config.DESTINATIONS:
            for depart, ret in weekends:
                depart_str = depart.strftime('%Y-%m-%d')
                return_str = ret.strftime('%Y-%m-%d')
                print(f"Searching flights to {destination} departing {depart_str} and returning {return_str}")
                flights = self.search_flights(destination, depart_str, return_str)
                time.sleep(1)
                if flights:
                    self.deals_found.extend(flights)
        if self.deals_found:
            self.send_email()
        print(f"Total deals found: {len(self.deals_found)}")

if __name__ == "__main__":
    flight_monitor = FlightMoniter()
    flight_monitor.run()


    



