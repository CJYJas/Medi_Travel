import json
import re
import os
import asyncio

# 🔹 Existing pipeline
from utils.ocr_engine import extract_raw_text
from utils.translator import translate_medical_text
from utils.parser import get_concise_json

# 🔹 Agents
from agents.logistics_agent import get_transport_requirements
from agents.flight_agent import get_flight_options


# 🔒 PII Scrubber
def scrub_pii(data):
    """Masks common patterns (Dates and Phone numbers)."""
    if data.get("condition") == "Extraction Error":
        return data

    for key, value in data.items():
        if isinstance(value, str):
            value = re.sub(r'\d{2}/\d{2}/\d{4}', '[REDACTED_DATE]', value)
            value = re.sub(r'\+?\d{10,12}', '[REDACTED_PHONE]', value)
            data[key] = value

    return data


# 🚀 MAIN PIPELINE
def run_full_pipeline(file_path, country="Thailand"):
    print(f"\n--- 1. Extracting Text from {file_path} ---")
    raw_text = extract_raw_text(file_path)

    print("\n--- 2. Translating to English (ASEAN Pivot) ---")
    english_text = translate_medical_text(raw_text)
    print(f"DEBUG: Translator Output: '{english_text[:120]}...'")

    print("\n--- 3. Structuring Medical Data ---")
    structured_data = get_concise_json(english_text)

    print("\n--- 4. Inferring Logistics Requirements ---")
    logistics_data = get_transport_requirements(
        structured_data,
        origin="Bangkok",
        destination="Malaysia"
    )

    # 🔗 Merge medical + logistics
    final_output = {
        "medical_data": structured_data,
        "logistics": logistics_data
    }

    # 🧠 STEP 5: CORE TRANSPORT DECISION ENGINE (Amadeus API)
    print("\n--- 5. Generating Flight/Transport Recommendation (via Amadeus) ---")
    transport_plan = get_flight_options(logistics_data, country)

    final_output["transport_recommendation"] = transport_plan

    # 🔍 Debug before scrubbing
    print(f"\nDEBUG: Final output BEFORE scrubbing:\n{json.dumps(final_output, indent=2)}")

    # 🔒 STEP 7: Scrub PII (only on medical data)
    final_output["medical_data"] = scrub_pii(final_output["medical_data"])

    return final_output


# 🧪 TEST RUN
if __name__ == "__main__":
    path = r"C:\Users\User\Downloads\Safra-oncology-report-page-1.b197b0.pdf"

    if not os.path.exists(path):
        print(f"❌ ERROR: File not found at {path}")
    else:
        result = run_full_pipeline(path, country="Thailand")

        print("\n" + "="*50)
        print("🎯 FINAL CONSOLIDATED OUTPUT")
        print("="*50)
        print(json.dumps(result, indent=4))