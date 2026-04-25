import ollama
import json
from utils.schemas import LogisticsRequirements

MODEL_NAME = 'llama3.2:3b'

def get_transport_requirements(medical_json, origin="Bangkok", destination="Malaysia"):
    """
    Analyze medical condition and return structured logistics requirements.
    """

    if medical_json.get("condition") == "Extraction Error":
        return LogisticsRequirements(
            mobility_level="Unknown",
            required_equipment=[],
            medical_escort_needed=False,
            search_query=""
        ).dict()

    system_prompt = f"""
        You are a Medical Logistics Expert for ASEAN travel.

        Patient is traveling from {origin} to {destination}.

        You MUST return a JSON object with EXACT keys:
        - mobility_level (Ambulatory, Wheelchair, Stretcher)
        - required_equipment (list of strings)
        - medical_escort_needed (true/false)
        - search_query (string)

        Rules:
        1. If condition includes "metastatic", "bone", or severe trauma → Stretcher
        2. If patient needs monitoring → escort = true
        3. Equipment examples: Oxygen, IV Drip, Monitor

        search_query format:
        "[mobility_level] medical transport {origin} to {destination} with [equipment]"
        """

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            format='json',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': json.dumps(medical_json)}
            ],
            options={'temperature': 0}
        )

        data = json.loads(response['message']['content'])

        # ✅ Enforce schema (VERY IMPORTANT)
        validated = LogisticsRequirements(**data)

        return validated.dict()

    except Exception as e:
        print(f"Logistics Agent Error: {e}")

        return LogisticsRequirements(
            mobility_level="Unknown",
            required_equipment=[],
            medical_escort_needed=False,
            search_query="medical transport ASEAN"
        ).dict()