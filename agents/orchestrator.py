from typing import Any, Dict, List, Optional

from agents.charity_agent import calculate_potential_subsidy, match_charities
from agents.flight_agent import get_flight_options
from agents.logistics_agent import (
    get_transport_requirements,
    infer_hospital_city,
    resolve_user_origin_city,
    simulate_route_lookup,
)
from agents.medical_agent import generate_clinical_summary, match_hospitals
from utils.currency import convert_usd_to
from utils.date_calculator import calculate_travel_dates
from utils.llm import call_gemini
from utils.schemas import AntigravityState, StructuredItinerary, TotalCarePackage, UserPriorityPreference


def _dump_model(model: Any) -> Dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _hospital_cost_multiplier(tier: str) -> float:
    if tier == "Premium Private":
        return 1.18
    if tier == "Government / Semi-Gov":
        return 0.92
    return 1.0


def _tier_bonus(tier: str) -> int:
    if tier == "Premium Private":
        return 12
    if tier == "Government / Semi-Gov":
        return 8
    return 10


def _build_total_care_package(
    base_medical_cost: float,
    grant_reduction: float,
    travel_cost: float,
    budget_usd: float,
) -> TotalCarePackage:
    net_cost = round(max(0.0, base_medical_cost + travel_cost - grant_reduction), 2)
    return TotalCarePackage(
        base_medical_cost=round(base_medical_cost, 2),
        grant_reduction=round(grant_reduction, 2),
        travel_cost=round(travel_cost, 2),
        net_cost=net_cost,
        within_budget=net_cost <= float(budget_usd or 0),
    )


def _compute_accessibility_score(
    hospital: Dict[str, Any],
    total_care_package: Dict[str, Any],
    route: Dict[str, Any],
    subsidy: Dict[str, Any],
    budget_usd: float,
) -> int:
    net_cost = total_care_package["net_cost"]
    budget_gap = max(0.0, net_cost - float(budget_usd or 0))
    budget_score = 100.0 if budget_gap == 0 else max(5.0, 100.0 - (budget_gap / max(float(budget_usd or 1), 1.0)) * 100.0)

    travel_cost = float(route.get("travel_cost_usd", 0.0))
    travel_duration = float(route.get("travel_duration_hours", 0.0))
    travel_score = max(25.0, 100.0 - max(0.0, travel_cost - 90.0) * 0.25 - max(0.0, travel_duration - 1.5) * 16.0)

    grant_value = float(subsidy.get("potential_subsidy_usd", 0.0))
    grant_score = min(100.0, (grant_value / max(travel_cost, 1.0)) * 70.0 + (grant_value / max(total_care_package["base_medical_cost"], 1.0)) * 30.0)

    baseline_clinical = hospital.get("match_score")
    if baseline_clinical is None:
        baseline_clinical = max(55, 90 - ((hospital.get("semantic_rank", 1) - 1) * 10))
    clinical_score = min(100.0, float(baseline_clinical) + _tier_bonus(hospital.get("tier")))

    overall = (budget_score * 0.42) + (travel_score * 0.23) + (grant_score * 0.2) + (clinical_score * 0.15)
    return int(round(min(100.0, max(1.0, overall))))


def _build_package_label(index: int, preference: str, manual_override: bool) -> str:
    if manual_override:
        return f"Semantic Match {index}"

    if index == 1:
        labels = {
            "balanced": "Best Overall",
            "lowest_net_cost": "Most Affordable",
            "fastest_access": "Fastest Access",
            "clinical_quality": "Clinical Priority",
        }
        return labels.get(preference, "Best Overall")
    return f"Alternative {index}"


DESTINATION_AIRPORTS = {
    "Kuala Lumpur": "KUL",
    "Penang": "PEN",
    "Johor Bahru": "JHB",
    "Malacca": "MKZ",
    "Kota Kinabalu": "BKI",
    "Kuching": "KCH",
    "Putrajaya": "KUL",
}


def _destination_airport_for_hospital(hospital: Dict[str, Any]) -> str:
    city = infer_hospital_city(hospital.get("hospital_location", hospital.get("hospital", "")))
    return DESTINATION_AIRPORTS.get(city, "KUL")


