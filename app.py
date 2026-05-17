import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from agents.charity_agent import match_charities
from agents.flight_agent import get_flight_options
from agents.logistics_agent import get_transport_requirements
from agents.medical_agent import match_hospitals
from agents.orchestrator import generate_single_package
from api_models import (
    CombinePackageRequest,
    DoctorProfileRequest,
    GenerateLetterRequest,
    LayerRequest,
    MatchRequest,
    SaveSelectionRequest,
    TranslateBatchRequest,
    TranslateTemplateRequest,
    TranslateTextRequest,
    UserCreate,
)
from services.letter_service import generate_letter_pdf, preview_letter_html
from services.pipeline_service import (
    extract_medical_payload,
    full_pipeline_payload,
    match_package_payload,
)
from services.translation_service import translate_batch_texts
from utils.db import Selection, User, get_db
from utils.letter_generator import LETTER_SKELETONS
from utils.translator import (
    generate_friendly_reasoning,
    translate_template_text,
    translate_text,
)
from utils.transparency import (
    charity_match_transparency,
    extract_transparency,
    flight_match_transparency,
    hospital_match_transparency,
)

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Malaysia Medical Match API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = pwd_context.hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully"}


@app.post("/api/v1/login")
async def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"access_token": db_user.username, "token_type": "bearer"}


@app.post("/api/v1/save-selection")
async def save_selection(
    request: SaveSelectionRequest,
    username: str,
    db: Session = Depends(get_db),
):
    db_user = db.query(User).filter(User.username == username).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    selection = Selection(
        user_id=db_user.id,
        doctor_id=request.doctor_id,
        charity_id=request.charity_id,
    )
    db.add(selection)
    db.commit()
    return {"message": "Selection saved"}


@app.get("/")
def root():
    return {"status": "ok", "message": "Multi-layer Agent Backend is running."}


@app.get("/tester", response_class=HTMLResponse)
async def get_tester():
    tester_path = Path(__file__).resolve().parent / "frontend" / "pipeline_tester.html"
    try:
        return tester_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Tester UI file not found") from exc


@app.post("/api/v1/extract")
async def extract_chart(file: UploadFile = File(...)):
    extracted_payload = extract_medical_payload(file)
    return {
        "medical_data": extracted_payload["medical_data"],
        "privacy_logs": extracted_payload["privacy_logs"],
        "decision_transparency": extract_transparency(len(extracted_payload["privacy_logs"] or [])),
        "debug": extracted_payload["debug"],
    }


@app.post("/api/v1/match-packages")
async def match_packages(request: MatchRequest):
    return match_package_payload(
        medical_data=request.medical_data.model_dump(),
        origin_country=request.origin_country,
        budget_local=request.budget_local,
        currency=request.currency,
        preferred_month=request.preferred_month,
        preferred_language=request.preferred_language,
        user_origin=request.user_origin,
        user_priority_preference=request.user_priority_preference,
        manual_override=request.manual_override,
        session_id=request.session_id,
        rejected_hospitals=request.rejected_hospitals,
    )


@app.post("/api/v1/match-hospitals")
async def api_match_hospitals(request: LayerRequest):
    medical_data = request.medical_data.model_dump()
    hospitals = match_hospitals(medical_data)
    condition = medical_data.get("condition", "your condition")

    for hospital in hospitals:
        hospital["reasoning"] = generate_friendly_reasoning(
            "hospital/doctor",
            hospital,
            condition,
            request.language or "en",
        )

    return {
        "hospitals": hospitals,
        "decision_transparency": hospital_match_transparency(medical_data),
    }


@app.post("/api/v1/match-flights")
async def api_match_flights(request: LayerRequest):
    medical_data = request.medical_data.model_dump()
    logistics_data = get_transport_requirements(
        medical_data,
        origin=request.origin_country,
        destination="Malaysia",
    )
    flight_options = get_flight_options(logistics_data, request.origin_country)
    condition = medical_data.get("condition", "your condition")

    for option in flight_options.get("options", []):
        option["reasoning"] = generate_friendly_reasoning(
            "flight",
            option,
            condition,
            request.language or "en",
        )

    return {
        "logistics_data": logistics_data,
        "flight_options": flight_options,
        "decision_transparency": flight_match_transparency(
            request.origin_country,
            logistics_data,
            flight_options,
        ),
    }


