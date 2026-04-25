import requests
import json

def test_matching_api():
    print("🚀 Sending test request to Docker API (http://localhost:8000)...")
    
    url = "http://localhost:8000/api/v1/match-packages"
    
    payload = {
        "medical_data": {
            "condition": "Cardiology",
            "severity": "Moderate",
            "sub_specialty_inference": "Interventional Cardiology"
        },
        "origin_country": "Thailand",
        "budget_usd": 5000
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ SUCCESS! The Multi-Agent Orchestrator responded:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"❌ API Error ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Failed to connect to Docker API: {e}")

if __name__ == "__main__":
    test_matching_api()