def _normalize_selected_flight(
    flight_bundle: Dict[str, Any],
    fallback_route: Dict[str, Any],
) -> Dict[str, Any]:
    options = (flight_bundle or {}).get("options") or []
    selected = options[0] if options else {}
    travel_cost_usd = float(selected.get("travel_cost_usd") or fallback_route.get("travel_cost_usd") or 0.0)
    travel_duration_hours = float(selected.get("travel_duration_hours") or fallback_route.get("travel_duration_hours") or 0.0)

    return {
        "airline": selected.get("airline") or selected.get("provider") or "Flight option pending",
        "route": fallback_route.get("route", selected.get("route", "Route to Malaysia")),
        "departure": selected.get("departure", ""),
        "arrival": selected.get("arrival", ""),
        "price": selected.get("price") or f"{travel_cost_usd:.0f} USD",
        "type": selected.get("type") or fallback_route.get("travel_mode", "Commercial Flight"),
        "travel_mode": selected.get("travel_mode") or fallback_route.get("travel_mode", "Commercial Flight"),
        "travel_cost_usd": travel_cost_usd,
        "travel_duration_hours": travel_duration_hours,
        "origin_city": fallback_route.get("origin_city", ""),
        "destination_city": fallback_route.get("destination_city", ""),
        "lookup_type": selected.get("source") or fallback_route.get("lookup_type", "simulated_asean_route"),
    }

def _generate_reasoning_with_gemini(
    hospital: Dict[str, Any],
    route: Dict[str, Any],
    total_care_package: Dict[str, Any],
    subsidy: Dict[str, Any],
) -> Optional[str]:
    hospital_name = hospital.get("hospital", "the hospital")
    specialty = hospital.get("specialty", "the medical condition")
    net_cost = total_care_package["net_cost"]
    grant_amount = float(subsidy.get("potential_subsidy_usd", 0.0))
    grant_name = (subsidy.get("selected_charity") or {}).get("name") or "a charity grant"
    origin_city = route.get("origin_city", "your home city")
    travel_duration = route.get("travel_duration_hours", 0)

    prompt = f"""
    You are 'Antigravity', an empathetic AI medical travel coordinator. 
    Explain why this specific medical package is a great match for a patient with the following details:
    - Hospital: {hospital_name} (Specialty: {specialty})
    - Travel: From {origin_city} (Approx. {travel_duration} hours)
    - Financials: Net cost ${net_cost:,.2f} USD (Includes a ${grant_amount:,.2f} grant from {grant_name})

    The user is a layman and might be feeling anxious about medical travel. 
    Your goal is to provide a 'solid reason' why this package was chosen.
    Focus on:
    1. Clinical expertise: Why this specific hospital/specialist is trustable for {specialty}.
    2. Financial relief: How the ${grant_amount} subsidy helps them specifically.
    3. Logistics: Why this travel route from {origin_city} makes sense.

    Guidelines:
    - Start with a warm, reassuring tone.
    - Use clear, non-medical language.
    - Explain 'Why this match?' in a way that proves the Antigravity agent has deeply processed their request.
    - Keep it between 40-70 words.
    - Do NOT use markdown bolding or quotes.
    """
    
    try:
        response = call_gemini(prompt, "Generate reasoning.", model_name="gemini-3.0-flash")
    except Exception as exc:
        print(f"Gemini reasoning fallback triggered: {exc}")
        return None

    text = response.get("text", "").strip()
    if not text or text.startswith("MOCK:"):
        return None
    return text.replace("**", "").replace("\"", "")


