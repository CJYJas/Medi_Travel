from typing import Dict, List
from agents.medical_agent import match_hospitals
from agents.flight_agent import get_flight_options
from agents.charity_agent import match_charities
import ollama

def orchestrate_packages(medical_data: Dict, logistics_data: Dict, origin_country: str, budget_usd: int) -> List[Dict]:
    """
    Combines layers 1, 2, and 3 to create holistic medical travel packages.
    """
    # Layer 1
    hospitals = match_hospitals(medical_data)
    
    # Layer 2
    logistics = get_flight_options(logistics_data, origin_country)
    
    # Layer 3
    charities = match_charities(medical_data, origin_country)
    
    packages = []
    
    # We will generate up to 3 packages by combining these options
    for i, doc in enumerate(hospitals):
        
        # Determine top charity name
        charity_names = [c['name'] for c in charities]
        charity_text = f"Charities: {', '.join(charity_names)}" if charity_names else "No specific charities"
        
        prompt = (
            f"Context: Travel coordination for an international visitor to Malaysia.\n"
            f"Destination: {doc.get('hospital')}. Origin: {origin_country}. Budget: ${budget_usd} USD.\n"
            f"Specialist: {doc.get('name')} ({doc.get('specialty')})\n"
            f"Transport: {logistics.get('recommendation')}\n"
            f"- {charity_text}\n\n"
            f"Write two sentences for a travel brochure highlighting why this coordination of hospital reputation and logistics is a great value option."
        )
        
        try:
            response = ollama.chat(
                model='llama3.2:3b',
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.2, 'num_ctx': 800}
            )
            package_reasoning = response['message']['content'].strip()
        except Exception:
            package_reasoning = "This package combines top medical care, suitable logistics, and available financial aid."
            
        package = {
            "package_id": f"PKG_{i+1}",
            "package_reasoning": package_reasoning,
            "specialist": doc,
            "flight_logistics": logistics,
            "recommended_charities": charities
        }
        packages.append(package)
        
    return packages
