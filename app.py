from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import os
from pydantic import BaseModel, Field
import shutil
import uvicorn

# Import utilities
from utils.ocr_engine import extract_raw_text
from utils.translator import translate_medical_text
from utils.parser import get_concise_json, scrub_raw_text

# Import agents
from agents.logistics_agent import get_transport_requirements
from agents.orchestrator import orchestrate_packages

app = FastAPI(title="Malaysia Medical Match API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class MatchRequest(BaseModel):
    medical_data: Dict[str, Any]
    origin_country: str = Field(default="Indonesia", description="Where the patient is flying from")
    budget_usd: int = Field(default=5000, description="Patient's maximum budget in USD")

@app.get("/")
def root():
    return {"status": "ok", "message": "Multi-layer Agent Backend is running."}

@app.post("/api/v1/extract")
async def extract_chart(file: UploadFile = File(...)):
    """
    Step 1: Upload a medical chart (Image/PDF). Extracts text, translates, and parses to JSON.
    """
    file_location = f"temp_{file.filename}"
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
        # 1. OCR Extraction
        raw_text = extract_raw_text(file_location)
        if "Error" in raw_text:
            raise HTTPException(status_code=400, detail=raw_text)
            
        # Scrub sensitive info BEFORE sending to the LLM
        safe_raw_text = scrub_raw_text(raw_text)
            
        # 2. Translation
        english_text = translate_medical_text(safe_raw_text)
        
        # 3. Parsing
        structured_data = get_concise_json(english_text)
        
        return {
            "medical_data": structured_data,
            "debug": {
                "raw_text_original": raw_text,
                "raw_text_scrubbed": safe_raw_text,
                "translated_text": english_text
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_location):
            os.remove(file_location)

@app.post("/api/v1/match-packages")
async def match_packages(request: MatchRequest):
    """
    Step 2: Takes the extracted medical data and orchestrates layers 1, 2, and 3.
    """
    medical_data = request.medical_data
    origin = request.origin_country
    budget = request.budget_usd
    
    # Analyze logistics
    logistics_data = get_transport_requirements(medical_data, origin=origin, destination="Malaysia")
    
    # Orchestrate packages (Hospital, Flight, Charity)
    packages = orchestrate_packages(medical_data, logistics_data, origin, budget)
    
    return {
        "logistics": logistics_data,
        "recommended_packages": packages
    }

@app.post("/api/v1/full-pipeline")
async def full_pipeline(
    file: UploadFile = File(...),
    origin_country: str = Form("Indonesia"),
    budget_usd: int = Form(5000)
):
    """
    Step 3: All-in-One. Upload the chart, enter your country and budget, and instantly get packages.
    (This simulates exactly what the App Frontend will do in one click).
    """
    file_location = f"temp_full_{file.filename}"
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
        # Extract
        raw_text = extract_raw_text(file_location)
        if "Error" in raw_text:
            raise HTTPException(status_code=400, detail=raw_text)
            
        safe_raw_text = scrub_raw_text(raw_text)
        english_text = translate_medical_text(safe_raw_text)
        medical_data = get_concise_json(english_text)
        
        # Match
        logistics_data = get_transport_requirements(medical_data, origin=origin_country, destination="Malaysia")
        packages = orchestrate_packages(medical_data, logistics_data, origin_country, budget_usd)
        
        return {
            "extracted_medical_data": medical_data,
            "logistics": logistics_data,
            "recommended_packages": packages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_location):
            os.remove(file_location)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
