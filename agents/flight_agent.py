import os
from typing import Dict, List
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def get_serpapi_search(params):
    if not SERPAPI_KEY:
        return None
    try:
        params["api_key"] = SERPAPI_KEY
        return GoogleSearch(params)
    except Exception as e:
        print(f"SerpApi Error: {e}")
        return None

def find_flights(origin_country: str, destination_airport: str = "KUL", date: str = None, adults: int = 1, max_offers: int = 3) -> List[Dict]:
    """
    Uses SerpApi Google Flights to find real flights.
    Mocks the response if SerpApi is not configured or fails.
    """
    if date is None:
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")
        
    # Mapping for all 11 ASEAN countries to IATA codes
    iata_mapping = {
        "brunei": "BWN",
        "cambodia": "PNH",
        "indonesia": "CGK",
        "laos": "VTE",
        "malaysia": "KUL",
        "myanmar": "RGN",
        "philippines": "MNL",
        "singapore": "SIN",
        "thailand": "BKK",
        "timor-leste": "DIL",
        "vietnam": "SGN"
    }
    
    origin_airport = iata_mapping.get(origin_country.lower(), "BKK")
    
    params = {
        "engine": "google_flights",
        "departure_id": origin_airport,
        "arrival_id": destination_airport,
        "outbound_date": date,
        "currency": "USD",
        "hl": "en",
        "adults": adults,
        "type": "2" # One Way
    }
    
    search = get_serpapi_search(params)
    
    if search:
        try:
            response = search.get_dict()
            
            best_flights = response.get("best_flights", [])
            other_flights = response.get("other_flights", [])
            all_offers = best_flights + other_flights
            
            flights = []
            for offer in all_offers[:max_offers]:
                price = offer.get('price', 'Unknown')
                flights_info = offer.get('flights', [])
                
                airline = "Unknown"
                departing_at = "Unknown"
                arriving_at = "Unknown"
                
                if flights_info:
                    airline = flights_info[0].get('airline', 'Unknown')
                    departing_at = flights_info[0].get("departure_airport", {}).get("time", "Unknown")
                    # Use last segment for arrival if there are connections
                    arriving_at = flights_info[-1].get("arrival_airport", {}).get("time", "Unknown")
                
                price_str = f"{price} USD" if isinstance(price, (int, float)) else str(price)
                
                flights.append({
                    "airline": airline,
                    "price": price_str,
                    "departure": departing_at,
                    "arrival": arriving_at,
                    "type": "Commercial Flight (Google Flights)"
                })
            
            if flights:
                return flights
        except Exception as error:
            print(f"SerpApi Error: {error}")
            # Fallback to mock if API fails
            pass
            
    # Mock fallback
    print("⚠️ Using mock flight data (SerpApi not configured or failed)")
    return [
        {
            "airline": "AirAsia (Mock)",
            "price": "120 USD",
            "type": "Commercial Flight"
        },
        {
            "airline": "Malaysia Airlines (Mock)",
            "price": "250 USD",
            "type": "Commercial Flight"
        }
    ]

def get_flight_options(logistics_data: Dict, origin_country: str) -> Dict:
    """
    Analyzes logistics requirements and fetches appropriate flights.
    """
    mobility = logistics_data.get("mobility_level", "Ambulatory")
    date = logistics_data.get("departure_date")
    adults = logistics_data.get("adults", 1)
    max_offers = logistics_data.get("max_offers", 3)
    
    # If they need a stretcher, commercial flights from Amadeus aren't sufficient.
    if mobility == "Stretcher":
        email_body = (
            f"Dear Air Ambulance Provider,\n\n"
            f"We are requesting a quote for a private medical charter for a patient requiring a stretcher.\n\n"
            f"Origin: {origin_country}\n"
            f"Mobility Level: Stretcher\n"
            f"Companions: {adults - 1}\n\n"
            f"Please provide an estimated quote and availability.\n\n"
            f"Thank you."
        )
        
        return {
            "recommendation": "Air Ambulance Required",
            "options": [
                {
                    "provider": "Air Ambulance Operator",
                    "price": "Contact for Quote",
                    "type": "Private Medical Charter",
                    "email_draft": {
                        "to": "",
                        "subject": f"Medical Charter Request - Stretcher Patient from {origin_country}",
                        "body": email_body
                    }
                }
            ],
            "notes": "Patient requires stretcher. Standard commercial flights from Amadeus are not applicable. Please use the provided email draft to request quotes from specialized medical flight operators."
        }
        
    flights = find_flights(
        origin_country=origin_country,
        date=date,
        adults=adults,
        max_offers=max_offers
    )
    
    return {
        "recommendation": f"Commercial Flight suitable for {mobility} passengers",
        "options": flights,
        "notes": "Wheelchair assistance can be requested at the airport." if mobility == "Wheelchair" else "Standard travel."
    }
