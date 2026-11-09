#!/usr/bin/env python3
"""
PharmaShield AI - Clinical Demonstration CLI
Executes real clinical cases demonstrating neural entity resolution,
pairwise interaction analysis, cumulative toxicity indices, and safer alternatives.
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.schemas import PatientProfile, SeverityLevel
from app.core.semantic_matcher import SemanticDrugMatcher
from app.core.interaction_engine import ClinicalInteractionEngine
from app.core.responsible_ai import ResponsibleAIGuard
from app.core.pharmacology_db import DRUGS_DB


def run_case(case_num, title, drugs, patient, matcher, engine):
    print("\n" + "=" * 70)
    print(f" CLINICAL CASE #{case_num}: {title.upper()}")
    print("=" * 70)
    print(f"Prescribed Regimen: {', '.join(drugs)}")
    print(f"Patient Profile:    Age {patient.age}y | eGFR: {patient.eGFR} mL/min | Hepatic: {patient.hepatic_impairment} | Pregnant: {patient.is_pregnant}")
    print("-" * 70)

    t0 = time.perf_counter()

    # Step 1: Neural Entity Resolution
    canonical_ids = []
    print("1. NEURAL ENTITY RESOLUTION:")
    for drug_q in drugs:
        match = matcher.resolve_drug(drug_q)
        if match:
            drug_id, conf, method = match
            canonical_ids.append(drug_id)
            drug_info = DRUGS_DB[drug_id]
            print(f"   • Query '{drug_q}' ➔ {drug_info['name']} (Canonical ID: {drug_id})")
            print(f"     Class: {drug_info['class']} | Method: {method} (Confidence: {conf*100:.1f}%)")
        else:
            print(f"   • Query '{drug_q}' ➔ [UNRESOLVED]")

    # Step 2: Clinical Evaluation
    interactions, cumulative, alternatives, guidance, max_sev = engine.evaluate_regime(canonical_ids, patient)
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0

    print(f"\n2. SAFETY DETERMINATION: [{max_sev.value}] (Evaluated in {latency_ms:.2f} ms)")

    # Step 3: Pairwise Alerts
    if interactions:
        print(f"\n3. PAIRWISE INTERACTIONS DETECTED ({len(interactions)}):")
        for alert in interactions:
            print(f"   [{alert.severity.value}] {alert.drug_a} ⟷ {alert.drug_b}")
            print(f"       Mechanism:  {alert.mechanism_type} — {alert.mechanism}")
            print(f"       Effect:     {alert.clinical_effect}")
            print(f"       Management: {alert.clinical_management}")
            print(f"       Citations:  {', '.join(alert.evidence_citations)}")
    else:
        print("\n3. PAIRWISE INTERACTIONS: None detected (Safe combination).")

    # Step 4: Cumulative Polypharmacy Indices
    print("\n4. CUMULATIVE MULTI-DRUG TOXICITY INDICES:")
    print(f"   • Serotonin Syndrome Index:  {cumulative.serotonin_syndrome_risk:.2f} [{cumulative.serotonin_syndrome_status.value}]")
    print(f"   • QT Prolongation Arrhythmia: {cumulative.qt_prolongation_index:.2f} [{cumulative.qt_prolongation_status.value}]")
    print(f"   • Bleeding / Hemorrhage:      {cumulative.bleeding_risk_score:.2f} [{cumulative.bleeding_risk_status.value}]")
    print(f"   • CNS / Respiratory Sedation: {cumulative.cns_depression_risk:.2f} [{cumulative.cns_depression_status.value}]")
    if cumulative.triple_whammy_nephrotoxicity:
        print(f"   🚨 TRIPLE WHAMMY ALERT: Acute Kidney Injury Risk across ({', '.join(cumulative.triple_whammy_drugs)})")

    # Step 5: Safer Alternative Suggestions
    if alternatives:
        print("\n5. EVIDENCE-BASED SAFER ALTERNATIVES:")
        for alt in alternatives:
            print(f"   ➔ Substitute {alt.problematic_drug.upper()} with {alt.suggested_alternative.upper()} ({alt.therapeutic_class})")
            print(f"      Rationale: {alt.rationale}")
            print(f"      Advantage: {alt.safety_advantage}")

    # Step 6: Patient Guidance
    if guidance:
        print("\n6. PATIENT-FRIENDLY ACTIONABLE GUIDANCE:")
        for g in guidance:
            print(f"   {g}")


def main():
    print("=" * 70)
    print("      PHARMASHIELD AI - CLINICAL SAFETY DEMONSTRATION")
    print("      Zero-Cloud Egress Clinical Decision Support Engine")
    print("=" * 70)

    matcher = SemanticDrugMatcher(use_neural=True)
    engine = ClinicalInteractionEngine()

    cases = [
        (
            1,
            "Fatal Anticoagulation Bleed (CYP2C9 Blockade + Synergy)",
            ["Coumadin", "Cordarone", "Bayer Aspirin"],
            PatientProfile(age=68, eGFR=75.0)
        ),
        (
            2,
            "Lethal Serotonin Storm (Triple Serotonergic Polypharmacy)",
            ["Zoloft", "Ultram", "Zyvox"],
            PatientProfile(age=38, eGFR=95.0)
        ),
        (
            3,
            "Arrhythmogenic Torsades de Pointes (QTc Triad)",
            ["Z-Pak", "Haldol", "Celexa"],
            PatientProfile(age=72, eGFR=55.0)
        ),
        (
            4,
            "Geriatric 'Triple Whammy' Acute Kidney Injury",
            ["Lisinopril", "Lasix", "Advil"],
            PatientProfile(age=74, eGFR=45.0)
        ),
        (
            5,
            "Cardiometabolic Safe Regimen (Compatible Therapy)",
            ["Lipitor", "Glucophage", "Prinivil"],
            PatientProfile(age=52, eGFR=90.0)
        ),
    ]

    for c_num, title, drugs, patient in cases:
        run_case(c_num, title, drugs, patient, matcher, engine)

    print("\n" + "=" * 70)
    print(" ALL CLINICAL DEMONSTRATION CASES EVALUATED SUCCESSFULLY")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