def _build_structured_itinerary(
    hospital: Dict[str, Any],
    route: Dict[str, Any],
    total_care_package: Dict[str, Any],
    subsidy: Dict[str, Any],
    accessibility_score: int,
) -> Dict[str, Any]:
    hospital_name = hospital.get("hospital", "the matched hospital")
    origin_city = route.get("origin_city", "your city")
    destination_city = route.get("destination_city", "Malaysia")
    grant_amount = float(subsidy.get("potential_subsidy_usd", 0.0))
    grant_name = (subsidy.get("selected_charity") or {}).get("name") or "NGO subsidy"
    travel_cost = float(route.get("travel_cost_usd", 0.0))
    net_cost = total_care_package["net_cost"]

    summary = _generate_reasoning_with_gemini(hospital, route, total_care_package, subsidy)
    
    if not summary:
        specialty = hospital.get("specialty", "this condition")
        if grant_amount >= travel_cost and grant_amount > 0:
            summary = (
                f"Why this match? Our AI Agent carefully analyzed your medical data and specifically selected {hospital_name} because their specialists have verified expertise in {specialty}. "
                f"Furthermore, recognizing your budget constraints, our Financial Agent actively secured a ${grant_amount:,.0f} subsidy from {grant_name}. "
                f"This completely covers your flight from {origin_city}, bringing your total out-of-pocket estimated cost down to a manageable ${net_cost:,.0f}."
            )
        elif grant_amount > 0:
            summary = (
                f"Why this match? Our AI Agent carefully analyzed your medical data and specifically selected {hospital_name} because of their top-tier clinical team for {specialty}. "
                f"To further assist you, our Financial Agent identified a ${grant_amount:,.0f} subsidy from {grant_name} to help pay "
                f"for your trip from {origin_city}. This makes your total estimated cost around ${net_cost:,.0f}."
            )
        else:
            summary = (
                f"Why this match? Our AI Agent carefully analyzed your medical data and matched you with {hospital_name} due to their renowned expertise in treating {specialty}. "
                f"Our Logistics Agent also calculated a highly convenient {route.get('travel_duration_hours', 0):.1f}-hour journey from {origin_city}. "
                f"This keeps the total estimated cost of your treatment and travel around ${net_cost:,.0f}, perfectly balancing clinical quality with accessibility."
            )

    itinerary = StructuredItinerary(
        headline=f"Accessibility score {accessibility_score}/100 for {hospital_name}",
        summary=summary,
        origin_city=origin_city,
        destination_city=destination_city,
        destination_hospital=hospital_name,
        travel_mode=route.get("travel_mode", "Commercial Flight"),
        travel_duration_hours=float(route.get("travel_duration_hours", 0.0)),
        travel_cost_usd=travel_cost,
        grant_name=None if grant_amount <= 0 else grant_name,
        grant_amount_usd=grant_amount,
    )
    return _dump_model(itinerary)


def _default_clinical_score(package: Dict[str, Any]) -> float:
    specialist = package["specialist"]
    baseline = specialist.get("match_score")
    if baseline is None:
        baseline = max(55, 90 - ((specialist.get("semantic_rank", 1) - 1) * 10))
    return float(baseline) + _tier_bonus(specialist.get("tier"))


def _sort_packages(
    packages: List[Dict[str, Any]],
    preference: str,
    manual_override: bool,
) -> List[Dict[str, Any]]:
    if manual_override:
        return packages

    if preference == "lowest_net_cost":
        key_fn = lambda pkg: (
            pkg["total_care_package"]["net_cost"],
            -pkg["total_accessibility_score"],
            pkg["flight"]["travel_duration_hours"],
        )
    elif preference == "fastest_access":
        key_fn = lambda pkg: (
            pkg["flight"]["travel_duration_hours"],
            pkg["total_care_package"]["net_cost"],
            -pkg["total_accessibility_score"],
        )
    elif preference == "clinical_quality":
        key_fn = lambda pkg: (
            -_default_clinical_score(pkg),
            pkg["total_care_package"]["net_cost"],
            pkg["flight"]["travel_duration_hours"],
        )
    else:
        key_fn = lambda pkg: (
            -pkg["total_accessibility_score"],
            pkg["total_care_package"]["net_cost"],
            pkg["flight"]["travel_duration_hours"],
        )

    return sorted(packages, key=key_fn)