@app.post("/api/v1/match-charities")
async def api_match_charities(request: LayerRequest):
    medical_data = request.medical_data.model_dump()
    condition = medical_data.get("condition", "your condition")
    charities = match_charities(medical_data, request.origin_country)

    tavily_key = os.getenv("TAVILY_API_KEY")
    tavily_client = None
    if tavily_key:
        from tavily import TavilyClient

        tavily_client = TavilyClient(api_key=tavily_key)

    for charity in charities:
        charity["reasoning"] = generate_friendly_reasoning(
            "charity",
            charity,
            condition,
            request.language or "en",
        )
        charity["website"] = _resolve_charity_website(tavily_client, charity["name"])

    if not charities:
        charities = [
            {
                "id": "fallback_charity",
                "name": "Global Medical Aid",
                "organization": "Generic NGO",
                "max_coverage_usd": 1000,
                "website": "https://www.who.int",
                "reasoning": (
                    "This fallback option is provided because no specific charities "
                    "were found in the database for your condition."
                ),
            }
        ]

    return {
        "charities": charities,
        "decision_transparency": charity_match_transparency(
            request.origin_country,
            condition,
        ),
    }


@app.post("/api/v1/translate-template")
async def translate_template(request: TranslateTemplateRequest):
    if request.template_key not in LETTER_SKELETONS:
        raise HTTPException(status_code=404, detail="Template not found")

    translated_template = translate_template_text(
        LETTER_SKELETONS[request.template_key],
        request.target_language,
    )
    return {"translated_template": translated_template}


@app.post("/api/v1/translate-text")
async def api_translate_text(request: TranslateTextRequest):
    if not request.text.strip():
        return {"translated_text": ""}
    return {"translated_text": translate_text(request.text, request.target_language)}


@app.post("/api/v1/translate-batch")
async def api_translate_batch(request: TranslateBatchRequest):
    return {
        "translated_texts": translate_batch_texts(
            request.texts,
            request.target_language,
        )
    }


@app.post("/api/v1/doctor-profile")
async def api_doctor_profile(request: DoctorProfileRequest):
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        return {"profile_url": None, "error": "Tavily API key missing"}

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=tavily_key)
        query = (
            f'"{request.doctor_name}" "{request.hospital_name}" doctor profile '
            "site:com OR site:my OR site:sg OR site:id"
        )
        response = client.search(query, search_depth="basic", max_results=3)
        results = response.get("results", [])
        return {"profile_url": results[0]["url"] if results else None}
    except Exception as exc:
        print(f"Doctor profile search error: {exc}")
        return {"profile_url": None, "error": str(exc)}


@app.post("/api/v1/combine-package")
async def api_combine_package(request: CombinePackageRequest):
    package = generate_single_package(
        hospital=request.hospital,
        logistics_data=request.logistics_data,
        flight=request.flight,
        charity=request.charity,
        origin_country=request.origin_country,
        budget_usd=request.budget_usd,
    )
    return {"package": package}


@app.post("/api/v1/preview-letter")
async def api_preview_letter(request: GenerateLetterRequest):
    try:
        html = preview_letter_html(
            template_key=request.template_key,
            user_data=request.user_data,
            medical_data=request.medical_data or {},
            package_data=request.package_data or {},
            target_language=request.target_language,
        )
        return {"html": html}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"CRITICAL PDF PREVIEW ERROR: {exc}")
        raise HTTPException(status_code=500, detail=f"PDF Preview failed: {exc}") from exc


@app.post("/api/v1/generate-letter")
async def api_generate_letter(request: GenerateLetterRequest):
    try:
        pdf_bytes = generate_letter_pdf(
            template_key=request.template_key,
            user_data=request.user_data,
            medical_data=request.medical_data or {},
            package_data=request.package_data or {},
            target_language=request.target_language,
        )
        filename = f"{request.template_key}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        print(f"CRITICAL PDF ERROR: {exc}")
        raise HTTPException(status_code=500, detail=f"PDF Generation failed: {exc}") from exc


@app.post("/api/v1/full-pipeline")
async def full_pipeline(
    file: UploadFile = File(...),
    origin_country: str = Form("Indonesia"),
    user_origin: str | None = Form(None),
    budget_usd: int = Form(5000),
    currency: str = Form("USD"),
    preferred_month: str = Form("Next Month"),
    preferred_language: str = Form("English"),
    user_priority_preference: str = Form("balanced"),
    manual_override: bool = Form(False),
):
    return full_pipeline_payload(
        file=file,
        origin_country=origin_country,
        budget_local=budget_usd,
        currency=currency,
        preferred_month=preferred_month,
        preferred_language=preferred_language,
        user_origin=user_origin,
        user_priority_preference=user_priority_preference,
        manual_override=manual_override,
    )


def _resolve_charity_website(tavily_client, charity_name: str) -> str:
    if not tavily_client:
        return "#"

    try:
        response = tavily_client.search(
            f'"{charity_name}" official website',
            search_depth="basic",
            max_results=1,
        )
        results = response.get("results", [])
        return results[0]["url"] if results else "#"
    except Exception:
        return "#"


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
