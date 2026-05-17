import unittest
import sys
import types
from unittest.mock import patch

chromadb_stub = types.ModuleType("chromadb")
chromadb_stub.PersistentClient = object
chromadb_stub.Collection = object
chromadb_utils_stub = types.ModuleType("chromadb.utils")
embedding_stub = types.ModuleType("chromadb.utils.embedding_functions")


class _DummyEmbeddingFunction:
    def __call__(self, *args, **kwargs):
        return []


embedding_stub.DefaultEmbeddingFunction = _DummyEmbeddingFunction
chromadb_utils_stub.embedding_functions = embedding_stub

sys.modules.setdefault("chromadb", chromadb_stub)
sys.modules.setdefault("chromadb.utils", chromadb_utils_stub)
sys.modules.setdefault("chromadb.utils.embedding_functions", embedding_stub)
sys.modules.setdefault("ollama", types.ModuleType("ollama"))

requests_stub = types.ModuleType("requests")
requests_stub.get = lambda *args, **kwargs: None
requests_stub.Session = type("Session", (), {"__init__": lambda self, *args, **kwargs: None, "request": lambda *args, **kwargs: None, "mount": lambda *args, **kwargs: None, "close": lambda *args, **kwargs: None, "headers": {}})
sys.modules.setdefault("requests", requests_stub)

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)

from agents.orchestrator import orchestrate_packages


class OrchestratorPipelineTests(unittest.TestCase):
    def setUp(self):
        self.medical_data = {
            "condition": "Cardiology heart surgery",
            "severity": "High",
            "urgency": "Urgent",
            "summary": "Patient needs tertiary cardiac intervention.",
        }

    @patch("agents.orchestrator.calculate_travel_dates", return_value={"arrival_date": "2026-08-15", "departure_date": "2026-08-25"})
    @patch("agents.orchestrator.get_transport_requirements", return_value={"mobility_level": "Ambulatory", "required_equipment": [], "medical_escort_needed": False})
    @patch("agents.orchestrator.match_charities", return_value=[{"name": "ASEAN Heart Fund", "max_coverage_usd": 450, "organization": "ASEAN NGO"}])
    @patch("agents.orchestrator.generate_clinical_summary", return_value={"diagnosis": "Cardiology heart surgery", "procedure": "Cardiac Procedure", "estimated_cost_usd": 2000, "total_stay_days": 10, "professional_summary": "Summary"})
    @patch("agents.orchestrator.simulate_route_lookup")
    @patch("agents.orchestrator.match_hospitals")
    def test_manual_override_preserves_raw_semantic_order(
        self,
        mock_match_hospitals,
        mock_simulate_route_lookup,
        *_mocks,
    ):
        mock_match_hospitals.return_value = [
            {
                "id": "doc_1",
                "hospital": "Penang Adventist Hospital",
                "name": "Dr. First",
                "specialty": "Cardiology",
                "tier": "Standard Private",
                "hospital_location": "Penang, Malaysia",
                "grant_availability": "High",
                "hospital_metadata": {"Grant Availability": "High", "grant_cap_usd": 450},
                "semantic_rank": 1,
            },
            {
                "id": "doc_2",
                "hospital": "Gleneagles Kuala Lumpur",
                "name": "Dr. Second",
                "specialty": "Cardiology",
                "tier": "Premium Private",
                "hospital_location": "Kuala Lumpur, Malaysia",
                "grant_availability": "Low",
                "hospital_metadata": {"Grant Availability": "Low", "grant_cap_usd": 180},
                "semantic_rank": 2,
            },
        ]
        mock_simulate_route_lookup.side_effect = [
            {
                "origin_city": "Jakarta",
                "destination_city": "Penang",
                "route": "Jakarta to Penang",
                "travel_mode": "Commercial Flight",
                "travel_cost_usd": 160.0,
                "travel_duration_hours": 2.8,
            },
            {
                "origin_city": "Jakarta",
                "destination_city": "Kuala Lumpur",
                "route": "Jakarta to Kuala Lumpur",
                "travel_mode": "Commercial Flight",
                "travel_cost_usd": 135.0,
                "travel_duration_hours": 2.2,
            },
        ]

        packages = orchestrate_packages(
            medical_data=self.medical_data,
            origin_country="Indonesia",
            budget_usd=2400,
            currency="USD",
            preferred_month="August 2026",
            user_priority_preference="lowest_net_cost",
            manual_override=True,
        )

        self.assertEqual(len(packages), 2)
        self.assertEqual(packages[0]["specialist"]["hospital"], "Penang Adventist Hospital")
        self.assertEqual(packages[0]["package_type"], "Semantic Match 1")
        self.assertEqual(packages[0]["antigravity_state"]["retrieval_strategy"], "raw_semantic")
        self.assertTrue("Manual Override is active" in packages[0]["package_reasoning"])

    @patch("agents.orchestrator.calculate_travel_dates", return_value={"arrival_date": "2026-08-15", "departure_date": "2026-08-25"})
    @patch("agents.orchestrator.get_transport_requirements", return_value={"mobility_level": "Ambulatory", "required_equipment": [], "medical_escort_needed": False})
    @patch("agents.orchestrator.match_charities", return_value=[{"name": "ASEAN Heart Fund", "max_coverage_usd": 450, "organization": "ASEAN NGO"}])
    @patch("agents.orchestrator.generate_clinical_summary", return_value={"diagnosis": "Cardiology heart surgery", "procedure": "Cardiac Procedure", "estimated_cost_usd": 2000, "total_stay_days": 10, "professional_summary": "Summary"})
    @patch("agents.orchestrator.simulate_route_lookup", return_value={"origin_city": "Jakarta", "destination_city": "Kuala Lumpur", "route": "Jakarta to Kuala Lumpur", "travel_mode": "Commercial Flight", "travel_cost_usd": 135.0, "travel_duration_hours": 2.2})
    @patch("agents.orchestrator.match_hospitals")
    def test_packages_include_total_care_package_and_itinerary(
        self,
        mock_match_hospitals,
        *_mocks,
    ):
        mock_match_hospitals.return_value = [
            {
                "id": "doc_1",
                "hospital": "Sunway Medical Centre",
                "name": "Dr. Accessible",
                "specialty": "Cardiology",
                "tier": "Standard Private",
                "hospital_location": "Kuala Lumpur, Malaysia",
                "grant_availability": "Medium",
                "hospital_metadata": {"Grant Availability": "Medium", "grant_cap_usd": 320},
                "match_score": 78,
            }
        ]

        packages = orchestrate_packages(
            medical_data=self.medical_data,
            origin_country="Indonesia",
            budget_usd=2600,
            currency="USD",
            preferred_month="August 2026",
            user_priority_preference="balanced",
            manual_override=False,
        )

        self.assertEqual(len(packages), 1)
        package = packages[0]
        self.assertIn("total_care_package", package)
        self.assertIn("structured_itinerary", package)
        self.assertIn("total_accessibility_score", package)
        self.assertGreater(package["grant_analysis"]["potential_subsidy_usd"], 0)
        self.assertLessEqual(package["total_care_package"]["net_cost"], 2600)
        self.assertEqual(package["antigravity_state"]["retriever_source"], "chromadb")


if __name__ == "__main__":
    unittest.main()