def orchestrate_packages(
    medical_data: Dict[str, Any],
    origin_country: str,
    budget_usd: float,
    currency: str = "USD",
    preferred_month: str = "Next Month",
    user_origin: Optional[str] = None,
    user_priority_preference: str = "balanced",
    manual_override: bool = False,
    rejected_hospitals: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    ChromaDB remains the source of truth for hospital retrieval.
    This orchestrator wraps those hits with logistics, charity, scoring, and itinerary metadata.
    """
    print(f"\n--- Starting Antigravity Orchestrator for {origin_country} ---")

    retrieval_mode = "semantic_raw" if manual_override else "default"
    normalized_origin = user_origin or origin_country
    resolved_origin_city = resolve_user_origin_city(normalized_origin)

    clinical_summary = generate_clinical_summary(medical_data)
    hospitals = match_hospitals(medical_data, retrieval_mode=retrieval_mode, top_n=6)

    rejected_set = {rejected_hospital.lower() for rejected_hospital in (rejected_hospitals or [])}
    if rejected_set:
        hospitals = [
            hospital_record
            for hospital_record in hospitals
            if hospital_record.get("hospital", "").lower() not in rejected_set
        ]
        print(f"[MEMORY]: Filtered out {len(rejected_hospitals)} rejected hospital(s). Remaining: {len(hospitals)}")

    def select_top_k_facilities(
        facilities: List[Dict[str, Any]],
        top_k: int = 3,
        entity_type: str = "Hospitals",
    ) -> List[Dict[str, Any]]:
        total_count = len(facilities)
        if total_count == 0:
            print(f"[{entity_type.upper()}]: Warning - No items found to select from.")
            return []
        if total_count < top_k:
            print(f"[{entity_type.upper()}]: Info - Requested top {top_k}, but only {total_count} available.")
        else:
            print(f"[{entity_type.upper()}]: Info - Selecting top {top_k} from {total_count} available.")
        return facilities[:top_k]

    hospitals = select_top_k_facilities(hospitals, top_k=3, entity_type="Hospitals")
    if not hospitals:
        return []

    travel_dates = calculate_travel_dates(preferred_month, clinical_summary["total_stay_days"])
    transport_requirements = get_transport_requirements(
        medical_data,
        origin=resolved_origin_city,
        destination="Malaysia",
    )
    route_cache = {
        hospital.get("id", hospital.get("hospital", f"route_{index}")): simulate_route_lookup(
            hospital.get("hospital_location", hospital.get("hospital", "")),
            normalized_origin,
        )
        for index, hospital in enumerate(hospitals, start=1)
    }
    representative_travel_cost = min(
        (route.get("travel_cost_usd", 0.0) for route in route_cache.values()),
        default=0.0,
    )
    charities = match_charities(
        medical_data,
        origin_country,
        budget_usd=budget_usd,
        estimated_cost_usd=clinical_summary["estimated_cost_usd"] + representative_travel_cost,
    )

    packages: List[Dict] = []
    for hospital in hospitals:
        route = route_cache[hospital.get("id", hospital.get("hospital"))]
        flight_bundle = get_flight_options(
            {
                **transport_requirements,
                "departure_date": travel_dates["arrival_date"],
                "adults": 2 if transport_requirements.get("medical_escort_needed") else 1,
                "max_offers": 3,
            },
            origin_country=origin_country,
            destination_airport=_destination_airport_for_hospital(hospital),
        )
        selected_flight = _normalize_selected_flight(flight_bundle, route)
        adjusted_base_cost = round(
            clinical_summary["estimated_cost_usd"] * _hospital_cost_multiplier(hospital.get("tier")),
            2,
        )
        subsidy = calculate_potential_subsidy(
            hospital=hospital,
            matched_charities=charities,
            budget_usd=budget_usd,
            base_medical_cost_usd=adjusted_base_cost,
            travel_cost_usd=selected_flight["travel_cost_usd"],
        )

        total_care_package = _dump_model(
            _build_total_care_package(
                base_medical_cost=adjusted_base_cost,
                grant_reduction=subsidy["grant_reduction_usd"],
                travel_cost=selected_flight["travel_cost_usd"],
                budget_usd=budget_usd,
            )
        )
        total_care_package["net_cost_local"] = round(convert_usd_to(total_care_package["net_cost"], currency), 2)
        total_care_package["net_cost_formatted"] = f"${total_care_package['net_cost']:,.0f} USD ({currency} {total_care_package['net_cost_local']:,.0f})"

        package_clinical_summary = dict(clinical_summary)
        package_clinical_summary["estimated_cost_usd"] = adjusted_base_cost
        package_clinical_summary["estimated_cost_local"] = round(convert_usd_to(adjusted_base_cost, currency), 2)
        package_clinical_summary["estimated_cost_formatted"] = (
            f"${adjusted_base_cost:,.0f} USD ({currency} {package_clinical_summary['estimated_cost_local']:,.0f})"
        )

        package_logistics = {
            **transport_requirements,
            "route_estimate": route,
            "flight_search": flight_bundle,
        }

        accessibility_score = _compute_accessibility_score(
            hospital=hospital,
            total_care_package=total_care_package,
            route=selected_flight,
            subsidy=subsidy,
            budget_usd=budget_usd,
        )
        structured_itinerary = _build_structured_itinerary(
            hospital=hospital,
            route=selected_flight,
            total_care_package=total_care_package,
            subsidy=subsidy,
            accessibility_score=accessibility_score,
        )

        preference_state = UserPriorityPreference(
            mode=user_priority_preference,
            manual_override=manual_override,
        )
        antigravity_state = AntigravityState(
            retrieval_strategy="raw_semantic" if manual_override else "financial_reranker",
            user_origin=resolved_origin_city,
            hospital_location=hospital.get("hospital_location", "Malaysia"),
            user_priority_preference=preference_state,
            total_care_package=TotalCarePackage(
                **{
                    key: total_care_package[key]
                    for key in (
                        "base_medical_cost",
                        "grant_reduction",
                        "travel_cost",
                        "net_cost",
                        "within_budget",
                    )
                }
            ),
            logistics=package_logistics,
            charity=subsidy.get("selected_charity"),
        )

        package_reasoning = structured_itinerary["summary"]
        if manual_override:
            package_reasoning += " Note: Manual Override is active. This result reflects the raw clinical search order from our database without secondary financial reranking."

        packages.append(
            {
                "package_id": f"PKG_{hospital.get('id', hospital.get('hospital', 'MATCH')).replace('-', '_')}",
                "package_type": "",
                "package_reasoning": package_reasoning,
                "specialist": hospital,
                "flight": selected_flight,
                "flight_logistics": package_logistics,
                "travel_dates": travel_dates,
                "clinical_summary": package_clinical_summary,
                "charity": subsidy.get("selected_charity"),
                "grant_analysis": subsidy,
                "total_care_package": total_care_package,
                "total_accessibility_score": accessibility_score,
                "structured_itinerary": structured_itinerary,
                "antigravity_state": _dump_model(antigravity_state),
            }
        )

    packages = _sort_packages(packages, user_priority_preference, manual_override)
    for index, package in enumerate(packages, start=1):
        package["package_type"] = _build_package_label(index, user_priority_preference, manual_override)

    print("--- Orchestration complete ---\n")
    return packages


def generate_single_package(
    hospital: Dict[str, Any],
    logistics_data: Dict[str, Any],
    flight: Optional[Dict[str, Any]],
    charity: Optional[Dict[str, Any]],
    origin_country: str,
    budget_usd: int,
    travel_dates: Optional[Dict[str, Any]] = None,
    clinical_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a final package payload for a user-selected itinerary.
    """
    route = flight or logistics_data.get("route_estimate") or simulate_route_lookup(
        hospital.get("hospital_location", hospital.get("hospital", "")),
        origin_country,
    )
    clinical_summary = clinical_summary or generate_clinical_summary(
        {"condition": hospital.get("specialty", "General Medicine")}
    )
    base_cost = float(clinical_summary.get("estimated_cost_usd", 0.0))

    matched_charities = [charity] if charity else []
    subsidy = calculate_potential_subsidy(
        hospital=hospital,
        matched_charities=matched_charities,
        budget_usd=budget_usd,
        base_medical_cost_usd=base_cost,
        travel_cost_usd=float(route.get("travel_cost_usd", 0.0)),
    )
    total_care_package = _dump_model(
        _build_total_care_package(
            base_medical_cost=base_cost,
            grant_reduction=subsidy["grant_reduction_usd"],
            travel_cost=float(route.get("travel_cost_usd", 0.0)),
            budget_usd=budget_usd,
        )
    )
    score = _compute_accessibility_score(hospital, total_care_package, route, subsidy, budget_usd)
    structured_itinerary = _build_structured_itinerary(hospital, route, total_care_package, subsidy, score)

    return {
        "package_id": "PKG_CUSTOM",
        "package_type": "User Selected",
        "package_reasoning": structured_itinerary["summary"],
        "specialist": hospital,
        "flight": route,
        "flight_logistics": logistics_data,
        "charity": subsidy.get("selected_charity"),
        "grant_analysis": subsidy,
        "travel_dates": travel_dates or {},
        "clinical_summary": clinical_summary,
        "total_care_package": total_care_package,
        "total_accessibility_score": score,
        "structured_itinerary": structured_itinerary,
    }
