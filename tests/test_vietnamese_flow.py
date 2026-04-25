import requests
import json
import os

def test_vietnamese_flow():
    print("Testing Vietnamese Pipeline Integration...")
    
    url = "http://localhost:8000/api/v1/full-pipeline"
    # The report is in the same folder as the script
    report_path = os.path.join(os.path.dirname(__file__), "vietnamese_report.jpg")
    
    if not os.path.exists(report_path):
        print("Error: vietnamese_report.jpg not found.")
        return

    # Prepare the image and form data
    files = {'file': ('vietnamese_report.jpg', open(report_path, 'rb'), 'image/jpeg')}
    data = {
        'origin_country': 'Vietnam',
        'budget_usd': '6000'
    }
    
    try:
        response = requests.post(url, files=files, data=data)
        if response.status_code == 200:
            result = response.json()
            print("\nSUCCESS! The Multi-Agent System processed the Vietnamese report:")
            
            # Show the extraction & translation
            print("\n--- AI TRANSLATION & PARSING ---")
            print(f"Condition detected: {result.get('extracted_medical_data', {}).get('condition')}")
            
            # Show the specialist matching
            print("\n--- DOCTOR MATCHING (FROM RAG) ---")
            packages = result.get('recommended_packages', [])
            for pkg in packages[:1]:
                doc = pkg.get('specialist', {})
                print(f"Recommended Specialist: {doc.get('name')} at {doc.get('hospital')}")
                print(f"Sub-Specialty: {doc.get('specialty')}")
                print(f"Reasoning: {pkg.get('package_reasoning')}")
                
            # Show logistics
            print("\n--- LOGISTICS (LIVE FLIGHTS) ---")
            print(f"Mobility: {result.get('logistics', {}).get('mobility_level')}")
            options = result.get('recommended_packages', [{}])[0].get('flight_logistics', {}).get('options', [])
            if options:
                print(f"Top Flight: {options[0].get('airline')} at {options[0].get('price')}")
                
        else:
            print(f"API Error ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    test_vietnamese_flow()
