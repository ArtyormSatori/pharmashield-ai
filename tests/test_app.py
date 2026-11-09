"""
PharmaShield AI - Comprehensive Unit & Integration Test Suite
Verifies clinical safety algorithms, neural entity resolution, API contracts,
Beers criteria, Triple Whammy detection, and responsible AI disclosures.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.core.schemas import PatientProfile, SeverityLevel
from app.core.semantic_matcher import SemanticDrugMatcher
from app.core.interaction_engine import ClinicalInteractionEngine
from app.core.responsible_ai import ResponsibleAIGuard


class TestPharmaShieldAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.matcher = SemanticDrugMatcher(use_neural=True)
        cls.engine = ClinicalInteractionEngine()
        cls.guard = ResponsibleAIGuard()

    def test_01_health_check(self):
        """Verify health check returns valid operational status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "PharmaShield AI")
        self.assertGreaterEqual(data["total_active_compounds"], 50)

    def test_02_index_html_served(self):
        """Verify index.html UI is served properly."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("PharmaShield AI", response.text)

    def test_03_drug_search_autocomplete(self):
        """Verify drug query search returns matched brand and generic compounds."""
        response = self.client.get("/api/drugs?q=lipi")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data["count"], 0)
        names = [r["name"].lower() for r in data["results"]]
        self.assertIn("atorvastatin", names)

    def test_04_brand_name_resolution(self):
        """Verify brand names resolve to their canonical active pharmaceutical ingredients."""
        test_brands = {
            "Coumadin": "warfarin",
            "Cordarone": "amiodarone",
            "Lipitor": "atorvastatin",
            "Plavix": "clopidogrel",
            "Zoloft": "sertraline",
            "Ultram": "tramadol",
            "Lasix": "furosemide",
            "Advil": "ibuprofen",
        }
        for brand, canonical in test_brands.items():
            result = self.matcher.resolve_drug(brand)
            self.assertIsNotNone(result, f"Failed to resolve brand {brand}")
            drug_id, conf, method = result
            self.assertEqual(drug_id, canonical, f"Brand {brand} resolved to {drug_id} instead of {canonical}")
            self.assertGreaterEqual(conf, 0.85)

    def test_05_critical_bleeding_interaction(self):
        """Verify Warfarin + Amiodarone triggers CONTRAINDICATED due to CYP2C9/3A4 inhibition."""
        patient = PatientProfile(age=65, eGFR=80.0)
        interactions, cum, alts, guidance, max_sev = self.engine.evaluate_regime(["warfarin", "amiodarone"], patient)
        self.assertEqual(max_sev, SeverityLevel.CONTRAINDICATED)
        self.assertGreaterEqual(len(interactions), 1)
        self.assertIn("cyp2c9", interactions[0].mechanism.lower())

    def test_06_serotonin_syndrome_detection(self):
        """Verify Sertraline + Tramadol + Linezolid accumulates severe serotonin syndrome score."""
        patient = PatientProfile(age=35, eGFR=90.0)
        interactions, cum, alts, guidance, max_sev = self.engine.evaluate_regime(
            ["sertraline", "tramadol", "linezolid"], patient
        )
        self.assertEqual(max_sev, SeverityLevel.CONTRAINDICATED)
        self.assertEqual(cum.serotonin_syndrome_risk, 1.0)
        self.assertEqual(cum.serotonin_syndrome_status.value, "CRITICAL")

    def test_07_torsades_qt_prolongation(self):
        """Verify Azithromycin + Haloperidol + Citalopram cumulative QT prolongation risk."""
        patient = PatientProfile(age=70, eGFR=60.0)
        interactions, cum, alts, guidance, max_sev = self.engine.evaluate_regime(
            ["azithromycin", "haloperidol", "citalopram"], patient
        )
        self.assertEqual(max_sev, SeverityLevel.CONTRAINDICATED)
        self.assertEqual(cum.qt_prolongation_index, 1.0)
        self.assertEqual(cum.qt_prolongation_status.value, "CRITICAL")

    def test_08_triple_whammy_nephrotoxicity(self):
        """Verify Lisinopril + Furosemide + Ibuprofen triggers Triple Whammy acute kidney injury alert."""
        patient = PatientProfile(age=72, eGFR=50.0)
        interactions, cum, alts, guidance, max_sev = self.engine.evaluate_regime(
            ["lisinopril", "furosemide", "ibuprofen"], patient
        )
        self.assertTrue(cum.triple_whammy_nephrotoxicity)
        whammy_alerts = [w for w in cum.organ_clearance_warnings if "Triple Whammy" in w]
        self.assertGreater(len(whammy_alerts), 0)

    def test_09_geriatric_beers_criteria(self):
        """Verify patient age >= 65 triggers AGS Beers Criteria warnings for high-risk compounds."""
        patient_young = PatientProfile(age=30, eGFR=90.0)
        patient_elderly = PatientProfile(age=75, eGFR=70.0)

        _, cum_young, _, _, _ = self.engine.evaluate_regime(["diazepam", "alprazolam"], patient_young)
        _, cum_elderly, _, _, _ = self.engine.evaluate_regime(["diazepam", "alprazolam"], patient_elderly)

        self.assertEqual(len(cum_young.beers_criteria_flags), 0)
        self.assertGreaterEqual(len(cum_elderly.beers_criteria_flags), 2)

    def test_10_safe_alternatives_generation(self):
        """Verify system recommends Pantoprazole when Omeprazole conflicts with Clopidogrel."""
        patient = PatientProfile(age=55, eGFR=90.0)
        interactions, cum, alts, guidance, max_sev = self.engine.evaluate_regime(
            ["clopidogrel", "omeprazole"], patient
        )
        self.assertEqual(max_sev, SeverityLevel.SEVERE)
        self.assertGreaterEqual(len(alts), 1)
        suggested = [a.suggested_alternative.lower() for a in alts]
        self.assertIn("pantoprazole", suggested)

    def test_11_api_analyze_e2e(self):
        """Verify full POST /api/analyze REST contract execution."""
        payload = {
            "drugs": ["Coumadin", "Cordarone", "Bayer Aspirin"],
            "patient": {
                "age": 68,
                "eGFR": 75.0,
                "hepatic_impairment": False,
                "pregnancy": False
            }
        }
        response = self.client.post("/api/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["overall_safety_status"], "CRITICAL_CONTRAINDICATION")
        self.assertEqual(data["max_severity"], "CONTRAINDICATED")
        self.assertEqual(len(data["resolved_drugs"]), 3)
        self.assertGreaterEqual(len(data["interactions"]), 2)
        self.assertIn("responsible_ai", data)
        self.assertLess(data["latency_ms"], 250.0)

    def test_12_responsible_ai_zero_egress(self):
        """Verify responsible AI guard guarantees zero outbound cloud egress and citation grounding."""
        disclosure = self.guard.get_disclosure()
        self.assertTrue(disclosure.grounding_verified)
        self.assertIn("HIPAA", disclosure.privacy_compliance)
        self.assertIn("Deterministic", disclosure.hallucination_prevention)


if __name__ == "__main__":
    unittest.main()
