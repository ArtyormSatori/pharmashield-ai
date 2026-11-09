"""
PharmaShield AI - Pydantic Data Models & Schemas
Clinical Prescription Safety & Drug-Drug Interaction Intelligence System
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    CONTRAINDICATED = "CONTRAINDICATED"
    SEVERE = "SEVERE"
    MODERATE = "MODERATE"
    MINOR = "MINOR"
    SAFE = "SAFE"


class RiskCategory(str, Enum):
    LOW = "LOW"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PatientProfile(BaseModel):
    age: int = Field(default=45, ge=0, le=125, description="Patient age in years")
    eGFR: Optional[float] = Field(default=90.0, ge=0.0, le=200.0, description="Estimated Glomerular Filtration Rate in mL/min/1.73m²")
    hepatic_impairment: bool = Field(default=False, description="Presence of liver dysfunction or cirrhosis")
    is_pregnant: bool = Field(default=False, description="Pregnancy status")
    allergies: List[str] = Field(default_factory=list, description="Known drug/substance allergies")


class DrugInput(BaseModel):
    name: str = Field(..., description="Generic name or brand name (e.g., 'Atorvastatin' or 'Lipitor')")
    dosage: Optional[str] = Field(default=None, description="Dosage and unit, e.g. '20mg'")
    route: Optional[str] = Field(default="oral", description="Route of administration: oral, iv, etc.")


class AnalyzeRequest(BaseModel):
    drugs: List[str] = Field(..., min_length=1, description="List of drug names or brand names")
    patient: Optional[PatientProfile] = Field(default_factory=PatientProfile)


class InteractionAlert(BaseModel):
    drug_a: str
    drug_b: str
    severity: SeverityLevel
    mechanism_type: str  # Pharmacokinetic (CYP450), Pharmacodynamic (Synergistic/Antagonistic), Renal, etc.
    mechanism: str
    clinical_effect: str
    clinical_management: str
    evidence_level: str  # e.g., "FDA Black Box Warning", "Clinical Trial Cohort", "Established Pharmacological Guideline"
    evidence_citations: List[str] = Field(default_factory=list)


class CumulativeRiskReport(BaseModel):
    serotonin_syndrome_risk: float = Field(..., ge=0.0, le=1.0)
    serotonin_syndrome_status: RiskCategory
    serotonin_contributing_drugs: List[str]

    qt_prolongation_index: float = Field(..., ge=0.0, le=1.0)
    qt_prolongation_status: RiskCategory
    qt_contributing_drugs: List[str]

    bleeding_risk_score: float = Field(..., ge=0.0, le=1.0)
    bleeding_risk_status: RiskCategory
    bleeding_contributing_drugs: List[str]

    triple_whammy_nephrotoxicity: bool = Field(default=False, description="Concomitant ACEi/ARB + Diuretic + NSAID causing acute kidney failure")
    triple_whammy_drugs: List[str] = Field(default_factory=list)

    cns_depression_risk: float = Field(..., ge=0.0, le=1.0)
    cns_depression_status: RiskCategory
    cns_contributing_drugs: List[str]

    beers_criteria_flags: List[str] = Field(default_factory=list, description="Potentially inappropriate medications for geriatric patients (age >= 65)")
    organ_clearance_warnings: List[str] = Field(default_factory=list, description="Dosage and safety alerts based on eGFR and hepatic status")


class AlternativeRecommendation(BaseModel):
    problematic_drug: str
    suggested_alternative: str
    therapeutic_class: str
    rationale: str
    safety_advantage: str


class ResponsibleAIDisclosure(BaseModel):
    model_architecture: str = "Hybrid Neural Semantic Matcher (BGE-small-en-v1.5) + Deterministic Clinical Knowledge Graph"
    grounding_verified: bool = True
    hallucination_prevention: str = "100% Deterministically Grounded in Curated Clinical Pharmacology Guidelines; No Synthetic Black-Box Hallucinations"
    privacy_compliance: str = "Zero Outbound Data Egress; All Vector Embeddings and Pharmacology Inference Run 100% Locally"
    clinical_disclaimer: str = "PharmaShield AI is an intelligent clinical decision support tool for healthcare professionals and educational research. It does not replace certified physician or clinical pharmacist judgment."


class AnalysisResponse(BaseModel):
    resolved_drugs: List[Dict[str, Any]]
    patient_profile: PatientProfile
    overall_safety_status: str  # "SAFE", "CAUTION", "HIGH_RISK", "CRITICAL_CONTRAINDICATION"
    max_severity: SeverityLevel
    interactions: List[InteractionAlert]
    cumulative_risks: CumulativeRiskReport
    alternatives: List[AlternativeRecommendation]
    patient_friendly_guidance: List[str]
    responsible_ai: ResponsibleAIDisclosure
    latency_ms: float
