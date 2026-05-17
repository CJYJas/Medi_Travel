import os
import shutil
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile

from agents.logistics_agent import get_transport_requirements
from agents.orchestrator import orchestrate_packages
from utils.currency import convert_to_usd
from utils.db import get_few_shot_feedback, log_match
from utils.llm import check_for_clinical_gaps, normalize_medical_data_for_clarification
from utils.ocr_engine import extract_raw_text
from utils.parser import get_concise_json
from utils.privacy import PrivacyScrubber
from utils.translator import translate_medical_text, translate_text


def build_agent_response(packages: List[Dict[str, Any]], manual_override: bool) -> Dict[str, Any]:
    top_package = packages[0] if packages else None
    return {
        "retriever_source": "chromadb",
        "manual_override": manual_override,
        "total_accessibility_score": (top_package or {}).get("total_accessibility_score", 0),
        "structured_itinerary": (top_package or {}).get("structured_itinerary"),
        "antigravity_state": (top_package or {}).get("antigravity_state"),
    }


def extract_medical_payload(file: UploadFile, temp_prefix: str = "temp") -> Dict[str, Any]:
    file_location = f"{temp_prefix}_{file.filename}"
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        raw_text = extract_raw_text(file_location)
        if "Error" in raw_text:
            raise HTTPException(status_code=400, detail=raw_text)

        scrubber = PrivacyScrubber()
        scrubbed_text = scrubber.scrub_raw_text(raw_text)
        translated_text = translate_medical_text(scrubbed_text)
        medical_data = get_concise_json(translated_text)

        return {
            "medical_data": medical_data,
            "privacy_logs": scrubber.get_logs(),
            "debug": {
                "raw_text_original": raw_text,
                "raw_text_scrubbed": scrubbed_text,
                "translated_text": translated_text,
            },
        }
    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Data extraction error: {exc}") from exc
    finally:
        if os.path.exists(file_location):
            os.remove(file_location)


def translate_packages(packages: List[Dict[str, Any]], language: str) -> None:
    if language.lower() in {"english", "en"}:
        return

    for package in packages:
        package["package_type"] = translate_text(package["package_type"], language)
        package["package_reasoning"] = translate_text(package["package_reasoning"], language)

        itinerary = package.get("structured_itinerary") or {}
        if itinerary.get("summary"):
            itinerary["summary"] = translate_text(itinerary["summary"], language)

        clinical_summary = package.get("clinical_summary") or {}
        if clinical_summary.get("professional_summary"):
            clinical_summary["professional_summary"] = translate_text(
                clinical_summary["professional_summary"],
                language,
            )


def match_package_payload(
    medical_data: Dict[str, Any],
    origin_country: str,
    budget_local: float,
    currency: str,
    preferred_month: str,
    preferred_language: str,
    user_origin: Optional[str] = None,
    user_priority_preference: str = "balanced",
    manual_override: bool = False,
    session_id: Optional[str] = None,
    rejected_hospitals: Optional[List[str]] = None,
) -> Dict[str, Any]:
    normalized_medical_data = normalize_medical_data_for_clarification(medical_data)
    active_session_id = session_id or str(uuid.uuid4())

    clarification = check_for_clinical_gaps(normalized_medical_data)
    if clarification:
        return {
            "clarification_required": True,
            "session_id": active_session_id,
            "missing_detail": clarification.get("missing_detail_description"),
            "clarification_question": clarification.get("clarification_question"),
            "agent_thinking_step": "Checking for Clinical Gaps...",
        }

    condition = normalized_medical_data.get("condition", "")
    prior_feedback = get_few_shot_feedback(condition)
    if prior_feedback:
        feedback_notes = "; ".join(
            f'Previously corrected: {feedback["feedback"]}'
            for feedback in prior_feedback
        )
        normalized_medical_data["_prior_corrections"] = feedback_notes
        print(
            f"[FEW-SHOT]: Injecting {len(prior_feedback)} prior corrections for condition '{condition}'"
        )

    budget_usd = convert_to_usd(budget_local, currency)
    packages = orchestrate_packages(
        medical_data=normalized_medical_data,
        origin_country=origin_country,
        budget_usd=budget_usd,
        currency=currency,
        preferred_month=preferred_month,
        user_origin=user_origin,
        user_priority_preference=user_priority_preference,
        manual_override=manual_override,
        rejected_hospitals=rejected_hospitals or [],
    )

    logistics_data = (
        packages[0]["flight_logistics"]
        if packages
        else get_transport_requirements(normalized_medical_data, origin=origin_country, destination="Malaysia")
    )

    urgency = normalized_medical_data.get("urgency", "Stable")
    match_status = "pending" if urgency in ("Urgent", "Critical") else "approved"

    if packages:
        top_package = packages[0]
        hospital_name = (top_package.get("specialist") or {}).get("hospital", "Unknown")
        flight_name = (top_package.get("flight") or {}).get("airline", "Unknown")
        charity_name = (top_package.get("charity") or {}).get("name", "None")
        log_match(
            active_session_id,
            match_status,
            condition,
            hospital_name,
            flight_name,
            charity_name,
            urgency,
        )

    translate_packages(packages, preferred_language)

    return {
        "session_id": active_session_id,
        "match_status": match_status,
        "agent_response": build_agent_response(packages, manual_override),
        "logistics": logistics_data,
        "recommended_packages": packages,
    }


def full_pipeline_payload(
    file: UploadFile,
    origin_country: str,
    budget_local: float,
    currency: str,
    preferred_month: str,
    preferred_language: str,
    user_origin: Optional[str] = None,
    user_priority_preference: str = "balanced",
    manual_override: bool = False,
) -> Dict[str, Any]:
    extracted_payload = extract_medical_payload(file, temp_prefix="temp_full")
    packages = orchestrate_packages(
        medical_data=extracted_payload["medical_data"],
        origin_country=origin_country,
        budget_usd=budget_local,
        currency=currency,
        preferred_month=preferred_month,
        user_origin=user_origin,
        user_priority_preference=user_priority_preference,
        manual_override=manual_override,
    )
    logistics_data = (
        packages[0]["flight_logistics"]
        if packages
        else get_transport_requirements(
            extracted_payload["medical_data"],
            origin=origin_country,
            destination="Malaysia",
        )
    )
    translate_packages(packages, preferred_language)

    return {
        "agent_response": build_agent_response(packages, manual_override),
        "extracted_medical_data": extracted_payload["medical_data"],
        "privacy_logs": extracted_payload["privacy_logs"],
        "logistics": logistics_data,
        "recommended_packages": packages,
    }
